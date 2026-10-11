import json

import pytest

from app.database import database, init_database
from app.services.transcription_store import (
    TranscriptionError,
    expire_stale_sessions,
    microphone_check_session,
    save_microphone_check,
    save_transcription,
    transcription_attempt_status,
    transcription_context,
    verified_voice_answer,
)


def _seed_active_session(database_path):
    init_database(database_path)
    question = {
        "uid": "vi:AI101:q1",
        "question": "HTTP là gì?",
        "subject": "AI101",
        "topic": "Web",
        "concept": "HTTP",
    }
    with database(database_path) as connection:
        connection.execute(
            """
            INSERT INTO users (
                user_id, username, password_hash, full_name, role, active,
                created_at, updated_at
            ) VALUES (1, 'candidate', 'hash', 'Candidate', 'candidate', 1, 'now', 'now')
            """
        )
        connection.execute(
            """
            INSERT INTO interview_sessions (
                session_id, user_id, candidate_name, interview_mode, answer_mode,
                language, subject, requested_count, current_question_uid,
                current_question_json, current_difficulty_rank, evaluator_requested,
                status, created_at
            ) VALUES (
                'session-1', 1, 'Candidate', 'practice', 'voice', 'vi', 'AI101',
                1, 'vi:AI101:q1', ?, 1, 'rule', 'active', 'now'
            )
            """,
            (json.dumps(question, ensure_ascii=False),),
        )
    return question


def test_successful_microphone_check_is_reused_for_the_session(tmp_path):
    database_path = tmp_path / "test.db"
    _seed_active_session(database_path)
    current = microphone_check_session(
        database_path, user_id=1, session_id="session-1"
    )
    assert current["result"] == {}
    with pytest.raises(TranscriptionError, match="microphone"):
        transcription_context(
            database_path, session_id="session-1", user_id=1
        )

    first = save_microphone_check(
        database_path,
        session_id="session-1",
        user_id=1,
        result={"ready": True, "microphone_score_percent": 91},
    )
    second = save_microphone_check(
        database_path,
        session_id="session-1",
        user_id=1,
        result={"ready": False, "microphone_score_percent": 10},
    )

    assert first["already_checked"] is False
    assert second["already_checked"] is True
    assert second["microphone_score_percent"] == 91
    assert transcription_context(
        database_path, session_id="session-1", user_id=1
    )["microphone_check"]["ready"] is True


def test_recording_again_keeps_history_and_only_latest_can_be_submitted(tmp_path):
    database_path = tmp_path / "test.db"
    _seed_active_session(database_path)
    save_microphone_check(
        database_path,
        session_id="session-1",
        user_id=1,
        result={"ready": True},
    )
    common = {
        "database_path": database_path,
        "session_id": "session-1",
        "user_id": 1,
        "question_uid": "vi:AI101:q1",
        "model": "test",
        "runtime": "cpu/int8",
        "confidence": 0.9,
        "ambient_noise_dbfs": -40.0,
        "metadata": {},
    }
    first = save_transcription(
        **common,
        raw_text="Hát tê tê pê",
        corrected_text="HTTP",
    )
    second = save_transcription(
        **common,
        raw_text="HTTP là giao thức web",
        corrected_text="HTTP là giao thức web",
        retry_reason="transcript_still_incorrect",
    )

    with database(database_path) as connection:
        rows = connection.execute(
            """
            SELECT transcription_id, accepted, attempt_number, retry_reason,
                   superseded_by
            FROM speech_transcriptions ORDER BY attempt_number
            """
        ).fetchall()

    assert len(rows) == 2
    assert rows[0]["accepted"] == 0
    assert rows[0]["superseded_by"] == second
    assert rows[1]["accepted"] == 1
    assert transcription_attempt_status(
        database_path, transcription_id=second
    )["attempt_number"] == 2
    with pytest.raises(TranscriptionError):
        verified_voice_answer(
            database_path,
            transcription_id=first,
            session_id="session-1",
            user_id=1,
            question_uid="vi:AI101:q1",
        )
    assert verified_voice_answer(
        database_path,
        transcription_id=second,
        session_id="session-1",
        user_id=1,
        question_uid="vi:AI101:q1",
    )["text"] == "HTTP là giao thức web"


def test_microphone_check_is_bound_to_requested_session(tmp_path):
    database_path = tmp_path / "test.db"
    _seed_active_session(database_path)

    with pytest.raises(TranscriptionError, match="không tồn tại"):
        microphone_check_session(
            database_path, user_id=1, session_id="another-session"
        )


def test_expire_stale_practice_sessions(tmp_path):
    database_path = tmp_path / "test.db"
    _seed_active_session(database_path)
    with database(database_path) as connection:
        connection.execute(
            "UPDATE interview_sessions SET created_at = '2020-01-01T00:00:00+00:00'"
        )

    assert expire_stale_sessions(database_path, ttl_hours=24) == 1
    with database(database_path) as connection:
        row = connection.execute(
            "SELECT status, finish_reason FROM interview_sessions"
        ).fetchone()
    assert row["status"] == "completed"
    assert row["finish_reason"] == "session_expired"
