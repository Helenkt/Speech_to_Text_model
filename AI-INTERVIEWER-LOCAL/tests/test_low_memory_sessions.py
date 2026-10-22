import asyncio
import json
import os
import time
import threading
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.database import database, init_database
from app.services import evaluator, runtime_readiness, session_grading, speech_to_text
from app.services.exam_service import create_exam_round
from app.services.interview_engine import (
    InterviewError, finish_interview, interview_report, resume_interview, start_interview, submit_answer,
)
from app.services.question_importer import import_question_bank
from app.services.resource_policy import ollama_request_resources, resolve_resource_policy
from app.services.transcript_corrector import correct_transcript
from app.services.transcription_store import save_microphone_check, save_transcription
from app.services.teacher_review import review_reanalysis_context, TeacherReviewError


@pytest.mark.parametrize("ram,available,category,threads,retire", [
    (4, 2, "4gb", 2, True), (3.7, 1, "4gb", 2, True),
    (8, 6, "8gb", 4, False), (7.7, 5, "8gb", 4, False),
    (8.5, 7, "8gb", 4, False), (16, 3, "standard", 4, False),
    (0, 0, "unknown", 2, True),
])
def test_memory_policy_includes_eight_gb_even_when_memory_is_free(ram, available, category, threads, retire):
    policy = resolve_resource_policy(ram, available, 8)
    assert policy.staged
    assert policy.memory_class == category
    assert policy.cpu_threads == threads
    assert policy.retire_worker_between_stages == retire


def test_single_core_and_standard_machine_budgets():
    assert resolve_resource_policy(8, 5, 1).cpu_threads == 1
    assert not resolve_resource_policy(16, 8, 8).staged


def test_ollama_budget_preserves_context_and_output(test_settings, monkeypatch):
    monkeypatch.setattr(speech_to_text, "_memory_stats_gb", lambda: (8, 5, 38))
    budget = ollama_request_resources(test_settings)
    assert budget["keep_alive"] == "2m"
    assert budget["options"]["num_batch"] == 128
    assert not {"num_ctx", "num_predict", "temperature"} & budget["options"].keys()
    monkeypatch.setattr(speech_to_text, "_memory_stats_gb", lambda: (4, 2, 50))
    assert ollama_request_resources(test_settings)["keep_alive"] == "30s"
    test_settings.ollama_keep_alive = "0"
    assert ollama_request_resources(test_settings)["keep_alive"] == "0"


def test_whisper_uses_one_worker_and_a_bounded_thread_count(test_settings, monkeypatch):
    import faster_whisper
    hardware = speech_to_text.HardwareCapabilities(4, 8, 5, 38, False, 0, None)
    monkeypatch.setattr(speech_to_text, "detect_hardware", lambda: hardware)
    monkeypatch.setattr(speech_to_text, "_MODEL", None)
    monkeypatch.setattr(speech_to_text, "_MODEL_KEY", None)
    monkeypatch.setattr(speech_to_text, "_REQUESTED_MODEL_KEY", None)
    monkeypatch.setattr(speech_to_text, "_ACTIVE_PROFILE", None)
    calls = []
    def create(*args, **kwargs):
        calls.append(kwargs)
        return object()
    monkeypatch.setattr(faster_whisper, "WhisperModel", create)
    speech_to_text._get_model(test_settings, local_only=True)
    speech_to_text._get_model(test_settings, local_only=True)
    assert len(calls) == 1
    assert calls[0]["cpu_threads"] == 2
    assert calls[0]["num_workers"] == 1
    assert calls[0]["compute_type"] == "int8"
    assert calls[0]["local_files_only"]


def test_end_of_session_mode_never_preloads_llm_even_on_large_machine(test_settings, monkeypatch):
    test_settings.defer_grading_until_finish = True
    monkeypatch.setattr(speech_to_text, "_memory_stats_gb", lambda: (32, 24, 25))
    async def exercise():
        ready = runtime_readiness.RuntimeReadiness(test_settings)
        await ready._llm()
        assert ready.snapshot()["llm"] == {"state": "deferred", "reason": "end_of_session"}
    asyncio.run(exercise())


def test_eight_gb_gpu_keeps_medium_but_uses_low_tier(test_settings):
    test_settings.whisper_model = test_settings.whisper_device = test_settings.whisper_compute_type = "auto"
    hardware = speech_to_text.HardwareCapabilities(8, 8, 5, 38, True, 1, 8)
    profile = speech_to_text.resolve_runtime_profile(test_settings, hardware)
    assert (profile.model, profile.device, profile.tier) == ("medium", "cuda", "low")
    assert [p.model for p in speech_to_text._fallback_profiles(profile)] == ["medium", "small"]


def test_four_gb_worker_is_retired_before_llm(test_settings, monkeypatch):
    test_settings.inference_worker = True
    monkeypatch.setattr(speech_to_text, "_memory_stats_gb", lambda: (4, 2, 50))
    calls = []
    class Pool:
        def shutdown(self, **kwargs):
            calls.append("shutdown")
    async def exercise():
        ready = runtime_readiness.RuntimeReadiness(test_settings)
        ready.pool = Pool()
        async def infer(operation, *args):
            calls.append(operation.__name__)
        ready.run_inference = infer
        await ready.begin_grading()
        assert ready.pool is None
        assert ready.snapshot()["resources"]["memory_class"] == "4gb"
    asyncio.run(exercise())
    assert calls == ["release_speech", "shutdown"]


@pytest.mark.parametrize("ram,retired", [(4, True), (8, False)])
def test_real_worker_lifecycle_follows_memory_budget(test_settings, monkeypatch, ram, retired):
    test_settings.inference_worker = True
    monkeypatch.setattr(speech_to_text, "_memory_stats_gb", lambda: (ram, 3, 50))
    async def exercise():
        ready = runtime_readiness.RuntimeReadiness(test_settings)
        try:
            pid = await ready.run_inference(os.getpid)
            assert pid != os.getpid()
            original_pool = ready.pool
            await ready.begin_grading()
            if retired:
                assert ready.pool is None
            else:
                assert ready.pool is original_pool
            await ready.run_inference(os.getpid)
            assert (ready.pool is not original_pool) == retired
        finally:
            await ready.stop()
    asyncio.run(exercise())


def test_before_speech_unloads_owned_models_even_when_state_is_idle(test_settings, monkeypatch):
    test_settings.inference_worker = True
    monkeypatch.setattr(speech_to_text, "_memory_stats_gb", lambda: (8, 5, 38))
    released = []
    def respond(request):
        if request.method == "GET":
            return httpx.Response(200, json={"models": [{"name": name} for name in
                (test_settings.ollama_model, test_settings.question_generation_model, "unrelated:7b")]})
        released.append(json.loads(request.content)["model"])
        assert json.loads(request.content)["keep_alive"] == 0
        return httpx.Response(200, json={})
    actual = httpx.AsyncClient
    monkeypatch.setattr(runtime_readiness.httpx, "AsyncClient", lambda **kwargs: actual(transport=httpx.MockTransport(respond), **kwargs))
    async def exercise():
        ready = runtime_readiness.RuntimeReadiness(test_settings)
        await ready.before_speech()
        assert ready.pool is None
    asyncio.run(exercise())
    assert set(released) == {test_settings.ollama_model, test_settings.question_generation_model}


def prepare(settings, mode="practice", count=3):
    settings.defer_grading_until_finish = True
    init_database(settings.database_path)
    with database(settings.database_path) as connection:
        connection.execute("""INSERT INTO users (user_id,username,password_hash,full_name,role,created_at,updated_at)
            VALUES (1,'teacher','hash','Teacher','teacher','now','now'),
                   (2,'candidate','hash','Candidate','candidate','now','now')""")
    bank = [{"id": f"fixed-{level}", "language": "en", "subject": "DSA101", "difficulty": level,
             "question": f"Explain {topic}", "reference_answer": answer, "key_points": [answer]}
            for level, topic, answer in [("Easy", "Stack", "A stack is LIFO"),
                ("Medium", "Queue", "A queue is FIFO"), ("Hard", "binary search", "Binary search needs sorted data")]]
    import_question_bank(settings.database_path, json.dumps(bank).encode(), filename="course.json")
    exam_id = None
    if mode == "real":
        now = datetime.now(timezone.utc)
        exam = create_exam_round(settings.database_path, created_by=1, title="Fixed exam", exam_code="FIXED123",
            language="en", subject="DSA101", question_count=count, starting_difficulty="Easy", answer_mode="voice",
            starts_at=now-timedelta(hours=1), ends_at=now+timedelta(hours=1))
        exam_id = exam["exam_round_id"]
    session = start_interview(settings, user_id=2, candidate_name="Candidate", language="en", subject="DSA101",
        question_count=count, starting_difficulty="Easy", interview_mode=mode, exam_round_id=exam_id)
    save_microphone_check(settings.database_path, session_id=session["session_id"], user_id=2, result={"ready": True})
    return session


def answer_current(settings, sid):
    with database(settings.database_path) as connection:
        row = connection.execute("SELECT current_question_json FROM interview_sessions WHERE session_id=?", (sid,)).fetchone()
    question = json.loads(row[0])
    tid = save_transcription(settings.database_path, session_id=sid, user_id=2, question_uid=question["uid"],
        raw_text=question["reference_answer"], corrected_text=question["reference_answer"], model="test", runtime="cpu/int8",
        confidence=.95, ambient_noise_dbfs=-60, metadata={"uncertain_spans": [], "metrics": {"quality_score": .95}},
        audio_content=b"test-recording", audio_filename="answer.wav")
    return asyncio.run(submit_answer(settings, sid, "ignored client text", user_id=2, transcription_id=tid)), tid


@pytest.mark.parametrize("mode", ["practice", "real"])
def test_fixed_plan_and_no_grading_until_completed(test_settings, monkeypatch, mode):
    session = prepare(test_settings, mode)
    sid = session["session_id"]
    assert session["difficulty_schedule"] == ["Easy", "Medium", "Hard"]
    with database(test_settings.database_path) as connection:
        plan = json.loads(connection.execute("SELECT question_plan_json FROM interview_sessions WHERE session_id=?", (sid,)).fetchone()[0])
        connection.execute("UPDATE questions SET active=0,question='Changed after start'")
    async def forbidden(*args, **kwargs):
        raise AssertionError("Do not grade while collecting recordings")
    monkeypatch.setattr("app.services.interview_engine.evaluate_answer", forbidden)
    for index in range(3):
        assert resume_interview(test_settings, sid, user_id=2)["question"]["question"] == plan[index]["question"]
        result, tid = answer_current(test_settings, sid)
        replay = asyncio.run(submit_answer(test_settings, sid, "tampered", user_id=2, transcription_id=tid))
        assert replay == result
        assert result["grading_pending"]
        with database(test_settings.database_path) as connection:
            assert connection.execute("SELECT COUNT(*) FROM session_grading_jobs").fetchone()[0] == int(index == 2)
    report = interview_report(test_settings, sid)
    assert report["summary"]["scored_answer_count"] == 0
    assert report["summary"]["pending_answer_count"] == 3
    calls = []
    async def grade(settings, question, text, **kwargs):
        calls.append(question["uid"])
        assert text == question["reference_answer"]
        return evaluator._compose_result(question, [{"point": p, "status": "met"} for p in question["key_points"]], evaluator="test")
    monkeypatch.setattr(session_grading, "evaluate_answer", grade)
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    assert asyncio.run(jobs.run_once())
    assert calls == [question["uid"] for question in plan]
    assert jobs.status(sid)["report_ready"]
    assert not asyncio.run(jobs.run_once())
    with database(test_settings.database_path) as connection:
        rows = connection.execute("SELECT grading_pending,final_score FROM interview_answers").fetchall()
        assert all(row["grading_pending"] == 0 for row in rows)
        if mode == "real":
            assert all(row["final_score"] is None for row in rows)
        else:
            assert all(row["final_score"] == 100 for row in rows)


def test_finish_early_queues_only_submitted_answers(test_settings):
    session = prepare(test_settings)
    sid = session["session_id"]
    answer_current(test_settings, sid)
    finish_interview(test_settings, sid, user_id=2)
    finish_interview(test_settings, sid, user_id=2)
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM session_grading_jobs").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM interview_answers").fetchone()[0] == 1


def test_strong_review_does_not_start_during_collection_or_pending_batch(test_settings):
    sid = prepare(test_settings, mode="real")["session_id"]
    answer_current(test_settings, sid)
    with database(test_settings.database_path) as connection:
        answer_id = connection.execute("SELECT answer_id FROM interview_answers").fetchone()[0]
    with pytest.raises(TeacherReviewError, match="chấm lần đầu"):
        review_reanalysis_context(test_settings, answer_id=answer_id)


def test_no_llm_is_called_for_deferred_correction(test_settings):
    async def forbidden():
        raise AssertionError("Do not load an LLM during recording")
    result = asyncio.run(correct_transcript(test_settings, "some uncertain speech", language="en", approved_terms=[],
        uncertain_spans=["uncertain speech"], ensure_model=forbidden, allow_llm=False))
    assert result["corrected_text"] == "some uncertain speech"
    assert result["correction_deferred"]


def test_partial_failure_retries_only_unprocessed_answers(test_settings, monkeypatch):
    sid = prepare(test_settings)["session_id"]
    for _ in range(3):
        answer_current(test_settings, sid)
    calls = []
    async def grade(settings, question, text, **kwargs):
        calls.append(question["uid"])
        if len(calls) == 2:
            raise RuntimeError("injected model failure")
        return evaluator._compose_result(question, [{"point": p, "status": "met"} for p in question["key_points"]], evaluator="test")
    monkeypatch.setattr(session_grading, "evaluate_answer", grade)
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    asyncio.run(jobs.run_once())
    assert jobs.status(sid)["state"] == "failed"
    assert jobs.status(sid)["pending_count"] == 2
    jobs.retry(sid)
    asyncio.run(jobs.run_once())
    assert jobs.status(sid)["report_ready"]
    assert calls.count(calls[0]) == 1


def test_teacher_decision_wins_during_batch(test_settings, monkeypatch):
    sid = prepare(test_settings, count=1)["session_id"]
    answer_current(test_settings, sid)
    async def grade(settings, question, text, **kwargs):
        with database(settings.database_path) as connection:
            connection.execute("UPDATE interview_answers SET teacher_score=75,final_score=75,reviewed_at='now' WHERE session_id=?", (sid,))
        return evaluator._compose_result(question, [{"point": p, "status": "met"} for p in question["key_points"]], evaluator="test")
    monkeypatch.setattr(session_grading, "evaluate_answer", grade)
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    asyncio.run(jobs.run_once())
    with database(test_settings.database_path) as connection:
        row = connection.execute("SELECT final_score,grading_pending FROM interview_answers").fetchone()
    assert tuple(row) == (75, 0)


def test_missing_questions_does_not_create_partial_session(test_settings):
    prepare(test_settings, count=1)
    with pytest.raises(InterviewError):
        start_interview(test_settings, user_id=2, candidate_name="Candidate", language="en", subject="DSA101",
                        question_count=4, starting_difficulty="Easy")
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM interview_sessions").fetchone()[0] == 1


def test_migration_leaves_legacy_answers_and_recordings_unchanged(test_settings):
    sid = prepare(test_settings, count=1)["session_id"]
    answer_current(test_settings, sid)
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE interview_sessions SET grading_strategy='per_answer',question_plan_json=NULL")
        connection.execute("UPDATE interview_answers SET grading_pending=0,score=77,ai_score=77,final_score=77,score_provisional=0,evaluator='legacy'")
        connection.execute("DELETE FROM session_grading_jobs")
        before = tuple(connection.execute("SELECT answer_text,score,ai_score,final_score,evaluator FROM interview_answers").fetchone())
        voice = tuple(connection.execute("SELECT raw_text,corrected_text,audio_sha256 FROM speech_transcriptions").fetchone())
    init_database(test_settings.database_path)
    with database(test_settings.database_path) as connection:
        assert tuple(connection.execute("SELECT answer_text,score,ai_score,final_score,evaluator FROM interview_answers").fetchone()) == before
        assert tuple(connection.execute("SELECT raw_text,corrected_text,audio_sha256 FROM speech_transcriptions").fetchone()) == voice
        assert connection.execute("SELECT grading_strategy,question_plan_json FROM interview_sessions").fetchone()[:] == ("per_answer", None)
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    jobs.recover()
    assert not asyncio.run(jobs.run_once())


def test_expired_grading_lease_recovers_and_limit_is_terminal(test_settings, monkeypatch):
    sid = prepare(test_settings, count=1)["session_id"]
    answer_current(test_settings, sid)
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE session_grading_jobs SET state='processing',worker_id='old',lease_until=0,attempts=1")
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    assert jobs.claim() == sid
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE session_grading_jobs SET state='queued',attempts=3")
    assert jobs.claim() is None
    assert jobs.status(sid)["state"] == "failed"
    with pytest.raises(ValueError):
        jobs.retry(sid)


def test_batch_cannot_clear_original_audio_warning(test_settings, monkeypatch):
    sid = prepare(test_settings, count=1)["session_id"]
    answer_current(test_settings, sid)
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE speech_transcriptions SET metadata_json=?",
            (json.dumps({"quality_warnings": ["background speech"], "metrics": {"quality_score": .4}}),))
    async def grade(settings, question, text, **kwargs):
        return evaluator._compose_result(question, [{"point": p, "status": "met"} for p in question["key_points"]], evaluator="test")
    monkeypatch.setattr(session_grading, "evaluate_answer", grade)
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    asyncio.run(jobs.run_once())
    with database(test_settings.database_path) as connection:
        row = connection.execute("SELECT final_score,score_provisional,review_required FROM interview_answers").fetchone()
    assert tuple(row) == (None, 1, 0)


def test_api_recording_then_background_grading_is_responsive(client, login_candidate, test_settings, monkeypatch):
    import app.main as main
    test_settings.defer_grading_until_finish = True
    bank = [{"id": "api-fixed", "language": "en", "subject": "DSA101", "difficulty": "Easy",
             "question": "What is a stack?", "reference_answer": "A stack is LIFO", "key_points": ["A stack is LIFO"]}]
    import_question_bank(test_settings.database_path, json.dumps(bank).encode(), filename="course.json")
    started = client.post("/api/interviews/start", json={"language": "en", "subject": "DSA101",
        "question_count": 1, "starting_difficulty": "Easy"})
    assert started.status_code == 201, started.text
    sid = started.json()["session_id"]
    assert started.json()["question_selection"] == "fixed"
    save_microphone_check(test_settings.database_path, session_id=sid, user_id=login_candidate["user_id"], result={"ready": True})
    def transcribe(*args, **kwargs):
        return {"text": "A stack is LIFO", "model": "stub", "runtime": "cpu/int8", "uncertain_spans": [],
            "metrics": {"confidence": .98, "word_count": 4, "uncertain_word_ratio": 0,
                        "speech_duration_seconds": 3, "average_no_speech_probability": .01}}
    monkeypatch.setattr(main, "transcribe_bytes", transcribe)
    async def correction(settings, text, **kwargs):
        assert kwargs["allow_llm"] is True
        return await correct_transcript(settings, text, **kwargs)
    monkeypatch.setattr(main, "correct_transcript", correction)
    entered, release = threading.Event(), threading.Event()
    async def grade(settings, question, text, **kwargs):
        entered.set()
        await asyncio.to_thread(release.wait, 3)
        return evaluator._compose_result(question, [{"point": p, "status": "met"} for p in question["key_points"]], evaluator="test")
    monkeypatch.setattr(session_grading, "evaluate_answer", grade)
    transcript = client.post("/api/speech/transcribe", data={"session_id": sid},
        files={"file": ("answer.webm", b"audio", "audio/webm")})
    assert transcript.status_code == 200, transcript.text
    assert not entered.is_set()
    result = client.post(f"/api/interviews/{sid}/answer", json={"answer": "client cannot change this",
        "transcription_id": transcript.json()["transcription_id"]})
    assert result.status_code == 200 and result.json()["completed"]
    try:
        assert entered.wait(2)
        progress = client.get(f"/api/interviews/{sid}/grading")
        assert progress.status_code == 200
        assert progress.json()["state"] == "processing"
        assert progress.json()["report_ready"] is False
    finally:
        release.set()
    for _ in range(100):
        if client.get(f"/api/interviews/{sid}/grading").json()["report_ready"]:
            break
        time.sleep(.02)
    report = client.get(f"/api/interviews/{sid}/report").json()
    assert report["grading"]["report_ready"]
    assert report["summary"]["scored_answer_count"] == 1
    client.cookies.clear()
    assert client.get(f"/api/interviews/{sid}/grading").status_code == 401
