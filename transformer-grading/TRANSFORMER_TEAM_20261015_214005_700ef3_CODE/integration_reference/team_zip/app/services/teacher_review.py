from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.database import database


class TeacherReviewError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def review_cache_key(settings: Settings) -> str:
    return "|".join(
        (
            "teacher-review-v2",
            settings.review_whisper_model,
            settings.ollama_model,
            settings.transcript_correction_mode,
            settings.evaluator_mode,
            "key-points-v2",
        )
    )


def list_review_queue(settings: Settings) -> list[dict[str, Any]]:
    with database(settings.database_path) as connection:
        rows = connection.execute(
            """
            SELECT a.answer_id, a.session_id, a.sequence_number, a.answer_text,
                   a.score, a.ai_score, a.final_score, a.confidence, a.feedback,
                   a.teacher_score, a.teacher_feedback, a.reviewed_at,
                   a.review_ai_score, a.review_ai_feedback,
                   a.review_ai_evaluation_json, a.review_ai_at,
                   a.transcription_id, a.created_at, s.candidate_name,
                   s.language, s.subject, r.exam_code, r.title,
                   t.corrected_text AS original_transcript,
                   t.review_transcript, t.review_model, t.review_runtime,
                   t.review_confidence, t.review_metadata_json,
                   t.review_processed_at,
                   json_extract(a.question_json, '$.question') AS question
            FROM interview_answers AS a
            JOIN interview_sessions AS s ON s.session_id = a.session_id
            LEFT JOIN exam_rounds AS r ON r.exam_round_id = s.exam_round_id
            LEFT JOIN speech_transcriptions AS t
                ON t.transcription_id = a.transcription_id
            WHERE s.interview_mode = 'real'
              AND s.answer_mode = 'voice'
            ORDER BY a.created_at ASC
            """
        ).fetchall()
    answers: list[dict[str, Any]] = []
    for row in rows:
        answer = dict(row)
        original_ai_score = float(
            answer["ai_score"]
            if answer["ai_score"] is not None
            else answer["final_score"]
            if answer["final_score"] is not None
            else answer["score"]
        )
        try:
            metadata = json.loads(answer.get("review_metadata_json") or "{}")
            if not isinstance(metadata, dict):
                metadata = {}
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        strong_ready = bool(
            answer["review_processed_at"]
            and answer["review_ai_at"]
            and metadata.get("review_cache_key") == review_cache_key(settings)
        )
        strong_score = (
            float(answer["review_ai_score"])
            if answer["review_ai_score"] is not None
            else None
        )
        try:
            parsed_evaluation = json.loads(
                answer.get("review_ai_evaluation_json") or "{}"
            )
            review_evaluation = (
                parsed_evaluation if isinstance(parsed_evaluation, dict) else {}
            )
        except (TypeError, json.JSONDecodeError):
            review_evaluation = {}
        displayed_ai_score = strong_score if strong_score is not None else original_ai_score
        below_threshold = bool(
            strong_ready
            and strong_score is not None
            and strong_score < settings.teacher_review_score_threshold
        )
        answer.update(
            {
                "original_ai_score": original_ai_score,
                "ai_score": displayed_ai_score,
                "strong_review_ready": strong_ready,
                "review_ai_evaluation": review_evaluation,
                "review_policy": (
                    "ai_reanalysis_required"
                    if not strong_ready
                    else "teacher_decision_recommended"
                    if below_threshold
                    else "teacher_choice"
                ),
                "audio_required": False,
                "below_threshold": below_threshold,
                "can_accept_ai": strong_ready,
            }
        )
        answers.append(answer)
    answers.sort(
        key=lambda item: (
            item["reviewed_at"] is not None,
            not item["below_threshold"],
            item["created_at"],
        )
    )
    return answers


def review_answer(
    settings: Settings,
    *,
    answer_id: int,
    teacher_id: int,
    action: str,
    score: float | None,
    feedback: str,
) -> dict[str, Any]:
    feedback = feedback.strip()
    if action not in {"accept_ai", "manual"}:
        raise TeacherReviewError("Thao tác chấm không hợp lệ")

    with database(settings.database_path) as connection:
        row = connection.execute(
            """
            SELECT a.*, s.interview_mode, s.answer_mode, t.audio_path
            FROM interview_answers AS a
            JOIN interview_sessions AS s ON s.session_id = a.session_id
            LEFT JOIN speech_transcriptions AS t
                ON t.transcription_id = a.transcription_id
            WHERE a.answer_id = ?
            """,
            (answer_id,),
        ).fetchone()
        if not row:
            raise TeacherReviewError("Không tìm thấy câu trả lời")
        if row["interview_mode"] != "real":
            raise TeacherReviewError("Chỉ chấm lại câu trả lời của kỳ thi chính thức")
        if row["answer_mode"] != "voice":
            raise TeacherReviewError("Quy trình này chỉ áp dụng cho câu trả lời bằng voice")

        if action == "accept_ai" and row["review_ai_score"] is None:
            raise TeacherReviewError(
                "Cần chạy model STT mạnh và chấm lại trước khi dùng kết quả AI"
            )
        ai_score = float(
            row["review_ai_score"]
            if row["review_ai_score"] is not None
            else row["ai_score"]
            if row["ai_score"] is not None
            else row["score"]
        )
        if action == "accept_ai":
            score = ai_score
            feedback = feedback or "Giảng viên xác nhận sử dụng kết quả chấm của AI."
        else:
            if score is None or not 0 <= float(score) <= 100:
                raise TeacherReviewError("Điểm giảng viên phải từ 0 đến 100")
            score = float(score)
            if not feedback:
                raise TeacherReviewError("Giảng viên cần ghi nhận xét hoặc lý do chấm")

        previous = float(
            row["final_score"]
            if row["final_score"] is not None
            else row["review_ai_score"]
            if row["review_ai_score"] is not None
            else row["ai_score"]
            if row["ai_score"] is not None
            else row["score"]
        )
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
        "action": action,
        "ai_score": ai_score,
        "previous_final_score": previous,
        "final_score": score,
        "teacher_feedback": feedback,
        "reviewed_at": now,
    }


def review_reanalysis_context(
    settings: Settings, *, answer_id: int
) -> dict[str, Any]:
    with database(settings.database_path) as connection:
        row = connection.execute(
            """
            SELECT a.answer_id, a.question_json, a.answer_text,
                   a.review_ai_score, a.review_ai_feedback,
                   a.review_ai_evaluation_json, a.review_ai_at,
                   s.interview_mode, s.answer_mode, s.language,
                   t.transcription_id, t.corrected_text AS original_transcript,
                   t.audio_path, t.audio_mime_type, t.ambient_noise_dbfs,
                   t.review_transcript, t.review_model, t.review_runtime,
                   t.review_confidence, t.review_metadata_json,
                   t.review_processed_at
            FROM interview_answers AS a
            JOIN interview_sessions AS s ON s.session_id = a.session_id
            LEFT JOIN speech_transcriptions AS t
                ON t.transcription_id = a.transcription_id
            WHERE a.answer_id = ?
            """,
            (answer_id,),
        ).fetchone()
    if not row:
        raise TeacherReviewError("Không tìm thấy câu trả lời")
    if row["interview_mode"] != "real" or row["answer_mode"] != "voice":
        raise TeacherReviewError(
            "Model STT mạnh chỉ áp dụng cho câu trả lời voice của kỳ thi chính thức"
        )
    if not row["transcription_id"] or not row["audio_path"]:
        raise TeacherReviewError("Không có file voice để model mạnh xử lý")

    try:
        question = json.loads(row["question_json"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise TeacherReviewError("Dữ liệu câu hỏi không hợp lệ") from exc
    base = (settings.audio_storage_dir or settings.database_path.parent / "audio").resolve()
    audio_path = (base / row["audio_path"]).resolve()
    if not audio_path.is_relative_to(base) or not audio_path.is_file():
        raise TeacherReviewError("File voice không tồn tại hoặc đường dẫn không hợp lệ")

    phrases = [
        str(question.get(field) or "").strip()
        for field in ("subject", "topic", "concept")
    ]
    technical_tokens = re.findall(
        r"[A-Za-z][A-Za-z0-9+#._-]{2,}", str(question.get("question") or "")
    )
    try:
        review_metadata = json.loads(row["review_metadata_json"] or "{}")
        if not isinstance(review_metadata, dict):
            review_metadata = {}
    except (TypeError, json.JSONDecodeError):
        review_metadata = {}
    cache_key = review_cache_key(settings)
    cached = bool(
        row["review_processed_at"]
        and row["review_ai_at"]
        and review_metadata.get("review_cache_key") == cache_key
    )
    cached_evaluation: dict[str, Any] = {}
    if cached:
        try:
            parsed = json.loads(row["review_ai_evaluation_json"] or "{}")
            cached_evaluation = parsed if isinstance(parsed, dict) else {}
        except (TypeError, json.JSONDecodeError):
            cached_evaluation = {}
    strong_score = (
        float(row["review_ai_score"])
        if row["review_ai_score"] is not None
        else None
    )
    cached_result = (
        {
            "answer_id": answer_id,
            "original_transcript": row["original_transcript"],
            "review_transcript": row["review_transcript"],
            "review_model": row["review_model"],
            "review_runtime": row["review_runtime"],
            "review_confidence": float(row["review_confidence"] or 0.0),
            "review_ai_score": strong_score,
            "review_ai_feedback": row["review_ai_feedback"],
            "review_ai_evaluation": cached_evaluation,
            "review_processed_at": row["review_processed_at"],
            "strong_review_ready": True,
            "audio_required": False,
            "below_threshold": bool(
                strong_score is not None
                and strong_score < settings.teacher_review_score_threshold
            ),
            "can_accept_ai": strong_score is not None,
            "cached": True,
        }
        if cached
        else None
    )
    return {
        **dict(row),
        "question": question,
        "audio_path_resolved": audio_path,
        "approved_terms": list(
            dict.fromkeys(item for item in phrases + technical_tokens if item)
        ),
        "cached": cached,
        "cached_result": cached_result,
    }


def save_review_reanalysis(
    settings: Settings,
    *,
    answer_id: int,
    transcription_id: str,
    transcription: dict[str, Any],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    score = float(evaluation["score"])
    processed_at = _now()
    transcript = str(transcription.get("text") or "").strip()
    if not transcript:
        raise TeacherReviewError("Model mạnh không nhận dạng được nội dung voice")
    transcription = {
        **transcription,
        "review_cache_key": review_cache_key(settings),
    }
    with database(settings.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT transcription_id FROM interview_answers WHERE answer_id = ?",
            (answer_id,),
        ).fetchone()
        if not row or row["transcription_id"] != transcription_id:
            raise TeacherReviewError("Câu trả lời đã thay đổi trong lúc xử lý")
        connection.execute(
            """
            UPDATE speech_transcriptions
            SET review_transcript = ?, review_model = ?, review_runtime = ?,
                review_confidence = ?, review_metadata_json = ?,
                review_processed_at = ?
            WHERE transcription_id = ?
            """,
            (
                transcript,
                str(transcription.get("model") or settings.review_whisper_model),
                str(transcription.get("runtime") or "unknown"),
                float((transcription.get("metrics") or {}).get("confidence") or 0.0),
                json.dumps(transcription, ensure_ascii=False),
                processed_at,
                transcription_id,
            ),
        )
        connection.execute(
            """
            UPDATE interview_answers
            SET review_ai_score = ?, review_ai_feedback = ?,
                review_ai_evaluation_json = ?, review_ai_at = ?,
                review_required = ?
            WHERE answer_id = ?
            """,
            (
                score,
                str(evaluation.get("feedback") or ""),
                json.dumps(evaluation, ensure_ascii=False),
                processed_at,
                1,
                answer_id,
            ),
        )
    return {
        "answer_id": answer_id,
        "original_transcript": transcription.get("original_transcript"),
        "review_transcript": transcript,
        "review_model": str(
            transcription.get("model") or settings.review_whisper_model
        ),
        "review_runtime": str(transcription.get("runtime") or "unknown"),
        "review_confidence": float(
            (transcription.get("metrics") or {}).get("confidence") or 0.0
        ),
        "review_ai_score": score,
        "review_ai_feedback": str(evaluation.get("feedback") or ""),
        "review_ai_evaluation": evaluation,
        "review_processed_at": processed_at,
        "strong_review_ready": True,
        "audio_required": False,
        "below_threshold": score < settings.teacher_review_score_threshold,
        "can_accept_ai": True,
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
