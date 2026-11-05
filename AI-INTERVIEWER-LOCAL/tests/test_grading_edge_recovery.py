"""Regression coverage for rubric totals, terminal recovery and malformed saved evidence."""
import asyncio
from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.database import database
from app.main import create_app
from app.services import evaluator, runtime_readiness, session_grading
from app.services.assessment_feedback import assessment_feedback, normalize_assessments
from app.services.interview_engine import interview_report, list_practice_history
from app.services.practice_grading import question_breakdown, validate_ai_grade
from app.services.rubric_contract import digest, rubric_draft
from app.services.teacher_review import (
    TeacherReviewError, list_review_queue, review_answer, review_history,
    review_reanalysis_context, save_review_reanalysis,
)
from test_grading_reliability import due, pending_result, saved_practice
from test_low_memory_sessions import prepare, answer_current
from test_teacher_strong_review import _settings, _seed_voice_answer, _save_result


def jobs_for(settings):
    return session_grading.SessionGrading(settings, runtime_readiness.RuntimeReadiness(settings))


def terminal_failure(settings, monkeypatch):
    sid = prepare(settings, mode="real", count=1)["session_id"]
    answer_current(settings, sid)
    async def timeout(_settings, question, *_args, **_kwargs):
        return pending_result(question, "model_timeout")
    monkeypatch.setattr(session_grading, "evaluate_answer", timeout)
    jobs = jobs_for(settings)
    for _ in range(3):
        due(settings)
        asyncio.run(jobs.run_once())
    assert jobs.status(sid)["state"] == "failed" and jobs.status(sid)["attempts"] == 3
    with database(settings.database_path) as connection:
        row = connection.execute("SELECT answer_id,question_json FROM interview_answers").fetchone()
    return sid, row["answer_id"], json.loads(row["question_json"]), jobs


@pytest.mark.parametrize("score,action", [(100, "accept_ai"), (0, "manual")])
def test_strong_review_can_finish_terminal_failure_without_losing_voice(tmp_path, monkeypatch, score, action):
    settings = _settings(tmp_path)
    sid, aid, question, jobs = terminal_failure(settings, monkeypatch)
    with database(settings.database_path) as connection:
        before = tuple(connection.execute("SELECT answer_text,question_json,transcription_id FROM interview_answers").fetchone())
        voice = dict(connection.execute("SELECT * FROM speech_transcriptions").fetchone())
    context = review_reanalysis_context(settings, answer_id=aid)
    assert context["audio_path_resolved"].is_file() and not context["cached"]
    result = save_review_reanalysis(settings, answer_id=aid, transcription_id=context["transcription_id"],
        transcription={"text": "Strong transcript", "model": "large-v3"},
        evaluation={"score": score, "point_assessments": [
            {"point": p, "status": "met" if score == 100 else "missing"} for p in question["key_points"]]})
    assert result["can_accept_ai"] is (score == 100)
    if score == 0:
        with pytest.raises(TeacherReviewError):
            review_answer(settings, answer_id=aid, teacher_id=1, action="accept_ai", score=None, feedback="")
    review_answer(settings, answer_id=aid, teacher_id=1, action=action,
        score=35 if action == "manual" else None, feedback="Teacher decision")
    assert jobs.status(sid)["report_ready"] and jobs.status(sid)["attempts"] == 3
    assert len(review_history(settings, answer_id=aid)) == 1
    assert not asyncio.run(jobs.run_once())
    with database(settings.database_path) as connection:
        assert tuple(connection.execute("SELECT answer_text,question_json,transcription_id FROM interview_answers").fetchone()) == before
        after = dict(connection.execute("SELECT * FROM speech_transcriptions").fetchone())
    assert all(after[key] == voice[key] for key in (
        "raw_text", "corrected_text", "audio_path", "audio_sha256", "confirmed_text_sha256"))


@pytest.mark.parametrize("phase", ["active", "queued", "processing", "no_job"])
def test_strong_review_never_bypasses_active_or_unowned_pending_work(tmp_path, phase):
    settings = _settings(tmp_path)
    sid = prepare(settings, mode="real", count=2 if phase == "active" else 1)["session_id"]
    answer_current(settings, sid)
    with database(settings.database_path) as connection:
        aid = connection.execute("SELECT answer_id FROM interview_answers").fetchone()[0]
        if phase == "processing":
            connection.execute("UPDATE session_grading_jobs SET state='processing'")
        elif phase == "no_job":
            connection.execute("DELETE FROM session_grading_jobs")
    with pytest.raises(TeacherReviewError):
        review_reanalysis_context(settings, answer_id=aid)


@pytest.mark.parametrize("statuses,score,weights", [
    (["met", "met"], 80, None), (["missing", "missing"], 100, None),
    (["met", "missing"], 50, [3, 1]),
])
def test_strong_review_rejects_false_rubric_totals_before_writing(tmp_path, statuses, score, weights):
    settings = _settings(tmp_path)
    question = _seed_voice_answer(settings)
    if weights:
        question["key_point_weights"] = dict(zip(question["key_points"], weights))
        with database(settings.database_path) as connection:
            connection.execute("UPDATE interview_answers SET question_json=?", (json.dumps(question),))
    with database(settings.database_path) as connection:
        before = dict(connection.execute("SELECT * FROM speech_transcriptions").fetchone())
    with pytest.raises(TeacherReviewError):
        save_review_reanalysis(settings, answer_id=1, transcription_id="stt-1",
            transcription={"text": "Transcript must not be committed with a false total"},
            evaluation={"score": score, "point_assessments": [
                {"point": p, "status": s} for p, s in zip(question["key_points"], statuses)]})
    with database(settings.database_path) as connection:
        assert dict(connection.execute("SELECT * FROM speech_transcriptions").fetchone()) == before
        assert connection.execute("SELECT review_ai_score FROM interview_answers").fetchone()[0] is None


def test_current_version_cache_cannot_bypass_rubric_total_validation(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    result = _save_result(settings, 100)
    result["review_ai_evaluation"]["point_assessments"][0]["status"] = "missing"
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET review_ai_evaluation_json=?",
                           (json.dumps(result["review_ai_evaluation"]),))
    assert not list_review_queue(settings)[0]["can_accept_ai"]
    assert not review_reanalysis_context(settings, answer_id=1)["cached"]
    with pytest.raises(TeacherReviewError):
        review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")
    assert not review_history(settings, answer_id=1)


@pytest.mark.parametrize("weights,score", [([3, 1], 75), ([7, 3], 70)])
def test_valid_weighted_strong_review_remains_eligible(tmp_path, weights, score):
    settings = _settings(tmp_path)
    question = _seed_voice_answer(settings)
    question["key_point_weights"] = dict(zip(question["key_points"], weights))
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET question_json=?", (json.dumps(question),))
    result = save_review_reanalysis(settings, answer_id=1, transcription_id="stt-1",
        transcription={"text": "Strong transcript"}, evaluation={"score": score, "point_assessments": [
            {"point": p, "status": "met" if i == 0 else "missing"} for i, p in enumerate(question["key_points"])]})
    assert result["can_accept_ai"]
    assert review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")["final_score"] == score


def test_atomic_partial_cannot_be_adopted_as_half_credit(tmp_path):
    settings = _settings(tmp_path)
    question = _seed_voice_answer(settings)
    contract = rubric_draft(question)
    question["rubric_snapshot"] = {"contract": contract, "sha256": digest(contract)}
    question["key_point_weights"] = {p: 1.0 for p in question["key_points"]}
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET question_json=?", (json.dumps(question),))
    result = _save_result(settings, 75)
    assert not result["can_accept_ai"] and result["score_provisional"]
    assert result["review_ai_evaluation"]["score_provisional"]
    with pytest.raises(TeacherReviewError):
        review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")
    assert review_answer(settings, answer_id=1, teacher_id=1, action="manual", score=73,
        feedback="Teacher total does not infer half-credit for atomic criteria")["final_score"] == 73


@pytest.mark.parametrize("case", ["empty", "missing", "unresolved", "needs_review", "boolean"])
def test_every_nonfinal_breakdown_is_marked_provisional(case):
    question = {"key_points": ["first", "second"]}
    result = {"score": 100, "score_provisional": False, "point_assessments": [
        {"point": p, "status": "met"} for p in question["key_points"]]}
    if case == "empty":
        result["point_assessments"] = []
    elif case == "missing":
        result["point_assessments"].pop()
    elif case == "unresolved":
        result["point_assessments"][0]["status"] = "unresolved"
    elif case == "needs_review":
        result["point_assessments"][0]["needs_review"] = True
    else:
        result["score"] = True
    assert validate_ai_grade(question, result)["status"] != "final"
    assert result["score_provisional"]


@pytest.mark.parametrize("score", [100, True, float("nan"), float("inf"), -1, 101, 10 ** 1000])
def test_batch_never_persists_an_invalid_or_evidence_free_final(tmp_path, monkeypatch, score):
    settings = _settings(tmp_path)
    sid = prepare(settings, count=1)["session_id"]
    answer_current(settings, sid)
    async def malformed(_settings, question, *_args, **_kwargs):
        result = evaluator._compose_result(question, [{"point": p, "status": "met"}
            for p in question["key_points"]], evaluator="test")
        result.update(score=score, point_assessments=[], score_provisional=False)
        return result
    monkeypatch.setattr(session_grading, "evaluate_answer", malformed)
    asyncio.run(jobs_for(settings).run_once())
    with database(settings.database_path) as connection:
        row = connection.execute("SELECT final_score,score_provisional FROM interview_answers").fetchone()
    assert row["final_score"] is None and row["score_provisional"] == 1
    assert interview_report(settings, sid)["answers"][0]["evaluation"]["final_score"] is None


@pytest.mark.parametrize("field,value", [
    ("status", []), ("status", {}), ("review_reason", []), ("review_reason", {}),
    ("point", []), ("point", {}),
])
def test_nested_malformed_assessment_is_read_only_and_unresolved(tmp_path, field, value):
    settings = _settings(tmp_path)
    question = saved_practice(settings, score=50)
    assessments = [{"point": p, "status": "met" if i == 0 else "missing"}
                   for i, p in enumerate(question["key_points"])]
    assessments[0][field] = value
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET assessment_json=?", (json.dumps(assessments),))
        before = dict(connection.execute("SELECT * FROM interview_answers").fetchone())
    report = interview_report(settings, "session-1")
    assert report["answers"][0]["evaluation"]["final_score"] is None
    assert list_practice_history(settings.database_path, user_id=2)[0]["average_score"] is None
    with database(settings.database_path) as connection:
        assert dict(connection.execute("SELECT * FROM interview_answers").fetchone()) == before


@pytest.mark.parametrize("bad", [None, 42, []])
def test_extra_malformed_entries_cannot_be_silently_dropped_for_full_credit(bad):
    raw = [{"point": "claim", "status": "met"}, bad]
    original = deepcopy(raw)
    normalized = normalize_assessments(raw)
    assert raw == original and len(normalized) == 2
    assert normalized[1]["needs_review"]
    assert question_breakdown({"key_points": ["claim"]}, {
        "final_score": 100, "point_assessments": raw}, completed=True)["score"] is None
    assert assessment_feedback({"point_assessments": raw})["review_reasons"]


def teacher_client(settings, monkeypatch):
    monkeypatch.setattr(main_module, "get_user_by_token", lambda *_args: {
        "user_id": 1, "username": "teacher", "role": "teacher"})
    return TestClient(create_app(settings), raise_server_exceptions=False)


def test_http_strong_model_route_is_reachable_after_terminal_failure(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    _sid, aid, _question, _jobs = terminal_failure(settings, monkeypatch)
    called = []
    def no_real_model(*_args, **_kwargs):
        called.append(True)
        raise main_module.SpeechToTextError("Test stops before model loading")
    monkeypatch.setattr(main_module, "transcribe_review_audio", no_real_model)
    response = teacher_client(settings, monkeypatch).post(f"/api/teacher/answers/{aid}/ai-review")
    assert response.status_code == 503 and called


@pytest.mark.parametrize("field", ["status", "review_reason"])
def test_http_report_survives_malformed_nested_assessment(tmp_path, monkeypatch, field):
    settings = _settings(tmp_path)
    question = saved_practice(settings, score=50)
    assessments = [{"point": p, "status": "met" if i == 0 else "missing"}
                   for i, p in enumerate(question["key_points"])]
    assessments[0][field] = []
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET assessment_json=?", (json.dumps(assessments),))
    response = teacher_client(settings, monkeypatch).get("/api/teacher/results/session-1")
    assert response.status_code == 200
    assert response.json()["answers"][0]["evaluation"]["final_score"] is None
