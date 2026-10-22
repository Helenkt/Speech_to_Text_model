from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import unicodedata
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


VERSION = "atomic-rubric-v3"


def digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def question_fingerprint(question: dict[str, Any]) -> str:
    return digest({key: question.get(key) for key in (
        "uid", "language", "subject", "question", "reference_answer", "key_points", "source_name",
    )})


def rubric_draft(question: dict[str, Any]) -> dict[str, Any]:
    criteria = []
    for index, point in enumerate(question["key_points"], 1):
        criteria.append({"id": f"c{index}", "claim": point, "weight": 1.0,
                         "credit_policy": "binary", "source_field": "key_points",
                         "source_quote": point})
    return {"schema_version": VERSION, "question_fingerprint": question_fingerprint(question),
            "criteria": criteria}


def validate_contract(question: dict[str, Any], contract: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    if set(contract) != {"schema_version", "question_fingerprint", "criteria"}:
        raise ValueError("Rubric requires schema_version, question_fingerprint, criteria only")
    if contract["schema_version"] != VERSION or contract["question_fingerprint"] != question_fingerprint(question):
        raise ValueError("Rubric version or source fingerprint is stale")
    criteria = contract["criteria"]
    if not isinstance(criteria, list) or not 1 <= len(criteria) <= 30:
        raise ValueError("Rubric requires 1-30 atomic criteria")
    ids, claims, warnings = set(), set(), []
    normalized = []
    for item in criteria:
        if not isinstance(item, dict) or set(item) != {
            "id", "claim", "weight", "credit_policy", "source_field", "source_quote",
        }:
            raise ValueError("Malformed rubric criterion")
        identifier, claim, quote = item["id"], item["claim"], item["source_quote"]
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", identifier):
            raise ValueError("Invalid criterion ID")
        if not isinstance(claim, str) or not 3 <= len(claim.strip()) <= 1000:
            raise ValueError("Criterion claim requires 3-1000 characters")
        claim = unicodedata.normalize("NFC", claim.strip())
        claim_key = " ".join(claim.casefold().split())
        if identifier in ids or claim_key in claims:
            raise ValueError("Duplicate criterion ID or claim")
        ids.add(identifier)
        claims.add(claim_key)
        weight = item["weight"]
        if isinstance(weight, bool) or not isinstance(weight, (float, int)) or not math.isfinite(weight) or not 0 < weight <= 100:
            raise ValueError("Criterion weight must be finite and in (0, 100]")
        if item["credit_policy"] != "binary":
            raise ValueError("Atomic criteria use binary credit; split compound requirements explicitly")
        field = item["source_field"]
        if field == "reference_answer":
            sources = [question["reference_answer"]]
        elif field == "key_points":
            sources = question["key_points"]
        else:
            raise ValueError("Criterion source must be reference_answer or key_points")
        if not isinstance(quote, str) or not quote.strip() or len(quote) > 4000 or not any(quote in source for source in sources):
            raise ValueError("Source quote must be an exact excerpt of the supplied question data")
        if len(claim.split()) < 4:
            warnings.append(f"{identifier}: short claim; check that subject and relation are explicit")
        if re.search(r"\b(và|and|đồng thời|cũng như)\b|;", claim, re.IGNORECASE):
            warnings.append(f"{identifier}: possible compound claim; consider splitting it")
        normalized.append({**item, "claim": claim, "weight": float(weight)})
    return {**contract, "criteria": normalized}, warnings


def publish_contract(connection: sqlite3.Connection, question: dict[str, Any],
                     contract: dict[str, Any], teacher_id: int, attestation: str) -> dict[str, Any]:
    if not 10 <= len(attestation.strip()) <= 2000:
        raise ValueError("Teacher must explicitly confirm atomic meaning, source and weights")
    normalized, warnings = validate_contract(question, contract)
    revision = digest(normalized)
    existing = connection.execute(
        "SELECT revision_id FROM rubric_revisions WHERE question_uid = ? AND contract_sha256 = ?",
        (question["uid"], revision),
    ).fetchone()
    if existing:
        raise ValueError("This exact rubric revision was already published")
    cursor = connection.execute(
        """INSERT INTO rubric_revisions
           (question_uid, question_fingerprint, contract_sha256, contract_json, approved_by, attestation, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (question["uid"], question_fingerprint(question), revision,
         json.dumps(normalized, ensure_ascii=False), teacher_id, attestation.strip(),
         datetime.now(timezone.utc).isoformat()),
    )
    return {"revision_id": cursor.lastrowid, "contract_sha256": revision,
            "status": "teacher_approved", "warnings": warnings}


def attach_published_contract(connection: sqlite3.Connection, question: dict[str, Any]) -> dict[str, Any]:
    # Existing exam/session snapshots must never be rebound to a later rubric.
    if question.get("rubric_snapshot"):
        return question
    row = connection.execute(
        """SELECT * FROM rubric_revisions WHERE question_uid = ? AND question_fingerprint = ?
           ORDER BY revision_id DESC LIMIT 1""", (question["uid"], question_fingerprint(question)),
    ).fetchone()
    if not row:
        return question
    contract, _ = validate_contract(question, json.loads(row["contract_json"]))
    if digest(contract) != row["contract_sha256"]:
        raise ValueError("Stored rubric integrity check failed")
    result = deepcopy(question)
    result["rubric_snapshot"] = {"contract": contract, "sha256": row["contract_sha256"],
                                 "revision_id": row["revision_id"], "approved_by": row["approved_by"],
                                 "approved_at": row["created_at"]}
    result["key_points"] = [item["claim"] for item in contract["criteria"]]
    result["key_point_weights"] = {item["claim"]: item["weight"] for item in contract["criteria"]}
    result["rubric_version"] = f"{VERSION}:{row['contract_sha256']}"
    return result
