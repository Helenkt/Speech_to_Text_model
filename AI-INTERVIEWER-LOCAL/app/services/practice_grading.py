"""Read-only practice scores from the saved rubric and effective grading decisions."""
from __future__ import annotations

from collections import defaultdict
import math

from app.services.rubric_contract import rubric_hash, validate_rubric_points
from app.services.assessment_feedback import normalize_assessments


SCALE = 10


def valid_score(value) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and 0 <= value <= 100 and math.isfinite(value))


def question_breakdown(question: dict, evaluation: dict, *, completed: bool) -> dict:
    """Unresolved evidence keeps its original denominator and never earns a made-up zero."""
    pending = not completed or bool(evaluation.get("grading_pending"))
    result = {"scale": SCALE, "score": None, "status": "pending" if pending else "insufficient_evidence",
              "confirmed_points": 0.0, "possible_score_interval": [0.0, float(SCALE)],
              "criteria": [], "resolved_criterion_count": 0, "unresolved_criterion_count": 0,
              "confidence_is_accuracy": False}
    points = question.get("key_points")
    weights = question.get("key_point_weights")
    if weights is None:
        weights = {}
    try:
        validate_rubric_points(points, weights)
        rubric_sha = rubric_hash(question)
    except (ValueError, KeyError, TypeError):
        return {**result, "status": "invalid_rubric"}
    weights = {p: weights.get(p, 1.0) for p in points}
    raw = normalize_assessments(evaluation.get("point_assessments"))
    valid = (isinstance(raw, list) and len(raw) == len(points)
             and all(isinstance(item, dict) and isinstance(item.get("point"), str) for item in raw)
             and {item["point"] for item in raw} == set(points))
    assessments = {item["point"]: item for item in raw} if valid else {}
    snapshot = question.get("rubric_snapshot") or {}
    atomic = {item["claim"]: item for item in snapshot.get("contract", {}).get("criteria", [])}
    blocked_audio = evaluation.get("recognition_status") == "needs_review"
    total = sum(weights.values())
    lower = upper = 0.0
    for point in points:
        item = assessments.get(point, {})
        status = item.get("status", "unresolved")
        if (pending or blocked_audio or item.get("needs_review") or not isinstance(status, str)
                or status not in {"met", "partial", "missing", "contradicted"}
                or (point in atomic and status == "partial")):
            status = "unresolved"
        maximum = SCALE * weights[point] / total
        credit = {"met": 1.0, "partial": 0.5, "missing": 0.0, "contradicted": 0.0}.get(status)
        earned = maximum * credit if credit is not None else None
        lower += earned if earned is not None else 0
        upper += earned if earned is not None else maximum
        result["criteria"].append({"point": point, "criterion_id": atomic.get(point, {}).get("id"),
            "weight": weights[point], "max_points": round(maximum, 4), "status": status,
            "credit_policy": "binary" if point in atomic else "legacy_status_credit",
            "earned_points": round(earned, 4) if earned is not None else None,
            "needs_verification": credit is None, "reason": item.get("reason", "")})
    unresolved = sum(item["needs_verification"] for item in result["criteria"])
    result.update(rubric_sha256=rubric_sha, confirmed_points=round(lower, 2),
                  possible_score_interval=[round(lower, 2), round(upper, 2)],
                  resolved_criterion_count=len(points) - unresolved, unresolved_criterion_count=unresolved)
    final = evaluation.get("final_score")
    eligible = (not pending and not blocked_audio and unresolved == 0
                and not evaluation.get("score_provisional")
                and valid_score(final))
    if eligible:
        if abs(final / SCALE - lower) <= .011:
            result.update(score=round(final / SCALE, 2), status="final")
        else:
            result["status"] = "score_mismatch"
    return result


def validate_ai_grade(question: dict, evaluation: dict) -> dict:
    """A persisted AI total cannot override its saved rubric outcomes."""
    breakdown = question_breakdown(question, {**evaluation, "final_score": evaluation.get("score")}, completed=True)
    if breakdown["status"] != "final":
        evaluation.update(score_provisional=True, review_required=True,
                          grade_validation_error=breakdown["status"])
    return breakdown


def teacher_total_breakdown(score: float) -> dict:
    """Keep a legacy teacher total without inventing criterion-level decisions."""
    total = round(score / 10, 2)
    return {"scale": SCALE, "score": total, "status": "final", "basis": "teacher_total_only",
            "confirmed_points": total, "possible_score_interval": [total, total],
            "criteria": [], "resolved_criterion_count": 0, "unresolved_criterion_count": 0,
            "criterion_details_available": False, "confidence_is_accuracy": False}


def practice_summary(answers: list[dict], *, completed: bool) -> dict:
    """Questions have equal weight, matching the existing session-average policy."""
    def aggregate(rows):
        count = len(rows)
        finalized = [row["score"] for row in rows if row["status"] == "final"]
        complete = completed and count > 0 and len(finalized) == count
        pending = not completed or any(row["status"] == "pending" for row in rows)
        return {"scale": SCALE, "score": round(sum(finalized) / count, 2) if complete else None,
                "status": "final" if complete else "pending" if pending else "insufficient_evidence",
                "question_count": count, "scored_question_count": len(finalized),
                "unscored_question_count": count - len(finalized),
                "scored_only_average": round(sum(finalized) / len(finalized), 2) if finalized else None,
                "confirmed_points": round(sum(row["confirmed_points"] for row in rows) / count, 2) if count else 0.0,
                "possible_score_interval": [round(sum(row["possible_score_interval"][i] for row in rows) / count, 2)
                                            for i in (0, 1)] if count else [0.0, float(SCALE)]}

    subjects, competencies = defaultdict(list), defaultdict(list)
    for answer in answers:
        breakdown = answer["evaluation"]["score_breakdown"]
        question = answer["question"]
        subject = question.get("subject", "unknown")
        subjects[subject].append(breakdown)
        competencies[(subject, question.get("competency", "unknown"))].append(breakdown)
    return {"schema_version": "practice-grading-breakdown-v1", "grading_owner": "ai",
            "grading_time": "end_of_session", "aggregation": "equal_question_weight",
            "scope": "answered_questions", "confidence_is_accuracy": False,
            "session": aggregate([a["evaluation"]["score_breakdown"] for a in answers]),
            "subjects": [{"subject": subject, **aggregate(rows)} for subject, rows in sorted(subjects.items())],
            "competencies": [{"subject": subject, "competency": name, **aggregate(rows)}
                             for (subject, name), rows in sorted(competencies.items())]}
