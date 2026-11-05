"""Grade eligibility, recoverable failures and uncertainty are separate contracts."""
import asyncio
import json

import pytest

from app.database import database, init_database
from app.services import evaluator, runtime_readiness, session_grading, rubric_transformer
from app.services.grade_state import effective_grade
from app.services.interview_engine import interview_report, list_practice_history
from app.services.teacher_review import review_answer, TeacherReviewError, review_cache_key
from test_teacher_strong_review import _seed_voice_answer, _settings, _save_result
from test_low_memory_sessions import prepare, answer_current
from test_rubric_transformer import fake_backend, QUESTION as NLI_QUESTION


def saved_practice(settings, *, score=80, weights=None, pending=0):
    question = _seed_voice_answer(settings)
    if weights is not None:
        question["key_point_weights"] = dict(zip(question["key_points"], weights))
    assessments = [{"point": point, "status": "met" if i == 0 else "missing"}
                   for i, point in enumerate(question["key_points"])]
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_sessions SET interview_mode='practice'")
        connection.execute("""UPDATE interview_answers SET question_json=?,score=?,ai_score=?,final_score=?,
            score_provisional=0,review_required=0,assessment_json=?,grading_pending=?""",
            (json.dumps(question), score, score, score, json.dumps(assessments), pending))
    return question


@pytest.mark.parametrize("score,weights,expected", [(80, None, None), (50, None, 50),
    (75, [3, 1], 75), (50, [3, 1], None)])
def test_report_history_and_breakdown_agree_on_grade_eligibility(tmp_path, score, weights, expected):
    settings = _settings(tmp_path)
    saved_practice(settings, score=score, weights=weights)
    with database(settings.database_path) as connection:
        before = dict(connection.execute("SELECT * FROM interview_answers").fetchone())
    report = interview_report(settings, "session-1")
    result = report["answers"][0]["evaluation"]
    assert result["final_score"] == expected
    assert report["summary"]["average_score"] == expected
    assert list_practice_history(settings.database_path, user_id=2)[0]["average_score"] == expected
    assert result["score_breakdown"]["score"] == (expected / 10 if expected is not None else None)
    assert result["score_provisional"] is (expected is None)
    if expected is None:
        assert result["score_status"] == "insufficient_evidence"
        assert result["ai_score"] == score
        assert result["score_breakdown"]["status"] == "score_mismatch"
    with database(settings.database_path) as connection:
        assert dict(connection.execute("SELECT * FROM interview_answers").fetchone()) == before


def test_history_cannot_count_stale_score_during_queued_grading(tmp_path):
    settings = _settings(tmp_path)
    saved_practice(settings, score=50, pending=1)
    assert list_practice_history(settings.database_path, user_id=2)[0]["average_score"] is None
    assert interview_report(settings, "session-1")["summary"]["scored_answer_count"] == 0


def test_teacher_manual_total_is_not_replaced_by_ai_rubric_math(tmp_path):
    settings = _settings(tmp_path)
    question = _seed_voice_answer(settings)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET assessment_json=?", (json.dumps([
            {"point": p, "status": "missing"} for p in question["key_points"]]),))
    review_answer(settings, answer_id=1, teacher_id=1, action="manual", score=81, feedback="Teacher decision")
    report = interview_report(settings, "session-1")
    assert report["summary"]["average_score"] == report["answers"][0]["evaluation"]["final_score"] == 81


def test_legacy_teacher_practice_total_keeps_both_scales_without_invented_criteria(tmp_path):
    settings = _settings(tmp_path)
    saved_practice(settings, score=80)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET final_score=73,teacher_score=73,reviewed_at='now'")
    report = interview_report(settings, "session-1")
    assert report["summary"]["average_score"] == 73
    assert report["summary"]["practice_grading"]["session"]["score"] == 7.3
    assert report["answers"][0]["evaluation"]["score_breakdown"]["criteria"] == []
    assert list_practice_history(settings.database_path, user_id=2)[0]["average_score"] == 73


def test_false_model_total_is_not_finalized_when_batch_saves_it(test_settings, monkeypatch):
    sid = prepare(test_settings, count=1)["session_id"]
    answer_current(test_settings, sid)
    async def inconsistent(_settings, question, *_args, **_kwargs):
        result = evaluator._compose_result(question, [{"point": p, "status": "missing"}
            for p in question["key_points"]], evaluator="test")
        result["score"] = 100
        return result
    monkeypatch.setattr(session_grading, "evaluate_answer", inconsistent)
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    asyncio.run(jobs.run_once())
    with database(test_settings.database_path) as connection:
        row = connection.execute("SELECT final_score,score,score_provisional FROM interview_answers").fetchone()
    assert row[:] == (None, 100, 1)


@pytest.mark.parametrize("logits", [[-4, 8, -4], [.2, .3, .1]])
def test_neutral_is_unresolved_even_with_high_softmax(monkeypatch, tmp_path, logits):
    fake_backend(monkeypatch, logits)
    result = rubric_transformer.evaluate_with_transformer(tmp_path, NLI_QUESTION, "Một khái niệm khác.")
    assert result["unresolved_points"] == NLI_QUESTION["key_points"]
    assert result["missing_points"] == [] and result["score_provisional"]
    assert result["point_assessments"][0]["status"] == "unresolved"


@pytest.mark.parametrize("eligible,truncated,blocked", [(False, False, True), (None, False, True),
    (True, True, True), (True, False, False)])
def test_high_nli_probability_cannot_bypass_checkpoint_or_truncation_gate(
        test_settings, monkeypatch, tmp_path, eligible, truncated, blocked):
    test_settings.rubric_transformer_path = tmp_path
    (tmp_path / "tokenizer.json").write_text("{}")
    point, answer = "A required concept.", "A correct explanation."
    question = {"key_points": [point]}
    result = evaluator._coerce_llm_result({"point_assessments": [
        {"point": point, "status": "met", "evidence_quote": answer}]}, question, "test", answer)
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", lambda *_args, **_kwargs: {
        "acceptance_eligible": eligible, "point_assessments": [{"truncated": truncated,
        "probabilities": {"entailment": .99, "neutral": .005, "contradiction": .005}}]})
    checked = asyncio.run(evaluator._verify_llm_evidence(test_settings, question, result, answer))
    assert checked["score_provisional"] is blocked
    assert checked["point_assessments"][0]["status"] == ("unresolved" if blocked else "met")


def pending_result(question, reason):
    return evaluator._compose_result(question, [{"point": p, "status": "unresolved",
        "needs_review": True, "review_reason": reason} for p in question["key_points"]],
        evaluator="model-pending", confidence=0, review_required=True)


def due(settings):
    with database(settings.database_path) as connection:
        connection.execute("UPDATE session_grading_jobs SET retry_after=0")


@pytest.mark.parametrize("reason", ["model_timeout", "model_unavailable", "model_output_invalid", "evidence_verifier_unavailable"])
def test_technical_errors_retry_only_failed_answers_and_preserve_recordings(test_settings, monkeypatch, reason):
    sid = prepare(test_settings)["session_id"]
    for _ in range(3):
        answer_current(test_settings, sid)
    with database(test_settings.database_path) as connection:
        before = [tuple(r) for r in connection.execute("SELECT answer_text,question_json FROM interview_answers ORDER BY answer_id")]
        voice = [tuple(r) for r in connection.execute("SELECT raw_text,corrected_text,audio_sha256 FROM speech_transcriptions ORDER BY transcription_id")]
    calls = []
    async def grade(_settings, question, *_args, **_kwargs):
        calls.append(question["uid"])
        if len(calls) == 2:
            return pending_result(question, reason)
        return evaluator._compose_result(question, [{"point": p, "status": "met"}
            for p in question["key_points"]], evaluator="test")
    monkeypatch.setattr(session_grading, "evaluate_answer", grade)
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    asyncio.run(jobs.run_once())
    status = jobs.status(sid)
    assert status["state"] == "queued" and status["pending_count"] == 1
    assert not status["report_ready"] and status["report_available"] and status["retry_at"]
    assert jobs.claim() is None
    due(test_settings)
    asyncio.run(jobs.run_once())
    assert jobs.status(sid)["report_ready"] and len(calls) == 4 and calls[3] == calls[1]
    assert calls.count(calls[0]) == calls.count(calls[2]) == 1
    with database(test_settings.database_path) as connection:
        assert [tuple(r) for r in connection.execute("SELECT answer_text,question_json FROM interview_answers ORDER BY answer_id")] == before
        assert [tuple(r) for r in connection.execute("SELECT raw_text,corrected_text,audio_sha256 FROM speech_transcriptions ORDER BY transcription_id")] == voice


def test_repeated_timeouts_stop_after_three_total_attempts(test_settings, monkeypatch):
    sid = prepare(test_settings, count=1)["session_id"]
    answer_current(test_settings, sid)
    calls = []
    async def fail(_settings, question, *_args, **_kwargs):
        calls.append(question["uid"])
        return pending_result(question, "model_timeout")
    monkeypatch.setattr(session_grading, "evaluate_answer", fail)
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    for attempt in range(3):
        due(test_settings)
        assert asyncio.run(jobs.run_once())
        assert jobs.status(sid)["attempts"] == attempt + 1
    status = jobs.status(sid)
    assert status["state"] == "failed" and not status["can_retry"] and not status["report_ready"]
    assert len(calls) == 3 and status["pending_count"] == 1
    with pytest.raises(ValueError):
        jobs.retry(sid)
    jobs.recover()
    assert not asyncio.run(jobs.run_once())


@pytest.mark.parametrize("reason", ["neutral_evidence", "evidence_disagreement", "evidence_verifier_unvalidated"])
def test_semantic_uncertainty_does_not_trigger_infinite_technical_retries(test_settings, monkeypatch, reason):
    sid = prepare(test_settings, count=1)["session_id"]
    answer_current(test_settings, sid)
    async def uncertain(_settings, question, *_args, **_kwargs):
        return pending_result(question, reason)
    monkeypatch.setattr(session_grading, "evaluate_answer", uncertain)
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    asyncio.run(jobs.run_once())
    status = jobs.status(sid)
    assert status["state"] == "completed" and status["report_ready"] and status["attempts"] == 1
    assert interview_report(test_settings, sid)["summary"]["average_score"] is None
    jobs.recover()
    assert not asyncio.run(jobs.run_once())


@pytest.mark.parametrize("reviewed,attempts,expected", [(False, 1, "queued"), (False, 3, "failed"), (True, 1, "completed")])
def test_recovery_repairs_old_false_completed_jobs_without_resetting_attempts(
        test_settings, reviewed, attempts, expected):
    sid = prepare(test_settings, count=1)["session_id"]
    answer_current(test_settings, sid)
    with database(test_settings.database_path) as connection:
        question = json.loads(connection.execute("SELECT question_json FROM interview_answers").fetchone()[0])
        result = pending_result(question, "model_timeout")
        connection.execute("UPDATE interview_answers SET grading_pending=0,assessment_json=?,score_provisional=1,reviewed_at=?,final_score=?",
            (json.dumps(result["point_assessments"]), "teacher decided" if reviewed else None, 73 if reviewed else None))
        connection.execute("UPDATE session_grading_jobs SET state='completed',attempts=?", (attempts,))
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    jobs.recover()
    jobs.recover()
    assert jobs.status(sid)["state"] == expected and jobs.status(sid)["attempts"] == attempts
    with database(test_settings.database_path) as connection:
        row = connection.execute("SELECT grading_pending,final_score FROM interview_answers").fetchone()
    assert row[:] == ((0, 73) if reviewed else (1, None))


def test_teacher_decision_during_timeout_is_not_requeued(test_settings, monkeypatch):
    sid = prepare(test_settings, count=1)["session_id"]
    answer_current(test_settings, sid)
    async def grade(_settings, question, *_args, **_kwargs):
        with database(test_settings.database_path) as connection:
            connection.execute("UPDATE interview_answers SET reviewed_at='now',teacher_score=75,final_score=75")
        return pending_result(question, "model_timeout")
    monkeypatch.setattr(session_grading, "evaluate_answer", grade)
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    asyncio.run(jobs.run_once())
    assert jobs.status(sid)["state"] == "completed" and jobs.status(sid)["pending_count"] == 0
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT final_score FROM interview_answers").fetchone()[0] == 75


def test_manual_teacher_grade_can_finish_a_batch_after_retry_limit(test_settings, monkeypatch):
    sid = prepare(test_settings, mode="real", count=1)["session_id"]
    answer_current(test_settings, sid)
    async def timeout(_settings, question, *_args, **_kwargs):
        return pending_result(question, "model_timeout")
    monkeypatch.setattr(session_grading, "evaluate_answer", timeout)
    jobs = session_grading.SessionGrading(test_settings, runtime_readiness.RuntimeReadiness(test_settings))
    for _ in range(3):
        due(test_settings)
        asyncio.run(jobs.run_once())
    assert jobs.status(sid)["state"] == "failed"
    with database(test_settings.database_path) as connection:
        answer_id = connection.execute("SELECT answer_id FROM interview_answers").fetchone()[0]
    review_answer(test_settings, answer_id=answer_id, teacher_id=1, action="manual", score=73, feedback="Teacher's assessment")
    assert jobs.status(sid)["state"] == "completed" and jobs.status(sid)["report_ready"]
    assert jobs.status(sid)["attempts"] == 3
    report = interview_report(test_settings, sid)
    assert report["summary"]["average_score"] == 73
    assert report["answers"][0]["evaluation"]["point_assessments"] == []
    assert not asyncio.run(jobs.run_once())


def test_retry_column_migration_is_idempotent_and_does_not_regrade(tmp_path):
    settings = _settings(tmp_path)
    saved_practice(settings, score=80)
    with database(settings.database_path) as connection:
        before = dict(connection.execute("SELECT * FROM interview_answers").fetchone())
        connection.execute("ALTER TABLE session_grading_jobs DROP COLUMN retry_after")
    init_database(settings.database_path)
    init_database(settings.database_path)
    with database(settings.database_path) as connection:
        assert "retry_after" in {row["name"] for row in connection.execute("PRAGMA table_info(session_grading_jobs)")}
        assert dict(connection.execute("SELECT * FROM interview_answers").fetchone()) == before


@pytest.mark.parametrize("already_accepted", [True, False])
def test_old_unaccepted_review_cache_is_invalidated_but_teacher_decisions_remain(tmp_path, already_accepted):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    _save_result(settings, 100)
    if already_accepted:
        review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")
    old_key = "teacher-review-v7-span-correction-evidence|" + review_cache_key(settings).split("|", 1)[1]
    with database(settings.database_path) as connection:
        metadata = json.loads(connection.execute("SELECT review_metadata_json FROM speech_transcriptions").fetchone()[0])
        metadata["review_cache_key"] = old_key
        connection.execute("UPDATE speech_transcriptions SET review_metadata_json=?", (json.dumps(metadata),))
    if already_accepted:
        assert interview_report(settings, "session-1")["answers"][0]["evaluation"]["final_score"] == 100
    else:
        with pytest.raises(TeacherReviewError, match="phiên bản cũ"):
            review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")
