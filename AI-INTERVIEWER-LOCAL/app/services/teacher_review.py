from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.database import database


class TeacherReviewError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_review_queue(settings: Settings) -> list[dict[str, Any]]:
    with database(settings.database_path) as connection:
        rows = connection.execute(
            """
            SELECT a.answer_id, a.session_id, a.sequence_number, a.answer_text,
                   a.ai_score, a.final_score, a.confidence, a.feedback,
                   a.transcription_id, a.created_at, s.candidate_name,
                   s.language, s.subject, r.exam_code, r.title,
                   json_extract(a.question_json, '$.question') AS question
            FROM interview_answers AS a
            JOIN interview_sessions AS s ON s.session_id = a.session_id
            LEFT JOIN exam_rounds AS r ON r.exam_round_id = s.exam_round_id
            WHERE s.interview_mode = 'real'
              AND a.review_required = 1
              AND a.reviewed_at IS NULL
            ORDER BY a.created_at ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def review_answer(
    settings: Settings,
    *,
    answer_id: int,
    teacher_id: int,
    score: float,
    feedback: str,
) -> dict[str, Any]:
    score = float(score)
    feedback = feedback.strip()
    if not 0 <= score <= 100:
        raise TeacherReviewError("Điểm giảng viên phải từ 0 đến 100")
    if not feedback:
        raise TeacherReviewError("Giảng viên cần ghi nhận xét hoặc lý do chấm")

    with database(settings.database_path) as connection:
        row = connection.execute(
            """
            SELECT a.*, s.interview_mode
            FROM interview_answers AS a
            JOIN interview_sessions AS s ON s.session_id = a.session_id
            WHERE a.answer_id = ?
            """,
            (answer_id,),
        ).fetchone()
        if not row:
            raise TeacherReviewError("Không tìm thấy câu trả lời")
        if row["interview_mode"] != "real":
            raise TeacherReviewError("Chỉ chấm lại câu trả lời của kỳ thi chính thức")

        previous = float(row["final_score"] if row["final_score"] is not None else row["score"])
        now = _now()
        connection.execute(
            """
            INSERT INTO answer_reviews (
                answer_id, previous_final_score, teacher_score, feedback,
                reviewed_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (answer_id, previous, score, feedback, teacher_id, now),
        )
        connection.execute(
            """
            UPDATE interview_answers
            SET teacher_score = ?, final_score = ?, teacher_feedback = ?,
                reviewed_by = ?, reviewed_at = ?, review_required = 0
            WHERE answer_id = ?
            """,
            (score, score, feedback, teacher_id, now, answer_id),
        )
    return {
        "answer_id": answer_id,
        "ai_score": float(row["ai_score"] if row["ai_score"] is not None else row["score"]),
        "previous_final_score": previous,
        "final_score": score,
        "teacher_feedback": feedback,
        "reviewed_at": now,
    }


def transcription_audio(
    settings: Settings, *, transcription_id: str
) -> dict[str, Any]:
    with database(settings.database_path) as connection:
        row = connection.execute(
            """
            SELECT audio_path, audio_mime_type, audio_sha256, audio_size
            FROM speech_transcriptions WHERE transcription_id = ?
            """,
            (transcription_id,),
        ).fetchone()
    if not row or not row["audio_path"]:
        raise TeacherReviewError("Không tìm thấy file voice của câu trả lời")

    base = (settings.audio_storage_dir or settings.database_path.parent / "audio").resolve()
    path = (base / row["audio_path"]).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise TeacherReviewError("File voice không tồn tại hoặc đường dẫn không hợp lệ")
    return {
        "path": path,
        "media_type": row["audio_mime_type"] or "application/octet-stream",
        "sha256": row["audio_sha256"],
        "size": int(row["audio_size"] or path.stat().st_size),
    }


def review_history(settings: Settings, *, answer_id: int) -> list[dict[str, Any]]:
    with database(settings.database_path) as connection:
        rows = connection.execute(
            """
            SELECT r.review_id, r.previous_final_score, r.teacher_score,
                   r.feedback, r.created_at, u.full_name AS reviewed_by
            FROM answer_reviews AS r
            JOIN users AS u ON u.user_id = r.reviewed_by
            WHERE r.answer_id = ? ORDER BY r.created_at
            """,
            (answer_id,),
        ).fetchall()
    return [dict(row) for row in rows]
