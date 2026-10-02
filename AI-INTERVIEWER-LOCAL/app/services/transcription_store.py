from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.database import database


class TranscriptionError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def transcription_context(
    database_path: Path, *, session_id: str, user_id: int
) -> dict[str, Any]:
    with database(database_path) as connection:
        session = connection.execute(
            "SELECT * FROM interview_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    if not session or session["user_id"] != user_id:
        raise TranscriptionError("Không tìm thấy phiên phỏng vấn phù hợp")
    if session["status"] != "active" or not session["current_question_json"]:
        raise TranscriptionError("Phiên phỏng vấn không còn câu hỏi đang chờ trả lời")

    question = json.loads(session["current_question_json"])
    phrases = [
        str(question.get(field) or "").strip()
        for field in ("subject", "topic", "concept")
    ]
    technical_tokens = re.findall(
        r"[A-Za-z][A-Za-z0-9+#._-]{2,}", str(question.get("question") or "")
    )
    approved_terms = list(dict.fromkeys(item for item in phrases + technical_tokens if item))
    return {
        "session_id": session_id,
        "question_uid": session["current_question_uid"],
        "answer_mode": session["answer_mode"],
        "language": session["language"],
        "question_text": str(question.get("question") or "").strip(),
        "approved_terms": approved_terms,
    }


def save_transcription(
    database_path: Path,
    *,
    session_id: str,
    user_id: int,
    question_uid: str,
    raw_text: str,
    corrected_text: str,
    model: str,
    runtime: str,
    confidence: float,
    ambient_noise_dbfs: float | None,
    metadata: dict[str, Any],
) -> str:
    transcription_id = str(uuid.uuid4())
    with database(database_path) as connection:
        connection.execute(
            """
            INSERT INTO speech_transcriptions (
                transcription_id, session_id, user_id, question_uid, raw_text,
                corrected_text, model, runtime, confidence, ambient_noise_dbfs,
                metadata_json, accepted, consumed, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?)
            """,
            (
                transcription_id, session_id, user_id, question_uid, raw_text,
                corrected_text, model, runtime, confidence, ambient_noise_dbfs,
                json.dumps(metadata, ensure_ascii=False), _now(),
            ),
        )
    return transcription_id


def verified_voice_answer(
    database_path: Path,
    *,
    transcription_id: str,
    session_id: str,
    user_id: int,
    question_uid: str,
) -> dict[str, Any]:
    with database(database_path) as connection:
        row = connection.execute(
            """
            SELECT corrected_text, confidence, metadata_json FROM speech_transcriptions
            WHERE transcription_id = ? AND session_id = ? AND user_id = ?
              AND question_uid = ? AND accepted = 1 AND consumed = 0
            """,
            (transcription_id, session_id, user_id, question_uid),
        ).fetchone()
    if not row:
        raise TranscriptionError(
            "Bản ghi âm không hợp lệ hoặc đã được dùng. Hãy ghi âm lại câu trả lời."
        )
    try:
        metadata = json.loads(row["metadata_json"] or "{}")
    except (TypeError, json.JSONDecodeError):
        metadata = {}
    return {
        "text": str(row["corrected_text"]).strip(),
        "confidence": float(row["confidence"] or 0.0),
        "metadata": metadata if isinstance(metadata, dict) else {},
    }
