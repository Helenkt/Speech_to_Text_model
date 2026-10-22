from __future__ import annotations

import json
import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.database import database
from app.services.exam_policy import admit_recording, submission_admission, exam_is_open
from app.services.transcription_vocabulary import transcription_vocabulary
from app.services.audio_lifecycle import audio_exists


class TranscriptionError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def transcript_sha256(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def transcription_context(
    database_path: Path, *, session_id: str, user_id: int,
    received_job_id: str | None = None, require_open: bool = True
) -> dict[str, Any]:
    with database(database_path) as connection:
        session = connection.execute(
            "SELECT * FROM interview_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if session and session["user_id"] == user_id and require_open:
            try:
                if received_job_id:
                    submission_admission(connection, session, received_job_id)
                else:
                    admit_recording(connection, session)
            except ValueError as exc:
                raise TranscriptionError(str(exc)) from exc
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
    return {
        "session_id": session_id,
        "question_uid": session["current_question_uid"],
        "answer_mode": session["answer_mode"],
        "grading_strategy": session["grading_strategy"],
        "language": session["language"],
        "question_text": str(question.get("question") or "").strip(),
        **transcription_vocabulary(question),
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
              AND NOT EXISTS (
                  SELECT 1 FROM speech_jobs j
                  WHERE j.session_id=interview_sessions.session_id AND j.question_uid=interview_sessions.current_question_uid
                    AND json_valid(j.context_json) AND json_extract(j.context_json,'$.admission.version')=1
                    AND datetime(json_extract(j.context_json,'$.admission.accepted_at')) BETWEEN
                        datetime(json_extract(j.context_json,'$.admission.starts_at')) AND datetime(json_extract(j.context_json,'$.admission.ends_at'))
                    AND (j.state IN ('queued','processing') OR (j.state='failed' AND j.retryable=1 AND j.attempts<3)
                         OR (j.state='completed' AND EXISTS (SELECT 1 FROM speech_transcriptions t WHERE t.transcription_id=j.job_id AND t.accepted=1 AND t.consumed=0)))
              )
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
    transcription_id: str | None = None,
    audio_source_path: Path | None = None,
) -> str:
    transcription_id = transcription_id or str(uuid.uuid4())
    relative_audio_path: str | None = None
    audio_sha256: str | None = None
    audio_size: int | None = None
    saved_audio_path: Path | None = None

    if audio_source_path is not None:
        storage_root = (audio_storage_dir or database_path.parent / "audio").resolve()
        source = audio_source_path.resolve()
        if not source.is_relative_to(storage_root) or not source.is_file():
            raise TranscriptionError("Bản ghi lưu trước không hợp lệ")
        relative_audio_path = source.relative_to(storage_root).as_posix()
        audio_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
        audio_size = source.stat().st_size
    elif audio_content:
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
            existing = connection.execute("SELECT session_id, user_id, question_uid FROM speech_transcriptions WHERE transcription_id=?",
                                          (transcription_id,)).fetchone()
            if existing:
                if (existing["session_id"], existing["user_id"], existing["question_uid"]) != (session_id, user_id, question_uid):
                    raise TranscriptionError("Mã bản ghi đã được dùng")
                return transcription_id
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
                "candidate_requested_retake",
            }
            requested_reason = (retry_reason or "").strip()
            reason = (
                requested_reason
                if previous_rows and requested_reason in allowed_reasons
                else "candidate_requested_retake" if previous_rows else None
            )
            metadata_payload = {
                **metadata,
                "requires_confirmation": True,
                "transcript_editable": False,
                "answer_stage": "draft",
                "preview_sha256": transcript_sha256(corrected_text),
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
            SELECT t.attempt_number, t.retry_reason, t.accepted, t.consumed, t.confirmed_at,
                   s.status, s.interview_mode, s.exam_round_id,
                   s.current_question_uid=t.question_uid AS current_question
            FROM speech_transcriptions t JOIN interview_sessions s ON s.session_id=t.session_id
            WHERE t.transcription_id = ?
            """,
            (transcription_id,),
        ).fetchone()
        recording_allowed = bool(row and exam_is_open(connection, row))
    if not row:
        raise TranscriptionError("Không tìm thấy lần ghi âm vừa lưu.")
    return {
        "attempt_number": int(row["attempt_number"] or 1),
        "retry_reason": row["retry_reason"],
        "stage": "confirmed" if row["consumed"] else "draft" if row["accepted"] else "superseded",
        "confirmed_at": row["confirmed_at"],
        "can_retry": bool(row["accepted"] and not row["consumed"] and row["status"] == "active" and row["current_question"] and recording_allowed),
        "allowed_retry_reasons": [
            "transcript_still_incorrect",
            "candidate_spoke_incorrectly",
            "candidate_requested_retake",
        ],
    }


def draft_transcription(database_path: Path, *, session_id: str, user_id: int,
                        audio_storage_dir: Path | None = None) -> dict[str, Any]:
    """Return only the current candidate preview, not private rubric/answer data."""
    with database(database_path) as connection:
        session = connection.execute("SELECT * FROM interview_sessions WHERE session_id=? AND user_id=?",
                                     (session_id, user_id)).fetchone()
        if not session:
            raise TranscriptionError("Không tìm thấy phiên phỏng vấn phù hợp")
        if session["status"] != "active" or not session["current_question_uid"]:
            return {"draft": None, "can_confirm": False, "can_record": False}
        row = connection.execute("""SELECT * FROM speech_transcriptions
            WHERE session_id=? AND user_id=? AND question_uid=? AND accepted=1 AND consumed=0
            ORDER BY attempt_number DESC,created_at DESC LIMIT 1""",
            (session_id, user_id, session["current_question_uid"])).fetchone()
        pending = connection.execute("""SELECT 1 FROM speech_jobs WHERE session_id=? AND question_uid=?
            AND state IN ('queued','processing') LIMIT 1""", (session_id, session["current_question_uid"])).fetchone()
        audio_saved = bool(row and audio_exists(audio_storage_dir or database_path.parent / "audio", row["audio_path"]))
        can_confirm = bool(row and not pending and audio_saved)
        error = None
        if row and not audio_saved:
            error = "Không tìm thấy voice tạm; hãy ghi âm lại trước khi xác nhận"
        if can_confirm:
            try:
                submission_admission(connection, session, row["transcription_id"])
            except ValueError as exc:
                can_confirm, error = False, str(exc)
        try:
            mic_ready = bool(json.loads(session["mic_check_result_json"] or "{}").get("ready"))
        except (TypeError, ValueError, AttributeError):
            mic_ready = False
        can_record = exam_is_open(connection, session) and mic_ready
    draft = None
    if row:
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
            if not isinstance(metadata, dict):
                metadata = {}
        except (TypeError, ValueError):
            metadata = {}
        draft = {"transcription_id": row["transcription_id"], "question_uid": row["question_uid"],
                 "text": row["corrected_text"].strip(), "raw_text": row["raw_text"],
                 "preview_sha256": transcript_sha256(row["corrected_text"]),
                 "attempt_number": row["attempt_number"], "stage": "draft",
                 "requires_confirmation": True, "transcript_editable": False,
                 "audio_sha256": row["audio_sha256"],
                 "audio_saved": audio_saved,
                 "transcript_status": metadata.get("transcript_status"),
                 "quality_warnings": metadata.get("quality_warnings", []),
                 "correction_applied": metadata.get("correction_applied", False),
                 "correction_rejected_reason": metadata.get("correction_rejected_reason")}
    return {"draft": draft, "can_confirm": can_confirm, "can_record": can_record,
            "recording_in_progress": bool(pending), "confirmation_error": error}


def require_no_pending_recording(connection, session):
    if connection.execute("""SELECT 1 FROM speech_jobs WHERE session_id=? AND question_uid=?
            AND state IN ('queued','processing') LIMIT 1""",
            (session["session_id"], session["current_question_uid"])).fetchone():
        raise TranscriptionError("Bản ghi mới đang xử lý; hãy chờ transcript trước khi xác nhận")


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
            SELECT corrected_text, confidence, metadata_json,audio_path,audio_sha256 FROM speech_transcriptions
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
        "audio_path": row["audio_path"],
        "audio_sha256": row["audio_sha256"],
    }
