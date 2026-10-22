import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.database import database, init_database
from app.services import audio_lifecycle, exam_policy
from app.services.interview_engine import delete_practice_history, interview_report, list_practice_history
from app.services.teacher_review import review_answer, review_history
from app.services.transcription_store import expire_stale_sessions
from test_audit_20261018 import _make_real_session
from test_speech_jobs import create_job, recording_session, wait_job
from test_teacher_strong_review import _settings, _seed_voice_answer, _save_result


def test_adopted_result_is_frozen_after_a_new_ai_analysis(tmp_path):
    settings = _settings(tmp_path)
    question = _seed_voice_answer(settings)
    _save_result(settings, 100)
    review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET review_ai_evaluation_json='{}',review_ai_score=0,feedback='Old feedback',missing_points_json=?",
                           (json.dumps(question["key_points"]),))
        connection.execute("UPDATE speech_transcriptions SET review_transcript='New, different transcript'")
    result = interview_report(settings, "session-1")
    evaluation = result["answers"][0]["evaluation"]
    assert evaluation["final_score"] == 100 and not evaluation["score_provisional"]
    assert evaluation["grading_source"] == "strong_ai"
    assert evaluation["graded_transcript"].startswith("HTTP là giao thức")
    assert len(evaluation["point_assessments"]) == 2
    assert result["summary"]["gaps"] == []
    assert review_history(settings, answer_id=1)[0]["decision"]["score"] == 100


def test_manual_total_does_not_fabricate_rubric_outcomes(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    _save_result(settings, 100)
    review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")
    review_answer(settings, answer_id=1, teacher_id=1, action="manual", score=65, feedback="Teacher's manual assessment")
    report = interview_report(settings, "session-1")
    evaluation = report["answers"][0]["evaluation"]
    assert evaluation["final_score"] == 65
    assert evaluation["grading_source"] == "teacher_manual"
    assert evaluation["point_assessments"] == report["summary"]["strengths"] == report["summary"]["gaps"] == []
    assert evaluation["feedback"] == "Teacher's manual assessment"
    assert [entry["decision"]["source"] for entry in review_history(settings, answer_id=1)] == ["strong_ai", "teacher_manual"]


def test_migration_preserves_teacher_scores_and_is_idempotent(tmp_path):
    settings = _settings(tmp_path)
    question = _seed_voice_answer(settings)
    review_answer(settings, answer_id=1, teacher_id=1, action="manual", score=72, feedback="Teacher grade")
    with database(settings.database_path) as connection:
        connection.execute("DELETE FROM app_migrations WHERE name='grade-state-v2'")
        connection.execute("UPDATE interview_answers SET assessment_json=?", (json.dumps([{"point": question["key_points"][0], "status": "unresolved"}]),))
    init_database(settings.database_path)
    init_database(settings.database_path)
    with database(settings.database_path) as connection:
        assert connection.execute("SELECT teacher_score,final_score FROM interview_answers").fetchone()[:] == (72, 72)
        assert connection.execute("SELECT COUNT(*) FROM answer_reviews").fetchone()[0] == 1


def test_malformed_old_assessment_is_pending_in_both_views(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_sessions SET interview_mode='practice'")
        connection.execute("UPDATE interview_answers SET assessment_json='{bad json'")
    assert interview_report(settings, "session-1")["summary"]["scored_answer_count"] == 0
    assert list_practice_history(settings.database_path, user_id=2)[0]["average_score"] is None


def test_locked_audio_deletion_is_durable_and_retried(client, recording_session, test_settings, monkeypatch):
    job = wait_job(client, create_job(client))
    queue = client.app.state.speech_jobs
    path = queue.audio_path(queue._owned(job["job_id"], recording_session))
    original = Path.unlink
    def locked(self, *args, **kwargs):
        if self == path:
            raise PermissionError("Simulated Windows file lock")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", locked)
    result = delete_practice_history(test_settings.database_path, session_id="recording-session", user_id=recording_session)
    assert result["audio_cleanup_pending"] == 1 and not result["audio_cleanup_complete"] and path.is_file()
    monkeypatch.setattr(Path, "unlink", original)
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE audio_deletions SET retry_after=0")
    audio_lifecycle.drain_audio_deletions(test_settings.database_path)
    assert not path.exists()
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM audio_deletions").fetchone()[0] == 0


def test_cleanup_never_deletes_a_still_referenced_file(client, recording_session, test_settings):
    job = wait_job(client, create_job(client))
    queue = client.app.state.speech_jobs
    row = queue._owned(job["job_id"], recording_session)
    path = queue.audio_path(row)
    with database(test_settings.database_path) as connection:
        audio_lifecycle.schedule_session_audio(connection, "recording-session", path.parent.parent)
    audio_lifecycle.drain_audio_deletions(test_settings.database_path)
    assert path.is_file()
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT attempts FROM audio_deletions").fetchone()[0] >= 1


def test_cleanup_blocks_paths_outside_storage(test_settings, client):
    outside = test_settings.database_path.parent / "protected.txt"
    outside.write_text("keep", encoding="utf-8")
    root = test_settings.database_path.parent / "audio"
    with database(test_settings.database_path) as connection:
        connection.execute("INSERT INTO audio_deletions(storage_root,audio_path,created_at) VALUES (?,?,CURRENT_TIMESTAMP)", (str(root), "../protected.txt"))
    audio_lifecycle.drain_audio_deletions(test_settings.database_path)
    assert outside.read_text(encoding="utf-8") == "keep"
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT state FROM audio_deletions").fetchone()[0] == "blocked"


def test_predeadline_job_survives_expiry_restart_and_cannot_get_next_question(client, recording_session, test_settings, monkeypatch):
    _make_real_session(test_settings)
    queue = client.app.state.speech_jobs
    claim = queue.claim
    monkeypatch.setattr(queue, "claim", lambda: None)
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE interview_sessions SET requested_count=2 WHERE session_id='recording-session'")
    job = create_job(client)
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE exam_rounds SET ends_at=?", ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),))
    assert expire_stale_sessions(test_settings.database_path) == 0
    resumed = client.get("/api/interviews/recording-session/resume")
    assert resumed.status_code == 200 and resumed.json()["recording_allowed"] is False
    new = client.post("/api/speech/jobs", data={"session_id": "recording-session", "request_key": str(uuid.uuid4())},
                      files={"file": ("new.webm", b"new", "audio/webm")})
    assert new.status_code == 409
    monkeypatch.setattr(queue, "claim", claim)
    finished = wait_job(client, job)
    assert finished["state"] == "completed"
    response = client.post("/api/interviews/recording-session/answer", json={"answer": finished["result"]["text"],
                           "transcription_id": finished["result"]["transcription_id"]})
    assert response.status_code == 200, response.text
    assert response.json()["completed"] and response.json()["next_question"] is None
    assert response.json()["answered_count"] == 1 and response.json()["finish_reason"] == "exam_closed_after_recording"


def test_technical_retry_after_closure_uses_only_received_audio(client, recording_session, test_settings, monkeypatch):
    from app import main
    from app.services.speech_to_text import SpeechToTextError
    _make_real_session(test_settings)
    original = main.transcribe_bytes
    def fail(*args, **kwargs):
        raise SpeechToTextError("Temporary failure")
    monkeypatch.setattr(main, "transcribe_bytes", fail)
    failed = wait_job(client, create_job(client))
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE exam_rounds SET status='closed'")
    monkeypatch.setattr(main, "transcribe_bytes", original)
    retry = client.post(f"/api/speech/jobs/{failed['job_id']}/retry")
    assert retry.status_code == 200
    assert wait_job(client, retry.json())["state"] == "completed"


def test_late_recording_does_not_leave_a_job_or_audio(client, recording_session, test_settings, monkeypatch):
    _make_real_session(test_settings)
    monkeypatch.setattr(exam_policy, "now_utc", lambda: datetime.now(timezone.utc) + timedelta(days=1))
    response = client.post("/api/speech/jobs", data={"session_id": "recording-session", "request_key": str(uuid.uuid4()),
        "accepted_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}, files={"file": ("late.webm", b"late", "audio/webm")})
    assert response.status_code == 409
    assert not list((test_settings.database_path.parent / "audio").rglob("*.webm"))
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM speech_jobs").fetchone()[0] == 0


def test_unreviewed_legacy_migration_changes_status_not_numeric_grade(tmp_path):
    settings = _settings(tmp_path)
    question = _seed_voice_answer(settings)
    with database(settings.database_path) as connection:
        connection.execute("DELETE FROM app_migrations WHERE name='grade-state-v2'")
        connection.execute("UPDATE interview_sessions SET interview_mode='practice'")
        connection.execute("UPDATE interview_answers SET assessment_json=?", (json.dumps([{"point": question["key_points"][0], "status": "unresolved"}]),))
    init_database(settings.database_path)
    with database(settings.database_path) as connection:
        row = connection.execute("SELECT score,ai_score,final_score,score_provisional FROM interview_answers").fetchone()
    assert row[:] == (20, 20, 20, 1)
    assert list_practice_history(settings.database_path, user_id=2)[0]["average_score"] is None


def test_new_worker_after_restart_restores_predeadline_recording(client, recording_session, test_settings, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    _make_real_session(test_settings)
    monkeypatch.setattr(client.app.state.speech_jobs, "claim", lambda: None)
    job = create_job(client)
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE exam_rounds SET ends_at=?", ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),))
    with TestClient(create_app(test_settings)) as restarted:
        assert restarted.post("/api/auth/login", json={"username": "candidate01", "password": "Candidate@123"}).status_code == 200
        restored = wait_job(restarted, job)
        assert restored["state"] == "completed"
        resumed = restarted.post("/api/candidate/exams/AUDIT/start")
        assert resumed.status_code == 201 and resumed.json()["resumed"] and not resumed.json()["recording_allowed"]


def test_custom_audio_root_is_used_by_api_deletion(client, recording_session, test_settings):
    test_settings.audio_storage_dir = test_settings.database_path.parent / "custom-recordings"
    job = wait_job(client, create_job(client))
    queue = client.app.state.speech_jobs
    path = queue.audio_path(queue._owned(job["job_id"], recording_session))
    response = client.delete("/api/candidate/practice-history/recording-session")
    assert response.status_code == 200 and response.json()["audio_cleanup_complete"]
    assert not path.exists()


def test_expiry_during_audio_save_rejects_and_removes_file(client, recording_session, test_settings, monkeypatch):
    _make_real_session(test_settings)
    original = Path.write_bytes
    def save_then_expire(self, data):
        result = original(self, data)
        monkeypatch.setattr(exam_policy, "now_utc", lambda: datetime.now(timezone.utc) + timedelta(days=1))
        return result
    monkeypatch.setattr(Path, "write_bytes", save_then_expire)
    response = client.post("/api/speech/jobs", data={"session_id": "recording-session", "request_key": str(uuid.uuid4())},
                           files={"file": ("late.webm", b"late", "audio/webm")})
    assert response.status_code == 409
    assert not list((test_settings.database_path.parent / "audio").rglob("*.webm"))


def test_partial_audio_write_failure_does_not_leave_private_file(client, recording_session, test_settings, monkeypatch):
    original = Path.write_bytes
    def partial(self, data):
        original(self, data[:2])
        raise OSError("Simulated disk-full")
    monkeypatch.setattr(Path, "write_bytes", partial)
    queue = client.app.state.speech_jobs
    with pytest.raises(OSError, match="disk-full"):
        queue.create(user_id=recording_session, session_id="recording-session", request_key=str(uuid.uuid4()),
            content=b"private-voice", filename="test.webm", mime_type="audio/webm", ambient_noise_dbfs=None, retry_reason=None)
    assert not list((test_settings.database_path.parent / "audio").rglob("*.webm"))


def test_missing_audio_still_allows_manual_teacher_grade(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    (settings.audio_storage_dir / "session-1/voice.webm").unlink()
    result = review_answer(settings, answer_id=1, teacher_id=1, action="manual", score=81, feedback="Graded from available evidence")
    assert result["final_score"] == 81
    report = interview_report(settings, "session-1")
    assert report["answers"][0]["voice"]["audio_available"] is False
    assert report["summary"]["average_score"] == 81


@pytest.mark.parametrize("assessment", ["{}", "[]", "null"])
def test_legacy_score_without_criterion_evidence_is_pending(tmp_path, assessment):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_sessions SET interview_mode='practice'")
        connection.execute("UPDATE interview_answers SET assessment_json=?", (assessment,))
    assert interview_report(settings, "session-1")["summary"]["scored_answer_count"] == 0
    assert list_practice_history(settings.database_path, user_id=2)[0]["average_score"] is None
