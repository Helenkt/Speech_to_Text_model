from __future__ import annotations

import json
import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import Settings
from app.services.resource_policy import ollama_request_resources
from app.database import database
from app.services.question_generation_rubric import (
    build_generation_prompt,
    validate_generated_question,
)
from app.services.question_importer import normalize_question


class QuestionGenerationError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _source_question(row: Any) -> dict[str, Any]:
    return {
        "uid": row["uid"],
        "id": row["question_id"],
        "language": row["language"],
        "subject": row["subject"],
        "competency": row["competency"],
        "topic": row["topic"],
        "concept": row["concept"],
        "difficulty": row["difficulty"],
        "question": row["question"],
        "reference_answer": row["reference_answer"],
        "key_points": json.loads(row["key_points_json"]),
        "source_name": row["source_name"],
        "source_sha256": row["source_sha256"],
        "verification_status": row["verification_status"],
    }


def _load_sources(
    settings: Settings,
    *,
    language: str,
    subject: str,
    difficulty: str,
    topic: str | None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    clauses = ["active = 1", "bank_scope = 'learning'", "language = ?", "subject = ?"]
    parameters: list[Any] = [language, subject]
    if topic:
        clauses.append("topic = ?")
        parameters.append(topic)
    parameters.extend([difficulty, limit])
    with database(settings.database_path) as connection:
        rows = connection.execute(
            f"""
            SELECT q.*,
                   COALESCE((
                       SELECT qs.source_sha256
                       FROM question_sources AS qs
                       WHERE qs.source_name = q.source_name
                       ORDER BY qs.imported_at DESC LIMIT 1
                   ), '') AS source_sha256
            FROM questions AS q
            WHERE {' AND '.join(f'q.{clause}' for clause in clauses)}
            ORDER BY CASE WHEN difficulty = ? THEN 0 ELSE 1 END,
                     difficulty_rank, question_id
            LIMIT ?
            """,
            parameters,
        ).fetchall()
    return [_source_question(row) for row in rows]


def _parse_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise QuestionGenerationError("Model không trả về JSON hợp lệ") from exc
    if not isinstance(parsed, dict):
        raise QuestionGenerationError("Model phải trả về đúng một JSON object")
    return parsed


async def _generate_with_ollama(
    settings: Settings, prompt: str
) -> dict[str, Any]:
    resources = ollama_request_resources(settings)
    payload = {
        "model": settings.question_generation_model,
        "stream": False,
        "think": False,
        "format": "json",
        **resources,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Tuân thủ tuyệt đối dữ liệu nguồn và schema. "
                    "Không được sử dụng kiến thức ngoài SOURCE_QUESTIONS."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "options": {
            **resources["options"],
            "temperature": 0.2,
            "top_p": 0.85,
            "num_predict": 1_200,
        },
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.ollama_timeout_seconds)
        ) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/chat", json=payload
            )
            response.raise_for_status()
        content = response.json()["message"]["content"]
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise QuestionGenerationError(
            f"Không gọi được model sinh câu hỏi {settings.question_generation_model}"
        ) from exc
    return _parse_json_object(str(content))


def _store_candidate(
    settings: Settings,
    *,
    candidate: dict[str, Any],
    rubric_result: dict[str, Any],
    generated_by: int,
) -> dict[str, Any]:
    generated_id = str(uuid.uuid4())
    status = "draft" if rubric_result["status"] != "rejected" else "rejected"
    now = _now()
    with database(settings.database_path) as connection:
        connection.execute(
            """
            INSERT INTO generated_questions (
                generated_id, question_json, rubric_result_json, status,
                generated_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                generated_id,
                json.dumps(candidate, ensure_ascii=False),
                json.dumps(rubric_result, ensure_ascii=False),
                status,
                generated_by,
                now,
            ),
        )
    return {
        "generated_id": generated_id,
        "status": status,
        "question": candidate,
        "rubric": rubric_result,
        "created_at": now,
    }


async def generate_question_drafts(
    settings: Settings,
    *,
    generated_by: int,
    language: str,
    subject: str,
    counts: dict[str, int],
    topic: str | None = None,
) -> list[dict[str, Any]]:
    language = language.strip().lower()
    subject = subject.strip()
    topic = topic.strip() if topic else None
    if language not in {"vi", "en"}:
        raise QuestionGenerationError("Ngôn ngữ phải là vi hoặc en")
    if not subject:
        raise QuestionGenerationError("Thiếu môn học")
    total = sum(counts.values())
    if total < 1 or total > 20:
        raise QuestionGenerationError("Mỗi lần chỉ được sinh từ 1 đến 20 câu")

    with database(settings.database_path) as connection:
        existing_questions = [
            row["question"]
            for row in connection.execute(
                "SELECT question FROM questions WHERE active = 1 AND bank_scope = 'learning' AND language = ? AND subject = ?",
                (language, subject),
            ).fetchall()
        ]

    generated: list[dict[str, Any]] = []
    for difficulty in ("Easy", "Medium", "Hard"):
        for _ in range(int(counts.get(difficulty, 0))):
            sources = _load_sources(
                settings,
                language=language,
                subject=subject,
                difficulty=difficulty,
                topic=topic,
            )
            if not sources:
                raise QuestionGenerationError(
                    f"Không có dữ liệu nguồn phù hợp cho mức {difficulty}"
                )
            prompt = build_generation_prompt(
                source_questions=sources,
                target_difficulty=difficulty,
                language=language,
                subject=subject,
            )
            candidate = await _generate_with_ollama(settings, prompt)
            prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            candidate.update(
                {
                    "id": f"GEN_{uuid.uuid4().hex[:12].upper()}",
                    "language": language,
                    "subject": subject,
                    "difficulty": difficulty,
                    "source_provenance": [
                        {
                            "source_question_uid": source["uid"],
                            "source_question_id": source["id"],
                            "source_name": source["source_name"],
                            "source_sha256": source["source_sha256"],
                            "verification_status": source["verification_status"],
                            "topic": source["topic"],
                            "concept": source["concept"],
                            "reference_excerpt": source["reference_answer"],
                        }
                        for source in sources
                    ],
                    "generation_provenance": {
                        "model": settings.question_generation_model,
                        "prompt_sha256": prompt_sha256,
                        "generated_at": _now(),
                        "source_policy": "approved-internal-only",
                    },
                }
            )
            source_ids = {item["id"] for item in sources}
            result = validate_generated_question(
                candidate,
                existing_questions=existing_questions,
                approved_source_ids=source_ids,
                approved_sources={item["id"]: item for item in sources},
            )
            stored = _store_candidate(
                settings,
                candidate=candidate,
                rubric_result=result,
                generated_by=generated_by,
            )
            generated.append(stored)
            if stored["status"] == "draft":
                existing_questions.append(str(candidate.get("question") or ""))
    return generated


def list_generated_questions(
    settings: Settings, *, status: str | None = None
) -> list[dict[str, Any]]:
    parameters: list[Any] = []
    where = ""
    if status:
        if status not in {"draft", "approved", "rejected"}:
            raise QuestionGenerationError("Trạng thái câu hỏi không hợp lệ")
        where = "WHERE g.status = ?"
        parameters.append(status)
    with database(settings.database_path) as connection:
        rows = connection.execute(
            f"""
            SELECT g.*, creator.full_name AS generated_by_name,
                   approver.full_name AS approved_by_name
            FROM generated_questions AS g
            JOIN users AS creator ON creator.user_id = g.generated_by
            LEFT JOIN users AS approver ON approver.user_id = g.approved_by
            {where}
            ORDER BY g.created_at DESC
            """,
            parameters,
        ).fetchall()
    return [
        {
            "generated_id": row["generated_id"],
            "status": row["status"],
            "question": json.loads(row["question_json"]),
            "rubric": json.loads(row["rubric_result_json"]),
            "generated_by": row["generated_by_name"],
            "approved_by": row["approved_by_name"],
            "created_at": row["created_at"],
            "reviewed_at": row["reviewed_at"],
        }
        for row in rows
    ]


def review_generated_question(
    settings: Settings,
    *,
    generated_id: str,
    action: str,
    teacher_id: int,
) -> dict[str, Any]:
    if action not in {"approve", "reject"}:
        raise QuestionGenerationError("Hành động phải là approve hoặc reject")
    with database(settings.database_path) as connection:
        row = connection.execute(
            "SELECT * FROM generated_questions WHERE generated_id = ?",
            (generated_id,),
        ).fetchone()
        if not row:
            raise QuestionGenerationError("Không tìm thấy câu hỏi đã sinh")
        if row["status"] != "draft":
            raise QuestionGenerationError("Câu hỏi này không còn ở trạng thái chờ duyệt")

        now = _now()
        if action == "reject":
            connection.execute(
                """
                UPDATE generated_questions
                SET status = 'rejected', approved_by = ?, reviewed_at = ?
                WHERE generated_id = ?
                """,
                (teacher_id, now, generated_id),
            )
            return {"generated_id": generated_id, "status": "rejected"}

        candidate = json.loads(row["question_json"])
        normalized = normalize_question(candidate, index=1)
        connection.execute(
            """
            INSERT INTO questions (
                uid, question_id, language, subject, competency, topic, concept,
                difficulty, difficulty_rank, question, reference_answer,
                key_points_json, source_name, verification_status, active,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'verified', 1, ?, ?)
            """,
            (
                normalized["uid"],
                normalized["id"],
                normalized["language"],
                normalized["subject"],
                normalized["competency"],
                normalized["topic"],
                normalized["concept"],
                normalized["difficulty"],
                normalized["difficulty_rank"],
                normalized["question"],
                normalized["reference_answer"],
                json.dumps(normalized["key_points"], ensure_ascii=False),
                f"ai-generated:{generated_id}",
                now,
                now,
            ),
        )
        connection.execute(
            """
            UPDATE generated_questions
            SET status = 'approved', approved_by = ?, reviewed_at = ?
            WHERE generated_id = ?
            """,
            (teacher_id, now, generated_id),
        )
    return {
        "generated_id": generated_id,
        "status": "approved",
        "question_uid": normalized["uid"],
    }
