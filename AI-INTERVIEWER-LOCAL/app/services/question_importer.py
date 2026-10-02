from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.database import active_question_count, database


DIFFICULTY_ALIASES = {
    "easy": ("Easy", 1),
    "e": ("Easy", 1),
    "1": ("Easy", 1),
    "dễ": ("Easy", 1),
    "de": ("Easy", 1),
    "medium": ("Medium", 2),
    "m": ("Medium", 2),
    "2": ("Medium", 2),
    "trung bình": ("Medium", 2),
    "trung binh": ("Medium", 2),
    "hard": ("Hard", 3),
    "h": ("Hard", 3),
    "3": ("Hard", 3),
    "khó": ("Hard", 3),
    "kho": ("Hard", 3),
}


class QuestionBankError(ValueError):
    pass


def _text(value: Any, field: str, required: bool = True) -> str:
    if value is None:
        value = ""
    result = str(value).strip()
    if required and not result:
        raise QuestionBankError(f"Thiếu trường '{field}'")
    return result


def _first(raw: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in raw and raw[key] is not None:
            return raw[key]
    return None


def _key_points(raw: dict[str, Any]) -> list[str]:
    value = _first(raw, "key_points", "rubric", "expected_points", "criteria")
    if isinstance(value, str):
        value = [line.strip(" -•\t") for line in value.splitlines() if line.strip()]
    if not isinstance(value, list):
        raise QuestionBankError("'key_points' phải là một danh sách không rỗng")

    points: list[str] = []
    for item in value:
        if isinstance(item, dict):
            item = _first(item, "text", "point", "description", "criterion")
        point = str(item or "").strip()
        if point and point not in points:
            points.append(point)
    if not points:
        raise QuestionBankError("'key_points' phải có ít nhất một ý")
    return points


def normalize_question(
    raw: Any, *, index: int, default_language: str | None = None
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise QuestionBankError("Mỗi câu hỏi phải là một JSON object")

    language = _text(
        _first(raw, "language", "lang") or default_language,
        "language",
    ).lower()
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,11}", language):
        raise QuestionBankError("'language' phải có dạng vi, en, vi-VN...")

    question_text = _text(_first(raw, "question", "question_text", "prompt"), "question")
    reference_answer = _text(
        _first(raw, "reference_answer", "answer", "ideal_answer", "sample_answer"),
        "reference_answer",
    )
    difficulty_key = _text(
        _first(raw, "difficulty", "level") or "Medium", "difficulty"
    ).lower()
    if difficulty_key not in DIFFICULTY_ALIASES:
        raise QuestionBankError("'difficulty' chỉ nhận Easy, Medium hoặc Hard")
    difficulty, difficulty_rank = DIFFICULTY_ALIASES[difficulty_key]

    subject = _text(_first(raw, "subject", "category", "domain"), "subject")
    topic = _text(_first(raw, "topic") or subject, "topic")
    concept = _text(_first(raw, "concept") or topic, "concept")
    competency = _text(_first(raw, "competency", "skill") or subject, "competency")
    question_id = _text(_first(raw, "id", "question_id"), "id", required=False)
    if not question_id:
        digest = hashlib.sha256(
            f"{language}|{subject}|{question_text}".encode("utf-8")
        ).hexdigest()[:12].upper()
        question_id = f"Q_{digest}"

    return {
        "uid": f"{language}:{question_id}",
        "id": question_id,
        "language": language,
        "subject": subject,
        "competency": competency,
        "topic": topic,
        "concept": concept,
        "difficulty": difficulty,
        "difficulty_rank": difficulty_rank,
        "question": question_text,
        "reference_answer": reference_answer,
        "key_points": _key_points(raw),
        "_row": index,
    }


def parse_question_bank(
    content: bytes, *, filename: str, default_language: str | None = None
) -> tuple[list[dict[str, Any]], str]:
    try:
        document = json.loads(content.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise QuestionBankError("Tệp phải dùng mã hóa UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise QuestionBankError(
            f"JSON không hợp lệ tại dòng {exc.lineno}, cột {exc.colno}: {exc.msg}"
        ) from exc

    inherited_language = default_language
    if isinstance(document, dict):
        inherited_language = _first(document, "language", "lang") or inherited_language
        items = _first(document, "questions", "data", "items")
    else:
        items = document

    if not isinstance(items, list) or not items:
        raise QuestionBankError(
            "Tệp phải là một mảng câu hỏi hoặc object có trường 'questions'"
        )

    normalized: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        try:
            question = normalize_question(
                item, index=index, default_language=inherited_language
            )
            if question["uid"] in seen:
                raise QuestionBankError(f"ID bị trùng: {question['id']}")
            seen.add(question["uid"])
            normalized.append(question)
        except QuestionBankError as exc:
            if len(errors) < 20:
                errors.append(f"Câu #{index}: {exc}")

    if errors:
        suffix = "" if len(errors) < 20 else " (chỉ hiển thị 20 lỗi đầu)"
        raise QuestionBankError("; ".join(errors) + suffix)

    return normalized, hashlib.sha256(content).hexdigest()


def import_question_bank(
    database_path: Path,
    content: bytes,
    *,
    filename: str,
    mode: str = "upsert",
    default_language: str | None = None,
) -> dict[str, Any]:
    mode = mode.strip().lower()
    if mode not in {"upsert", "replace"}:
        raise QuestionBankError("Chế độ import phải là 'upsert' hoặc 'replace'")

    questions, source_sha256 = parse_question_bank(
        content, filename=filename, default_language=default_language
    )
    languages = sorted({item["language"] for item in questions})
    now = datetime.now(timezone.utc).isoformat()

    with database(database_path) as connection:
        existing = {
            row["uid"]
            for row in connection.execute(
                f"SELECT uid FROM questions WHERE language IN ({','.join('?' for _ in languages)})",
                languages,
            ).fetchall()
        }

        if mode == "replace":
            connection.execute(
                f"DELETE FROM questions WHERE language IN ({','.join('?' for _ in languages)})",
                languages,
            )
            existing = set()

        for item in questions:
            connection.execute(
                """
                INSERT INTO questions (
                    uid, question_id, language, subject, competency, topic, concept,
                    difficulty, difficulty_rank, question, reference_answer,
                    key_points_json, source_name, verification_status, active,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unverified', 1, ?, ?)
                ON CONFLICT(uid) DO UPDATE SET
                    question_id = excluded.question_id,
                    language = excluded.language,
                    subject = excluded.subject,
                    competency = excluded.competency,
                    topic = excluded.topic,
                    concept = excluded.concept,
                    difficulty = excluded.difficulty,
                    difficulty_rank = excluded.difficulty_rank,
                    question = excluded.question,
                    reference_answer = excluded.reference_answer,
                    key_points_json = excluded.key_points_json,
                    source_name = excluded.source_name,
                    verification_status = 'unverified',
                    active = 1,
                    updated_at = excluded.updated_at
                """,
                (
                    item["uid"],
                    item["id"],
                    item["language"],
                    item["subject"],
                    item["competency"],
                    item["topic"],
                    item["concept"],
                    item["difficulty"],
                    item["difficulty_rank"],
                    item["question"],
                    item["reference_answer"],
                    json.dumps(item["key_points"], ensure_ascii=False),
                    Path(filename).name,
                    now,
                    now,
                ),
            )

        connection.execute(
            """
            INSERT INTO question_sources (
                source_name, source_sha256, languages, question_count,
                import_mode, verification_status, imported_at
            ) VALUES (?, ?, ?, ?, ?, 'unverified', ?)
            """,
            (
                Path(filename).name,
                source_sha256,
                ",".join(languages),
                len(questions),
                mode,
                now,
            ),
        )

    created = sum(1 for item in questions if item["uid"] not in existing)
    return {
        "filename": Path(filename).name,
        "mode": mode,
        "imported": len(questions),
        "created": created,
        "updated": len(questions) - created,
        "languages": languages,
        "verification_status": "unverified",
        "total_active": active_question_count(database_path),
    }


def load_demo_banks(database_path: Path, demo_data_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for filename in ("question_bank_vi.json", "question_bank_en.json"):
        path = demo_data_dir / filename
        if path.exists():
            results.append(
                import_question_bank(
                    database_path,
                    path.read_bytes(),
                    filename=filename,
                    mode="replace",
                )
            )
    return results

