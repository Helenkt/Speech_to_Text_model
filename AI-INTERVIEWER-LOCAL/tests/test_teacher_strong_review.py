import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

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
        "id": "AI101:q1",
        "difficulty": "Easy",
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
            # Stub grades exercise the review workflow, not the grader's score arithmetic.
            "point_assessments": [
                {"point": "giao thức", "status": "met"},
                {"point": "truyền tải siêu văn bản", "status": "met"},
            ],
        },
    )


def test_strong_review_below_threshold_requires_manual_teacher_decision(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    result = _save_result(settings, 45)

    assert result["audio_required"] is False
    assert result["below_threshold"] is True
    assert result["can_accept_ai"] is False
    assert result["manual_review_required"] is True
    queue = list_review_queue(settings)
    assert queue[0]["original_transcript"] == "HTTP"
    assert queue[0]["review_transcript"].startswith("HTTP là giao thức")
    assert queue[0]["review_policy"] == "teacher_manual_required"
    cached = review_reanalysis_context(settings, answer_id=1)
    assert cached["cached"] is True
    assert cached["cached_result"]["can_accept_ai"] is False
    assert cached["cached_result"]["manual_review_required"] is True
    with pytest.raises(TeacherReviewError, match="dưới trung bình"):
        review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")
    reviewed = review_answer(
        settings,
        answer_id=1,
        teacher_id=1,
        action="manual",
        score=45,
        feedback="Giảng viên tự chấm theo rubric.",
    )
    assert reviewed["final_score"] == 45


@pytest.mark.parametrize("score", [50, 78])
def test_teacher_can_accept_strong_review_at_or_above_threshold(tmp_path, score):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    _save_result(settings, score)

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

    assert reviewed["ai_score"] == score
    assert reviewed["final_score"] == score
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


def test_provisional_ai_score_cannot_be_adopted_but_manual_review_is_allowed(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    _save_result(settings, 70)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET review_ai_evaluation_json = ? WHERE answer_id = 1",
                           (json.dumps({"score": 70, "score_provisional": True}),))
    assert list_review_queue(settings)[0]["can_accept_ai"] is False
    with pytest.raises(TeacherReviewError, match="chưa xác minh"):
        review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")
    result = review_answer(settings, answer_id=1, teacher_id=1, action="manual", score=75,
                           feedback="Giảng viên đã đối chiếu từng ý.")
    assert result["final_score"] == 75
    assert len(review_history(settings, answer_id=1)) == 1


def test_outdated_ai_reanalysis_cannot_be_adopted_by_calling_api_directly(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    _save_result(settings, 70)
    settings.ollama_model = "different-model"
    with pytest.raises(TeacherReviewError, match="phiên bản cũ"):
        review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")


def test_strong_review_cache_is_invalidated_when_model_changes(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    _save_result(settings, 74)
    assert review_reanalysis_context(settings, answer_id=1)["cached"] is True

    settings.review_whisper_model = "large-v3-turbo"

    assert review_reanalysis_context(settings, answer_id=1)["cached"] is False
    assert list_review_queue(settings)[0]["strong_review_ready"] is False
    assert list_review_queue(settings)[0]["ai_score"] == 20


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


def test_cached_provisional_result_never_offers_adoption(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    _save_result(settings, 70)
    with database(settings.database_path) as connection:
        evaluation = json.loads(connection.execute(
            "SELECT review_ai_evaluation_json FROM interview_answers WHERE answer_id = 1").fetchone()[0])
        evaluation["score_provisional"] = True
        evaluation["point_assessments"][0]["needs_review"] = True
        connection.execute("UPDATE interview_answers SET review_ai_evaluation_json = ? WHERE answer_id = 1",
            (json.dumps(evaluation),))
    result = review_reanalysis_context(settings, answer_id=1)["cached_result"]
    assert result["can_accept_ai"] is False
    assert result["score_provisional"] is True


@pytest.mark.parametrize("payload", [{}, {"score": 70}, {"score": 70, "point_assessments": []}])
def test_incomplete_stored_review_cannot_be_adopted(tmp_path, payload):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    _save_result(settings, 70)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET review_ai_evaluation_json = ? WHERE answer_id = 1",
                           (json.dumps(payload),))
    assert list_review_queue(settings)[0]["can_accept_ai"] is False
    assert review_reanalysis_context(settings, answer_id=1)["cached"] is False
    with pytest.raises(TeacherReviewError):
        review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -1, 101, True])
def test_invalid_reanalysis_score_is_rejected_before_any_write(tmp_path, score):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    with pytest.raises(TeacherReviewError):
        _save_result(settings, score)
    with database(settings.database_path) as connection:
        assert connection.execute("SELECT review_ai_score FROM interview_answers").fetchone()[0] is None


@pytest.mark.parametrize("mutation", ["score", "duplicate", "unknown_status", "bad_status_type", "missing_timestamp"])
def test_inconsistent_stored_review_cannot_be_adopted(tmp_path, mutation):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    result = _save_result(settings, 70)
    evaluation = result["review_ai_evaluation"]
    if mutation == "score":
        evaluation["score"] = 99
    elif mutation == "duplicate":
        evaluation["point_assessments"][1] = evaluation["point_assessments"][0]
    elif mutation == "unknown_status":
        evaluation["point_assessments"][0]["status"] = "excellent"
    elif mutation == "bad_status_type":
        evaluation["point_assessments"][0]["status"] = ["met"]
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET review_ai_evaluation_json = ? WHERE answer_id = 1",
                           (json.dumps(evaluation),))
        if mutation == "missing_timestamp":
            connection.execute("UPDATE speech_transcriptions SET review_processed_at = NULL")
    assert list_review_queue(settings)[0]["can_accept_ai"] is False
    assert review_reanalysis_context(settings, answer_id=1)["cached"] is False
    with pytest.raises(TeacherReviewError):
        review_answer(settings, answer_id=1, teacher_id=1, action="accept_ai", score=None, feedback="")
    assert review_history(settings, answer_id=1) == []


def test_teacher_can_repair_an_invalid_ai_score_without_invalid_history(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET final_score = NULL, review_ai_score = ?", (float("inf"),))
    result = review_answer(settings, answer_id=1, teacher_id=1, action="manual", score=75,
                           feedback="Verified directly against the answer.")
    assert result["ai_score"] == result["previous_final_score"] == 20
    assert review_history(settings, answer_id=1)[0]["teacher_score"] == 75


def test_concurrent_teacher_decisions_keep_a_serial_history(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    barrier = Barrier(2)

    def submit(score):
        barrier.wait(timeout=10)
        return review_answer(settings, answer_id=1, teacher_id=1, action="manual", score=score,
                             feedback="Concurrent history regression test.")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, [65, 85]))
    history = review_history(settings, answer_id=1)
    assert len(history) == 2
    assert history[0]["previous_final_score"] == 20
    assert history[1]["previous_final_score"] == history[0]["teacher_score"]
    assert {item["final_score"] for item in results} == {65, 85}
    with database(settings.database_path) as connection:
        assert connection.execute("SELECT final_score FROM interview_answers").fetchone()[0] == history[-1]["teacher_score"]


def test_report_and_queue_agree_that_a_provisional_strong_score_is_not_final(tmp_path):
    from app.services.interview_engine import interview_report

    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    result = _save_result(settings, 70)
    result["review_ai_evaluation"]["score_provisional"] = True
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET final_score=NULL, review_ai_evaluation_json=?",
                           (json.dumps(result["review_ai_evaluation"]),))
    evaluation = interview_report(settings, "session-1")["answers"][0]["evaluation"]
    assert evaluation["score_provisional"] is True and evaluation["can_accept_ai"] is False
    assert evaluation["final_score"] is None
    assert list_review_queue(settings)[0]["can_accept_ai"] is False
