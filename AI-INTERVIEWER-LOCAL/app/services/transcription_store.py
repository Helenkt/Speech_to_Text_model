from __future__ import annotations

import json
import hashlib
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

    try:
        mic_result = json.loads(session["mic_check_result_json"] or "{}")
    except (TypeError, json.JSONDecodeError):
        mic_result = {}
    if not mic_result.get("ready"):
        raise TranscriptionError(
            "Hãy hoàn tất kiểm tra microphone trước khi ghi câu trả lời."
        )

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
        "microphone_check": mic_result,
    }


def microphone_check_session(
    database_path: Path, *, user_id: int, session_id: str
) -> dict[str, Any]:
    with database(database_path) as connection:
        row = connection.execute(
            """
            SELECT session_id, mic_checked_at, mic_check_result_json
            FROM interview_sessions
            WHERE session_id = ? AND user_id = ? AND status = 'active'
            """,
            (session_id, user_id),
        ).fetchone()
    if not row:
        raise TranscriptionError(
            "Phiên phỏng vấn này không tồn tại hoặc không còn hoạt động."
        )
    try:
        result = json.loads(row["mic_check_result_json"] or "{}")
    except (TypeError, json.JSONDecodeError):
        result = {}
    return {
        "session_id": row["session_id"],
        "checked_at": row["mic_checked_at"],
        "result": result if isinstance(result, dict) else {},
    }


def expire_stale_sessions(database_path: Path, *, ttl_hours: int = 24) -> int:
    """Close abandoned sessions without deleting their answers or recordings."""
    ttl_hours = max(1, int(ttl_hours))
    with database(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        practice = connection.execute(
            """
            UPDATE interview_sessions
            SET status = 'completed', finish_reason = 'session_expired',
                current_question_uid = NULL, current_question_json = NULL,
                finished_at = CURRENT_TIMESTAMP
            WHERE status = 'active' AND interview_mode = 'practice'
              AND datetime(created_at) <= datetime('now', ?)
            """,
            (f"-{ttl_hours} hours",),
        ).rowcount
        real = connection.execute(
            """
            UPDATE interview_sessions
            SET status = 'completed', finish_reason = 'exam_expired',
                current_question_uid = NULL, current_question_json = NULL,
                finished_at = CURRENT_TIMESTAMP
            WHERE status = 'active' AND interview_mode = 'real'
              AND EXISTS (
                  SELECT 1 FROM exam_rounds AS exams
                  WHERE exams.exam_round_id = interview_sessions.exam_round_id
                    AND datetime(exams.ends_at) <= datetime('now')
              )
            """
        ).rowcount
    return int(practice or 0) + int(real or 0)


def save_microphone_check(
    database_path: Path,
    *,
    session_id: str,
    user_id: int,
    result: dict[str, Any],
) -> dict[str, Any]:
    now = _now()
    payload = {**result, "checked_at": now, "session_id": session_id}
    with database(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT mic_check_result_json FROM interview_sessions
            WHERE session_id = ? AND user_id = ? AND status = 'active'
            """,
            (session_id, user_id),
        ).fetchone()
        if not row:
            raise TranscriptionError("Phiên phỏng vấn không còn hoạt động.")
        try:
            previous = json.loads(row["mic_check_result_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            previous = {}
        if isinstance(previous, dict) and previous.get("ready"):
            return {**previous, "already_checked": True}
        connection.execute(
            """
            UPDATE interview_sessions
            SET mic_checked_at = ?, mic_check_result_json = ?
            WHERE session_id = ? AND user_id = ?
            """,
            (now, json.dumps(payload, ensure_ascii=False), session_id, user_id),
        )
    return {**payload, "already_checked": False}


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
    audio_storage_dir: Path | None = None,
    audio_content: bytes | None = None,
    audio_filename: str | None = None,
    audio_mime_type: str | None = None,
    retry_reason: str | None = None,
) -> str:
    transcription_id = str(uuid.uuid4())
    relative_audio_path: str | None = None
    audio_sha256: str | None = None
    audio_size: int | None = None
    saved_audio_path: Path | None = None

    if audio_content:
        allowed_extensions = {".webm", ".wav", ".mp3", ".m4a", ".ogg", ".flac", ".mp4"}
        extension = Path(audio_filename or "recording.webm").suffix.lower()
        if extension not in allowed_extensions:
            extension = ".webm"
        storage_root = (audio_storage_dir or database_path.parent / "audio").resolve()
        session_dir = storage_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        saved_audio_path = session_dir / f"{transcription_id}{extension}"
        temporary_path = saved_audio_path.with_suffix(saved_audio_path.suffix + ".tmp")
        temporary_path.write_bytes(audio_content)
        temporary_path.replace(saved_audio_path)
        relative_audio_path = saved_audio_path.relative_to(storage_root).as_posix()
        audio_sha256 = hashlib.sha256(audio_content).hexdigest()
        audio_size = len(audio_content)

    try:
        with database(database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            session = connection.execute(
                """
                SELECT status, current_question_uid FROM interview_sessions
                WHERE session_id = ? AND user_id = ?
                """,
                (session_id, user_id),
            ).fetchone()
            if (
                not session
                or session["status"] != "active"
                or session["current_question_uid"] != question_uid
            ):
                raise TranscriptionError(
                    "Phiên phỏng vấn hoặc câu hỏi hiện tại đã thay đổi."
                )
            previous_rows = connection.execute(
                """
                SELECT transcription_id, attempt_number
                FROM speech_transcriptions
                WHERE session_id = ? AND user_id = ? AND question_uid = ?
                  AND consumed = 0
                ORDER BY attempt_number, created_at
                """,
                (session_id, user_id, question_uid),
            ).fetchall()
            attempt_number = max(
                (int(row["attempt_number"] or 1) for row in previous_rows),
                default=0,
            ) + 1
            allowed_reasons = {
                "transcript_still_incorrect",
                "candidate_spoke_incorrectly",
            }
            requested_reason = (retry_reason or "").strip()
            reason = (
                requested_reason
                if previous_rows and requested_reason in allowed_reasons
                else "candidate_requested_retake" if previous_rows else None
            )
            metadata_payload = {
                **metadata,
                "attempt": {
                    "number": attempt_number,
                    "retry_reason": reason,
                    "supersedes": [row["transcription_id"] for row in previous_rows],
                },
            }
            connection.execute(
                """
                INSERT INTO speech_transcriptions (
                    transcription_id, session_id, user_id, question_uid, raw_text,
                    corrected_text, model, runtime, confidence, ambient_noise_dbfs,
                    metadata_json, audio_path, audio_sha256, audio_mime_type,
                    audio_size, accepted, consumed, attempt_number, retry_reason,
                    superseded_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, NULL, ?)
                """,
                (
                    transcription_id,
                    session_id,
                    user_id,
                    question_uid,
                    raw_text,
                    corrected_text,
                    model,
                    runtime,
                    confidence,
                    ambient_noise_dbfs,
                    json.dumps(metadata_payload, ensure_ascii=False),
                    relative_audio_path,
                    audio_sha256,
                    audio_mime_type,
                    audio_size,
                    attempt_number,
                    reason,
                    _now(),
                ),
            )
            if previous_rows:
                connection.execute(
                    """
                    UPDATE speech_transcriptions
                    SET accepted = 0, retry_reason = COALESCE(retry_reason, ?),
                        superseded_by = ?
                    WHERE session_id = ? AND user_id = ? AND question_uid = ?
                      AND transcription_id <> ? AND consumed = 0
                    """,
                    (
                        reason,
                        transcription_id,
                        session_id,
                        user_id,
                        question_uid,
                        transcription_id,
                    ),
                )
    except Exception:
        if saved_audio_path:
            saved_audio_path.unlink(missing_ok=True)
        raise
    return transcription_id


def transcription_attempt_status(
    database_path: Path, *, transcription_id: str
) -> dict[str, Any]:
    with database(database_path) as connection:
        row = connection.execute(
            """
            SELECT attempt_number, retry_reason FROM speech_transcriptions
            WHERE transcription_id = ?
            """,
            (transcription_id,),
        ).fetchone()
    if not row:
        raise TranscriptionError("Không tìm thấy lần ghi âm vừa lưu.")
    return {
        "attempt_number": int(row["attempt_number"] or 1),
        "retry_reason": row["retry_reason"],
        "can_retry": True,
        "allowed_retry_reasons": [
            "transcript_still_incorrect",
            "candidate_spoke_incorrectly",
        ],
    }


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
