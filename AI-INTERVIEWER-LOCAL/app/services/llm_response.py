"""Decode complete model responses without inventing decisions or evidence."""
from __future__ import annotations

import json
import math
import re
from typing import Any


class ModelResponseError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ModelResponseError("duplicate_json_key", "Repeated JSON field: " + key)
        result[key] = value
    return result


def _reject_constant(value):
    raise ModelResponseError("nonfinite_number", "Non-finite JSON number: " + value)


def decode_model_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip().lstrip("\ufeff").strip()
    fenced = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        raise ModelResponseError("invalid_json", "Model output is not a complete JSON document") from exc


def validate_point_decisions(value: Any, points: list[str], statements: dict[str, str], *,
                             isolate_local_errors: bool = False) -> dict:
    data = decode_model_json(value)
    if not isinstance(data, dict) or not isinstance(data.get("point_assessments"), list):
        raise ModelResponseError("missing_assessments", "Missing per-point assessments")
    items, seen = [], set()
    for item in data["point_assessments"]:
        if not isinstance(item, dict):
            raise ModelResponseError("invalid_assessment", "Malformed point assessment")
        point, status, ids = item.get("point"), item.get("status"), item.get("evidence_ids")
        if not isinstance(point, str) or point not in points or point in seen:
            raise ModelResponseError("invalid_point", "Unknown or duplicate rubric point")
        if not isinstance(status, str) or status not in {"met", "partial", "missing", "contradicted", "unresolved"}:
            raise ModelResponseError("invalid_status", "Invalid rubric status")
        if (not isinstance(ids, list) or len(ids) > 4
                or any(not isinstance(key, str) or key not in statements for key in ids)
                or len(set(ids)) != len(ids)):
            raise ModelResponseError("invalid_evidence", "Invalid evidence IDs")
        reason = item.get("reason", "")
        if not reason and isinstance(item.get("required_meaning"), str) and isinstance(item.get("student_meaning"), str):
            reason = "Expected: " + item["required_meaning"][:240] + " Student: " + item["student_meaning"][:240]
        if not isinstance(reason, str):
            raise ModelResponseError("invalid_reason", "Reason must be text")
        local_error = status == "missing" and bool(ids)
        if local_error and not isolate_local_errors:
            raise ModelResponseError("unexpected_evidence", "Missing criteria cannot cite supporting evidence")
        quotes = [statements[key] for key in ids]
        # Ignore model-supplied quotes and scores; evidence comes only from source IDs.
        items.append({"point": point, "status": status, "reason": reason,
                      "evidence_quote": quotes[0] if quotes else "", "evidence_quotes": quotes})
        if local_error:
            items[-1].update(status="unresolved", review_reason="invalid_missing_evidence",
                             reason="Nhãn vắng ý nhưng lại dẫn chứng nội dung; cần đối chiếu lại ý này.")
        seen.add(point)
    if seen != set(points):
        raise ModelResponseError("incomplete_rubric", "Incomplete rubric coverage")
    confidence = data.get("confidence", 0.7)
    if (isinstance(confidence, bool) or not isinstance(confidence, (int, float))
            or not math.isfinite(confidence) or not 0 <= confidence <= 100):
        raise ModelResponseError("invalid_confidence", "Invalid model confidence")
    return {"point_assessments": items, "confidence": confidence}
