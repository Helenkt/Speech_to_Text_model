from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


_NUMBER = r"-?\d+(?:[.,]\d+)?"
_UNIT = r"(?:diem|%|phan tram|kb|mb|gb|tb|byte|bytes|ms|s|giay|phut|gio)?"
_ENTITY_VALUE = re.compile(
    rf"\b(?P<entity>[a-z][a-z0-9_+-]{{0,30}})\s+"
    rf"(?:(?:duoc|dat|co|la)\s+)?(?P<value>{_NUMBER})\s*(?P<unit>{_UNIT})\b"
)
_GREATER = r"cao hon|lon hon|nhieu hon|greater than|higher than|more than|>"
_LESS = r"thap hon|nho hon|it hon|less than|lower than|fewer than|<"
_EQUAL = r"bang nhau|bang voi|bang|equal to|same as|="
_IGNORED_ENTITIES = {
    "cau",
    "co",
    "duoc",
    "hon",
    "la",
    "mot",
    "nam",
    "so",
    "thang",
    "trong",
    "vi",
    "voi",
}


@dataclass(frozen=True, slots=True)
class FactCheck:
    status: str
    confidence: float
    reason: str = ""
    evidence: str = ""
    entities: tuple[str, ...] = ()
    verification_rule: str = ""


def split_clauses(value: str) -> list[str]:
    """Keep decimals and closed quotations together; return exact input substrings."""
    protected: list[tuple[int, int]] = []
    quoted = re.compile(r'"[^"\n]*"|(?<!\w)\x27[^\x27\n]*\x27(?!\w)|\u201c[^\u201d]*\u201d|\u2018[^\u2019]*\u2019')
    protected.extend((match.start(), match.end()) for match in quoted.finditer(value))
    start, clauses = 0, []
    for match in re.finditer(r"[!?;\n]+|(?<!\d)\.|\.(?!\d)", value):
        if any(left <= match.start() < right for left, right in protected):
            continue
        clause = value[start:match.start()].strip()
        if clause:
            clauses.append(clause)
        start = match.end()
    if value[start:].strip():
        clauses.append(value[start:].strip())
    return clauses


def asserted_text(value: str) -> str:
    # Rules must not treat quoted, hypothetical or explicitly rejected claims as facts.
    clauses = split_clauses(value)
    uncertain = re.compile(
        r"\b(neu|gia su|gia thiet|sai khi noi|khong dung khi noi|phu dinh khang dinh|"
        r"if|suppose|hypothetical|false to say|wrong to say)\b"
    )
    refuted_quote = re.compile(
        r"(?:\"[^\"]*\"|'[^']*'|\u201c[^\u201d]*\u201d|\u2018[^\u2019]*\u2019)"
        r"\s*(?:la\s+)?(?:sai|khong dung|is false|is wrong)\b"
    )
    correction_prefix = re.compile(
        r"^\s*(?:(?:em|tôi|toi)\s+)?(?:xin\s+)?"
        r"(?:sửa lại|sua lai|đính chính|dinh chinh)\s*:\s*|"
        r"^\s*(?:correction|let me correct(?: myself)?|i correct myself|i meant)\s*:\s*",
        re.IGNORECASE,
    )
    return ". ".join(correction_prefix.sub("", clause, count=1) for clause in clauses
                     if not uncertain.search(plain_text(clause))
                     and not refuted_quote.search(plain_text(clause)))


def plain_text(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower())
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return value.replace("đ", "d").replace("−", "-")


def _number(value: str) -> float:
    normalized = value.replace(",", ".")
    return float(normalized)


def _canonical_unit(value: str) -> str:
    unit = value.strip()
    aliases = {
        "diem": "point",
        "%": "percent",
        "phan tram": "percent",
        "byte": "byte",
        "bytes": "byte",
        "giay": "second",
        "s": "second",
        "phut": "minute",
        "gio": "hour",
    }
    return aliases.get(unit, unit)


def extract_entity_values(value: str) -> dict[str, tuple[float, str]]:
    facts: dict[str, tuple[float, str]] = {}
    for match in _ENTITY_VALUE.finditer(plain_text(value)):
        entity = match.group("entity").strip()
        if entity in _IGNORED_ENTITIES:
            continue
        facts[entity] = (_number(match.group("value")), _canonical_unit(match.group("unit")))
    return facts


def _compare(left: float, right: float) -> str:
    if abs(left - right) < 1e-9:
        return "="
    return ">" if left > right else "<"


def _claimed_comparisons(answer: str, entities: list[str]) -> list[tuple[str, str, str, str]]:
    if len(entities) < 2:
        return []
    alternatives = "|".join(re.escape(item) for item in sorted(entities, key=len, reverse=True))
    pattern = re.compile(
        rf"\b(?P<left>{alternatives})\b[^.!?\n]{{0,28}}?"
        rf"(?P<op>>=|<=|!=|{_GREATER}|{_LESS}|{_EQUAL})"
        rf"[^.!?\n]{{0,28}}?\b(?P<right>{alternatives})\b"
    )
    comparisons: list[tuple[str, str, str, str]] = []
    normalized = plain_text(answer)
    for match in pattern.finditer(normalized):
        op_text = match.group("op")
        if re.fullmatch(_GREATER, op_text):
            relation = ">"
        elif re.fullmatch(_LESS, op_text):
            relation = "<"
        else:
            relation = "="
        if op_text in {">=", "<=", "!="}:
            relation = op_text
        prefix = normalized[match.start():match.start("op")]
        if re.search(r"\b(khong|not|never)\b", prefix):
            relation = {">": "<=", "<": ">=", "=": "!=",
                        "<=": ">", ">=": "<", "!=": "="}[relation]
        comparisons.append(
            (match.group("left"), relation, match.group("right"), match.group(0))
        )
    return comparisons


def _negated_rubric_point(point: str, answer: str) -> str:
    normalized_point = plain_text(point).strip(" .")
    normalized_answer = plain_text(asserted_text(answer))
    if " la " in normalized_point:
        left, right = normalized_point.split(" la ", 1)
        pattern = re.compile(
            rf"\b{re.escape(left)}\s+(?:khong|chua)\s+"
            rf"(?:phai\s+)?(?:la\s+)?{re.escape(right)}\b"
        )
        match = pattern.search(normalized_answer)
        if match:
            return match.group(0)
    for copula in (" is ", " are "):
        if copula in normalized_point:
            left, right = normalized_point.split(copula, 1)
            pattern = re.compile(
                rf"\b{re.escape(left)}{copula}(?:not|never)\s+{re.escape(right)}\b"
            )
            match = pattern.search(normalized_answer)
            if match:
                return match.group(0)
    return ""


def _relation_holds(relation: str, actual: str) -> bool:
    return actual in {">": {">"}, "<": {"<"}, "=": {"="},
                      "<=": {"<", "="}, ">=": {">", "="}, "!=": {"<", ">"}}[relation]


def check_rubric_point(question: dict[str, Any], answer: str, point: str) -> FactCheck:
    """Return only facts attributable to this point, never a whole-answer grade."""
    from app.services.course_verifier import check_course_point
    course_check = check_course_point(answer, point, question=question)
    if course_check.status != "unknown":
        return course_check
    evidence = _negated_rubric_point(point, answer)
    normalized_point = plain_text(point).strip(" .")
    clauses = split_clauses(plain_text(asserted_text(answer)))
    explicit_rejection = [clause for clause in clauses if clause in {
        f"khong dung la {normalized_point}", f"it is false that {normalized_point}",
        f"toi phu dinh khang dinh sau: {normalized_point}"}]
    if explicit_rejection:
        evidence = explicit_rejection[0]
    if evidence:
        # A later correction or an inconsistent assertion requires semantic adjudication.
        positive = plain_text(point).strip(" .")
        if any(clause.startswith(positive) for clause in clauses):
            return FactCheck("conflicted", 0.0, "Cùng một ý vừa được khẳng định vừa bị phủ định.", evidence)
        return FactCheck("contradicted", 0.99,
                         f"Câu trả lời phủ định trực tiếp tiêu chí: {point}.", evidence)

    # A complete, asserted subject-copula-predicate relation is stronger than token overlap.
    # Never recover a mere substring, a hypothetical, or a relation with an ambiguous tail.
    for copula in (" la ", " is ", " are "):
        if copula not in normalized_point:
            continue
        subject, predicate = normalized_point.split(copula, 1)
        if re.search(r"\b(khong|chua|not|never|va|and|hoac|or)\b", predicate):
            continue
        candidates = [fragment for clause in split_clauses(plain_text(asserted_text(answer)))
                      for fragment in re.split(r"(?<!\d),|,(?!\d)|\s+va\s+|\s+and\s+", clause)]
        candidates = [re.sub(r"^(?:tuy nhien|nhung|con|however|but)\s+", "", clause.strip())
                      for clause in candidates]
        relevant = [clause for clause in candidates if clause.startswith(subject + copula)]
        if not relevant:
            continue
        exact_relation = re.compile(
            rf"{re.escape(subject + copula + predicate)}(?:\s+(?:cua|of)\s+[a-z ]+)?"
        )
        if all(exact_relation.fullmatch(clause) for clause in relevant):
            return FactCheck("supported", 0.99,
                             "Phát biểu khẳng định đúng quan hệ chủ thể và thuộc tính trong tiêu chí.", relevant[0])

    expected = extract_entity_values(f"{question.get('question', '')} {question.get('reference_answer', '')}")
    entities = [entity for entity in expected if re.search(rf"\b{re.escape(entity)}\b", normalized_point)]
    if not entities:
        return FactCheck("unknown", 0.0)
    asserted = asserted_text(answer)
    for entity, (value, unit) in extract_entity_values(asserted).items():
        if entity not in entities:
            continue
        original, original_unit = expected[entity]
        if (not unit or not original_unit or unit == original_unit) and abs(value - original) > 1e-9:
            return FactCheck("contradicted", 0.99,
                             f"Giá trị của {entity} là {value:g}, khác dữ kiện {original:g}.",
                             f"{entity} {value:g} {unit}".strip(), (entity,))
    desired = _claimed_comparisons(point, entities)
    if not desired:
        return FactCheck("unknown", 0.0)
    claims = _claimed_comparisons(asserted, entities)
    judgments = []
    for left, relation, right, quote in claims:
        if not any({left, right} == {a, b} for a, _, b, _ in desired):
            continue
        left_value, left_unit = expected[left]
        right_value, right_unit = expected[right]
        if left_unit and right_unit and left_unit != right_unit:
            continue
        judgments.append((_relation_holds(relation, _compare(left_value, right_value)), quote))
    if len({correct for correct, _ in judgments}) > 1:
        return FactCheck("conflicted", 0.0, "Các quan hệ so sánh trong câu trả lời không nhất quán.")
    if not judgments:
        return FactCheck("unknown", 0.0)
    # This narrow rule can establish a single numeric comparison, not a compound criterion.
    if len(desired) != 1 or re.search(r"\b(va|and|dong thoi)\b", normalized_point):
        return FactCheck("unknown", 0.0)
    correct, quote = judgments[0]
    return FactCheck("supported" if correct else "contradicted", 0.995,
                     "Đối chiếu quan hệ với dữ kiện số trong đề.", quote, tuple(entities))


def analyze_fact_consistency(question: dict[str, Any], answer: str) -> FactCheck:
    checks = [check_rubric_point(question, answer, str(point))
              for point in question.get("key_points") or []]
    for check in checks:
        if check.status == "contradicted":
            return check
    if checks and all(check.status == "supported" for check in checks):
        return checks[0]
    return FactCheck(status="unknown", confidence=0.0)


def contradiction_evaluation(
    question: dict[str, Any], answer: str, check: FactCheck
) -> dict[str, Any]:
    from app.services.evaluator import _compose_result

    assessments = []
    for point in question.get("key_points") or []:
        scoped = check_rubric_point(question, answer, point)
        status = {"supported": "met", "contradicted": "contradicted"}.get(scoped.status, "unresolved")
        assessments.append({"point": point, "status": status,
                            "reason": scoped.reason, "evidence_quote": scoped.evidence,
                            "needs_review": status == "unresolved"})
    return _compose_result(question, assessments, evaluator="factguard-v1",
                           confidence=check.confidence, review_required=True)
