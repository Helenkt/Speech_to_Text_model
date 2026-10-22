from __future__ import annotations

import json
import sqlite3
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings
from app.database import database
from app.services.evaluator import evaluate_answer
from app.services.rubric_contract import attach_published_contract
from app.services.teacher_review import review_readiness
from app.services.grade_state import effective_grade
from app.services.audio_lifecycle import audio_exists, deletion_result, schedule_session_audio
from app.services.exam_policy import exam_is_open, submission_admission, received_admission
from app.services.transcription_store import (
    TranscriptionError,
    verified_voice_answer,
    transcript_sha256,
    require_no_pending_recording,
)


DIFFICULTY_RANK = {"Easy": 1, "Medium": 2, "Hard": 3}
PUBLIC_QUESTION_FIELDS = (
    "id",
    "language",
    "subject",
    "competency",
    "topic",
    "concept",
    "difficulty",
    "question",
)


class InterviewError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_question(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "uid": row["uid"],
        "id": row["question_id"],
        "language": row["language"],
        "subject": row["subject"],
        "competency": row["competency"],
        "topic": row["topic"],
        "concept": row["concept"],
        "difficulty": row["difficulty"],
        "difficulty_rank": row["difficulty_rank"],
        "question": row["question"],
        "reference_answer": row["reference_answer"],
        "key_points": json.loads(row["key_points_json"]),
        "source_name": row["source_name"],
        "verification_status": row["verification_status"],
    }


def public_question(question: dict[str, Any] | None) -> dict[str, Any] | None:
    if question is None:
        return None
    return {key: question[key] for key in PUBLIC_QUESTION_FIELDS}


def _select_question(
    connection: sqlite3.Connection,
    *,
    language: str,
    subject: str | None,
    target_rank: int,
    excluded_uids: list[str] | None = None,
    preferred_topic: str | None = None,
    preferred_concept: str | None = None,
    exam_round_id: str | None = None,
) -> dict[str, Any] | None:
    if exam_round_id:
        clauses = ["exam_round_id = ?"]
        parameters: list[Any] = [exam_round_id]
        if excluded_uids:
            clauses.append(
                f"question_uid NOT IN ({','.join('?' for _ in excluded_uids)})"
            )
            parameters.extend(excluded_uids)
        if preferred_concept:
            order = (
                "ABS(difficulty_rank - ?), "
                "CASE WHEN concept = ? THEN 0 ELSE 1 END, "
                "CASE WHEN topic = ? THEN 0 ELSE 1 END, RANDOM()"
            )
            parameters.extend([target_rank, preferred_concept, preferred_topic or ""])
        elif preferred_topic:
            order = (
                "ABS(difficulty_rank - ?), "
                "CASE WHEN topic = ? THEN 0 ELSE 1 END, RANDOM()"
            )
            parameters.extend([target_rank, preferred_topic])
        else:
            order = "ABS(difficulty_rank - ?), RANDOM()"
            parameters.append(target_rank)
        row = connection.execute(
            f"""
            SELECT question_json FROM exam_round_questions
            WHERE {' AND '.join(clauses)} ORDER BY {order} LIMIT 1
            """,
            parameters,
        ).fetchone()
        return json.loads(row["question_json"]) if row else None

    clauses = ["active = 1", "bank_scope = 'learning'", "language = ?"]
    parameters = [language]
    if subject:
        clauses.append("subject = ?")
        parameters.append(subject)
    if excluded_uids:
        clauses.append(f"uid NOT IN ({','.join('?' for _ in excluded_uids)})")
        parameters.extend(excluded_uids)

    if preferred_concept:
        order = (
            "ABS(difficulty_rank - ?), CASE WHEN concept = ? THEN 0 ELSE 1 END, "
            "CASE WHEN topic = ? THEN 0 ELSE 1 END, RANDOM()"
        )
        parameters.extend([target_rank, preferred_concept, preferred_topic or ""])
    elif preferred_topic:
        order = "ABS(difficulty_rank - ?), CASE WHEN topic = ? THEN 0 ELSE 1 END, RANDOM()"
        parameters.extend([target_rank, preferred_topic])
    else:
        order = "ABS(difficulty_rank - ?), RANDOM()"
        parameters.append(target_rank)

    row = connection.execute(
        f"SELECT * FROM questions WHERE {' AND '.join(clauses)} ORDER BY {order} LIMIT 1",
        parameters,
    ).fetchone()
    return attach_published_contract(connection, _row_to_question(row)) if row else None


def start_interview(
    settings: Settings,
    *,
    user_id: int,
    candidate_name: str,
    language: str,
    subject: str | None,
    question_count: int,
    starting_difficulty: str,
    interview_mode: str = "practice",
    exam_round_id: str | None = None,
    answer_mode: str = "voice",
) -> dict[str, Any]:
    # The product is a live spoken interview; typed answers are never accepted.
    answer_mode = "voice"
    language = language.strip().lower()
    subject = subject.strip() if subject else None
    target_rank = DIFFICULTY_RANK[starting_difficulty]
    session_id = str(uuid.uuid4())

    with database(settings.database_path) as connection:
        first_question = _select_question(
            connection,
            language=language,
            subject=subject,
            target_rank=target_rank,
            exam_round_id=exam_round_id,
        )
        if not first_question:
            raise InterviewError("Không tìm thấy câu hỏi phù hợp với bộ lọc đã chọn")

        plan = None
        if settings.defer_grading_until_finish:
            plan = [first_question]
            for index in range(1, question_count):
                question = _select_question(connection, language=language, subject=subject,
                    target_rank=planned_difficulty(target_rank, index, question_count),
                    excluded_uids=[item["uid"] for item in plan], exam_round_id=exam_round_id)
                if question is None:
                    raise InterviewError("Ngân hàng chưa đủ câu hỏi khác nhau để chuẩn bị toàn bộ đề")
                plan.append(question)

        connection.execute(
            """
            INSERT INTO interview_sessions (
                session_id, user_id, candidate_name, interview_mode, exam_round_id,
                answer_mode, language, subject, requested_count,
                current_question_uid, current_question_json, current_difficulty_rank,
                evaluator_requested, status, created_at, grading_strategy, starting_difficulty_rank, question_plan_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
            """,
            (
                session_id,
                user_id,
                candidate_name.strip(),
                interview_mode,
                exam_round_id,
                answer_mode,
                language,
                subject,
                question_count,
                first_question["uid"],
                json.dumps(first_question, ensure_ascii=False),
                target_rank,
                settings.evaluator_mode,
                _now(),
                "end_of_session" if settings.defer_grading_until_finish else "per_answer",
                target_rank,
                json.dumps(plan, ensure_ascii=False) if plan else None,
            ),
        )

    return {
        "session_id": session_id,
        "candidate_name": candidate_name.strip(),
        "requested_count": question_count,
        "answered_count": 0,
        "interview_mode": interview_mode,
        "answer_mode": answer_mode,
        "language": language,
        "resumed": False,
        "grading_strategy": "end_of_session" if settings.defer_grading_until_finish else "per_answer",
        "question_selection": "fixed" if plan else "adaptive",
        "difficulty_schedule": [item["difficulty"] for item in plan] if plan else None,
        "question": public_question(first_question),
    }


def resume_interview(settings: Settings, session_id: str, *, user_id: int) -> dict[str, Any]:
    with database(settings.database_path) as connection:
        row = connection.execute("SELECT * FROM interview_sessions WHERE session_id=? AND user_id=?", (session_id, user_id)).fetchone()
        if not row or row["status"] != "active" or not row["current_question_json"]:
            raise InterviewError("Phiên này không còn câu hỏi đang làm")
        exam = None
        if row["interview_mode"] == "real":
            exam = connection.execute("SELECT * FROM exam_rounds WHERE exam_round_id=?", (row["exam_round_id"],)).fetchone()
            jobs = connection.execute("SELECT job_id FROM speech_jobs WHERE session_id=? AND question_uid=? ORDER BY rowid DESC",
                                      (session_id, row["current_question_uid"])).fetchall()
            if not exam or not (exam_is_open(connection, row) or any(received_admission(connection, row, job[0]) for job in jobs)):
                raise InterviewError("Đợt thi đã đóng hoặc hết thời gian")
        recording_allowed = exam_is_open(connection, row)
    return {key: row[key] for key in ("session_id", "candidate_name", "requested_count", "answered_count", "interview_mode", "answer_mode", "language")} | {
        "resumed": True, "recording_allowed": recording_allowed,
        "grading_strategy": row["grading_strategy"],
        "question_selection": "fixed" if row["question_plan_json"] else "adaptive",
        "question": public_question(json.loads(row["current_question_json"])),
        "microphone_check": json.loads(row["mic_check_result_json"] or "{}"),
        "exam": {key: exam[key] for key in ("exam_code", "title")} if exam else None,
    }


def _next_rank(current_rank: int, score: float) -> int:
    if score >= 80:
        return min(3, current_rank + 1)
    if score < 45:
        return max(1, current_rank - 1)
    return current_rank


def planned_difficulty(starting_rank: int, answered_count: int, requested_count: int) -> int:
    levels = 4 - starting_rank
    return starting_rank + min(levels - 1, answered_count * levels // max(1, requested_count))


def pending_session_evaluation() -> dict[str, Any]:
    return {
        "score": 0, "score_provisional": True, "verdict": "Chờ chấm cuối phiên",
        "matched_points": [], "missing_points": [], "point_assessments": [],
        "feedback": "Đã lưu câu trả lời. Hệ thống sẽ chấm và tổng hợp báo cáo khi kết thúc phiên.",
        "confidence": 0, "evaluator": "deferred:session", "review_required": False,
        "rubric_version": "key-points-v2", "grading_deferred": True, "review_reasons": [],
    }


def apply_voice_assurance(settings, evaluation, question, voice_quality, interview_mode):
    from app.services.assessment_feedback import assessment_feedback, voice_requires_review
    if voice_requires_review(voice_quality):
        evaluation["review_required"] = evaluation["score_provisional"] = True
        notice = (
            ("Bản ghi giọng nói có cảnh báo chất lượng; chưa đủ cơ sở tính điểm luyện tập."
             if interview_mode == "practice" else
             "Bản ghi giọng nói có cảnh báo chất lượng; giáo viên cần đối chiếu transcript trước khi dùng điểm.")
            if question.get("language") == "vi" else
            "The voice recording has quality warnings; review the transcript before using this score.")
        if notice not in evaluation["feedback"]:
            evaluation["feedback"] = f'{evaluation["feedback"]} {notice}'.strip()
    if interview_mode == "real":
        evaluation["review_required"] = True
    evaluation.update(assessment_feedback(evaluation, voice_quality, interview_mode=interview_mode))
    return evaluation


def queue_session_grading(connection, session_id):
    connection.execute("""INSERT OR IGNORE INTO session_grading_jobs (session_id)
        SELECT session_id FROM interview_sessions WHERE session_id=? AND status='completed'
          AND grading_strategy='end_of_session'
          AND EXISTS (SELECT 1 FROM interview_answers WHERE session_id=? AND grading_pending=1)""",
        (session_id, session_id))


async def submit_answer(
    settings: Settings,
    session_id: str,
    answer_text: str,
    *,
    user_id: int,
    transcription_id: str | None = None,
    ensure_model=None,
    inference_runner=None,
    expected_preview_sha256: str | None = None,
) -> dict[str, Any]:
    def replay(connection):
        if not transcription_id:
            return None
        row = connection.execute("SELECT response_json FROM submission_receipts WHERE session_id=? AND user_id=? AND request_key=?",
                                 (session_id, user_id, transcription_id)).fetchone()
        if not row:
            return None
        result = json.loads(row[0])
        if (expected_preview_sha256 is not None
                and result.get("confirmation", {}).get("preview_sha256") != expected_preview_sha256):
            raise InterviewError("Transcript xác nhận không khớp bản đã nộp")
        return result

    with database(settings.database_path) as connection:
        previous_result = replay(connection)
        if previous_result is not None:
            return previous_result
        session = connection.execute(
            "SELECT * FROM interview_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not session:
            raise InterviewError("Không tìm thấy phiên phỏng vấn")
        if session["user_id"] != user_id:
            raise InterviewError("Bạn không có quyền trả lời phiên này")
        if session["status"] != "active" or not session["current_question_json"]:
            raise InterviewError("Phiên phỏng vấn đã kết thúc")
        try:
            admitted = submission_admission(connection, session, transcription_id)
        except ValueError as exc:
            raise InterviewError(str(exc)) from exc
        current_question = json.loads(session["current_question_json"])
        expected_question_uid = session["current_question_uid"]
        try:
            require_no_pending_recording(connection, session)
        except TranscriptionError as exc:
            raise InterviewError(str(exc)) from exc

        resolved_answer = answer_text.strip()
        voice_quality: dict[str, Any] = {}
        if session["answer_mode"] == "voice":
            if not transcription_id:
                raise InterviewError("Chế độ Voice yêu cầu bản ghi âm đã được xác nhận")
            try:
                verified = verified_voice_answer(
                    settings.database_path,
                    transcription_id=transcription_id,
                    session_id=session_id,
                    user_id=user_id,
                    question_uid=expected_question_uid,
                )
                resolved_answer = verified["text"]
                voice_quality = verified["metadata"]
                if expected_preview_sha256 is not None and transcript_sha256(resolved_answer) != expected_preview_sha256:
                    raise TranscriptionError("Transcript đã thay đổi; hãy xem lại bản ghi trước khi xác nhận")
                if (expected_preview_sha256 is not None or session["grading_strategy"] == "end_of_session") and not audio_exists(
                        settings.audio_storage_dir or settings.database_path.parent / "audio", verified["audio_path"]):
                    raise TranscriptionError("Không tìm thấy voice tạm; hãy ghi âm lại trước khi xác nhận")
            except TranscriptionError as exc:
                raise InterviewError(str(exc)) from exc

    deferred = session["grading_strategy"] == "end_of_session"
    if deferred:
        evaluation = pending_session_evaluation()
    else:
        evaluation = await evaluate_answer(settings, current_question, resolved_answer,
            **({"ensure_model": ensure_model} if ensure_model else {}),
            **({"inference_runner": inference_runner} if inference_runner else {}))
        apply_voice_assurance(settings, evaluation, current_question, voice_quality, session["interview_mode"])

    with database(settings.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        previous_result = replay(connection)
        if previous_result is not None:
            return previous_result
        session = connection.execute(
            "SELECT * FROM interview_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if (
            not session
            or session["status"] != "active"
            or session["current_question_uid"] != expected_question_uid
        ):
            raise InterviewError("Trạng thái phiên đã thay đổi; câu trả lời chưa được lưu")
        try:
            submission_admission(connection, session, transcription_id, admitted=admitted)
        except ValueError as exc:
            raise InterviewError(str(exc)) from exc

        sequence_number = int(session["answered_count"]) + 1
        if session["answer_mode"] == "voice":
            try:
                require_no_pending_recording(connection, session)
                latest = verified_voice_answer(settings.database_path, transcription_id=transcription_id,
                    session_id=session_id, user_id=user_id, question_uid=expected_question_uid)
                if latest["text"] != resolved_answer:
                    raise TranscriptionError("Transcript đã thay đổi; cần xác nhận lại bản đang xem")
            except TranscriptionError as exc:
                raise InterviewError(str(exc)) from exc
        connection.execute(
            """
            INSERT INTO interview_answers (
                session_id, sequence_number, question_uid, question_json, answer_text,
                score, verdict, matched_points_json, missing_points_json, feedback,
                confidence, evaluator, assessment_json, review_required,
                rubric_version, transcription_id, ai_score, final_score, created_at, score_provisional,
                grading_pending
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                sequence_number,
                current_question["uid"],
                json.dumps(current_question, ensure_ascii=False),
                resolved_answer,
                evaluation["score"],
                evaluation["verdict"],
                json.dumps(evaluation["matched_points"], ensure_ascii=False),
                json.dumps(evaluation["missing_points"], ensure_ascii=False),
                evaluation["feedback"],
                evaluation["confidence"],
                evaluation["evaluator"],
                json.dumps(evaluation.get("point_assessments", []), ensure_ascii=False),
                int(bool(evaluation.get("review_required"))),
                evaluation.get("rubric_version", "key-points-v2"),
                transcription_id,
                evaluation["score"],
                (
                    None
                    if evaluation.get("score_provisional") or (
                        session["interview_mode"] == "real" and session["answer_mode"] == "voice"
                    )
                    else evaluation["score"]
                ),
                _now(),
                int(bool(evaluation.get("score_provisional"))),
                int(deferred),
            ),
        )

        if session["answer_mode"] == "voice" and transcription_id:
            confirmed_at = _now()
            connection.execute(
                "UPDATE speech_transcriptions SET consumed=1,confirmed_at=?,confirmed_text_sha256=? WHERE transcription_id=?",
                (confirmed_at, transcript_sha256(resolved_answer), transcription_id),
            )

        closed_after_receipt = not exam_is_open(connection, session)
        completed = sequence_number >= int(session["requested_count"]) or closed_after_receipt
        next_question: dict[str, Any] | None = None
        next_rank = int(session["current_difficulty_rank"]) if evaluation.get("score_provisional") else _next_rank(
            int(session["current_difficulty_rank"]), float(evaluation["score"])
        )
        if deferred:
            next_rank = planned_difficulty(int(session["starting_difficulty_rank"] or 1),
                                           sequence_number, int(session["requested_count"]))
        finish_reason: str | None = "exam_closed_after_recording" if closed_after_receipt else "requested_count_reached" if completed else None

        if not completed and session["question_plan_json"]:
            plan = json.loads(session["question_plan_json"])
            next_question = plan[sequence_number] if sequence_number < len(plan) else None
            if next_question:
                next_rank = int(next_question["difficulty_rank"])
            else:
                completed, finish_reason = True, "question_plan_completed"
        elif not completed:
            used_uids = [
                row["question_uid"]
                for row in connection.execute(
                    "SELECT question_uid FROM interview_answers WHERE session_id = ?",
                    (session_id,),
                ).fetchall()
            ]
            next_question = _select_question(
                connection,
                language=session["language"],
                subject=session["subject"],
                target_rank=next_rank,
                excluded_uids=used_uids,
                preferred_topic=(
                    current_question.get("topic")
                    if not evaluation.get("score_provisional") and float(evaluation["score"]) < 80
                    else None
                ),
                preferred_concept=(
                    current_question.get("concept")
                    if not evaluation.get("score_provisional") and float(evaluation["score"]) < 80
                    else None
                ),
                exam_round_id=session["exam_round_id"],
            )
            if not next_question:
                completed = True
                finish_reason = "no_more_questions"

        if completed:
            connection.execute(
                """
                UPDATE interview_sessions
                SET answered_count = ?, current_question_uid = NULL,
                    current_question_json = NULL, current_difficulty_rank = ?,
                    status = 'completed', finish_reason = ?, finished_at = ?
                WHERE session_id = ?
                """,
                (sequence_number, next_rank, finish_reason, _now(), session_id),
            )
        else:
            connection.execute(
                """
                UPDATE interview_sessions
                SET answered_count = ?, current_question_uid = ?,
                    current_question_json = ?, current_difficulty_rank = ?
                WHERE session_id = ?
                """,
                (
                    sequence_number,
                    next_question["uid"],
                    json.dumps(next_question, ensure_ascii=False),
                    next_rank,
                    session_id,
                ),
            )

        response = {
            "session_id": session_id, "answered_count": sequence_number,
            "requested_count": int(session["requested_count"]), "completed": completed,
            "finish_reason": finish_reason,
            "evaluation": evaluation if session["interview_mode"] == "practice" else None,
            "next_question": public_question(next_question),
            "grading_strategy": session["grading_strategy"],
            "grading_pending": deferred,
            "answer_confirmed": True,
            "confirmation": {"transcription_id": transcription_id,
                             "preview_sha256": transcript_sha256(resolved_answer),
                             "confirmed_at": confirmed_at if transcription_id and session["answer_mode"] == "voice" else None},
        }
        if completed and deferred:
            queue_session_grading(connection, session_id)
        if transcription_id:
            connection.execute("INSERT INTO submission_receipts (session_id,user_id,request_key,response_json) VALUES (?,?,?,?)",
                               (session_id, user_id, transcription_id, json.dumps(response, ensure_ascii=False)))
    return response


def finish_interview(
    settings: Settings, session_id: str, *, user_id: int
) -> dict[str, Any]:
    with database(settings.database_path) as connection:
        session = connection.execute(
            "SELECT * FROM interview_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not session:
            raise InterviewError("Không tìm thấy phiên phỏng vấn")
        if session["user_id"] != user_id:
            raise InterviewError("Bạn không có quyền kết thúc phiên này")
        if session["interview_mode"] == "real" and session["status"] == "active":
            raise InterviewError(
                "Interview thật chỉ kết thúc sau khi trả lời đủ số câu"
            )
        if session["status"] == "active":
            connection.execute(
                """
                UPDATE interview_sessions
                SET status = 'completed', finish_reason = 'ended_by_user',
                    current_question_uid = NULL, current_question_json = NULL,
                    finished_at = ? WHERE session_id = ?
                """,
                (_now(), session_id),
            )
        queue_session_grading(connection, session_id)
    return {"session_id": session_id, "completed": True}


def interview_report(settings: Settings, session_id: str) -> dict[str, Any]:
    with database(settings.database_path) as connection:
        session = connection.execute(
            "SELECT * FROM interview_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not session:
            raise InterviewError("Không tìm thấy phiên phỏng vấn")
        answer_rows = connection.execute(
            """
            SELECT a.*, t.audio_path, t.audio_sha256, t.audio_mime_type,
                   t.audio_size, t.raw_text, t.corrected_text,
                   t.review_transcript, t.review_model, t.review_runtime,
                   t.review_confidence, t.review_processed_at, t.review_metadata_json,
                   t.metadata_json AS voice_metadata_json
            FROM interview_answers AS a
            LEFT JOIN speech_transcriptions AS t
                ON t.transcription_id = a.transcription_id
            WHERE a.session_id = ? ORDER BY a.sequence_number
            """,
            (session_id,),
        ).fetchall()

    scores: list[float] = []
    competency_scores: dict[str, list[float]] = defaultdict(list)
    matched_counter: Counter[str] = Counter()
    missing_counter: Counter[str] = Counter()
    details: list[dict[str, Any]] = []

    for row in answer_rows:
        question = json.loads(row["question_json"])
        grade = effective_grade(row, interview_mode=session["interview_mode"])
        ai_score, final_score, score = grade["ai_score"], grade["final_score"], grade["score"]
        if session["interview_mode"] == "real" and row["reviewed_at"] is None:
            final_score = None
        provisional = grade["score_provisional"]
        matched, missing, assessments = grade["matched_points"], grade["missing_points"], grade["point_assessments"]
        try:
            review_evaluation = json.loads(row["review_ai_evaluation_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            review_evaluation = {}
        if not isinstance(review_evaluation, dict):
            review_evaluation = {}
        readiness = review_readiness(settings, question=question, score=row["review_ai_score"],
            evaluation_json=row["review_ai_evaluation_json"], metadata_json=row["review_metadata_json"],
            ai_at=row["review_ai_at"], processed_at=row["review_processed_at"], interview_mode=session["interview_mode"])
        provisional = provisional or (readiness["strong_review_ready"] and readiness["score_provisional"])
        if row["reviewed_at"] is not None:
            provisional = False
        if (session["interview_mode"] == "practice" and not provisional) or final_score is not None:
            scores.append(score)
            competency_scores[question["competency"]].append(score)
        if not provisional or row["reviewed_at"] is not None:
            matched_counter.update(matched)
            missing_counter.update(missing)
        details.append(
            {
                "sequence_number": row["sequence_number"],
                "answer_id": row["answer_id"],
                "question": public_question(question),
                "reference_answer": question["reference_answer"],
                "key_points": question["key_points"],
                "answer": row["answer_text"],
                "voice": {
                    "transcription_id": row["transcription_id"],
                    "audio_available": audio_exists(settings.audio_storage_dir or settings.database_path.parent / "audio", row["audio_path"]),
                    "audio_sha256": row["audio_sha256"],
                    "audio_mime_type": row["audio_mime_type"],
                    "audio_size": row["audio_size"],
                    "raw_transcript": row["raw_text"],
                    "verified_transcript": row["corrected_text"],
                    "review_transcript": row["review_transcript"],
                    "review_model": row["review_model"],
                    "review_runtime": row["review_runtime"],
                    "review_confidence": row["review_confidence"],
                    "review_processed_at": row["review_processed_at"],
                },
                "evaluation": {
                    "grading_pending": bool(row["grading_pending"]),
                    "score": score,
                    "ai_score": ai_score,
                    "review_ai_score": row["review_ai_score"],
                    "review_ai_feedback": row["review_ai_feedback"],
                    "review_ai_evaluation": review_evaluation,
                    "review_ai_at": row["review_ai_at"],
                    "final_score": final_score,
                    "score_status": "pending" if row["grading_pending"] else "final" if final_score is not None else
                        "insufficient_evidence" if session["interview_mode"] == "practice" else "proposed",
                    "grading_status": "pending" if row["grading_pending"] else grade["grading_status"],
                    "grading_owner": "ai" if session["interview_mode"] == "practice" else "teacher",
                    "teacher_review_required": session["interview_mode"] == "real" and bool(row["review_required"]),
                    "review_reasons": grade["review_reasons"],
                    "confidence_is_accuracy": False,
                    **readiness,
                    "review_score_provisional": readiness["score_provisional"],
                    "score_provisional": provisional and row["reviewed_at"] is None,
                    "teacher_score": row["teacher_score"],
                    "teacher_feedback": row["teacher_feedback"],
                    "reviewed_by": row["reviewed_by"],
                    "reviewed_at": row["reviewed_at"],
                    "grading_source": grade["grading_source"],
                    "graded_transcript": grade["graded_transcript"],
                    "verdict": _report_verdict(score, session["language"]) if row["reviewed_at"] else row["verdict"],
                    "matched_points": matched,
                    "missing_points": missing,
                    "point_assessments": assessments,
                    "feedback": grade["feedback"],
                    "confidence": grade["confidence"],
                    "evaluator": grade["evaluator"],
                    "review_required": session["interview_mode"] == "real" and bool(row["review_required"]),
                    "rubric_version": grade["rubric_version"],
                },
            }
        )

    average_score = round(sum(scores) / len(scores), 1) if scores else None
    return {
        "session": {
            "session_id": session["session_id"],
            "user_id": session["user_id"],
            "candidate_name": session["candidate_name"],
            "interview_mode": session["interview_mode"],
            "exam_round_id": session["exam_round_id"],
            "answer_mode": session["answer_mode"],
            "grading_strategy": session["grading_strategy"],
            "question_selection": "fixed" if session["question_plan_json"] else "adaptive",
            "language": session["language"],
            "subject": session["subject"],
            "requested_count": session["requested_count"],
            "answered_count": session["answered_count"],
            "status": session["status"],
            "finish_reason": session["finish_reason"],
            "created_at": session["created_at"],
            "finished_at": session["finished_at"],
        },
        "summary": {
            "average_score": average_score,
            "scored_answer_count": len(scores),
            "pending_answer_count": max(0, len(answer_rows) - len(scores)),
            "overall_verdict": (
                _report_verdict(average_score, session["language"])
                if scores
                else ("Chưa đủ cơ sở chấm điểm" if session["language"] == "vi" else "Insufficient evidence to score")
            ),
            "competencies": [
                {
                    "name": name,
                    "average_score": round(sum(values) / len(values), 1),
                    "question_count": len(values),
                }
                for name, values in sorted(competency_scores.items())
            ],
            "strengths": [item for item, _ in matched_counter.most_common(5)],
            "gaps": [item for item, _ in missing_counter.most_common(5)],
        },
        "answers": details,
    }


def session_metadata(database_path: Path, session_id: str) -> dict[str, Any] | None:
    with database(database_path) as connection:
        row = connection.execute(
            """
            SELECT session_id, user_id, interview_mode, exam_round_id, status, grading_strategy
            FROM interview_sessions WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def list_practice_history(
    database_path: Path, *, user_id: int, limit: int = 100
) -> list[dict[str, Any]]:
    """Return only the signed-in candidate's practice sessions."""
    safe_limit = max(1, min(int(limit), 200))
    with database(database_path) as connection:
        rows = connection.execute(
            """
            SELECT
                sessions.session_id,
                sessions.language,
                sessions.subject,
                sessions.requested_count,
                sessions.answered_count,
                sessions.status,
                sessions.finish_reason,
                sessions.created_at,
                sessions.finished_at,
                COUNT(answers.answer_id) AS stored_answer_count,
                AVG(CASE WHEN grade_is_provisional(answers.score_provisional,answers.assessment_json,voice.metadata_json)=0 OR answers.reviewed_at IS NOT NULL
                    THEN COALESCE(answers.final_score, answers.score) END) AS average_score
            FROM interview_sessions AS sessions
            LEFT JOIN interview_answers AS answers
                ON answers.session_id = sessions.session_id
            LEFT JOIN speech_transcriptions AS voice ON voice.transcription_id=answers.transcription_id
            WHERE sessions.user_id = ? AND sessions.interview_mode = 'practice'
            GROUP BY sessions.session_id
            ORDER BY sessions.created_at DESC
            LIMIT ?
            """,
            (user_id, safe_limit),
        ).fetchall()

    history: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["stored_answer_count"] = int(item["stored_answer_count"] or 0)
        item["average_score"] = (
            round(float(item["average_score"]), 1)
            if item["average_score"] is not None
            else None
        )
        item["can_view_report"] = item["stored_answer_count"] > 0
        history.append(item)
    return history


def delete_practice_history(
    database_path: Path, *, session_id: str, user_id: int, audio_storage_dir: Path | None = None
) -> dict[str, Any]:
    with database(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        session = connection.execute(
            """
            SELECT session_id, user_id, interview_mode
            FROM interview_sessions WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        if not session:
            raise InterviewError("Không tìm thấy lịch sử luyện tập")
        if session["interview_mode"] != "practice" or session["user_id"] != user_id:
            raise InterviewError("Bạn không có quyền xóa lịch sử này")
        audio_keys = schedule_session_audio(connection, session_id, audio_storage_dir or database_path.parent / "audio")

        connection.execute(
            """
            DELETE FROM answer_reviews
            WHERE answer_id IN (
                SELECT answer_id FROM interview_answers WHERE session_id = ?
            )
            """,
            (session_id,),
        )
        connection.execute(
            "DELETE FROM interview_answers WHERE session_id = ?", (session_id,)
        )
        connection.execute(
            "DELETE FROM speech_transcriptions WHERE session_id = ?", (session_id,)
        )
        connection.execute(
            "DELETE FROM interview_sessions WHERE session_id = ?", (session_id,)
        )
    return {"deleted": True, "session_id": session_id, **deletion_result(database_path, audio_keys)}


def delete_real_interview_result(
    database_path: Path, *, session_id: str, audio_storage_dir: Path | None = None
) -> dict[str, Any]:
    with database(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        session = connection.execute(
            """
            SELECT session_id, interview_mode
            FROM interview_sessions WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        if not session:
            raise InterviewError("Không tìm thấy kết quả Interview")
        if session["interview_mode"] != "real":
            raise InterviewError("Chỉ được xóa kết quả Interview thật tại đây")
        audio_keys = schedule_session_audio(connection, session_id, audio_storage_dir or database_path.parent / "audio")

        connection.execute(
            """
            DELETE FROM answer_reviews
            WHERE answer_id IN (
                SELECT answer_id FROM interview_answers WHERE session_id = ?
            )
            """,
            (session_id,),
        )
        connection.execute(
            "DELETE FROM interview_answers WHERE session_id = ?", (session_id,)
        )
        connection.execute(
            "DELETE FROM speech_transcriptions WHERE session_id = ?", (session_id,)
        )
        connection.execute(
            "DELETE FROM interview_sessions WHERE session_id = ?", (session_id,)
        )
    return {"deleted": True, "session_id": session_id, **deletion_result(database_path, audio_keys)}


def _report_verdict(score: float, language: str) -> str:
    if language == "vi":
        return "Mạnh" if score >= 80 else "Khá" if score >= 65 else "Cần phát triển"
    return "Strong" if score >= 80 else "Developing" if score >= 65 else "Needs development"


def question_summary(database_path: Path) -> dict[str, Any]:
    with database(database_path) as connection:
        rows = connection.execute(
            """
            SELECT language, subject, difficulty, difficulty_rank, COUNT(*) AS total
            FROM questions WHERE active = 1 AND bank_scope = 'learning'
            GROUP BY language, subject, difficulty, difficulty_rank
            ORDER BY language, subject, difficulty_rank
            """
        ).fetchall()
        sources = connection.execute(
            """
            SELECT source_name, languages, question_count, import_mode,
                   verification_status, imported_at
            FROM question_sources ORDER BY source_id DESC LIMIT 10
            """
        ).fetchall()

    languages: dict[str, dict[str, Any]] = {}
    total = 0
    for row in rows:
        language = languages.setdefault(
            row["language"],
            {"language": row["language"], "total": 0, "subjects": {}},
        )
        subject = language["subjects"].setdefault(
            row["subject"],
            {
                "name": row["subject"],
                "total": 0,
                "difficulties": {"Easy": 0, "Medium": 0, "Hard": 0},
            },
        )
        count = int(row["total"])
        subject["total"] += count
        subject["difficulties"][row["difficulty"]] = count
        language["total"] += count
        total += count

    return {
        "total": total,
        "languages": [
            {
                **value,
                "subjects": list(value["subjects"].values()),
            }
            for value in languages.values()
        ],
        "sources": [dict(row) for row in sources],
        "verification_status": "unverified",
    }
