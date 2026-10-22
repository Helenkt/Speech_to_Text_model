"""Explain score eligibility independently of the proposed rubric outcomes."""
import math


def voice_requires_review(voice: dict) -> bool:
    try:
        quality = (voice.get("metrics") or {}).get("quality_score")
        return bool(voice.get("transcript_status") == "needs_review" or voice.get("quality_warnings")
                    or (quality is not None and (not math.isfinite(float(quality)) or float(quality) < .55)))
    except (ValueError, TypeError, AttributeError):
        return True


def assessment_feedback(evaluation: dict, voice: dict | None = None, *, interview_mode: str | None = None) -> dict:
    voice = voice or {}
    reasons = []
    codes = {item.get("review_reason") for item in evaluation.get("point_assessments", []) if isinstance(item, dict)}
    if codes & {"model_unavailable", "model_timeout", "model_output_invalid"}:
        reasons.append({"code": "model_unavailable", "category": "system", "action": "retry_grading",
            "message": "Bộ chấm chưa hoàn tất xử lý. Hệ thống sẽ thử chấm lại bản trả lời đã lưu; không cần ghi âm lại."})
    if voice_requires_review(voice):
        reasons.append({"code": "transcript_review", "category": "audio", "action": "check_audio",
            "message": "Bản chép lời còn đoạn chưa chắc chắn. Có thể ghi âm lại trước khi gửi nếu nội dung không đúng lời bạn nói."})
    pending = [item.get("point") for item in evaluation.get("point_assessments", [])
               if isinstance(item, dict) and (item.get("needs_review") or item.get("status") == "unresolved")]
    if pending and not reasons:
        reasons.append({"code": "evidence_unverified", "category": "grading", "action": "verify_evidence",
            "message": "Còn tiêu chí chưa xác minh được bằng chứng. Đây chưa phải kết luận câu trả lời sai.", "points": pending})
    if evaluation.get("score_provisional") and not reasons:
        reasons.append({"code": "verification_pending", "category": "grading", "action": "verify_evidence",
            "message": "Điểm đề xuất còn cần xác minh trước khi đưa vào tổng kết."})
    practice = interview_mode == "practice"
    if practice:
        for reason in reasons:
            if reason["category"] == "audio":
                reason["action"] = "practice_again"
                reason["message"] = "Bản chép lời chưa đủ chắc chắn để dùng điểm. Bạn có thể luyện tập lại bằng ghi âm rõ hơn."
            elif reason["category"] == "grading":
                reason["action"] = "practice_again"
                reason["message"] = "AI chưa đủ cơ sở xác minh câu trả lời; kết quả này chưa được tính vào điểm luyện tập."
    policy = ({"grading_owner": "ai" if practice else "teacher",
               "teacher_review_required": not practice and bool(evaluation.get("review_required"))}
              if interview_mode else {})
    if practice:
        policy["review_required"] = False
    return {"grading_status": ("insufficient_evidence" if practice else "pending") if evaluation.get("score_provisional") else "verified",
            "recognition_status": "needs_review" if any(r["category"] == "audio" for r in reasons) else "processed",
            "review_reasons": reasons, **policy}
