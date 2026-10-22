"""Shared grade eligibility and immutable teacher-decision snapshots."""
from __future__ import annotations

import hashlib
import json
import math
from app.services.assessment_feedback import assessment_feedback


def json_object(value):
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def json_array(value):
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except (TypeError, ValueError):
        return []


def original_is_provisional(flag, assessment_json, metadata_json=None):
    if flag:
        return True
    try:
        assessments = json.loads(assessment_json or "[]")
        if not isinstance(assessments, list) or not assessments:
            return True
        if any(not isinstance(item, dict) or not isinstance(item.get("point"), str) or not item["point"].strip() or item.get("needs_review") or
               item.get("status") not in {"met", "partial", "missing", "contradicted"}
               for item in assessments):
            return True
        metadata = json.loads(metadata_json or "{}")
        if not isinstance(metadata, dict):
            return True
        quality = (metadata.get("metrics") or {}).get("quality_score")
        return bool(metadata.get("transcript_status") == "needs_review" or
                    metadata.get("quality_warnings") or
                    (quality is not None and (not math.isfinite(float(quality)) or float(quality) < .55)))
    except (TypeError, ValueError, AttributeError):
        return True


def decision_snapshot(*, source, score, feedback, question, transcript, evaluation=None):
    return {
        "version": 1, "source": source, "score": score, "feedback": feedback,
        "question_uid": question.get("uid"), "transcript": transcript,
        "rubric_sha256": hashlib.sha256(json.dumps(question, sort_keys=True, ensure_ascii=False,
            separators=(",", ":")).encode("utf-8")).hexdigest(),
        "rubric_snapshot": question.get("rubric_snapshot"),
        "evaluation": evaluation if source == "strong_ai" else None,
    }


def effective_grade(row, *, interview_mode=None):
    """Never infer criterion outcomes from a teacher's aggregate score."""
    row = dict(row)
    provisional = original_is_provisional(row.get("score_provisional"), row.get("assessment_json"),
                                          row.get("voice_metadata_json"))
    ai_score = float(row["ai_score"] if row.get("ai_score") is not None else row["score"])
    reviewed = bool(row.get("reviewed_at"))
    final = row.get("final_score") if reviewed or not provisional else None
    decision = json_object(row.get("final_decision_json")) if reviewed else {}
    original = {"point_assessments": json_array(row.get("assessment_json")),
                "matched_points": json_array(row.get("matched_points_json")),
                "missing_points": json_array(row.get("missing_points_json"))}
    if reviewed:
        evaluation = decision.get("evaluation") if decision.get("source") == "strong_ai" else {}
    else:
        evaluation = original
    evaluation = evaluation if isinstance(evaluation, dict) else {}
    assessments = evaluation.get("point_assessments")
    assessments = assessments if isinstance(assessments, list) else []
    matched = [item["point"] for item in assessments if isinstance(item, dict) and item.get("point") and item.get("status") == "met"]
    missing = [item["point"] for item in assessments if isinstance(item, dict) and item.get("point") and item.get("status") in {"missing", "contradicted", "partial"}]
    if not assessments and not reviewed:
        matched = original.get("matched_points", [])
        missing = original.get("missing_points", []) if not provisional else []
    status = assessment_feedback({"score_provisional": provisional and not reviewed, "point_assessments": assessments},
                                 json_object(row.get("voice_metadata_json")) if not reviewed else {},
                                 interview_mode=interview_mode)
    return {**status, "score": float(final) if final is not None else ai_score, "final_score": final,
            "ai_score": ai_score, "score_provisional": provisional and not reviewed,
            "grading_source": decision.get("source", "legacy_teacher" if reviewed else "original_ai"),
            "graded_transcript": decision.get("transcript", row.get("answer_text")),
            "confidence": evaluation.get("confidence", row.get("confidence") if not reviewed else None),
            "rubric_version": evaluation.get("rubric_version", row.get("rubric_version")),
            "point_assessments": assessments, "matched_points": matched, "missing_points": missing,
            "feedback": evaluation.get("feedback", row.get("teacher_feedback") if reviewed else row.get("feedback")),
            "evaluator": evaluation.get("evaluator", "teacher" if reviewed else row.get("evaluator"))}
