"""Adversarial audit reproductions; no production data or model changes."""
import json
from datetime import datetime, timedelta, timezone

from app.database import database
from app.services import interview_engine
from app.services.interview_engine import delete_practice_history, interview_report, list_practice_history
from app.services.teacher_review import review_answer
from test_speech_jobs import create_job, recording_session, wait_job
from test_teacher_strong_review import _save_result, _seed_voice_answer, _settings


def _make_real_session(settings):
    now = datetime.now(timezone.utc)
    with database(settings.database_path) as connection:
        teacher_id = connection.execute("SELECT user_id FROM users WHERE role='teacher' LIMIT 1").fetchone()[0]
        connection.execute("""INSERT INTO exam_rounds
            (exam_round_id,exam_code,title,language,subject,question_count,starting_difficulty,
             answer_mode,starts_at,ends_at,created_by,created_at,updated_at)
            VALUES ('audit-exam','AUDIT','Audit','en','DSA101',1,'Medium','voice',?,?,?,?,?)""",
            ((now - timedelta(hours=1)).isoformat(), (now + timedelta(hours=1)).isoformat(),
             teacher_id, now.isoformat(), now.isoformat()))
        connection.execute("UPDATE interview_sessions SET interview_mode='real',exam_round_id='audit-exam' WHERE session_id='recording-session'")


def test_exam_closed_during_grading_finishes_received_question_only(client, recording_session, test_settings, monkeypatch):
    _make_real_session(test_settings)
    job = wait_job(client, create_job(client))
    original = interview_engine.evaluate_answer

    async def close_exam_then_evaluate(*args, **kwargs):
        with database(test_settings.database_path) as connection:
            connection.execute("UPDATE exam_rounds SET status='closed' WHERE exam_round_id='audit-exam'")
        return await original(*args, **kwargs)

    monkeypatch.setattr(interview_engine, "evaluate_answer", close_exam_then_evaluate)
    response = client.post("/api/interviews/recording-session/answer", json={
        "answer": job["result"]["text"], "transcription_id": job["result"]["transcription_id"]})
    # Adopted policy: a server-received recording may finish, but gets no next question.
    assert response.status_code == 200, response.text
    assert response.json()["completed"] is True
    assert response.json()["finish_reason"] == "exam_closed_after_recording"
    assert response.json()["next_question"] is None
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM interview_answers").fetchone()[0] == 1


def test_report_uses_adopted_strong_rubric_not_original_missing_points(tmp_path):
    settings = _settings(tmp_path)
    question = _seed_voice_answer(settings)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET missing_points_json=? WHERE answer_id=1",
                           (json.dumps(question["key_points"]),))
    _save_result(settings, 100)
    review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")
    report = interview_report(settings, "session-1")
    assert report["summary"]["average_score"] == 100
    assert report["summary"]["gaps"] == [], f"Adopted 100/100 still reports missing: {report['summary']['gaps']}"
    assert report["answers"][0]["evaluation"]["point_assessments"] == [
        {"point": point, "status": "met"} for point in question["key_points"]]


def test_missing_audio_does_not_hide_completed_job_status(client, recording_session, test_settings):
    job = wait_job(client, create_job(client))
    assert job["state"] == "completed"
    queue = client.app.state.speech_jobs
    queue.audio_path(queue._owned(job["job_id"], recording_session)).unlink()
    response = client.get(f"/api/speech/jobs/{job['job_id']}")
    assert response.status_code == 200, f"Saved result cannot be read: {response.status_code} {response.text}"
    assert response.json()["audio_saved"] is False
    assert response.json()["result"]["text"] == "A stack is LIFO."


def test_permanent_practice_deletion_removes_private_audio(client, recording_session, test_settings):
    job = wait_job(client, create_job(client))
    queue = client.app.state.speech_jobs
    path = queue.audio_path(queue._owned(job["job_id"], recording_session))
    assert path.is_file()
    delete_practice_history(test_settings.database_path, session_id="recording-session", user_id=recording_session)
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM interview_sessions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM speech_jobs").fetchone()[0] == 0
    assert not path.exists(), "Permanent deletion retains private voice without a database owner"


def test_closed_exam_does_not_enqueue_expensive_stt(client, recording_session, test_settings, monkeypatch):
    _make_real_session(test_settings)
    queue = client.app.state.speech_jobs
    monkeypatch.setattr(queue, "claim", lambda: None)
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE exam_rounds SET status='closed' WHERE exam_round_id='audit-exam'")
    import uuid
    response = client.post("/api/speech/jobs", data={"session_id": "recording-session", "request_key": str(uuid.uuid4())},
                           files={"file": ("answer.webm", b"test-audio", "audio/webm")})
    assert response.status_code == 409, f"Closed exam queued STT: {response.status_code} {response.text}"


def test_legacy_unresolved_grade_is_not_counted_in_practice_history(tmp_path):
    settings = _settings(tmp_path)
    question = _seed_voice_answer(settings)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_sessions SET interview_mode='practice' WHERE session_id='session-1'")
        connection.execute("UPDATE interview_answers SET score_provisional=0,assessment_json=? WHERE answer_id=1",
            (json.dumps([{"point": question["key_points"][0], "status": "unresolved", "needs_review": True}]),))
    report = interview_report(settings, "session-1")
    assert report["summary"]["scored_answer_count"] == 0
    history = list_practice_history(settings.database_path, user_id=2)
    assert history[0]["average_score"] is None, f"History treats legacy unresolved result as final: {history[0]['average_score']}"
