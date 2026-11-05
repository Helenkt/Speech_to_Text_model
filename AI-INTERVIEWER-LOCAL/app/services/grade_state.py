"""Shared grade eligibility and immutable teacher-decision snapshots."""
from __future__ import annotations

import hashlib
import json
import math
from app.services.assessment_feedback import assessment_feedback, normalize_assessments
from app.services.practice_grading import question_breakdown, teacher_total_breakdown
from app.services.voice_evidence import project_voice_assessments, voice_requires_review


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
        assessments = normalize_assessments(assessments)
        if not assessments:
            return True
        if any(not isinstance(item, dict) or not isinstance(item.get("point"), str) or not item["point"].strip() or item.get("needs_review") or
               item.get("status") not in {"met", "partial", "missing", "contradicted"}
               for item in assessments):
            return True
        metadata = json.loads(metadata_json or "{}")
        if not isinstance(metadata, dict):
            return True
        return voice_requires_review(metadata, assessments)
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


def effective_grade(row, *, interview_mode=None, completed=True):
    """Never infer criterion outcomes from a teacher's aggregate score."""
    row = dict(row)
    provisional = original_is_provisional(row.get("score_provisional"), row.get("assessment_json"),
                                          row.get("voice_metadata_json"))
    ai_score = float(row["ai_score"] if row.get("ai_score") is not None else row["score"])
    reviewed = bool(row.get("reviewed_at"))
    final = row.get("final_score") if reviewed or not provisional else None
    decision = json_object(row.get("final_decision_json")) if reviewed else {}
    original = {"point_assessments": normalize_assessments(json_array(row.get("assessment_json"))),
                "matched_points": json_array(row.get("matched_points_json")),
                "missing_points": json_array(row.get("missing_points_json"))}
    if reviewed:
        evaluation = decision.get("evaluation") if decision.get("source") == "strong_ai" else {}
    else:
        evaluation = original
    evaluation = evaluation if isinstance(evaluation, dict) else {}
    assessments = normalize_assessments(evaluation.get("point_assessments"))
    if not reviewed:
        assessments = project_voice_assessments(json_object(row.get("voice_metadata_json")), assessments)
    matched = [item["point"] for item in assessments if isinstance(item, dict) and item.get("point") and item.get("status") == "met"]
    missing = [item["point"] for item in assessments if isinstance(item, dict) and item.get("point") and item.get("status") in {"missing", "contradicted", "partial"}]
    if not assessments and not reviewed:
        matched = original.get("matched_points", [])
        missing = original.get("missing_points", []) if not provisional else []
    breakdown = None
    if (interview_mode == "practice" and reviewed and isinstance(final, (int, float))
            and not isinstance(final, bool) and math.isfinite(final) and 0 <= final <= 100):
        breakdown = teacher_total_breakdown(final)
    if interview_mode == "practice" and not reviewed:
        question = json_object(row.get("question_json"))
        voice_status = assessment_feedback({"score_provisional": provisional, "point_assessments": assessments},
                                          json_object(row.get("voice_metadata_json")), interview_mode="practice")
        breakdown = question_breakdown(question, {**voice_status, "final_score": final,
            "score_provisional": provisional, "grading_pending": bool(row.get("grading_pending")),
            "point_assessments": assessments}, completed=completed)
        if breakdown["status"] != "final":
            provisional, final = True, None
    status = assessment_feedback({"score_provisional": provisional and not reviewed, "point_assessments": assessments},
                                 json_object(row.get("voice_metadata_json")) if not reviewed else {},
                                 interview_mode=interview_mode)
    if breakdown and breakdown["status"] in {"invalid_rubric", "score_mismatch"}:
        status["review_reasons"].append({"code": breakdown["status"], "category": "grading",
            "action": "verify_evidence", "message": "Điểm lưu chưa khớp rubric; chưa dùng làm điểm chính thức."})
    return {**status, **({"score_breakdown": breakdown} if breakdown is not None else {}),
            "score": float(final) if final is not None else ai_score, "final_score": final,
            "ai_score": ai_score, "score_provisional": provisional and not reviewed,
            "grading_source": decision.get("source", "legacy_teacher" if reviewed else "original_ai"),
            "graded_transcript": decision.get("transcript", row.get("answer_text")),
            "confidence": evaluation.get("confidence", row.get("confidence") if not reviewed else None),
            "rubric_version": evaluation.get("rubric_version", row.get("rubric_version")),
            "point_assessments": assessments, "matched_points": matched, "missing_points": missing,
            "feedback": evaluation.get("feedback", row.get("teacher_feedback") if reviewed else row.get("feedback")),
            "evaluator": evaluation.get("evaluator", "teacher" if reviewed else row.get("evaluator"))}


def practice_final_score(question_json, assessment_json, score, final_score, flag, voice_json,
                         reviewed_at, grading_pending, session_status):
    """SQLite projection uses the same eligibility decision as the report; never writes grades."""
    if score is None:
        return None
    try:
        result = effective_grade({"question_json": question_json, "assessment_json": assessment_json,
            "score": score, "final_score": final_score, "score_provisional": flag,
            "voice_metadata_json": voice_json, "reviewed_at": reviewed_at, "grading_pending": grading_pending},
            interview_mode="practice", completed=session_status == "completed")
        return result["final_score"]
    except (ValueError, TypeError, KeyError, AttributeError):
        return None
