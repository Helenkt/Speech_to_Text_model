from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings
from app.database import database
from app.services.interview_engine import (
    InterviewError,
    _row_to_question,
    public_question,
    start_interview,
)


class ExamError(ValueError):
    pass


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _now() -> str:
    return _now_dt().isoformat()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ExamError("Thời gian bắt đầu và kết thúc phải có múi giờ")
    return value.astimezone(timezone.utc)


def _availability(row: Any, now: datetime | None = None) -> str:
    current = now or _now_dt()
    if row["status"] != "open":
        return "closed" if row["status"] == "closed" else "draft"
    starts_at = datetime.fromisoformat(row["starts_at"])
    ends_at = datetime.fromisoformat(row["ends_at"])
    if current < starts_at:
        return "not_started"
    if current > ends_at:
        return "expired"
    return "available"


def _round_dict(row: Any) -> dict[str, Any]:
    data = {
        "exam_round_id": row["exam_round_id"],
        "exam_code": row["exam_code"],
        "title": row["title"],
        "language": row["language"],
        "subject": row["subject"],
        "question_count": int(row["question_count"]),
        "starting_difficulty": row["starting_difficulty"],
        "answer_mode": row["answer_mode"],
        "starts_at": row["starts_at"],
        "ends_at": row["ends_at"],
        "status": row["status"],
        "availability": _availability(row),
        "created_at": row["created_at"],
    }
    keys = set(row.keys())
    if "attempt_count" in keys:
        data["attempt_count"] = int(row["attempt_count"] or 0)
    if "completed_count" in keys:
        data["completed_count"] = int(row["completed_count"] or 0)
    return data


def create_exam_round(
    database_path: Path,
    *,
    created_by: int,
    title: str,
    exam_code: str,
    language: str,
    subject: str,
    question_count: int,
    starting_difficulty: str,
    answer_mode: str,
    starts_at: datetime,
    ends_at: datetime,
) -> dict[str, Any]:
    # All exam rounds use verified server-side speech transcriptions.
    answer_mode = "voice"
    code = exam_code.strip().upper()
    language = language.strip().lower()
    subject = subject.strip()
    title = title.strip() or f"Interview {subject}"
    starts = _utc(starts_at)
    ends = _utc(ends_at)

    if not re.fullmatch(r"[A-Z0-9_-]{4,20}", code):
        raise ExamError("Mã đề gồm 4-20 ký tự: A-Z, 0-9, gạch ngang hoặc gạch dưới")
    if not subject:
        raise ExamError("Vui lòng chọn môn học/lĩnh vực")
    if ends <= starts:
        raise ExamError("Thời gian kết thúc phải sau thời gian bắt đầu")
    if answer_mode not in {"text", "voice", "both"}:
        raise ExamError("Hình thức trả lời không hợp lệ")

    round_id = str(uuid.uuid4())
    now = _now()
    with database(database_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM questions
            WHERE active = 1 AND language = ? AND subject = ?
            ORDER BY difficulty_rank, question_id
            """,
            (language, subject),
        ).fetchall()
        if len(rows) < question_count:
            raise ExamError(
                f"Bộ dữ liệu chỉ có {len(rows)} câu phù hợp; cần ít nhất {question_count} câu"
            )
        try:
            connection.execute(
                """
                INSERT INTO exam_rounds (
                    exam_round_id, exam_code, title, language, subject,
                    question_count, starting_difficulty, answer_mode, starts_at,
                    ends_at, status, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?)
                """,
                (
                    round_id,
                    code,
                    title,
                    language,
                    subject,
                    question_count,
                    starting_difficulty,
                    answer_mode,
                    starts.isoformat(),
                    ends.isoformat(),
                    created_by,
                    now,
                    now,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ExamError("Mã đề đã tồn tại; hãy dùng mã khác") from exc

        snapshots = []
        for row in rows:
            question = _row_to_question(row)
            snapshots.append(
                (
                    round_id,
                    question["uid"],
                    json.dumps(question, ensure_ascii=False),
                    question["difficulty_rank"],
                    question["topic"],
                    question["concept"],
                )
            )
        connection.executemany(
            """
            INSERT INTO exam_round_questions (
                exam_round_id, question_uid, question_json, difficulty_rank, topic,
                concept
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            snapshots,
        )
        row = connection.execute(
            "SELECT * FROM exam_rounds WHERE exam_round_id = ?", (round_id,)
        ).fetchone()
    return _round_dict(row)


def list_exam_rounds(database_path: Path) -> list[dict[str, Any]]:
    with database(database_path) as connection:
        rows = connection.execute(
            """
            SELECT r.*,
                   COUNT(s.session_id) AS attempt_count,
                   SUM(CASE WHEN s.status = 'completed' THEN 1 ELSE 0 END) AS completed_count
            FROM exam_rounds AS r
            LEFT JOIN interview_sessions AS s ON s.exam_round_id = r.exam_round_id
            GROUP BY r.exam_round_id
            ORDER BY r.created_at DESC
            """
        ).fetchall()
    return [_round_dict(row) for row in rows]


def set_exam_status(
    database_path: Path, exam_round_id: str, status: str
) -> dict[str, Any]:
    if status not in {"open", "closed"}:
        raise ExamError("Trạng thái chỉ nhận open hoặc closed")
    with database(database_path) as connection:
        found = connection.execute(
            "SELECT 1 FROM exam_rounds WHERE exam_round_id = ?", (exam_round_id,)
        ).fetchone()
        if not found:
            raise ExamError("Không tìm thấy đợt Interview")
        connection.execute(
            "UPDATE exam_rounds SET status = ?, updated_at = ? WHERE exam_round_id = ?",
            (status, _now(), exam_round_id),
        )
        row = connection.execute(
            "SELECT * FROM exam_rounds WHERE exam_round_id = ?", (exam_round_id,)
        ).fetchone()
    return _round_dict(row)


def delete_exam_round(database_path: Path, exam_round_id: str) -> dict[str, Any]:
    """Delete an Interview round and every record that depends on it."""
    with database(database_path) as connection:
        exam = connection.execute(
            "SELECT exam_code FROM exam_rounds WHERE exam_round_id = ?",
            (exam_round_id,),
        ).fetchone()
        if not exam:
            raise ExamError("Không tìm thấy đợt Interview")

        counts = connection.execute(
            """
            SELECT COUNT(DISTINCT s.session_id) AS attempt_count,
                   COUNT(a.answer_id) AS answer_count
            FROM interview_sessions AS s
            LEFT JOIN interview_answers AS a ON a.session_id = s.session_id
            WHERE s.exam_round_id = ?
            """,
            (exam_round_id,),
        ).fetchone()
        question_count = connection.execute(
            "SELECT COUNT(*) FROM exam_round_questions WHERE exam_round_id = ?",
            (exam_round_id,),
        ).fetchone()[0]

        connection.execute(
            """
            DELETE FROM speech_transcriptions
            WHERE session_id IN (
                SELECT session_id FROM interview_sessions WHERE exam_round_id = ?
            )
            """,
            (exam_round_id,),
        )
        connection.execute(
            """
            DELETE FROM interview_answers
            WHERE session_id IN (
                SELECT session_id FROM interview_sessions WHERE exam_round_id = ?
            )
            """,
            (exam_round_id,),
        )
        connection.execute(
            "DELETE FROM interview_sessions WHERE exam_round_id = ?",
            (exam_round_id,),
        )
        connection.execute(
            "DELETE FROM exam_round_questions WHERE exam_round_id = ?",
            (exam_round_id,),
        )
        connection.execute(
            "DELETE FROM exam_rounds WHERE exam_round_id = ?",
            (exam_round_id,),
        )

    return {
        "deleted": True,
        "exam_round_id": exam_round_id,
        "exam_code": exam["exam_code"],
        "deleted_attempts": int(counts["attempt_count"] or 0),
        "deleted_answers": int(counts["answer_count"] or 0),
        "deleted_question_snapshots": int(question_count or 0),
    }


def find_candidate_exam(database_path: Path, exam_code: str) -> dict[str, Any]:
    with database(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM exam_rounds WHERE exam_code = ? COLLATE NOCASE",
            (exam_code.strip(),),
        ).fetchone()
    if not row:
        raise ExamError("Mã đề không tồn tại")
    return _round_dict(row)


def start_real_interview(
    settings: Settings, *, user: dict[str, Any], exam_code: str
) -> dict[str, Any]:
    exam = find_candidate_exam(settings.database_path, exam_code)
    if exam["availability"] != "available":
        messages = {
            "not_started": "Đợt Interview chưa đến giờ bắt đầu",
            "expired": "Đợt Interview đã hết thời gian",
            "closed": "Giáo viên chưa mở hoặc đã đóng đợt Interview",
            "draft": "Đợt Interview chưa được mở",
        }
        raise ExamError(messages.get(exam["availability"], "Chưa thể bắt đầu Interview"))

    with database(settings.database_path) as connection:
        previous = connection.execute(
            """
            SELECT * FROM interview_sessions
            WHERE exam_round_id = ? AND user_id = ?
            """,
            (exam["exam_round_id"], user["user_id"]),
        ).fetchone()
    if previous:
        if previous["status"] == "active" and previous["current_question_json"]:
            return {
                "session_id": previous["session_id"],
                "candidate_name": previous["candidate_name"],
                "requested_count": int(previous["requested_count"]),
                "answered_count": int(previous["answered_count"]),
                "interview_mode": "real",
                "answer_mode": previous["answer_mode"],
                "language": previous["language"],
                "exam": exam,
                "resumed": True,
                "question": public_question(json.loads(previous["current_question_json"])),
            }
        raise ExamError("Bạn đã sử dụng lượt làm bài cho mã đề này")

    try:
        session = start_interview(
            settings,
            user_id=user["user_id"],
            candidate_name=user["full_name"],
            language=exam["language"],
            subject=exam["subject"],
            question_count=exam["question_count"],
            starting_difficulty=exam["starting_difficulty"],
            interview_mode="real",
            exam_round_id=exam["exam_round_id"],
            answer_mode=exam["answer_mode"],
        )
    except (InterviewError, sqlite3.IntegrityError) as exc:
        raise ExamError(str(exc)) from exc
    session["exam"] = exam
    return session


def list_exam_attempts(
    database_path: Path, exam_round_id: str | None = None
) -> list[dict[str, Any]]:
    clauses = ["s.interview_mode = 'real'"]
    parameters: list[Any] = []
    if exam_round_id:
        clauses.append("s.exam_round_id = ?")
        parameters.append(exam_round_id)
    with database(database_path) as connection:
        rows = connection.execute(
            f"""
            SELECT s.session_id, s.candidate_name, s.status, s.answered_count,
                   s.requested_count, s.created_at, s.finished_at, u.username,
                   u.email, u.student_id, r.exam_code, r.title, r.subject,
                   ROUND(AVG(a.score), 1) AS average_score
            FROM interview_sessions AS s
            JOIN users AS u ON u.user_id = s.user_id
            JOIN exam_rounds AS r ON r.exam_round_id = s.exam_round_id
            LEFT JOIN interview_answers AS a ON a.session_id = s.session_id
            WHERE {' AND '.join(clauses)}
            GROUP BY s.session_id
            ORDER BY s.created_at DESC
            """,
            parameters,
        ).fetchall()
    return [dict(row) for row in rows]
