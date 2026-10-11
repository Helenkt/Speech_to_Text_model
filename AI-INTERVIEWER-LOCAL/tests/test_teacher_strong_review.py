import json

import pytest

from app.config import Settings
from app.database import database, init_database
from app.services.teacher_review import (
    TeacherReviewError,
    list_review_queue,
    review_answer,
    review_history,
    review_reanalysis_context,
    save_review_reanalysis,
)


def _settings(tmp_path):
    return Settings(
        root_dir=tmp_path,
        database_path=tmp_path / "test.db",
        static_dir=tmp_path,
        demo_data_dir=tmp_path,
        whisper_download_root=tmp_path / "models",
        audio_storage_dir=tmp_path / "audio",
        auto_seed_demo=False,
        evaluator_mode="rule",
    )


def _seed_voice_answer(settings):
    init_database(settings.database_path)
    question = {
        "uid": "vi:AI101:q1",
        "language": "vi",
        "subject": "AI101",
        "competency": "Khái niệm",
        "topic": "HTTP",
        "concept": "HTTP",
        "difficulty": "Easy",
        "question": "HTTP là gì?",
        "reference_answer": "HTTP là giao thức truyền tải siêu văn bản.",
        "key_points": ["giao thức", "truyền tải siêu văn bản"],
    }
    audio_dir = settings.audio_storage_dir / "session-1"
    audio_dir.mkdir(parents=True)
    (audio_dir / "voice.webm").write_bytes(b"voice")
    with database(settings.database_path) as connection:
        connection.execute(
            """
            INSERT INTO users (
                user_id, username, password_hash, full_name, role, active,
                created_at, updated_at
            ) VALUES
                (1, 'teacher', 'hash', 'Teacher', 'teacher', 1, 'now', 'now'),
                (2, 'candidate', 'hash', 'Candidate', 'candidate', 1, 'now', 'now')
            """
        )
        connection.execute(
            """
            INSERT INTO interview_sessions (
                session_id, user_id, candidate_name, interview_mode, answer_mode,
                language, subject, requested_count, answered_count,
                current_difficulty_rank, evaluator_requested, status, created_at
            ) VALUES (
                'session-1', 2, 'Candidate', 'real', 'voice', 'vi', 'AI101',
                1, 1, 1, 'rule', 'completed', 'now'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO speech_transcriptions (
                transcription_id, session_id, user_id, question_uid, raw_text,
                corrected_text, model, runtime, confidence, metadata_json,
                audio_path, audio_mime_type, audio_size, consumed, created_at
            ) VALUES (
                'stt-1', 'session-1', 2, 'vi:AI101:q1', 'hát tê tê pê',
                'HTTP', 'medium', 'cpu/int8', 0.8, '{}',
                'session-1/voice.webm', 'audio/webm', 5, 1, 'now'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO interview_answers (
                answer_id, session_id, sequence_number, question_uid, question_json,
                answer_text, score, verdict, matched_points_json,
                missing_points_json, feedback, confidence, evaluator,
                assessment_json, review_required, transcription_id, ai_score,
                final_score, created_at
            ) VALUES (
                1, 'session-1', 1, 'vi:AI101:q1', ?, 'HTTP', 20, 'Cần bổ sung',
                '[]', '[]', 'Thiếu ý', 0.8, 'rule', '[]', 1, 'stt-1', 20, 20, 'now'
            )
            """,
            (json.dumps(question, ensure_ascii=False),),
        )
    return question


def _save_result(settings, score):
    return save_review_reanalysis(
        settings,
        answer_id=1,
        transcription_id="stt-1",
        transcription={
            "original_transcript": "HTTP",
            "text": "HTTP là giao thức truyền tải siêu văn bản.",
            "model": "large-v3",
            "runtime": "cpu/int8",
            "metrics": {"confidence": 0.96},
        },
        evaluation={
            "score": score,
            "feedback": "Kết quả chấm lại từ transcript model mạnh.",
            "point_assessments": [],
        },
    )


def test_strong_review_below_threshold_remains_teacher_decision(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    result = _save_result(settings, 45)

    assert result["audio_required"] is False
    assert result["below_threshold"] is True
    assert result["can_accept_ai"] is True
    queue = list_review_queue(settings)
    assert queue[0]["original_transcript"] == "HTTP"
    assert queue[0]["review_transcript"].startswith("HTTP là giao thức")
    assert queue[0]["review_policy"] == "teacher_decision_recommended"
    assert review_reanalysis_context(settings, answer_id=1)["cached"] is True
    reviewed = review_answer(
        settings,
        answer_id=1,
        teacher_id=1,
        action="accept_ai",
        score=None,
        feedback="",
    )
    assert reviewed["final_score"] == 45


def test_teacher_can_accept_strong_review_above_threshold(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    _save_result(settings, 78)

    queue = list_review_queue(settings)
    assert queue[0]["can_accept_ai"] is True
    with database(settings.database_path) as connection:
        assert connection.execute(
            "SELECT review_required FROM interview_answers WHERE answer_id = 1"
        ).fetchone()["review_required"] == 1
    reviewed = review_answer(
        settings,
        answer_id=1,
        teacher_id=1,
        action="accept_ai",
        score=None,
        feedback="",
    )

    assert reviewed["ai_score"] == 78
    assert reviewed["final_score"] == 78
    with database(settings.database_path) as connection:
        assert connection.execute(
            "SELECT review_required FROM interview_answers WHERE answer_id = 1"
        ).fetchone()["review_required"] == 0


def test_teacher_can_grade_without_playing_audio(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    _save_result(settings, 62)

    reviewed = review_answer(
        settings,
        answer_id=1,
        teacher_id=1,
        action="manual",
        score=70,
        feedback="Chấm trực tiếp theo transcript và rubric.",
    )

    assert reviewed["final_score"] == 70
    assert review_history(settings, answer_id=1)[0]["teacher_score"] == 70


def test_strong_review_cache_is_invalidated_when_model_changes(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    _save_result(settings, 74)
    assert review_reanalysis_context(settings, answer_id=1)["cached"] is True

    settings.review_whisper_model = "large-v3-turbo"

    assert review_reanalysis_context(settings, answer_id=1)["cached"] is False
    assert list_review_queue(settings)[0]["strong_review_ready"] is False


def test_database_migration_keeps_real_voice_score_provisional(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)

    init_database(settings.database_path)

    with database(settings.database_path) as connection:
        row = connection.execute(
            "SELECT ai_score, final_score, review_required FROM interview_answers"
        ).fetchone()
    assert row["ai_score"] == 20
    assert row["final_score"] is None
    assert row["review_required"] == 1
