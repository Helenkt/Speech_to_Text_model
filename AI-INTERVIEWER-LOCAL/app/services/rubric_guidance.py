"""Source-bound preparation hints; never publish or change rubric weights."""
from __future__ import annotations

import re

from app.services.course_verifier import fact_examples, parse_course_fact
from app.services.rubric_contract import question_fingerprint


def grading_guidance(question: dict) -> dict:
    criteria = []
    for index, point in enumerate(question["key_points"], 1):
        fact = parse_course_fact(point)
        compound = bool(re.search(r"\b(và|and|đồng thời|cũng như)\b|;", point, re.IGNORECASE))
        criteria.append({"id": f"k{index}", "point": point, "source_field": "key_points",
            "source_quote": point, "possible_compound": compound,
            "accepted_expression_examples": fact_examples(fact, question.get("language", "vi")) if fact else [],
            "verification": {"kind": fact.kind, "subject": fact.subject, "expected": fact.value} if fact else None,
            "critical_literals": re.findall(r"\b\d+(?:[.,]\d+)?\s*(?:TB|GB|MB|KB|%|ms)?\b|\b(?:NULL|LIFO|FIFO)\b", point),
            "credit_policy": "require_complete_meaning_not_keyword_overlap"})
    return {"version": "source-guidance-v1", "question_fingerprint": question_fingerprint(question),
            "approval_status": "derived_hints_not_teacher_approval", "changes_weights": False,
            "criteria": criteria}


def compact_guidance(question: dict) -> list[dict]:
    return [{"point": c["point"], "possible_compound": c["possible_compound"],
             **({"equivalent_examples": c["accepted_expression_examples"]} if c["accepted_expression_examples"] else {}),
             **({"expected_relation": c["verification"]} if c["verification"] else {})}
            for c in grading_guidance(question)["criteria"]]
