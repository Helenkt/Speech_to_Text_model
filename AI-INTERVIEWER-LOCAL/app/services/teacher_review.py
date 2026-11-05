from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.database import database
from app.services.grade_state import decision_snapshot, json_object
from app.services.practice_grading import question_breakdown, validate_ai_grade, valid_score as _valid_score
from app.services.transcription_vocabulary import transcription_vocabulary


class TeacherReviewError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _evaluation_complete(evaluation: Any, question: dict,
                         stored_score: float | None = None) -> bool:
    if not isinstance(evaluation, dict) or not _valid_score(evaluation.get("score")):
        return False
    if stored_score is not None and (not _valid_score(stored_score)
            or abs(evaluation["score"] - stored_score) > 1e-6):
        return False
    assessments = evaluation.get("point_assessments")
    if not isinstance(assessments, list) or not assessments:
        return False
    found = []
    for item in assessments:
        if (not isinstance(item, dict) or not isinstance(item.get("point"), str)
                or not item["point"].strip() or not isinstance(item.get("status"), str)
                or item["status"] not in {
                    "met", "partial", "missing", "contradicted", "unresolved"}):
            return False
        found.append(item["point"])
    if len(set(found)) != len(found) or set(found) != set(question.get("key_points", [])):
        return False
    breakdown = question_breakdown(question, {**evaluation, "final_score": evaluation["score"],
        "score_provisional": False}, completed=True)
    return breakdown["status"] not in {"invalid_rubric", "score_mismatch"}


def _score_is_provisional(evaluation: dict[str, Any], question: dict,
                           stored_score: float | None = None) -> bool:
    return (not _evaluation_complete(evaluation, question, stored_score)
            or question_breakdown(question, {**evaluation, "final_score": evaluation.get("score")},
                                  completed=True)["status"] != "final")


def review_cache_key(settings: Settings) -> str:
    return "|".join(
        (
            "teacher-review-v12-complete-clause-coverage",
            settings.review_whisper_model,
            settings.ollama_model,
            settings.transcript_correction_mode,
            settings.evaluator_mode,
            "key-points-v2",
        )
    )


def review_readiness(settings: Settings, *, question: dict, score: Any, evaluation_json: str | None,
                     metadata_json: str | None, ai_at: Any, processed_at: Any,
                     interview_mode: str = "real") -> dict:
    if interview_mode == "practice":
        return {"strong_review_ready": False, "can_accept_ai": False, "review_ai_evaluation": {},
                "score_provisional": False, "below_threshold": False, "audio_required": False,
                "manual_review_required": False, "review_policy": "practice_ai_only"}
    def object_json(value):
        try:
            parsed = json.loads(value or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            return {}
    evaluation, metadata = object_json(evaluation_json), object_json(metadata_json)
    ready = bool(ai_at and processed_at and _valid_score(score)
        and metadata.get("review_cache_key") == review_cache_key(settings)
        and _evaluation_complete(evaluation, question, score))
    provisional = _score_is_provisional(evaluation, question, score)
    below = bool(ready and score < settings.teacher_review_score_threshold)
    return {"strong_review_ready": ready, "can_accept_ai": ready and not provisional and not below,
            "review_ai_evaluation": evaluation,
            "score_provisional": provisional, "below_threshold": below, "audio_required": False,
            "manual_review_required": below,
            "review_policy": "ai_reanalysis_required" if not ready else
                "teacher_manual_required" if below else "teacher_decision_recommended" if provisional else "teacher_choice"}


def list_review_queue(settings: Settings) -> list[dict[str, Any]]:
    with database(settings.database_path) as connection:
        rows = connection.execute(
            """
            SELECT a.answer_id, a.session_id, a.sequence_number, a.answer_text,
                   a.score, a.ai_score, a.final_score, a.confidence, a.feedback,
                   a.teacher_score, a.teacher_feedback, a.reviewed_at,
                   a.review_ai_score, a.review_ai_feedback,
                   a.review_ai_evaluation_json, a.review_ai_at,
                   a.transcription_id, a.created_at, a.question_json, s.candidate_name,
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
        question = json.loads(answer.pop("question_json"))
        original_ai_score = float(
            answer["ai_score"]
            if answer["ai_score"] is not None
            else answer["final_score"]
            if answer["final_score"] is not None
            else answer["score"]
        )
        answer.update(review_readiness(settings, question=question, score=answer["review_ai_score"],
            evaluation_json=answer["review_ai_evaluation_json"], metadata_json=answer["review_metadata_json"],
            ai_at=answer["review_ai_at"], processed_at=answer["review_processed_at"]))
        answer["original_ai_score"] = original_ai_score
        answer["ai_score"] = float(answer["review_ai_score"]) if answer["strong_review_ready"] else original_ai_score
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
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT a.*, s.interview_mode, s.answer_mode, t.audio_path,
                   t.review_metadata_json, t.review_processed_at, t.review_transcript
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
        if action == "accept_ai":
            try:
                evaluation = json.loads(row["review_ai_evaluation_json"] or "{}")
                metadata = json.loads(row["review_metadata_json"] or "{}")
                if not isinstance(evaluation, dict) or not isinstance(metadata, dict):
                    raise ValueError("Invalid review metadata")
            except (TypeError, ValueError):
                raise TeacherReviewError("Kết quả AI không hợp lệ; cần xử lý lại") from None
            if metadata.get("review_cache_key") != review_cache_key(settings):
                raise TeacherReviewError("Kết quả AI thuộc phiên bản cũ; cần chấm lại")
            if not row["review_ai_at"] or not row["review_processed_at"]:
                raise TeacherReviewError("Kết quả AI chưa xử lý đầy đủ; cần chấm lại")
            question = json.loads(row["question_json"])
            if _score_is_provisional(evaluation, question, row["review_ai_score"]):
                raise TeacherReviewError("Điểm AI còn ý chưa xác minh; cần xử lý lại hoặc giảng viên tự chấm")
            if row["review_ai_score"] < settings.teacher_review_score_threshold:
                raise TeacherReviewError("Điểm AI chấm lại dưới trung bình; giảng viên cần tự chấm và ghi nhận xét")
        ai_score = next((float(value) for value in (row["review_ai_score"], row["ai_score"], row["score"])
                         if _valid_score(value)), 0.0)
        if action == "accept_ai":
            score = ai_score
            feedback = feedback or "Giảng viên xác nhận sử dụng kết quả chấm của AI."
        else:
            if not _valid_score(score):
                raise TeacherReviewError("Điểm giảng viên phải từ 0 đến 100")
            score = float(score)
            if not feedback:
                raise TeacherReviewError("Giảng viên cần ghi nhận xét hoặc lý do chấm")

        previous = next((float(value) for value in (
            row["final_score"], row["review_ai_score"], row["ai_score"], row["score"]
        ) if _valid_score(value)), 0.0)
        now = _now()
        decision = decision_snapshot(source="strong_ai" if action == "accept_ai" else "teacher_manual",
            score=score, feedback=feedback, question=json.loads(row["question_json"]),
            transcript=row["review_transcript"] if action == "accept_ai" else None,
            evaluation=evaluation if action == "accept_ai" else None)
        serialized_decision = json.dumps(decision, ensure_ascii=False, allow_nan=False)
        connection.execute(
            """
            INSERT INTO answer_reviews (
                answer_id, previous_final_score, teacher_score, feedback,
                reviewed_by, created_at, decision_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (answer_id, previous, score, feedback, teacher_id, now, serialized_decision),
        )
        connection.execute(
            """
            UPDATE interview_answers
            SET teacher_score = ?, final_score = ?, teacher_feedback = ?,
                reviewed_by = ?, reviewed_at = ?, review_required = 0, final_decision_json = ?, grading_pending = 0
            WHERE answer_id = ?
            """,
            (score, score, feedback, teacher_id, now, serialized_decision, answer_id),
        )
        # A teacher can finish a failed batch without reviving AI or resetting attempt history.
        connection.execute("""UPDATE session_grading_jobs SET state='completed',error=NULL,retry_after=NULL,
            processed_count=(SELECT COUNT(*) FROM interview_answers WHERE session_id=? AND grading_pending=0),
            updated_at=CURRENT_TIMESTAMP WHERE session_id=? AND state IN ('queued','failed')
            AND NOT EXISTS (SELECT 1 FROM interview_answers WHERE session_id=? AND grading_pending=1)""",
            (row["session_id"], row["session_id"], row["session_id"]))
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
            SELECT a.answer_id, a.question_json, a.answer_text, a.grading_pending,
                   a.review_ai_score, a.review_ai_feedback,
                   a.review_ai_evaluation_json, a.review_ai_at,
                   s.interview_mode, s.answer_mode, s.language, s.grading_strategy, s.status AS session_status,
                   j.state AS grading_job_state,
                   t.transcription_id, t.corrected_text AS original_transcript,
                   t.audio_path, t.audio_mime_type, t.ambient_noise_dbfs,
                   t.review_transcript, t.review_model, t.review_runtime,
                   t.review_confidence, t.review_metadata_json,
                   t.review_processed_at
            FROM interview_answers AS a
            JOIN interview_sessions AS s ON s.session_id = a.session_id
            LEFT JOIN speech_transcriptions AS t
                ON t.transcription_id = a.transcription_id
            LEFT JOIN session_grading_jobs AS j ON j.session_id = a.session_id
            WHERE a.answer_id = ?
            """,
            (answer_id,),
        ).fetchone()
    if not row:
        raise TeacherReviewError("Không tìm thấy câu trả lời")
    if row["grading_strategy"] == "end_of_session" and (row["session_status"] == "active"
            or (row["grading_pending"] and row["grading_job_state"] != "failed")):
        raise TeacherReviewError("Hãy chờ phiên kết thúc và chấm lần đầu hoàn tất trước khi chạy model chấm lại")
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
        if _valid_score(row["review_ai_score"])
        else None
    )
    cached = cached and strong_score is not None and _evaluation_complete(cached_evaluation, question, strong_score)
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
            **review_readiness(settings, question=question, score=strong_score,
                evaluation_json=row["review_ai_evaluation_json"], metadata_json=row["review_metadata_json"],
                ai_at=row["review_ai_at"], processed_at=row["review_processed_at"]),
            "cached": True,
        }
        if cached
        else None
    )
    return {
        **dict(row),
        "question": question,
        "audio_path_resolved": audio_path,
        **transcription_vocabulary(question),
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
    if not isinstance(evaluation, dict) or not _valid_score(evaluation.get("score")):
        raise TeacherReviewError("Điểm AI phải là số hữu hạn từ 0 đến 100")
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
            "SELECT transcription_id, question_json FROM interview_answers WHERE answer_id = ?",
            (answer_id,),
        ).fetchone()
        if not row or row["transcription_id"] != transcription_id:
            raise TeacherReviewError("Câu trả lời đã thay đổi trong lúc xử lý")
        question = json.loads(row["question_json"])
        if not _evaluation_complete(evaluation, question):
            raise TeacherReviewError("Kết quả AI thiếu hoặc sai đối chiếu từng ý rubric; cần xử lý lại")
        evaluation = dict(evaluation)
        validate_ai_grade(question, evaluation)
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
        **review_readiness(settings, question=question, score=score,
            evaluation_json=json.dumps(evaluation, ensure_ascii=False), metadata_json=json.dumps(transcription, ensure_ascii=False),
            ai_at=processed_at, processed_at=processed_at),
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
                   r.feedback, r.created_at, r.decision_json, u.full_name AS reviewed_by
            FROM answer_reviews AS r
            JOIN users AS u ON u.user_id = r.reviewed_by
            WHERE r.answer_id = ? ORDER BY r.review_id
            """,
            (answer_id,),
        ).fetchall()
    return [{**dict(row), "decision": json_object(row["decision_json"])} for row in rows]
