from __future__ import annotations

import math
from typing import Any

SCHEMA_VERSION = "rubric-context-v1"
LABELS = ("met", "partial", "missing", "contradicted", "uncertain")
LABEL2ID = {name: i for i, name in enumerate(LABELS)}
FACTORS = {"met": 1.0, "partial": 0.5, "missing": 0.0,
           "contradicted": 0.0, "uncertain": 0.0}


def make_pair(question: str, criterion: str, reference: str, answer: str) -> tuple[str, str]:
    # Teacher material and the untrusted student's answer occupy separate sequences.
    return (
        f"Question: {question}\nCriterion: {criterion}\nReference: {reference}",
        f"Student answer: {answer}",
    )


def decide(probabilities: dict[str, float], threshold: float, margin: float) -> dict[str, Any]:
    if set(probabilities) != set(LABELS):
        raise ValueError("Checkpoint must expose all five rubric labels")
    if any(not math.isfinite(v) or v < 0 or v > 1 for v in probabilities.values()):
        raise ValueError("Invalid model probabilities")
    if abs(sum(probabilities.values()) - 1) > 0.01:
        raise ValueError("Probabilities must sum to one")
    ranked = sorted(probabilities, key=probabilities.get, reverse=True)
    best, second = ranked[:2]
    confidence = probabilities[best]
    accepted = best != "uncertain" and confidence >= threshold and confidence - probabilities[second] >= margin
    return {
        "status": best if accepted else "uncertain",
        "predicted_label": best,
        "confidence": round(confidence, 6),
        "probabilities": probabilities,
        "abstained": not accepted,
    }
