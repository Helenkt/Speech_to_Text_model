import asyncio
import json
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import main
from app.database import database
from app.services import evaluator, runtime_readiness, session_grading
from app.services.account_importer import seed_demo_accounts
from app.services.interview_engine import interview_report
from app.services.question_importer import import_question_bank
from app.services.teacher_review import TeacherReviewError, list_review_queue, review_answer
from test_low_memory_sessions import answer_current, prepare


@pytest.fixture
def session_app(test_settings, monkeypatch):
    test_settings.runtime_warmup = True
    test_settings.defer_grading_until_finish = True
    calls, gate = [], threading.Event()

    def warm(_settings):
        calls.append("prepare_stt")
        gate.wait(3)
        return {"state": "ready", "model": "test-small"}

    async def unload(_self, *_args):
        calls.append("unload_owned_llms")

    async def unavailable(_settings):
        return {"running": False, "model_available": False}

    monkeypatch.setattr(runtime_readiness, "prepare_speech", warm)
    monkeypatch.setattr(runtime_readiness.RuntimeReadiness, "_unload_owned_llms", unload)
    monkeypatch.setattr(runtime_readiness, "release_transformer", lambda: None)
    monkeypatch.setattr(main, "ollama_status", unavailable)
    monkeypatch.setattr(main, "transformer_status", lambda *_: {"ready": False})
    monkeypatch.setattr(main, "stt_status", lambda *_: {"installed": True, "ready": False, "model": "test"})
    app = main.create_app(test_settings)
    with TestClient(app) as client:
        seed_demo_accounts(test_settings.database_path, test_settings.demo_data_dir)
        import_question_bank(test_settings.database_path, json.dumps([{
            "id": "start-policy", "language": "en", "subject": "DSA101", "difficulty": "Easy",
            "question": "What is a stack?", "reference_answer": "A stack is LIFO", "key_points": ["A stack is LIFO"],
        }]).encode(), filename="course.json")
        try:
            yield client, app, calls, gate
        finally:
            gate.set()


def login(client, teacher=False):
    response = client.post("/api/auth/login", json={
        "username": "teacher" if teacher else "candidate01",
        "password": "Teacher@123" if teacher else "Candidate@123"})
    assert response.status_code == 200
    return response.json()["user"]


def start(client):
    return client.post("/api/interviews/start", json={"language": "en", "subject": "DSA101",
        "question_count": 1, "starting_difficulty": "Easy"})


def wait_ready(client):
    for _ in range(100):
        if client.get("/api/runtime/readiness").json()["speech"]["state"] == "ready":
            return
        time.sleep(.02)
    raise AssertionError("STT preparation did not finish")


def test_opening_web_login_and_health_do_not_load_models(session_app):
    client, app, calls, _ = session_app
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/api/health").status_code == 200
    assert start(client).status_code == 401
    login(client)
    assert client.get("/api/questions/summary").status_code == 200
    assert client.get("/api/runtime/readiness").json()["speech"]["state"] == "idle"
    assert app.state.readiness.speech_task is None
    assert app.state.readiness.llm_task is None
    assert app.state.readiness.pool is None
    assert calls == []


def test_invalid_starts_and_resume_do_not_prepare_models(session_app):
    client, app, calls, _ = session_app
    login(client)
    assert client.post("/api/interviews/start", json={"language": "en", "subject": "NO-SUCH-SUBJECT",
        "question_count": 1}).status_code == 422
    assert client.post("/api/candidate/exams/NOEXAM/start").status_code == 409
    assert client.get("/api/interviews/missing/resume").status_code == 409
    assert app.state.readiness.speech_task is None
    assert calls == []


def test_start_prepares_in_background_and_reuses_ready_worker(session_app):
    client, app, calls, gate = session_app
    login(client)
    response = start(client)
    assert response.status_code == 201, response.text
    sid = response.json()["session_id"]
    assert response.json()["runtime_readiness"]["speech"]["state"] == "loading"
    first_task = app.state.readiness.speech_task
    assert not first_task.done()
    assert client.get(f"/api/interviews/{sid}/resume").status_code == 200
    assert app.state.readiness.speech_task is first_task
    gate.set()
    wait_ready(client)
    assert start(client).status_code == 201
    assert app.state.readiness.speech_task is first_task
    assert calls.count("prepare_stt") == 1
    assert app.state.readiness.llm_task is None


def test_official_start_also_triggers_stt_preparation(session_app):
    client, app, calls, gate = session_app
    login(client, teacher=True)
    now = datetime.now(timezone.utc)
    response = client.post("/api/teacher/exams", json={"title": "Start policy", "exam_code": "STARTTEST",
        "language": "en", "subject": "DSA101", "question_count": 1, "starting_difficulty": "Easy",
        "starts_at": (now-timedelta(hours=1)).isoformat(), "ends_at": (now+timedelta(hours=1)).isoformat()})
    assert response.status_code == 201, response.text
    exam_id = response.json()["exam"]["exam_round_id"]
    assert client.patch(f"/api/teacher/exams/{exam_id}/status", json={"status": "open"}).status_code == 200
    assert calls == []
    login(client)
    response = client.post("/api/candidate/exams/STARTTEST/start")
    assert response.status_code == 201, response.text
    assert response.json()["runtime_readiness"]["speech"]["state"] == "loading"
    gate.set()
    wait_ready(client)
    assert calls.count("prepare_stt") == 1
    assert app.state.readiness.llm_task is None


@pytest.mark.parametrize("stage", ["before_speech", "before_generation", "begin_grading", "ensure_llm"])
def test_early_recording_does_not_deadlock_queued_preparation(test_settings, monkeypatch, stage):
    test_settings.runtime_warmup = True
    test_settings.evaluator_mode = "auto"
    calls = []

    async def before(_self):
        pass

    def warm(_settings):
        calls.append("warm")
        return "ready"

    async def llm(_self, force=False):
        _self.states["llm"] = {"state": "ready"}

    monkeypatch.setattr(runtime_readiness.RuntimeReadiness, "_unload_owned_llms", before)
    monkeypatch.setattr(runtime_readiness.RuntimeReadiness, "_llm", llm)
    monkeypatch.setattr(runtime_readiness, "release_transformer", lambda: None)
    monkeypatch.setattr(runtime_readiness, "prepare_speech", warm)

    async def exercise():
        ready = runtime_readiness.RuntimeReadiness(test_settings)
        async with ready.inference_lock:
            ready.start()
            await asyncio.sleep(0)
            # The foreground operation owns the lane while warmup is queued.
            await asyncio.wait_for(getattr(ready, stage)(), timeout=1)
            ready.states["speech"] = {"state": "ready"}
        await asyncio.wait_for(ready.speech_task, timeout=1)
        assert calls == []
        await ready.stop()

    monkeypatch.setattr(runtime_readiness.RuntimeReadiness, "_release_speech_stage", before)
    asyncio.run(exercise())


def test_stt_preparation_is_serialized_with_grading_and_generation(test_settings, monkeypatch):
    test_settings.runtime_warmup = True
    calls = []

    async def before(_self):
        pass

    monkeypatch.setattr(runtime_readiness.RuntimeReadiness, "before_speech", before)
    monkeypatch.setattr(runtime_readiness, "prepare_speech", lambda _: calls.append("warm") or "ready")

    async def exercise():
        ready = runtime_readiness.RuntimeReadiness(test_settings)
        async with ready.inference_lock:
            ready.start()
            await asyncio.sleep(.02)
            assert calls == []
        await asyncio.wait_for(ready.speech_task, timeout=1)
        assert calls == ["warm"]
        ready.start()
        assert calls == ["warm"]
        await ready.stop()

    asyncio.run(exercise())


def test_failed_preparation_can_be_requested_again(test_settings, monkeypatch):
    test_settings.runtime_warmup = True
    attempts = []

    async def before(_self):
        pass

    def warm(_settings):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("test warmup failure")
        return "ready"

    monkeypatch.setattr(runtime_readiness.RuntimeReadiness, "before_speech", before)
    monkeypatch.setattr(runtime_readiness, "prepare_speech", warm)

    async def exercise():
        ready = runtime_readiness.RuntimeReadiness(test_settings)
        ready.start()
        await ready.speech_task
        assert ready.snapshot()["speech"]["state"] == "unavailable"
        ready.start()
        await ready.speech_task
        assert ready.snapshot()["speech"]["state"] == "ready"
        assert len(attempts) == 2
        await ready.stop()

    asyncio.run(exercise())


@pytest.mark.parametrize("outcome,expected", [("met", 100), ("missing", 0), ("unresolved", None), ("noise", None)])
def test_practice_ai_grades_without_teacher_or_fabricated_final_score(test_settings, monkeypatch, outcome, expected):
    sid = prepare(test_settings, count=1)["session_id"]
    answer_current(test_settings, sid)
    if outcome == "noise":
        with database(test_settings.database_path) as connection:
            connection.execute("UPDATE speech_transcriptions SET metadata_json=?",
                (json.dumps({"quality_warnings": ["background voices"], "metrics": {"quality_score": .4}}),))

    async def grade(settings, question, text, **kwargs):
        return evaluator._compose_result(question,
            [{"point": p, "status": "met" if outcome == "noise" else outcome} for p in question["key_points"]], evaluator="test")

    monkeypatch.setattr(session_grading, "evaluate_answer", grade)
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    asyncio.run(jobs.run_once())
    assert jobs.status(sid)["report_ready"]
    report = interview_report(test_settings, sid)
    result = report["answers"][0]["evaluation"]
    assert result["final_score"] == expected
    assert result["grading_owner"] == "ai"
    assert result["review_policy"] == "practice_ai_only"
    assert not result["review_required"] and not result["teacher_review_required"]
    assert result["score_provisional"] == (expected is None)
    if expected is None:
        assert result["score_status"] == "insufficient_evidence"
        assert report["summary"]["average_score"] is None
        assert report["summary"]["scored_answer_count"] == 0
    assert list_review_queue(test_settings) == []
    with pytest.raises(TeacherReviewError, match="chính thức"):
        review_answer(test_settings, answer_id=report["answers"][0]["answer_id"], teacher_id=1,
            action="manual", score=80, feedback="Not allowed for practice")


def test_shutdown_cancels_preparation_waiting_for_inference_lane(test_settings):
    test_settings.runtime_warmup = True

    async def exercise():
        ready = runtime_readiness.RuntimeReadiness(test_settings)
        async with ready.inference_lock:
            ready.start()
            await asyncio.sleep(0)
            await asyncio.wait_for(ready.stop(), timeout=1)
            assert ready.speech_task.cancelled()

    asyncio.run(exercise())


@pytest.mark.parametrize("cache_policy", ["kept_for_next_review", "released_after_request"])
@pytest.mark.parametrize("prepare_queued", [False, True])
def test_student_session_prepares_again_after_strong_teacher_stt(test_settings, monkeypatch, cache_policy, prepare_queued):
    test_settings.runtime_warmup = True
    calls = []

    async def before(_self):
        pass

    def strong(*_args, **_kwargs):
        return {"text": "test", "model": "large-v3", "purpose": "teacher_review", "model_cache_policy": cache_policy}

    monkeypatch.setattr(runtime_readiness.RuntimeReadiness, "before_speech", before)
    monkeypatch.setattr(runtime_readiness.speech, "transcribe_review_audio", strong)
    monkeypatch.setattr(runtime_readiness, "prepare_speech", lambda _: calls.append("student_warmup") or "ready")

    async def exercise():
        ready = runtime_readiness.RuntimeReadiness(test_settings)
        async with ready.inference_lock:
            if prepare_queued:
                ready.start()
                await asyncio.sleep(0)
            await ready.run_inference(runtime_readiness.speech.transcribe_review_audio, test_settings, b"test")
        assert ready.snapshot()["speech"]["purpose"] == "teacher_review"
        assert ready.snapshot()["speech"]["state"] == ("released" if cache_policy == "released_after_request" else "ready")
        if not prepare_queued:
            ready.start()
        await ready.speech_task
        assert calls == ["student_warmup"]
        assert ready.snapshot()["speech"]["state"] == "ready"
        await ready.stop()

    asyncio.run(exercise())


def test_released_student_model_is_not_reported_as_still_loaded(test_settings, monkeypatch):
    def transcribe(*_args, **_kwargs):
        return {"text": "test", "model": "small"}

    monkeypatch.setattr(runtime_readiness.speech, "transcribe_bytes", transcribe)

    async def exercise():
        ready = runtime_readiness.RuntimeReadiness(test_settings)
        await ready.run_inference(runtime_readiness.speech.transcribe_bytes, test_settings, b"test", release_after=True)
        assert ready.snapshot()["speech"]["state"] == "released"
        await ready.stop()

    asyncio.run(exercise())
