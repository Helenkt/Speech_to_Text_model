import json
import threading
import time
import uuid

import pytest

from app import main as main_module
from app.database import database
from app.services.speech_jobs import SpeechJobError
from app.services.speech_to_text import SpeechToTextError
from app.services.interview_engine import interview_report, list_practice_history


@pytest.fixture
def recording_session(client, login_candidate, test_settings, monkeypatch):
    question = {"id": "STACK", "uid": "en:STACK", "language": "en", "subject": "DSA101",
                "competency": "Concept", "topic": "Stack", "concept": "Stack", "difficulty": "Medium",
                "question": "What is a stack?", "reference_answer": "A stack is LIFO", "key_points": ["A stack is LIFO"]}
    with database(test_settings.database_path) as connection:
        connection.execute("""INSERT INTO interview_sessions
            (session_id,user_id,candidate_name,language,subject,requested_count,current_question_uid,
             current_question_json,current_difficulty_rank,evaluator_requested,created_at,mic_check_result_json)
            VALUES ('recording-session',?,'Test','en','DSA101',1,'en:STACK',?,2,'rule',CURRENT_TIMESTAMP,'{"ready":true}')""",
            (login_candidate["user_id"], json.dumps(question)))

    def transcribe(*_args, **kwargs):
        assert kwargs["language"] == "en"
        return {"text": "A stack is LIFO.", "model": "stub", "runtime": "test", "uncertain_spans": [],
                "metrics": {"confidence": .98, "word_count": 4, "uncertain_word_ratio": 0,
                            "speech_duration_seconds": 3, "average_no_speech_probability": .01}}

    async def correct(_settings, text, **_kwargs):
        return {"raw_text": text, "corrected_text": text, "correction_applied": False}
    monkeypatch.setattr(main_module, "transcribe_bytes", transcribe)
    monkeypatch.setattr(main_module, "correct_transcript", correct)
    return login_candidate["user_id"]


def create_job(client, request_key=None, content=b"saved-voice"):
    response = client.post("/api/speech/jobs", data={"session_id": "recording-session", "request_key": request_key or str(uuid.uuid4())},
                           files={"file": ("answer.webm", content, "audio/webm")})
    assert response.status_code == 202, response.text
    return response.json()


def wait_job(client, job):
    for _ in range(200):
        response = client.get(f"/api/speech/jobs/{job['job_id']}")
        assert response.status_code == 200, response.text
        job = response.json()
        if job["state"] in {"failed", "completed", "cancelled"}:
            return job
        time.sleep(.025)
    pytest.fail("Local test job did not finish")


def test_audio_is_saved_and_replayed_without_duplicate_transcriptions(client, recording_session, test_settings):
    key = str(uuid.uuid4())
    first = create_job(client, key)
    assert first["audio_saved"] is True
    finished = wait_job(client, first)
    assert finished["state"] == "completed"
    assert finished["result"]["transcript_status"] == "processed"
    assert finished["result"]["accuracy_percent"] is None
    repeated = create_job(client, key)
    assert repeated["job_id"] == first["job_id"]
    assert client.get("/api/speech/jobs?session_id=recording-session").json()["job"]["job_id"] == first["job_id"]
    resumed = client.get("/api/interviews/recording-session/resume")
    assert resumed.status_code == 200 and resumed.json()["microphone_check"]["ready"]
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM speech_transcriptions").fetchone()[0] == 1
        path = connection.execute("SELECT audio_path FROM speech_jobs").fetchone()[0]
    assert (test_settings.database_path.parent / "audio" / path).read_bytes() == b"saved-voice"
    changed = client.post("/api/speech/jobs", data={"session_id": "recording-session", "request_key": key},
                          files={"file": ("answer.webm", b"different", "audio/webm")})
    assert changed.status_code == 409
    with pytest.raises(SpeechJobError):
        client.app.state.speech_jobs.status(first["job_id"], recording_session + 999)


def test_failed_stt_can_retry_the_same_audio(client, recording_session, test_settings, monkeypatch):
    original = main_module.transcribe_bytes
    def fail(*_args, **_kwargs):
        raise SpeechToTextError("Temporary test failure")
    monkeypatch.setattr(main_module, "transcribe_bytes", fail)
    failed = wait_job(client, create_job(client))
    assert failed["state"] == "failed" and failed["retryable"]
    assert failed["audio_saved"]
    monkeypatch.setattr(main_module, "transcribe_bytes", original)
    retried = client.post(f"/api/speech/jobs/{failed['job_id']}/retry")
    assert retried.status_code == 200
    finished = wait_job(client, retried.json())
    assert finished["state"] == "completed" and finished["attempts"] == 2
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM speech_jobs").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM speech_transcriptions").fetchone()[0] == 1


def test_cancellation_does_not_create_a_transcript_or_lose_audio(client, recording_session, test_settings, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    original = main_module.transcribe_bytes
    def blocked(*args, **kwargs):
        entered.set()
        release.wait(5)
        return original(*args, **kwargs)
    monkeypatch.setattr(main_module, "transcribe_bytes", blocked)
    job = create_job(client)
    try:
        assert entered.wait(3)
        assert client.post(f"/api/speech/jobs/{job['job_id']}/cancel").json()["cancel_requested"]
    finally:
        release.set()
    cancelled = wait_job(client, job)
    assert cancelled["state"] == "cancelled" and cancelled["audio_saved"]
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM speech_transcriptions").fetchone()[0] == 0


def test_replayed_answer_returns_the_original_receipt(client, recording_session, test_settings):
    job = wait_job(client, create_job(client))
    body = {"answer": "Client text cannot replace the recording", "transcription_id": job["result"]["transcription_id"]}
    one = client.post("/api/interviews/recording-session/answer", json=body)
    two = client.post("/api/interviews/recording-session/answer", json=body)
    assert one.status_code == two.status_code == 200
    assert one.json() == two.json()
    with database(test_settings.database_path) as connection:
        row = connection.execute("SELECT answer_text FROM interview_answers").fetchall()
        assert len(row) == 1 and row[0][0] == "A stack is LIFO."


def test_uncertain_transcript_is_not_final_or_used_to_lower_difficulty(client, recording_session, test_settings, monkeypatch):
    original = main_module.transcribe_bytes
    def uncertain(*args, **kwargs):
        result = original(*args, **kwargs)
        result["uncertain_spans"] = ["LIFO"]
        return result
    monkeypatch.setattr(main_module, "transcribe_bytes", uncertain)
    job = wait_job(client, create_job(client))
    assert job["result"]["transcript_status"] == "needs_review"
    response = client.post("/api/interviews/recording-session/answer", json={"answer": job["result"]["text"],
                          "transcription_id": job["result"]["transcription_id"]})
    assert response.status_code == 200, response.text
    assert response.json()["evaluation"]["score_provisional"] is True
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT final_score FROM interview_answers").fetchone()[0] is None
        assert connection.execute("SELECT current_difficulty_rank FROM interview_sessions").fetchone()[0] == 2
    report = interview_report(test_settings, "recording-session")
    assert report["summary"]["scored_answer_count"] == 0
    assert report["summary"]["strengths"] == report["summary"]["gaps"] == []
    assert list_practice_history(test_settings.database_path, user_id=recording_session)[0]["average_score"] is None


def test_quality_rejection_keeps_audio_without_endless_reprocessing(client, recording_session, monkeypatch):
    original = main_module.transcribe_bytes
    def silence(*args, **kwargs):
        return {**original(*args, **kwargs), "text": ""}
    monkeypatch.setattr(main_module, "transcribe_bytes", silence)
    job = wait_job(client, create_job(client))
    assert job["state"] == "failed" and not job["retryable"] and job["audio_saved"]
    assert client.post(f"/api/speech/jobs/{job['job_id']}/retry").status_code == 409


@pytest.mark.parametrize("noise", ["nan", "inf", "1", "-101"])
def test_invalid_noise_metadata_cannot_poison_saved_jobs(client, recording_session, noise):
    response = client.post("/api/speech/jobs", data={"session_id": "recording-session", "request_key": str(uuid.uuid4()), "ambient_noise_dbfs": noise},
                           files={"file": ("answer.webm", b"audio", "audio/webm")})
    assert response.status_code == 422


def test_interrupted_worker_lease_keeps_audio_and_allows_recovery(client, recording_session, test_settings, monkeypatch):
    queue = client.app.state.speech_jobs
    original = queue.claim
    monkeypatch.setattr(queue, "claim", lambda: None)
    job = create_job(client)
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE speech_jobs SET state='processing', worker_id='dead-worker', lease_until=0 WHERE job_id=?", (job["job_id"],))
    monkeypatch.setattr(queue, "claim", original)
    interrupted = wait_job(client, job)
    assert interrupted["state"] == "failed" and interrupted["retryable"] and interrupted["audio_saved"]
    response = client.post(f"/api/speech/jobs/{job['job_id']}/retry")
    assert response.status_code == 200
    assert wait_job(client, response.json())["state"] == "completed"


def test_crash_after_transcript_commit_replays_canonical_text_without_stt(client, recording_session, test_settings, monkeypatch):
    job = wait_job(client, create_job(client))
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE speech_jobs SET state='failed', retryable=1, result_json=NULL WHERE job_id=?", (job["job_id"],))
    def must_not_decode(*_args, **_kwargs):
        raise AssertionError("Committed transcript must not be inferred again")
    monkeypatch.setattr(main_module, "transcribe_bytes", must_not_decode)
    response = client.post(f"/api/speech/jobs/{job['job_id']}/retry")
    restored = wait_job(client, response.json())
    assert restored["state"] == "completed"
    assert restored["result"]["text"] == job["result"]["text"]
    assert restored["result"]["transcription_id"] == job["result"]["transcription_id"]
