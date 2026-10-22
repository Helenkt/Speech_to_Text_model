"""Session-triggered STT preparation sharing the application's inference lane."""
from __future__ import annotations

import asyncio
import time
import functools
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool

import httpx

from app.services import speech_to_text as speech
from app.services.resource_policy import canonical_ollama_name, detect_resource_policy, ollama_request_resources


def release_speech():
    with speech._INFERENCE_LOCK:
        speech._clear_loaded_model()


def release_transformer():
    from app.services.rubric_transformer import release_transformer as release
    release()


def prepare_speech(settings):
    if not settings.whisper_download_root.exists():
        return "missing"
    with speech._INFERENCE_LOCK:
        started = time.monotonic()
        model = speech._get_model(settings, local_only=True)
        model_at = time.monotonic()
        import numpy as np
        from faster_whisper.vad import get_vad_model
        get_vad_model()
        vad_at = time.monotonic()
        segments, _ = model.transcribe(np.zeros(16000, dtype=np.float32), language="vi",
                                      beam_size=1, vad_filter=True, condition_on_previous_text=False)
        list(segments)
        segments, _ = model.transcribe(np.zeros(16000, dtype=np.float32), language="vi",
                                      beam_size=1, vad_filter=False, condition_on_previous_text=False)
        list(segments)
        speech._write_ready_marker(settings)
    return {"state": "ready", "purpose": "candidate_answer", "model": speech._MODEL_KEY[0] if speech._MODEL_KEY else settings.whisper_model,
        "timings": {"model_seconds": round(model_at - started, 3),
        "vad_seconds": round(vad_at - model_at, 3), "decode_seconds": round(time.monotonic() - vad_at, 3)}}


class RuntimeReadiness:
    def __init__(self, settings):
        self.settings = settings
        self.states = {"speech": {"state": "idle"}, "llm": {"state": "idle"}, "transformer": {"state": "idle"}}
        self.speech_task = None
        self.llm_task = None
        self.inference_lock = asyncio.Lock()
        self.preparation_lock = asyncio.Lock()
        self.staged = False
        self.pool = None
        self.resource_policy = None

    async def refresh_resources(self):
        self.resource_policy = await asyncio.to_thread(detect_resource_policy)
        self.staged = self.resource_policy.staged
        return self.resource_policy

    async def run_inference(self, operation, *args, **kwargs):
        call = functools.partial(operation, *args, **kwargs)
        try:
            if not self.settings.inference_worker:
                result = await asyncio.to_thread(call)
            else:
                if self.pool is None:
                    self.pool = ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("spawn"))
                result = await asyncio.get_running_loop().run_in_executor(self.pool, call)
            function = operation.func if isinstance(operation, functools.partial) else operation
            if function in {speech.transcribe_bytes, speech.transcribe_review_audio}:
                options = {**(operation.keywords if isinstance(operation, functools.partial) else {}), **kwargs}
                released = options.get("release_after") or result.get("model_cache_policy") == "released_after_request"
                self.states["speech"] = {"state": "released" if released else "ready",
                    "purpose": "teacher_review" if function is speech.transcribe_review_audio else "candidate_answer",
                    "model": result.get("model"), "runtime": result.get("runtime")}
            elif getattr(function, "__name__", "") == "evaluate_with_transformer":
                self.states["transformer"] = {"state": "ready"}
            return result
        except BrokenProcessPool as exc:
            pool, self.pool = self.pool, None
            if pool:
                pool.shutdown(wait=False, cancel_futures=True)
            self.states["speech"] = {"state": "unavailable", "reason": "worker_restarting"}
            self.states["transformer"] = {"state": "unavailable", "reason": "worker_restarting"}
            raise RuntimeError("Worker suy luận bị gián đoạn; bản ghi được giữ để thử lại") from exc

    def snapshot(self):
        result = {key: dict(value) for key, value in self.states.items()}
        if self.resource_policy:
            result["resources"] = self.resource_policy.snapshot()
        return result

    async def _release_speech_stage(self):
        if self.pool is not None or not self.settings.inference_worker:
            await self.run_inference(release_speech)
        self.states["speech"] = {"state": "released", "reason": "memory_budget"}
        if self.resource_policy.retire_worker_between_stages and self.pool is not None:
            pool, self.pool = self.pool, None
            await asyncio.to_thread(pool.shutdown, wait=True, cancel_futures=True)
            self.states["transformer"] = {"state": "released", "reason": "memory_budget"}

    async def _unload_owned_llms(self, models=None):
        owned = {canonical_ollama_name(model) for model in
                 (models if models is not None else (self.settings.ollama_model, self.settings.question_generation_model))}
        try:
            async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
                response = await client.get(self.settings.ollama_base_url + "/api/ps")
                response.raise_for_status()
                loaded = {name for item in response.json().get("models", [])
                          if isinstance(item, dict) and isinstance(name := item.get("name") or item.get("model"), str)}
                for model in sorted(name for name in loaded if canonical_ollama_name(name) in owned):
                    response = await client.post(self.settings.ollama_base_url + "/api/generate",
                        json={"model": model, "stream": False, "keep_alive": 0})
                    response.raise_for_status()
            if canonical_ollama_name(self.settings.ollama_model) in owned:
                self.states["llm"] = {"state": "released", "reason": "memory_budget"}
        except httpx.ConnectError:
            # STT remains usable when the local Ollama service is not running.
            self.states["llm"] = {"state": "unavailable"}
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            self.states["llm"] = {"state": "unavailable", "reason": "release_failed"}
            raise speech.SpeechToTextError(
                "Chưa giải phóng được bộ nhớ LLM. Bản ghi được giữ để thử lại."
            ) from exc

    async def _speech(self):
        self.states["speech"] = {"state": "loading"}
        started = time.monotonic()
        try:
            state = await self.run_inference(prepare_speech, self.settings)
            self.states["speech"] = {**(state if isinstance(state, dict) else {"state": state}),
                                     "seconds": round(time.monotonic() - started, 3)}
        except Exception as exc:
            self.states["speech"] = {"state": "unavailable", "error_type": type(exc).__name__}

    async def _llm(self, force=False):
        await self.refresh_resources()
        if not force and (self.staged or self.settings.defer_grading_until_finish):
            self.states["llm"] = {"state": "deferred", "reason":
                                  "memory_budget" if self.staged else "end_of_session"}
            return
        if self.staged or self.settings.defer_grading_until_finish:
            await self._release_speech_stage()
            await self._unload_owned_llms([self.settings.question_generation_model])
        self.states["llm"] = {"state": "loading"}
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(180), trust_env=False) as client:
                tags = await client.get(self.settings.ollama_base_url + "/api/tags", timeout=2)
                tags.raise_for_status()
                names = {item.get("name") for item in tags.json().get("models", [])}
                if self.settings.ollama_model not in names:
                    self.states["llm"] = {"state": "missing"}
                    return
                resources = ollama_request_resources(self.settings)
                response = await client.post(self.settings.ollama_base_url + "/api/generate", json={
                    "model": self.settings.ollama_model, "prompt": "OK", "stream": False,
                    **resources, "options": {**resources["options"], "num_predict": 1, "temperature": 0}})
                response.raise_for_status()
            self.states["llm"] = {"state": "ready", "seconds": round(time.monotonic() - started, 3)}
        except (httpx.HTTPError, ValueError, TypeError):
            self.states["llm"] = {"state": "unavailable"}

    def start(self):
        """Called only after a valid start/resume; never preloads an LLM."""
        if not self.settings.runtime_warmup:
            return
        if self.speech_task and not self.speech_task.done():
            return
        if (self.states["speech"]["state"] == "ready"
                and self.states["speech"].get("purpose") != "teacher_review"):
            return
        self.states["speech"] = {"state": "loading", "stage": "waiting_for_inference"}
        if self.states["llm"]["state"] == "idle":
            self.states["llm"] = {"state": "deferred", "reason": "on_demand"}
        self.speech_task = asyncio.create_task(self._prepare_session_speech())

    async def _prepare_session_speech(self):
        try:
            async with self.inference_lock:
                # A recording may have acquired the lane first and loaded the model.
                if (self.states["speech"]["state"] == "ready"
                        and self.states["speech"].get("purpose") != "teacher_review"):
                    return
                await self.before_speech()
                await self._speech()
        except Exception as exc:
            self.states["speech"] = {"state": "unavailable", "error_type": type(exc).__name__}

    async def ensure_llm(self):
        async with self.preparation_lock:
            await self._ensure_llm()

    async def _ensure_llm(self):
        if not (self.settings.runtime_warmup or self.settings.inference_worker) or self.settings.evaluator_mode not in {"auto", "ollama"}:
            return
        # Foreground operations already own inference_lock. A queued warmup may
        # need that lock, so awaiting it here would deadlock an early recording.
        if self.llm_task and not self.llm_task.done():
            await asyncio.shield(self.llm_task)
        await self.refresh_resources()
        if (self.staged or self.settings.defer_grading_until_finish) and self.states["speech"]["state"] != "released":
            await self._release_speech_stage()
        if self.states["llm"]["state"] == "ready":
            try:
                async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
                    response = await client.get(self.settings.ollama_base_url + "/api/ps")
                    response.raise_for_status()
                    if any(item.get("name", item.get("model")) == self.settings.ollama_model
                           for item in response.json().get("models", [])):
                        return
            except (httpx.HTTPError, ValueError, TypeError):
                pass
            self.states["llm"] = {"state": "idle"}
        if self.llm_task is None or self.llm_task.done():
            self.llm_task = asyncio.create_task(self._llm(force=True))
        await asyncio.shield(self.llm_task)

    async def before_speech(self):
        if not (self.settings.runtime_warmup or self.settings.inference_worker):
            return
        if self.llm_task and not self.llm_task.done():
            await asyncio.shield(self.llm_task)
        await self.refresh_resources()
        if self.staged or self.settings.defer_grading_until_finish:
            # Check Ollama itself: process-local readiness can be stale after restart.
            await self._unload_owned_llms()
            if self.pool is not None or not self.settings.inference_worker:
                await self.run_inference(release_transformer)
            self.states["transformer"] = {"state": "released", "reason": "memory_budget"}

    async def before_generation(self):
        if not (self.settings.runtime_warmup or self.settings.inference_worker):
            return
        if self.llm_task and not self.llm_task.done():
            await asyncio.shield(self.llm_task)
        await self.refresh_resources()
        if self.staged or self.settings.defer_grading_until_finish:
            await self._release_speech_stage()
            await self._unload_owned_llms()

    async def after_generation(self):
        if self.resource_policy and (self.resource_policy.staged or self.settings.defer_grading_until_finish):
            await self._unload_owned_llms([self.settings.question_generation_model])

    async def begin_grading(self):
        if not (self.settings.runtime_warmup or self.settings.inference_worker):
            return
        await self.refresh_resources()
        if self.staged or self.settings.defer_grading_until_finish:
            await self._release_speech_stage()

    async def end_preview(self):
        if self.resource_policy and self.resource_policy.staged and self.states["llm"]["state"] == "ready":
            try:
                await self._unload_owned_llms([self.settings.ollama_model])
            except speech.SpeechToTextError:
                return False
        return True

    async def end_grading(self):
        if self.resource_policy and (self.resource_policy.staged or self.settings.defer_grading_until_finish):
            await self._unload_owned_llms()
            if self.resource_policy.retire_worker_between_stages:
                await self._release_speech_stage()

    async def stop(self):
        tasks = [task for task in (self.speech_task, self.llm_task) if task]
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if self.pool:
            pool, self.pool = self.pool, None
            await asyncio.to_thread(pool.shutdown, wait=True, cancel_futures=True)
