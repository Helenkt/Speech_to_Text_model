"""Frozen, LLM-free grading candidate. Shadow results never change real grades."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Any

from app.services.fact_guard import check_rubric_point
from app.services.grading_semantics import requires_semantic_audit
from app.services.rubric_contract import criterion_key, digest
from app.services.rubric_transformer import predict_nli_pairs


SCHEMA = "specialist-grader-shadow-v1"
INPUT_FORMAT = "student_answer__rubric_claim_v1"
REQUIRED_FILES = {"model.int8.onnx", "tokenizer.json", "config.json"}
NLI_LABELS = {"entailment", "neutral", "contradiction"}


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def freeze_candidate(model_dir: Path) -> dict[str, Any]:
    """Record existing INT8 weights; no download, training, or model-folder writes."""
    files = {}
    for name in sorted(REQUIRED_FILES):
        path = model_dir / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing regular model file: {name}")
    config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Model config must be an object")
    input_format = config.get("rubric_input_format")
    if input_format is not None and not isinstance(input_format, str):
        raise ValueError("rubric_input_format must be a string")
    if input_format not in {None, "answer_claim_pair_v0", INPUT_FORMAT}:
        raise ValueError("Checkpoint uses a different input contract; do not silently change its inputs")
    labels = config.get("id2label", {})
    if (not isinstance(labels, dict) or set(labels) != {"0", "1", "2"}
            or any(not isinstance(label, str) for label in labels.values())
            or {label.lower() for label in labels.values()} != NLI_LABELS):
        raise ValueError("Expected a three-class NLI checkpoint")
    max_length = config.get("rubric_max_length", 256)
    if isinstance(max_length, bool) or not isinstance(max_length, int) or not 16 <= max_length <= 512:
        raise ValueError("Unsupported rubric_max_length")
    for name in sorted(REQUIRED_FILES):
        path = model_dir / name
        files[name] = {"sha256": file_hash(path), "bytes": path.stat().st_size}
    body = {"schema_version": SCHEMA, "input_format": INPUT_FORMAT,
            "execution": "shadow_only", "production_ready": False,
            "neutral_policy": "unresolved_not_missing", "max_tokens": max_length,
            "files": files}
    return {**body, "artifact_sha256": digest(body)}


def validate_grading_input(question: dict[str, Any], answer: str) -> tuple[list[str], dict[str, float]]:
    """Validate before loading a model; keep transcript, claim text and weights unchanged."""
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 32000:
        raise ValueError("Answer requires 1-32000 characters")
    if not isinstance(question, dict) or not isinstance(question.get("question"), str) or not question["question"].strip():
        raise ValueError("Question text is required")
    points = question.get("key_points")
    if (not isinstance(points, list) or not 1 <= len(points) <= 30
            or any(not isinstance(p, str) or not 3 <= len(p.strip()) <= 1000 for p in points)
            or len({criterion_key(p) for p in points}) != len(points)):
        raise ValueError("Expected 1-30 unique rubric claims")
    weights = question.get("key_point_weights")
    if weights is None or weights == {}:
        weights = {p: 1.0 for p in points}
    if not isinstance(weights, dict) or set(weights) != set(points) or any(
        isinstance(w, bool) or not isinstance(w, (float, int)) or not math.isfinite(w) or not 0 < w <= 100
        for w in weights.values()
    ):
        raise ValueError("Weights must match every claim and be finite values in (0, 100]")
    from app.services.grading_quality import rubric_hash
    rubric_hash(question)
    return points, weights


class SpecialistGrader:
    def __init__(self, model_dir: Path, manifest: dict[str, Any]):
        self.model_dir = model_dir.resolve()
        self.manifest = json.loads(json.dumps(manifest))
        expected = freeze_candidate(self.model_dir)
        if self.manifest != expected:
            raise ValueError("Candidate manifest or runtime files changed; freeze a new candidate")
        self._stamp = self._runtime_stamp()

    def _runtime_stamp(self) -> tuple:
        return tuple((name, (self.model_dir / name).stat().st_size,
                      (self.model_dir / name).stat().st_mtime_ns) for name in sorted(REQUIRED_FILES))

    def grade(self, question: dict[str, Any], answer: str) -> dict[str, Any]:
        started = perf_counter()
        if self._runtime_stamp() != self._stamp:
            raise ValueError("Runtime changed after verification; reload a newly frozen candidate")
        points, weights = validate_grading_input(question, answer)
        from app.services.grading_quality import rubric_hash
        rubric_sha = rubric_hash(question)
        complex_scope = requires_semantic_audit(answer)
        assessments, pending = [], []
        for point in points:
            fact = None if complex_scope else check_rubric_point(question, answer, point)
            status = {"supported": "met", "contradicted": "contradicted", "missing": "missing"}.get(
                fact.status if fact else "unknown", "unresolved")
            item = {"point": point, "weight": float(weights[point]), "status": status,
                    "suggested_status": status, "needs_review": status == "unresolved",
                    "source": "closed_rule" if status != "unresolved" else "nli_candidate",
                    "evidence_quote": "", "reason": fact.reason if fact else "Complex assertion scope",
                    "probabilities": None, "confidence_is_accuracy": False}
            if status != "unresolved" and status != "missing":
                quote = fact.evidence if fact.evidence and fact.evidence in answer else answer
                item.update(evidence_quote=quote, evidence_start=answer.index(quote),
                            evidence_end=answer.index(quote) + len(quote),
                            evidence_kind="rule_excerpt" if quote != answer else "full_transcript")
            if status == "unresolved":
                # Conflicts established by a closed rule must not be overridden by NLI.
                if fact and fact.status == "conflicted":
                    item["source"] = "rule_conflict"
                else:
                    pending.append(len(assessments))
            assessments.append(item)
        if pending:
            predictions = predict_nli_pairs(self.model_dir, [(answer, points[i]) for i in pending])
            if len(predictions) != len(pending):
                raise ValueError("Missing NLI predictions")
            for index, prediction in zip(pending, predictions, strict=True):
                probabilities = prediction["probabilities"]
                if (set(probabilities) != NLI_LABELS or any(
                    isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or not 0 <= v <= 1
                    for v in probabilities.values()) or abs(sum(probabilities.values()) - 1) > 1e-4):
                    raise ValueError("Invalid NLI probabilities")
                label = max(probabilities, key=probabilities.get)
                suggested = {"entailment": "met", "contradiction": "contradicted", "neutral": "unresolved"}[label]
                blocked = prediction["truncated"] or complex_scope
                assessments[index].update(
                    suggested_status="unresolved" if blocked else suggested,
                    raw_label=label, probabilities=probabilities, truncated=prediction["truncated"],
                    reason="input_truncated" if prediction["truncated"] else
                           "complex_assertion_scope" if complex_scope else
                           "neutral_is_not_proof_of_missing" if label == "neutral" else "candidate_not_validated",
                    evidence_quote=answer, evidence_start=0, evidence_end=len(answer),
                    evidence_kind="full_transcript_model_input_not_verified_support",
                )
        total = sum(weights.values())
        lower = 100 * sum(i["weight"] for i in assessments if i["status"] == "met") / total
        upper = lower + 100 * sum(i["weight"] for i in assessments if i["status"] == "unresolved") / total
        suggestion_complete = all(i["suggested_status"] != "unresolved" for i in assessments)
        proposed = (round(100 * sum(i["weight"] for i in assessments if i["suggested_status"] == "met") / total, 2)
                    if suggestion_complete else None)
        return {"schema_version": SCHEMA, "evaluator": "specialist:nli-int8-shadow-v1",
                "execution": "shadow_only", "production_ready": False, "final_score": None,
                "changes_final_grade": False, "used_llm": False, "trained_during_grading": False,
                "artifact_sha256": self.manifest["artifact_sha256"], "answer_sha256": digest(answer),
                "rubric_sha256": rubric_sha, "point_assessments": assessments,
                "nli_pair_count": len(pending),
                "proposed_score": proposed, "rule_resolved_score_interval": [round(lower, 2), round(upper, 2)],
                "review_required": any(i["needs_review"] for i in assessments),
                "latency_ms": round((perf_counter() - started) * 1000, 2),
                "feedback": "Shadow candidate only; no real grade is replaced. Neutral evidence is unresolved, not wrong.",
                "confidence_is_accuracy": False}
