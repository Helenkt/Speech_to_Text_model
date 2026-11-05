"""Regression coverage for model failure, interruptions and concurrent teacher decisions."""
import asyncio
import json
import threading
import time

import httpx
import pytest
from fastapi.testclient import TestClient


from app.database import database, init_database
from app.main import create_app
from app.services import evaluator, runtime_readiness, session_grading
from app.services.auth import create_session, COOKIE_NAME
from app.services.fact_guard import check_rubric_point
from app.services.interview_engine import start_interview, submit_answer, interview_report
from app.services.practice_grading import validate_ai_grade
from app.services.question_importer import import_question_bank
from app.services.teacher_review import review_answer, review_history, list_review_queue, review_reanalysis_context, TeacherReviewError
from app.services.transcription_store import save_microphone_check, save_transcription
from test_low_memory_sessions import prepare, answer_current
from test_grading_reliability import due, pending_result
from test_teacher_strong_review import _settings, _seed_voice_answer, _save_result


QUESTION = {
    "id": "audit-base-case", "language": "en", "subject": "DSA101", "difficulty": "Easy",
    "question": "Explain the role of the base case in recursion.",
    "reference_answer": "The base case prevents infinite recursion.",
    "key_points": ["base case prevents infinite recursion"],
}
WRONG = "Infinite recursion prevents the base case."


def jobs_for(settings):
    return session_grading.SessionGrading(settings, runtime_readiness.RuntimeReadiness(settings))


def grade(question, status="met"):
    return evaluator._compose_result(question, [{"point": p, "status": status}
        for p in question["key_points"]], evaluator="audit")


def seed_course_answer(settings):
    init_database(settings.database_path)
    with database(settings.database_path) as connection:
        connection.execute("""INSERT INTO users
            (user_id,username,password_hash,full_name,role,created_at,updated_at) VALUES
            (1,'teacher','hash','Teacher','teacher','now','now'),
            (2,'candidate','hash','Candidate','candidate','now','now')""")
    import_question_bank(settings.database_path, json.dumps([QUESTION]).encode(), filename="audit.json")
    session = start_interview(settings, user_id=2, candidate_name="Candidate", language="en",
        subject="DSA101", question_count=1, starting_difficulty="Easy")
    sid = session["session_id"]
    save_microphone_check(settings.database_path, session_id=sid, user_id=2, result={"ready": True})
    with database(settings.database_path) as connection:
        question = json.loads(connection.execute("SELECT current_question_json FROM interview_sessions").fetchone()[0])
    tid = save_transcription(settings.database_path, session_id=sid, user_id=2, question_uid=question["uid"],
        raw_text=WRONG, corrected_text=WRONG, model="audit", runtime="cpu/int8", confidence=.95,
        ambient_noise_dbfs=-60, metadata={"metrics": {"quality_score": .95}},
        audio_content=b"audit-recording", audio_filename="answer.wav")
    asyncio.run(submit_answer(settings, sid, "ignored client text", user_id=2, transcription_id=tid))
    return sid


@pytest.mark.parametrize("failure", [ImportError, RuntimeError, OSError, ValueError, KeyError, MemoryError, None])
def test_transformer_failure_never_falls_back_to_keyword_final_score(tmp_path, monkeypatch, failure):
    settings = _settings(tmp_path)
    settings.defer_grading_until_finish = True
    settings.evaluator_mode = "transformer"
    settings.rubric_transformer_path = tmp_path / "missing-model"
    assert check_rubric_point(QUESTION, WRONG, QUESTION["key_points"][0]).status == "unknown"
    def unavailable(*_args, **_kwargs):
        raise failure("Controlled local transformer failure")
    if failure is not None:
        monkeypatch.setattr(evaluator, "evaluate_with_transformer", unavailable)
    sid = seed_course_answer(settings)
    jobs = jobs_for(settings)
    asyncio.run(jobs.run_once())
    evaluation = interview_report(settings, sid)["answers"][0]["evaluation"]
    assert evaluation["final_score"] is None, {
        "final_score": evaluation["final_score"], "evaluator": evaluation["evaluator"],
        "assessment": evaluation["point_assessments"],
    }
    assert evaluation["score_provisional"]


def test_control_verified_factguard_does_not_require_transformer(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    settings.evaluator_mode = "transformer"
    question = {**QUESTION, "question": "Explain a stack.", "reference_answer": "A stack is LIFO",
                "key_points": ["A stack is LIFO"]}
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Verified deterministic relation does not need model inference")
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", forbidden)
    result = asyncio.run(evaluator.evaluate_answer(settings, question, "A stack is LIFO"))
    assert result["score"] == 100 and not result["score_provisional"]
    assert validate_ai_grade(question, result)["status"] == "final"


@pytest.mark.parametrize("mode", ["auto", "ollama"])
def test_control_llm_failure_keeps_evidence_unresolved(tmp_path, monkeypatch, mode):
    settings = _settings(tmp_path)
    settings.evaluator_mode = mode
    def unavailable(*_args, **_kwargs):
        raise RuntimeError("Transformer unavailable")
    async def offline(*_args, **_kwargs):
        raise httpx.ConnectError("Ollama unavailable")
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", unavailable)
    monkeypatch.setattr(evaluator, "evaluate_with_ollama", offline)
    result = asyncio.run(evaluator.evaluate_answer(settings, QUESTION, WRONG))
    assert result["score_provisional"]
    assert validate_ai_grade(QUESTION, result)["status"] != "final"


@pytest.mark.parametrize("stops", [1, 3, 5])
def test_graceful_stops_while_waiting_for_inference_do_not_exhaust_grading(tmp_path, monkeypatch, stops):
    settings = _settings(tmp_path)
    sid = prepare(settings, count=1)["session_id"]
    answer_current(settings, sid)
    jobs = jobs_for(settings)
    calls = []
    async def available(_settings, question, *_args, **_kwargs):
        calls.append(question["uid"])
        return grade(question)
    monkeypatch.setattr(session_grading, "evaluate_answer", available)
    async def exercise():
        class ObservedLock:
            def __init__(self):
                self.lock = asyncio.Lock()
                self.waiting = asyncio.Event()
            async def __aenter__(self):
                self.waiting.set()
                await self.lock.acquire()
            async def __aexit__(self, *_args):
                self.lock.release()
        lock = ObservedLock()
        jobs.readiness.inference_lock = lock
        async with lock:
            for _ in range(stops):
                lock.waiting.clear()
                jobs.task = asyncio.create_task(jobs.run_once())
                await asyncio.wait_for(lock.waiting.wait(), 3)
                assert jobs.status(sid)["state"] == "processing"
                assert jobs.status(sid)["attempts"] == 0
                assert calls == []
                await jobs.stop()
                assert jobs.status(sid)["state"] == "queued"
        return await jobs.run_once()
    ran = asyncio.run(exercise())
    assert ran and calls and jobs.status(sid)["report_ready"], jobs.status(sid)
    assert jobs.status(sid)["attempts"] == 1


def test_missing_transformer_cannot_finalize_an_excerpt_with_unparsed_context(tmp_path):
    settings = _settings(tmp_path)
    settings.evaluator_mode = "transformer"
    settings.rubric_transformer_path = tmp_path / "missing-model"
    question = {**QUESTION, "key_points": ["A stack is LIFO", QUESTION["key_points"][0]]}
    result = asyncio.run(evaluator.evaluate_answer(settings, question, f"A stack is LIFO. {WRONG}"))
    assessments = result["point_assessments"]
    assert all(item["status"] == "unresolved" and item["needs_review"] for item in assessments)
    assert all(item["review_reason"] == "model_unavailable" for item in assessments)
    assert result["score_provisional"]
    assert validate_ai_grade(question, result)["status"] != "final"


def test_missing_transformer_preserves_facts_when_other_clauses_are_accounted_for(tmp_path):
    settings = _settings(tmp_path)
    settings.evaluator_mode = "transformer"
    settings.rubric_transformer_path = tmp_path / "missing-model"
    question = {**QUESTION, "key_points": ["A stack is LIFO", QUESTION["key_points"][0]]}
    result = asyncio.run(evaluator.evaluate_answer(settings, question, "A stack is LIFO. Queue follows FIFO."))
    assessments = result["point_assessments"]
    assert assessments[0]["status"] == "met" and not assessments[0]["needs_review"]
    assert assessments[1]["status"] == "unresolved" and assessments[1]["needs_review"]
    assert assessments[1]["review_reason"] == "model_unavailable"
    assert result["score"] == 50 and result["score_provisional"]
    assert validate_ai_grade(question, result)["status"] != "final"


def test_semantic_uncertainty_is_not_a_retryable_model_failure(tmp_path):
    settings = _settings(tmp_path)
    settings.evaluator_mode = "transformer"
    result = asyncio.run(evaluator.evaluate_answer(settings, QUESTION,
        "I retract the previous answer. The base case prevents infinite recursion."))
    assert result["evaluator"] == "semantic-pending" and result["score_provisional"]
    assert all(item.get("review_reason") not in {"model_unavailable", "model_output_invalid"}
               for item in result["point_assessments"])


def test_unknown_mode_cannot_implicitly_enable_demo_scoring(tmp_path):
    settings = _settings(tmp_path)
    settings.evaluator_mode = "invalid-direct-setting"
    result = asyncio.run(evaluator.evaluate_answer(settings, QUESTION, WRONG))
    assert result["score_provisional"] and result["evaluator"] == "model-pending"


def test_explicit_demo_mode_remains_explicit(tmp_path):
    settings = _settings(tmp_path)
    settings.evaluator_mode = "rule"
    result = asyncio.run(evaluator.evaluate_answer(settings, QUESTION, WRONG))
    assert result["evaluator"] == "rule-demo"
    assert not result["confidence_is_accuracy"]


def test_control_restart_resumes_only_unfinished_answers(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    sid = prepare(settings, count=2)["session_id"]
    for _ in range(2):
        answer_current(settings, sid)
    calls = []
    async def exercise():
        entered = asyncio.Event()
        hold = asyncio.Event()
        async def interrupted(_settings, question, *_args, **_kwargs):
            calls.append(question["uid"])
            if len(calls) == 2:
                entered.set()
                await hold.wait()
            return grade(question)
        monkeypatch.setattr(session_grading, "evaluate_answer", interrupted)
        old = jobs_for(settings)
        task = asyncio.create_task(old.run_once())
        await asyncio.wait_for(entered.wait(), 3)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        assert old.status(sid)["pending_count"] == 1
        new = jobs_for(settings)
        new.recover()
        await new.run_once()
        assert new.status(sid)["report_ready"]
    asyncio.run(exercise())
    assert len(calls) == 3 and calls[1] == calls[2] and calls[0] != calls[1]


@pytest.mark.parametrize("attempts", [1, 3])
def test_teacher_finishing_all_answers_during_ai_does_not_leave_job_failed(tmp_path, monkeypatch, attempts):
    settings = _settings(tmp_path)
    sid = prepare(settings, mode="real", count=2)["session_id"]
    for _ in range(2):
        answer_current(settings, sid)
    with database(settings.database_path) as connection:
        aids = [r[0] for r in connection.execute("SELECT answer_id FROM interview_answers ORDER BY answer_id")]
    calls = []
    async def overlap(_settings, question, *_args, **_kwargs):
        calls.append(question["uid"])
        if len(calls) == attempts * 2:
            for aid, score in zip(aids, [73, 81]):
                review_answer(settings, answer_id=aid, teacher_id=1, action="manual", score=score,
                    feedback="Teacher finished while AI was processing")
            return grade(question)
        return pending_result(question, "model_timeout")
    monkeypatch.setattr(session_grading, "evaluate_answer", overlap)
    jobs = jobs_for(settings)
    for _ in range(attempts):
        due(settings)
        asyncio.run(jobs.run_once())
    assert jobs.status(sid)["pending_count"] == 0
    assert interview_report(settings, sid)["summary"]["average_score"] == 77
    assert all(len(review_history(settings, answer_id=aid)) == 1 for aid in aids)
    jobs.recover()
    assert jobs.status(sid)["report_ready"], jobs.status(sid)


@pytest.mark.parametrize("method,path", [
    ("get", "/api/teacher/reviews"),
    ("get", "/api/teacher/transcriptions/stt-1/audio"),
    ("post", "/api/teacher/answers/1/ai-review"),
    ("get", "/api/interviews/session-1/report"),
])
def test_control_candidate_cannot_read_teacher_voice_or_exam_results(tmp_path, method, path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    token, _ = create_session(settings.database_path, 2)
    client = TestClient(create_app(settings), raise_server_exceptions=False)
    client.cookies.set(COOKIE_NAME, token)
    response = getattr(client, method)(path)
    assert response.status_code == 403, response.text


def test_control_candidate_cannot_retry_someone_elses_grading(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    with database(settings.database_path) as connection:
        connection.execute("""INSERT INTO users
            (user_id,username,password_hash,full_name,role,created_at,updated_at)
            VALUES (3,'other','hash','Other','candidate','now','now')""")
    token, _ = create_session(settings.database_path, 3)
    client = TestClient(create_app(settings), raise_server_exceptions=False)
    client.cookies.set(COOKIE_NAME, token)
    response = client.post("/api/interviews/session-1/grading/retry")
    assert response.status_code == 403


def test_cancel_during_database_claim_releases_ownership_without_spending_attempt(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    sid = prepare(settings, count=1)["session_id"]
    answer_current(settings, sid)
    jobs = jobs_for(settings)
    claimed, finish_claim = threading.Event(), threading.Event()
    real_claim = jobs.claim
    def delayed_claim():
        result = real_claim()
        claimed.set()
        assert finish_claim.wait(5)
        return result
    monkeypatch.setattr(jobs, "claim", delayed_claim)
    async def exercise():
        task = asyncio.create_task(jobs.run_once())
        try:
            assert await asyncio.to_thread(claimed.wait, 3)
            task.cancel()
            await asyncio.sleep(0)
        finally:
            finish_claim.set()
            await asyncio.gather(task, return_exceptions=True)
    asyncio.run(exercise())
    assert jobs.status(sid)["state"] == "queued" and jobs.status(sid)["attempts"] == 0
    with database(settings.database_path) as connection:
        row = connection.execute("SELECT worker_id,lease_until FROM session_grading_jobs").fetchone()
    assert row[:] == (None, None)


def test_interruptions_after_inference_starts_still_consume_the_retry_budget(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    sid = prepare(settings, count=1)["session_id"]
    answer_current(settings, sid)
    with database(settings.database_path) as connection:
        voice = dict(connection.execute("SELECT * FROM speech_transcriptions").fetchone())
    calls = []
    async def exercise():
        entered, hold = asyncio.Event(), asyncio.Event()
        async def interrupted(_settings, question, *_args, **_kwargs):
            calls.append(question["uid"])
            entered.set()
            await hold.wait()
        monkeypatch.setattr(session_grading, "evaluate_answer", interrupted)
        old = jobs_for(settings)
        old.task = asyncio.create_task(old.run_once())
        await asyncio.wait_for(entered.wait(), 3)
        await old.stop()
        assert old.status(sid)["attempts"] == 1
        async def timeout(_settings, question, *_args, **_kwargs):
            calls.append(question["uid"])
            return pending_result(question, "model_timeout")
        monkeypatch.setattr(session_grading, "evaluate_answer", timeout)
        new = jobs_for(settings)
        new.recover()
        for _ in range(2):
            due(settings)
            await new.run_once()
        assert new.status(sid)["state"] == "failed" and new.status(sid)["attempts"] == 3
        new.recover()
        assert not await new.run_once()
    asyncio.run(exercise())
    assert len(calls) == 3
    with database(settings.database_path) as connection:
        assert dict(connection.execute("SELECT * FROM speech_transcriptions").fetchone()) == voice


def test_teacher_can_finish_before_waiting_worker_enters_inference(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    sid = prepare(settings, mode="real", count=1)["session_id"]
    answer_current(settings, sid)
    jobs = jobs_for(settings)
    async def forbidden(*_args, **_kwargs):
        raise AssertionError("No model work is needed after the teacher has finished")
    monkeypatch.setattr(session_grading, "evaluate_answer", forbidden)
    monkeypatch.setattr(jobs.readiness, "begin_grading", forbidden)
    async def exercise():
        await jobs.readiness.inference_lock.acquire()
        task = asyncio.create_task(jobs.run_once())
        try:
            for _ in range(200):
                if jobs.status(sid)["state"] == "processing":
                    break
                await asyncio.sleep(.005)
            assert jobs.status(sid)["state"] == "processing"
            with database(settings.database_path) as connection:
                aid = connection.execute("SELECT answer_id FROM interview_answers").fetchone()[0]
            review_answer(settings, answer_id=aid, teacher_id=1, action="manual", score=81, feedback="Teacher finished")
        finally:
            jobs.readiness.inference_lock.release()
        await task
    asyncio.run(exercise())
    assert jobs.status(sid)["report_ready"] and jobs.status(sid)["attempts"] == 0
    assert interview_report(settings, sid)["summary"]["average_score"] == 81


@pytest.mark.parametrize("last_error", ["technical", "exception", "cancel"])
def test_finalization_rechecks_teacher_decisions_made_during_model_cleanup(tmp_path, monkeypatch, last_error):
    settings = _settings(tmp_path)
    sid = prepare(settings, mode="real", count=2)["session_id"]
    for _ in range(2):
        answer_current(settings, sid)
    with database(settings.database_path) as connection:
        aids = [row[0] for row in connection.execute("SELECT answer_id FROM interview_answers ORDER BY answer_id")]
    last = False
    async def fail(_settings, question, *_args, **_kwargs):
        if last and last_error == "exception":
            raise RuntimeError("Controlled failure before the teacher's decision")
        if last and last_error == "cancel":
            raise asyncio.CancelledError()
        return pending_result(question, "model_timeout")
    async def cleanup():
        if last:
            for aid, score in zip(aids, [73, 81]):
                review_answer(settings, answer_id=aid, teacher_id=1, action="manual",
                    score=score, feedback="Teacher decided during model cleanup")
    jobs = jobs_for(settings)
    monkeypatch.setattr(session_grading, "evaluate_answer", fail)
    monkeypatch.setattr(jobs.readiness, "end_grading", cleanup)
    async def exercise():
        nonlocal last
        for attempt in range(3):
            last = attempt == 2
            due(settings)
            await asyncio.gather(jobs.run_once(), return_exceptions=True)
        assert not await jobs.run_once()
    asyncio.run(exercise())
    assert jobs.status(sid)["report_ready"] and jobs.status(sid)["attempts"] == 3
    assert interview_report(settings, sid)["summary"]["average_score"] == 77
    assert all(len(review_history(settings, answer_id=aid)) == 1 for aid in aids)


@pytest.mark.parametrize("state,expired", [("queued", False), ("failed", False), ("processing", True), ("processing", False)])
def test_recovery_heals_resolved_jobs_but_never_steals_a_live_lease(tmp_path, state, expired):
    settings = _settings(tmp_path)
    sid = prepare(settings, mode="real", count=1)["session_id"]
    answer_current(settings, sid)
    with database(settings.database_path) as connection:
        aid = connection.execute("SELECT answer_id FROM interview_answers").fetchone()[0]
    review_answer(settings, answer_id=aid, teacher_id=1, action="manual", score=81, feedback="Teacher decision")
    with database(settings.database_path) as connection:
        connection.execute("UPDATE session_grading_jobs SET state=?,attempts=3,worker_id='other',lease_until=?,error='old error'",
                           (state, 0 if expired else time.time() + 3600))
        before = dict(connection.execute("SELECT * FROM interview_answers").fetchone())
        history = [tuple(row) for row in connection.execute("SELECT * FROM answer_reviews")]
    jobs = jobs_for(settings)
    jobs.recover()
    jobs.recover()
    assert jobs.claim() is None
    live = state == "processing" and not expired
    assert jobs.status(sid)["state"] == ("processing" if live else "completed")
    assert jobs.status(sid)["attempts"] == 3 and jobs.status(sid)["report_ready"] is not live
    with database(settings.database_path) as connection:
        assert dict(connection.execute("SELECT * FROM interview_answers").fetchone()) == before
        assert [tuple(row) for row in connection.execute("SELECT * FROM answer_reviews")] == history


def test_recovery_does_not_mark_still_pending_answers_complete(tmp_path):
    settings = _settings(tmp_path)
    sid = prepare(settings, count=1)["session_id"]
    answer_current(settings, sid)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE session_grading_jobs SET state='failed',attempts=3")
    jobs = jobs_for(settings)
    jobs.recover()
    assert jobs.claim() is None
    assert jobs.status(sid)["state"] == "failed" and jobs.status(sid)["pending_count"] == 1
    assert not jobs.status(sid)["report_ready"]


@pytest.mark.parametrize("state,attempts", [("queued", 1), ("failed", 1), ("queued", 3), ("failed", 3)])
def test_recovery_restores_legacy_technical_failures_before_completing_idle_jobs(tmp_path, state, attempts):
    settings = _settings(tmp_path)
    sid = prepare(settings, count=1)["session_id"]
    answer_current(settings, sid)
    with database(settings.database_path) as connection:
        question = json.loads(connection.execute("SELECT question_json FROM interview_answers").fetchone()[0])
        result = pending_result(question, "model_timeout")
        connection.execute("UPDATE interview_answers SET grading_pending=0,score_provisional=1,assessment_json=?",
                           (json.dumps(result["point_assessments"]),))
        connection.execute("UPDATE session_grading_jobs SET state=?,attempts=?", (state, attempts))
    jobs = jobs_for(settings)
    jobs.recover()
    assert jobs.status(sid)["pending_count"] == 1 and not jobs.status(sid)["report_ready"]
    assert jobs.status(sid)["state"] == ("queued" if attempts < 3 else "failed")
    assert jobs.status(sid)["attempts"] == attempts


def test_old_worker_cannot_start_or_finalize_a_new_owners_job(tmp_path):
    settings = _settings(tmp_path)
    sid = prepare(settings, count=1)["session_id"]
    answer_current(settings, sid)
    old, new = jobs_for(settings), jobs_for(settings)
    assert old.claim() == sid
    with database(settings.database_path) as connection:
        connection.execute("UPDATE session_grading_jobs SET worker_id=?", (new.owner,))
        before = dict(connection.execute("SELECT * FROM session_grading_jobs").fetchone())
    with pytest.raises(RuntimeError, match="ownership"):
        old.begin_attempt(sid)
    old.finish_job(sid, "failed", "Stale worker must not write this")
    with database(settings.database_path) as connection:
        assert dict(connection.execute("SELECT * FROM session_grading_jobs").fetchone()) == before
    assert new.begin_attempt(sid) and new.status(sid)["attempts"] == 1


@pytest.mark.parametrize("accepted", [False, True])
def test_previous_policy_cache_is_invalid_but_confirmed_decisions_remain(tmp_path, accepted):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    _save_result(settings, 100)
    if accepted:
        review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")
    with database(settings.database_path) as connection:
        metadata = json.loads(connection.execute("SELECT review_metadata_json FROM speech_transcriptions").fetchone()[0])
        metadata["review_cache_key"] = "teacher-review-v9-rubric-totals-terminal-recovery"
        connection.execute("UPDATE speech_transcriptions SET review_metadata_json=?", (json.dumps(metadata),))
    assert not list_review_queue(settings)[0]["can_accept_ai"]
    assert not review_reanalysis_context(settings, answer_id=1)["cached"]
    with pytest.raises(TeacherReviewError):
        review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")
    result = interview_report(settings, "session-1")["answers"][0]["evaluation"]
    assert result["final_score"] == (100 if accepted else None)
    assert len(review_history(settings, answer_id=1)) == (1 if accepted else 0)
