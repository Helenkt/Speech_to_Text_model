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
from app.services.transcription_store import (
    TranscriptionError,
    verified_voice_answer,
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

    clauses = ["active = 1", "language = ?"]
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
    return _row_to_question(row) if row else None


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

        connection.execute(
            """
            INSERT INTO interview_sessions (
                session_id, user_id, candidate_name, interview_mode, exam_round_id,
                answer_mode, language, subject, requested_count,
                current_question_uid, current_question_json, current_difficulty_rank,
                evaluator_requested, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
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
        "question": public_question(first_question),
    }


def _next_rank(current_rank: int, score: float) -> int:
    if score >= 80:
        return min(3, current_rank + 1)
    if score < 45:
        return max(1, current_rank - 1)
    return current_rank


async def submit_answer(
    settings: Settings,
    session_id: str,
    answer_text: str,
    *,
    user_id: int,
    transcription_id: str | None = None,
) -> dict[str, Any]:
    with database(settings.database_path) as connection:
        session = connection.execute(
            "SELECT * FROM interview_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not session:
            raise InterviewError("Không tìm thấy phiên phỏng vấn")
        if session["user_id"] != user_id:
            raise InterviewError("Bạn không có quyền trả lời phiên này")
        if session["status"] != "active" or not session["current_question_json"]:
            raise InterviewError("Phiên phỏng vấn đã kết thúc")
        if session["interview_mode"] == "real":
            exam = connection.execute(
                "SELECT status, starts_at, ends_at FROM exam_rounds WHERE exam_round_id = ?",
                (session["exam_round_id"],),
            ).fetchone()
            current_time = datetime.now(timezone.utc)
            if (
                not exam
                or exam["status"] != "open"
                or current_time < datetime.fromisoformat(exam["starts_at"])
                or current_time > datetime.fromisoformat(exam["ends_at"])
            ):
                raise InterviewError("Đợt Interview đã đóng hoặc hết thời gian")
        current_question = json.loads(session["current_question_json"])
        expected_question_uid = session["current_question_uid"]

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
            except TranscriptionError as exc:
                raise InterviewError(str(exc)) from exc

    evaluation = await evaluate_answer(settings, current_question, resolved_answer)
    stt_warnings = list(voice_quality.get("quality_warnings") or [])
    quality_score_value = (voice_quality.get("metrics") or {}).get("quality_score")
    quality_score = float(quality_score_value) if quality_score_value is not None else None
    if stt_warnings or (quality_score is not None and quality_score < 0.55):
        evaluation["review_required"] = True
        notice = (
            "Bản ghi giọng nói có cảnh báo chất lượng; giáo viên cần đối chiếu transcript trước khi dùng điểm."
            if current_question.get("language") == "vi"
            else "The voice recording has quality warnings; review the transcript before using this score."
        )
        if notice not in evaluation["feedback"]:
            evaluation["feedback"] = f'{evaluation["feedback"]} {notice}'.strip()

    with database(settings.database_path) as connection:
        session = connection.execute(
            "SELECT * FROM interview_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if (
            not session
            or session["status"] != "active"
            or session["current_question_uid"] != expected_question_uid
        ):
            raise InterviewError("Trạng thái phiên đã thay đổi; câu trả lời chưa được lưu")

        sequence_number = int(session["answered_count"]) + 1
        connection.execute(
            """
            INSERT INTO interview_answers (
                session_id, sequence_number, question_uid, question_json, answer_text,
                score, verdict, matched_points_json, missing_points_json, feedback,
                confidence, evaluator, assessment_json, review_required,
                rubric_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                _now(),
            ),
        )

        if session["answer_mode"] == "voice" and transcription_id:
            connection.execute(
                "UPDATE speech_transcriptions SET consumed = 1 WHERE transcription_id = ?",
                (transcription_id,),
            )

        completed = sequence_number >= int(session["requested_count"])
        next_question: dict[str, Any] | None = None
        next_rank = _next_rank(
            int(session["current_difficulty_rank"]), float(evaluation["score"])
        )
        finish_reason: str | None = "requested_count_reached" if completed else None

        if not completed:
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
                    if float(evaluation["score"]) < 80
                    else None
                ),
                preferred_concept=(
                    current_question.get("concept")
                    if float(evaluation["score"]) < 80
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

    return {
        "session_id": session_id,
        "answered_count": sequence_number,
        "requested_count": int(session["requested_count"]),
        "completed": completed,
        "finish_reason": finish_reason,
        "evaluation": evaluation if session["interview_mode"] == "practice" else None,
        "next_question": public_question(next_question),
    }


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
            SELECT * FROM interview_answers
            WHERE session_id = ? ORDER BY sequence_number
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
        score = float(row["score"])
        scores.append(score)
        competency_scores[question["competency"]].append(score)
        matched = json.loads(row["matched_points_json"])
        missing = json.loads(row["missing_points_json"])
        assessments = json.loads(row["assessment_json"] or "{}")
        if not isinstance(assessments, list):
            assessments = []
        matched_counter.update(matched)
        missing_counter.update(missing)
        details.append(
            {
                "sequence_number": row["sequence_number"],
                "question": public_question(question),
                "reference_answer": question["reference_answer"],
                "key_points": question["key_points"],
                "answer": row["answer_text"],
                "evaluation": {
                    "score": score,
                    "verdict": row["verdict"],
                    "matched_points": matched,
                    "missing_points": missing,
                    "point_assessments": assessments,
                    "feedback": row["feedback"],
                    "confidence": row["confidence"],
                    "evaluator": row["evaluator"],
                    "review_required": bool(row["review_required"]),
                    "rubric_version": row["rubric_version"],
                },
            }
        )

    average_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    return {
        "session": {
            "session_id": session["session_id"],
            "user_id": session["user_id"],
            "candidate_name": session["candidate_name"],
            "interview_mode": session["interview_mode"],
            "exam_round_id": session["exam_round_id"],
            "answer_mode": session["answer_mode"],
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
            "overall_verdict": (
                _report_verdict(average_score, session["language"])
                if scores
                else ("Chưa có dữ liệu" if session["language"] == "vi" else "No data")
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
            SELECT session_id, user_id, interview_mode, exam_round_id, status
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
                AVG(answers.score) AS average_score
            FROM interview_sessions AS sessions
            LEFT JOIN interview_answers AS answers
                ON answers.session_id = sessions.session_id
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
    database_path: Path, *, session_id: str, user_id: int
) -> dict[str, Any]:
    with database(database_path) as connection:
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

        connection.execute(
            "DELETE FROM speech_transcriptions WHERE session_id = ?", (session_id,)
        )
        connection.execute(
            "DELETE FROM interview_answers WHERE session_id = ?", (session_id,)
        )
        connection.execute(
            "DELETE FROM interview_sessions WHERE session_id = ?", (session_id,)
        )
    return {"deleted": True, "session_id": session_id}


def delete_real_interview_result(
    database_path: Path, *, session_id: str
) -> dict[str, Any]:
    with database(database_path) as connection:
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

        connection.execute(
            "DELETE FROM speech_transcriptions WHERE session_id = ?", (session_id,)
        )
        connection.execute(
            "DELETE FROM interview_answers WHERE session_id = ?", (session_id,)
        )
        connection.execute(
            "DELETE FROM interview_sessions WHERE session_id = ?", (session_id,)
        )
    return {"deleted": True, "session_id": session_id}


def _report_verdict(score: float, language: str) -> str:
    if language == "vi":
        return "Mạnh" if score >= 80 else "Khá" if score >= 65 else "Cần phát triển"
    return "Strong" if score >= 80 else "Developing" if score >= 65 else "Needs development"


def question_summary(database_path: Path) -> dict[str, Any]:
    with database(database_path) as connection:
        rows = connection.execute(
            """
            SELECT language, subject, difficulty, difficulty_rank, COUNT(*) AS total
            FROM questions WHERE active = 1
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
