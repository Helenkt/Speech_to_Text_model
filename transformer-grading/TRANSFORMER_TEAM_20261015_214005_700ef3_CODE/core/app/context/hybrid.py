from __future__ import annotations

import copy
from typing import Any

from app.context.contracts import FACTORS


def reconcile(base: dict[str, Any], predictions: list[dict[str, Any]], answer: str, mode: str) -> dict[str, Any]:
    """Independent checks; a disagreement is provisional, never silent final grading."""
    result = copy.deepcopy(base)
    rows = {row["point"]: row for row in predictions}
    issues = []
    is_llm = str(base.get("evaluator", "")).startswith("ollama:")
    for assessment in result.get("point_assessments", []):
        prediction = rows.get(assessment["point"])
        if prediction is None:
            issues.append("missing_transformer_criterion")
            assessment["context"] = {"status": "unavailable"}
            if mode == "hybrid":
                assessment["status"] = "uncertain"
            continue
        assessment["context"] = prediction
        quote = assessment.get("evidence_quote", "")
        needs_evidence = assessment["status"] in {"met", "partial", "contradicted"}
        valid_evidence = not needs_evidence or bool(quote and quote in answer)
        agreed = is_llm and prediction["status"] == assessment["status"] and valid_evidence
        if not agreed or prediction["abstained"]:
            issues.append("transformer_llm_disagreement_or_uncertain")
            if mode == "hybrid":
                assessment["status"] = "uncertain"
                assessment["reason"] += " | Chưa thống nhất giữa LLM và Transformer; giáo viên cần chấm lại."
        if prediction.get("demo_only", True):
            issues.append("demo_checkpoint")
    if not is_llm:
        issues.append("llm_unavailable_rule_fallback")
    if issues:
        result["review_required"] = True
        result["confidence"] = min(float(result.get("confidence", 0)), 0.5)
        result["feedback"] += " Điểm tạm: cần giáo viên đối chiếu ngữ cảnh (Transformer/LLM)."
    if mode == "hybrid":
        assessments = result.get("point_assessments", [])
        result["score"] = round(100 * sum(FACTORS.get(a["status"], 0) for a in assessments) / max(1, len(assessments)), 1)
        result["matched_points"] = [a["point"] for a in assessments if a["status"] == "met"]
        result["partial_points"] = [a["point"] for a in assessments if a["status"] == "partial"]
        result["contradicted_points"] = [a["point"] for a in assessments if a["status"] == "contradicted"]
        result["missing_points"] = [a["point"] for a in assessments if a["status"] != "met"]
        result["verdict"] = "Cần giáo viên xác minh" if issues else base["verdict"]
    result["evaluator"] = f"{base['evaluator']}+context-{mode}"
    result["rubric_version"] = "key-points-v3-context"
    return result
