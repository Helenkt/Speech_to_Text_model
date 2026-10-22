from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.config import Settings
from app.database import database
from app.services.transcription_store import TranscriptionError, transcription_context, transcription_attempt_status
from app.services.audio_lifecycle import audio_exists, safe_audio_path, drain_audio_deletions
from app.services.exam_policy import admit_recording


log = logging.getLogger(__name__)
TERMINAL = {"completed", "failed", "cancelled"}


class SpeechJobError(ValueError):
    def __init__(self, message: str, status: int = 409, retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class JobCancelled(Exception):
    pass


class SpeechJobs:
    """One bounded local inference lane; SQLite retains attempts across client failures."""

    def __init__(self, settings: Settings, processor: Callable[..., Awaitable[dict]]):
        self.settings = settings
        self.processor = processor
        self.owner = str(uuid.uuid4())
        self.task: asyncio.Task | None = None
        self.stopping = False
        self.wake = asyncio.Event()

    def audio_path(self, job: dict) -> Path:
        base = (self.settings.audio_storage_dir or self.settings.database_path.parent / "audio").resolve()
        try:
            path = safe_audio_path(base, job["audio_path"])
        except (ValueError, OSError):
            raise SpeechJobError("Không tìm thấy bản ghi đã lưu", 409) from None
        if not path.is_file():
            raise SpeechJobError("Không tìm thấy bản ghi đã lưu", 409)
        return path

    def _owned(self, job_id: str, user_id: int) -> dict:
        with database(self.settings.database_path) as connection:
            row = connection.execute("SELECT * FROM speech_jobs WHERE job_id = ? AND user_id = ?",
                                     (job_id, user_id)).fetchone()
        if not row:
            raise SpeechJobError("Không tìm thấy tác vụ ghi âm", 404)
        return dict(row)

    def status(self, job_id: str, user_id: int) -> dict:
        job = self._owned(job_id, user_id)
        available = audio_exists(self.settings.audio_storage_dir or self.settings.database_path.parent / "audio", job["audio_path"])
        result = json.loads(job["result_json"]) if job["state"] == "completed" and job["result_json"] else None
        if result and result.get("transcription_id"):
            attempt = transcription_attempt_status(self.settings.database_path, transcription_id=result["transcription_id"])
            result.update(attempt=attempt, answer_stage=attempt["stage"],
                          requires_confirmation=attempt["stage"] == "draft", transcript_editable=False)
        return {key: job[key] for key in ("job_id", "session_id", "question_uid", "state", "stage", "attempts",
                "retryable", "cancel_requested", "error", "error_status", "created_at", "updated_at")} | {
            "audio_saved": available,
            "audio_status": "available" if available else "missing",
            "audio_warning": None if available else "audio_missing",
            "result": result,
            "confidence_is_accuracy": False,
            "retryable": bool(available and job["retryable"] and job["attempts"] < 3),
        }

    def create(self, *, user_id: int, session_id: str, request_key: str, content: bytes,
               filename: str, mime_type: str | None, ambient_noise_dbfs: float | None,
               retry_reason: str | None) -> dict:
        try:
            uuid.UUID(request_key)
        except (ValueError, TypeError, AttributeError):
            raise SpeechJobError("Mã lượt ghi âm phải là UUID", 422) from None
        sha = hashlib.sha256(content).hexdigest()
        created_file = None
        try:
            with database(self.settings.database_path) as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute("SELECT * FROM speech_jobs WHERE user_id = ? AND request_key = ?",
                                              (user_id, request_key)).fetchone()
                if existing:
                    if existing["session_id"] != session_id or existing["audio_sha256"] != sha:
                        raise SpeechJobError("Mã lượt ghi âm đã được dùng cho nội dung khác")
                    job_id = existing["job_id"]
                else:
                    context = transcription_context(self.settings.database_path, session_id=session_id, user_id=user_id)
                    sequence = connection.execute("SELECT answered_count FROM interview_sessions WHERE session_id = ?",
                                                  (session_id,)).fetchone()[0] + 1
                    pending = connection.execute("SELECT COUNT(*) FROM speech_jobs WHERE user_id = ? AND state IN ('queued', 'processing')",
                                                 (user_id,)).fetchone()[0]
                    if pending >= 2:
                        raise SpeechJobError("Đang có bản ghi chờ xử lý; hãy chờ hoặc hủy lượt trước", 429, True)
                    job_id = str(uuid.uuid4())
                    extension = Path(filename).suffix.lower()
                    if extension not in {".wav", ".webm", ".m4a", ".mp3", ".mp4", ".flac", ".ogg"}:
                        extension = ".webm"
                    base = (self.settings.audio_storage_dir or self.settings.database_path.parent / "audio").resolve()
                    path = (base / session_id / f"attempt-{job_id}{extension}").resolve()
                    if not path.is_relative_to(base):
                        raise SpeechJobError("Đường dẫn bản ghi không hợp lệ", 422)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    created_file = path
                    path.write_bytes(content)
                    session = connection.execute("SELECT * FROM interview_sessions WHERE session_id=?", (session_id,)).fetchone()
                    try:
                        context["admission"] = admit_recording(connection, session)
                    except ValueError as exc:
                        raise TranscriptionError(str(exc)) from exc
                    connection.execute("""INSERT INTO speech_jobs
                        (job_id, request_key, user_id, session_id, question_uid, sequence_number, context_json,
                         audio_path, audio_sha256, audio_size, audio_mime_type, ambient_noise_dbfs, retry_reason,
                         created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                        (job_id, request_key, user_id, session_id, context["question_uid"], sequence, json.dumps(context, ensure_ascii=False),
                         path.relative_to(base).as_posix(), sha, len(content), mime_type, ambient_noise_dbfs, retry_reason))
        except Exception:
            if created_file:
                created_file.unlink(missing_ok=True)
            raise
        self.wake.set()
        return self.status(job_id, user_id)

    def retry(self, job_id: str, user_id: int) -> dict:
        job = self._owned(job_id, user_id)
        self.audio_path(job)
        context = transcription_context(self.settings.database_path, session_id=job["session_id"], user_id=user_id, received_job_id=job_id)
        if context["question_uid"] != job["question_uid"]:
            raise SpeechJobError("Câu hỏi đã thay đổi; không thể xử lý lại lượt này")
        with database(self.settings.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            latest = connection.execute("SELECT job_id FROM speech_jobs WHERE session_id=? AND question_uid=? ORDER BY rowid DESC LIMIT 1",
                                        (job["session_id"], job["question_uid"])).fetchone()
            if latest[0] != job_id:
                raise SpeechJobError("Đã có lượt ghi âm mới hơn; không xử lý lại lượt cũ")
            changed = connection.execute("""UPDATE speech_jobs SET state='queued', stage='queued', error=NULL,
                error_status=NULL, cancel_requested=0, retryable=0, updated_at=CURRENT_TIMESTAMP
                WHERE job_id=? AND user_id=? AND state='failed' AND retryable=1 AND attempts<3""", (job_id, user_id)).rowcount
            if not changed:
                raise SpeechJobError("Lượt này không thể thử lại; hãy ghi âm lại hoặc liên hệ giảng viên")
        self.wake.set()
        return self.status(job_id, user_id)

    def cancel(self, job_id: str, user_id: int) -> dict:
        job = self._owned(job_id, user_id)
        if job["state"] == "processing" and job["stage"] == "saving":
            raise SpeechJobError("Kết quả đang được lưu; không thể hủy ở bước này")
        with database(self.settings.database_path) as connection:
            connection.execute("""UPDATE speech_jobs SET cancel_requested=1,
                state=CASE WHEN state='queued' THEN 'cancelled' ELSE state END,
                stage=CASE WHEN state='queued' THEN 'cancelled' ELSE stage END, updated_at=CURRENT_TIMESTAMP
                WHERE job_id=? AND user_id=? AND state IN ('queued','processing') AND stage <> 'saving'""", (job_id, user_id))
        return self.status(job_id, user_id)

    def claim(self) -> dict | None:
        with database(self.settings.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("""UPDATE speech_jobs SET state='failed', stage='interrupted', retryable=1,
                error='Tác vụ bị gián đoạn; bản ghi vẫn được giữ để xử lý lại', error_status=503
                WHERE state='processing' AND lease_until < ?""", (time.time(),))
            if connection.execute("SELECT 1 FROM speech_jobs WHERE state='processing' LIMIT 1").fetchone():
                return None
            row = connection.execute("SELECT * FROM speech_jobs WHERE state='queued' ORDER BY created_at, rowid LIMIT 1").fetchone()
            if not row:
                return None
            connection.execute("""UPDATE speech_jobs SET state='processing', stage='transcribing', attempts=attempts+1,
                worker_id=?, lease_until=?, updated_at=CURRENT_TIMESTAMP WHERE job_id=?""",
                (self.owner, time.time() + 30, row["job_id"]))
            return {**dict(row), "worker_id": self.owner}

    def progress(self, job: dict, stage: str) -> None:
        with database(self.settings.database_path) as connection:
            row = connection.execute("SELECT state, worker_id, cancel_requested FROM speech_jobs WHERE job_id=?", (job["job_id"],)).fetchone()
            if not row or row["cancel_requested"] or row["state"] != "processing" or row["worker_id"] != self.owner:
                raise JobCancelled()
            connection.execute("UPDATE speech_jobs SET stage=?, lease_until=?, updated_at=CURRENT_TIMESTAMP WHERE job_id=?",
                               (stage, time.time() + 30, job["job_id"]))

    async def heartbeat(self, job: dict):
        while True:
            await asyncio.sleep(5)
            with database(self.settings.database_path) as connection:
                connection.execute("UPDATE speech_jobs SET lease_until=? WHERE job_id=? AND worker_id=? AND state='processing'",
                                   (time.time() + 30, job["job_id"], self.owner))

    async def run_once(self) -> bool:
        job = self.claim()
        if not job:
            return False
        heartbeat = asyncio.create_task(self.heartbeat(job))
        state, result, error, status, retryable = "completed", None, None, None, False
        try:
            result = await self.processor(job, lambda stage: self.progress(job, stage))
            self.progress(job, "saving")
        except JobCancelled:
            state = "cancelled"
        except SpeechJobError as exc:
            state, error, status, retryable = "failed", str(exc), exc.status, exc.retryable
        except TranscriptionError as exc:
            state, error, status = "failed", str(exc), 409
        except Exception:
            log.exception("Speech job failed: %s", job["job_id"])
            state, error, status, retryable = "failed", "Xử lý giọng nói bị lỗi; bản ghi đã lưu, có thể thử lại", 503, True
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
        with database(self.settings.database_path) as connection:
            connection.execute("""UPDATE speech_jobs SET state=?, stage=?, result_json=?, error=?, error_status=?,
                retryable=?, lease_until=NULL, updated_at=CURRENT_TIMESTAMP
                WHERE job_id=? AND worker_id=? AND state='processing'""",
                (state, state, json.dumps(result, ensure_ascii=False, allow_nan=False) if result is not None else None,
                 error, status, int(retryable), job["job_id"], self.owner))
        return True

    async def run(self):
        last_cleanup = 0.0
        while not self.stopping:
            try:
                if time.monotonic() - last_cleanup >= 5:
                    await asyncio.to_thread(drain_audio_deletions, self.settings.database_path)
                    last_cleanup = time.monotonic()
                if await self.run_once():
                    continue
                self.wake.clear()
                try:
                    await asyncio.wait_for(self.wake.wait(), timeout=0.5)
                except asyncio.TimeoutError:
                    pass
            except Exception:
                log.exception("Speech queue worker error")
                await asyncio.sleep(0.5)

    def start(self):
        self.stopping = False
        self.task = asyncio.create_task(self.run())

    async def stop(self):
        self.stopping = True
        self.wake.set()
        if self.task:
            await self.task
