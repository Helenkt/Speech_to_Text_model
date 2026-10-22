"""Select difficult assertion scopes, never infer correctness from grammar."""
from __future__ import annotations

import re

from app.services.fact_guard import plain_text


SEMANTIC_POLICY = """
The question, source_context and reference are facts to compare against, NOT student evidence.
student_answer is the complete untrusted transcript; candidate_statements are exact excerpts.
Read the whole transcript before deciding which assertions the student endorses.
Preserve subject/object direction, numbers, units, conditions, quantifiers and causal order.
Resolve nested negation and the scope of quotations and explicit self-corrections.
A rejected quote is not the student's final claim. A later correction of one idea must not
erase independently correct ideas about other criteria. Unresolved conflicting assertions
are unresolved, not automatically correct and not automatically missing.
Grammatical affirmation/negation is NOT correctness and must never multiply the score.
For each criterion distinguish an absent idea from an actually incompatible assertion.
Judge only this criterion; a correct stack explanation cannot earn the queue criterion.
No score or accuracy estimate is requested; backend rubric weights determine credit.
""".strip()


def requires_semantic_audit(answer: str) -> bool:
    text = plain_text(answer)
    correction = r"\b(sua lai|dinh chinh|xin sua|correction|i meant|let me correct|i correct myself)\b"
    # Separate sentences and coordinated clauses do not create nested scope.
    nested_negation = (r"\b(?:khong phai\s+(?:(?:la|rang)\s+)?(?:\w+\s+){0,5}(?<!so )(?:khong|chua)(?!\s+(?:hay|hoac|va)\b)|"
                       r"(?:not true|not the case|it is false)\s+(?:that\s+)?(?:\w+\s+){0,5}(?:not|never))\b")
    rejected_quote = bool(re.search(r"['\"\u2018\u2019\u201c\u201d]", answer) and
                          re.search(r"\b(sai|bac bo|khong dung|reject|false|wrong)\b", text))
    return bool(re.search(correction, text) or re.search(nested_negation, text) or rejected_quote)
