import asyncio
import json
import threading
import time

import pytest

from app import main
from app.database import database
from app.services import evaluator, session_grading
from app.services.interview_engine import InterviewError, submit_answer
from app.services.question_importer import import_question_bank
from app.services.transcription_store import (
    draft_transcription, save_microphone_check, save_transcription, transcript_sha256,
)
from test_low_memory_sessions import prepare, answer_current


@pytest.fixture
def preview_session(client, login_candidate, test_settings, monkeypatch):
    test_settings.defer_grading_until_finish = True
    questions = [
        {"id": "preview-stack", "language": "en", "subject": "DSA101", "difficulty": "Easy",
         "question": "What is a stack?", "reference_answer": "A stack is LIFO.", "key_points": ["A stack is LIFO"]},
        {"id": "preview-queue", "language": "en", "subject": "DSA101", "difficulty": "Medium",
         "question": "What is a queue?", "reference_answer": "A queue is FIFO.", "key_points": ["A queue is FIFO"]},
    ]
    import_question_bank(test_settings.database_path, json.dumps(questions).encode(), filename="course.json")
    response = client.post("/api/interviews/start", json={"language": "en", "subject": "DSA101",
        "question_count": 2, "starting_difficulty": "Easy"})
    assert response.status_code == 201, response.text
    sid = response.json()["session_id"]
    save_microphone_check(test_settings.database_path, session_id=sid, user_id=login_candidate["user_id"], result={"ready": True})
    corrected = {"A stack is lee foe.": "A stack is LIFO.",
                 "A stack uses last in first out.": "A stack uses last in first out.",
                 "A queue is fee foe.": "A queue is FIFO."}
    recordings = {b"first": "A stack is lee foe.", b"retake": "A stack uses last in first out.", b"queue": "A queue is fee foe."}
    correction_calls, grading_calls = [], []
    def transcribe(_settings, content, **kwargs):
        return {"text": recordings[content], "model": "test-stt", "runtime": "cpu/int8", "uncertain_spans": [],
                "metrics": {"confidence": .98, "word_count": 8, "uncertain_word_ratio": 0,
                            "speech_duration_seconds": 3, "average_no_speech_probability": .01}}
    async def correct(settings, raw, **kwargs):
        assert kwargs["allow_llm"] is True
        correction_calls.append(raw)
        return {"raw_text": raw, "corrected_text": corrected[raw], "correction_applied": corrected[raw] != raw,
                "correction_engine": "test-preview", "corrections": [], "rejected_corrections": []}
    async def grade(settings, question, text, **kwargs):
        grading_calls.append((question["uid"], text))
        return evaluator._compose_result(question, [{"point": p, "status": "met"} for p in question["key_points"]], evaluator="test-grade")
    monkeypatch.setattr(main, "transcribe_bytes", transcribe)
    monkeypatch.setattr(main, "correct_transcript", correct)
    monkeypatch.setattr(session_grading, "evaluate_answer", grade)
    return {"sid": sid, "corrections": correction_calls, "grades": grading_calls, "transcribe": transcribe}


def preview(client, sid, content=b"first"):
    response = client.post("/api/speech/transcribe", data={"session_id": sid},
                           files={"file": ("answer.webm", content, "audio/webm")})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["answer_stage"] == "draft"
    assert result["requires_confirmation"] and not result["transcript_editable"]
    assert result["preview_sha256"] == transcript_sha256(result["text"])
    return result


def confirm(client, sid, draft, **extra):
    return client.post(f"/api/interviews/{sid}/transcriptions/{draft['transcription_id']}/confirm",
                       json={"preview_sha256": draft["preview_sha256"], **extra})


def test_preview_is_corrected_durable_but_not_an_answer(client, preview_session, test_settings):
    sid = preview_session["sid"]
    draft = preview(client, sid)
    assert draft["text"] == "A stack is LIFO."
    restored = client.get(f"/api/interviews/{sid}/draft").json()
    assert restored["can_confirm"] and restored["can_record"]
    assert restored["draft"]["text"] == draft["text"]
    assert restored["draft"]["preview_sha256"] == draft["preview_sha256"]
    assert restored["draft"]["audio_saved"]
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT answered_count FROM interview_sessions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM interview_answers").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM session_grading_jobs").fetchone()[0] == 0
        assert connection.execute("SELECT consumed,confirmed_at FROM speech_transcriptions").fetchone()[:] == (0, None)
    assert preview_session["corrections"] == ["A stack is lee foe."]
    assert preview_session["grades"] == []


def test_confirmation_rejects_wrong_preview_or_edited_text(client, preview_session, test_settings):
    sid = preview_session["sid"]
    draft = preview(client, sid)
    assert confirm(client, sid, draft, preview_sha256="0"*64).status_code == 409
    assert confirm(client, sid, draft, answer="Student edited the answer").status_code == 422
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM interview_answers").fetchone()[0] == 0


def test_retake_supersedes_preview_and_confirmation_is_idempotent(client, preview_session, test_settings):
    sid = preview_session["sid"]
    first = preview(client, sid)
    second = preview(client, sid, b"retake")
    assert first["transcription_id"] != second["transcription_id"]
    assert confirm(client, sid, first).status_code == 409
    old_job = client.get(f"/api/speech/jobs/{first['transcription_id']}").json()
    assert old_job["result"]["answer_stage"] == "superseded"
    assert not old_job["result"]["attempt"]["can_retry"]
    response = confirm(client, sid, second)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["answer_confirmed"] and not result["completed"]
    assert result["confirmation"]["preview_sha256"] == second["preview_sha256"]
    assert result["next_question"]["question"] == "What is a queue?"
    assert confirm(client, sid, second).json() == result
    assert confirm(client, sid, second, preview_sha256="0"*64).status_code == 409
    status = client.get(f"/api/speech/jobs/{second['transcription_id']}").json()["result"]
    assert status["answer_stage"] == "confirmed" and not status["requires_confirmation"]
    assert not status["attempt"]["can_retry"]
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT answer_text FROM interview_answers").fetchone()[0] == second["text"]
        row = connection.execute("SELECT consumed,confirmed_at,confirmed_text_sha256 FROM speech_transcriptions WHERE transcription_id=?",
                                 (second["transcription_id"],)).fetchone()
        assert row["consumed"] and row["confirmed_at"] and row["confirmed_text_sha256"] == second["preview_sha256"]
    assert preview_session["grades"] == []


def test_only_confirmed_transcripts_are_graded_and_never_rewritten(client, preview_session, test_settings):
    sid = preview_session["sid"]
    unused = preview(client, sid)
    first = preview(client, sid, b"retake")
    assert confirm(client, sid, first).status_code == 200
    second = preview(client, sid, b"queue")
    assert preview_session["grades"] == []
    with database(test_settings.database_path) as connection:
        before = [tuple(row) for row in connection.execute("SELECT transcription_id,raw_text,corrected_text,metadata_json,audio_sha256 FROM speech_transcriptions ORDER BY created_at")]
    result = confirm(client, sid, second)
    assert result.status_code == 200 and result.json()["completed"]
    for _ in range(150):
        if client.get(f"/api/interviews/{sid}/grading").json()["report_ready"]:
            break
        time.sleep(.02)
    report = client.get(f"/api/interviews/{sid}/report").json()
    assert report["grading"]["report_ready"]
    assert [text for _, text in preview_session["grades"]] == [first["text"], second["text"]]
    assert len(preview_session["corrections"]) == 3
    assert [item["answer"] for item in report["answers"]] == [first["text"], second["text"]]
    with database(test_settings.database_path) as connection:
        after = [tuple(row) for row in connection.execute("SELECT transcription_id,raw_text,corrected_text,metadata_json,audio_sha256 FROM speech_transcriptions ORDER BY created_at")]
        assert before == after
        assert connection.execute("SELECT COUNT(*) FROM interview_answers WHERE transcription_id=?", (unused["transcription_id"],)).fetchone()[0] == 0


def test_missing_temporary_audio_cannot_be_confirmed(client, preview_session, test_settings):
    sid = preview_session["sid"]
    draft = preview(client, sid)
    with database(test_settings.database_path) as connection:
        relative = connection.execute("SELECT audio_path FROM speech_transcriptions WHERE transcription_id=?", (draft["transcription_id"],)).fetchone()[0]
    root = (test_settings.audio_storage_dir or test_settings.database_path.parent / "audio").resolve()
    path = (root / relative).resolve()
    assert path.is_relative_to(root)
    path.unlink()
    restored = client.get(f"/api/interviews/{sid}/draft").json()
    assert not restored["can_confirm"] and not restored["draft"]["audio_saved"]
    assert confirm(client, sid, draft).status_code == 409


def test_confirmation_does_not_wait_for_new_recording_and_cannot_advance(client, preview_session, monkeypatch):
    sid = preview_session["sid"]
    draft = preview(client, sid)
    entered, release = threading.Event(), threading.Event()
    def blocked(*args, **kwargs):
        entered.set()
        release.wait(3)
        return preview_session["transcribe"](*args, **kwargs)
    monkeypatch.setattr(main, "transcribe_bytes", blocked)
    import uuid
    job = client.post("/api/speech/jobs", data={"session_id": sid, "request_key": str(uuid.uuid4())},
                      files={"file": ("answer.webm", b"retake", "audio/webm")})
    assert job.status_code == 202
    try:
        assert entered.wait(2)
        assert client.get(f"/api/interviews/{sid}/draft").json()["recording_in_progress"]
        assert confirm(client, sid, draft).status_code == 409
    finally:
        release.set()


def test_drafts_cannot_be_read_or_confirmed_by_another_candidate(client, preview_session, test_settings):
    sid = preview_session["sid"]
    draft = preview(client, sid)
    with database(test_settings.database_path) as connection:
        # Reuse the authenticated token, but transfer this test session's owner.
        teacher = connection.execute("SELECT user_id FROM users WHERE role='teacher'").fetchone()[0]
        connection.execute("UPDATE interview_sessions SET user_id=? WHERE session_id=?", (teacher, sid))
    assert client.get(f"/api/interviews/{sid}/draft").status_code == 409
    assert confirm(client, sid, draft).status_code == 409


def test_fingerprint_mismatch_prevents_batch_from_grading_changed_text(test_settings, monkeypatch):
    sid = prepare(test_settings, count=1)["session_id"]
    answer_current(test_settings, sid)
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET answer_text='changed after confirmation'")
    async def forbidden(*args, **kwargs):
        raise AssertionError("Never grade a changed confirmed transcript")
    monkeypatch.setattr(session_grading, "evaluate_answer", forbidden)
    jobs = session_grading.SessionGrading(test_settings, main.RuntimeReadiness(test_settings))
    asyncio.run(jobs.run_once())
    assert jobs.status(sid)["state"] == "failed"
    assert jobs.status(sid)["pending_count"] == 1


def test_confirmation_hash_is_checked_without_trusting_client_answer(test_settings):
    sid = prepare(test_settings, count=1)["session_id"]
    with database(test_settings.database_path) as connection:
        question = json.loads(connection.execute("SELECT current_question_json FROM interview_sessions WHERE session_id=?", (sid,)).fetchone()[0])
    tid = save_transcription(test_settings.database_path, session_id=sid, user_id=2, question_uid=question["uid"],
        raw_text="raw speech", corrected_text="A stack is LIFO", model="test", runtime="cpu/int8", confidence=.9,
        ambient_noise_dbfs=-60, metadata={}, audio_content=b"audio", audio_filename="recording.wav")
    assert draft_transcription(test_settings.database_path, session_id=sid, user_id=2)["can_confirm"]
    with pytest.raises(InterviewError):
        asyncio.run(submit_answer(test_settings, sid, "typed answer", user_id=2, transcription_id=tid,
                                  expected_preview_sha256="0"*64))
    result = asyncio.run(submit_answer(test_settings, sid, "typed answer", user_id=2, transcription_id=tid,
                                      expected_preview_sha256=transcript_sha256("A stack is LIFO")))
    assert result["answer_confirmed"]
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT answer_text FROM interview_answers").fetchone()[0] == "A stack is LIFO"
