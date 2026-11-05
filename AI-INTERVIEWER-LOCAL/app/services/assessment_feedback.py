"""Explain score eligibility independently of the proposed rubric outcomes."""
from app.services.voice_evidence import voice_risk, voice_requires_review


TECHNICAL_GRADING_REASONS = {"model_unavailable", "model_timeout", "model_output_invalid",
                             "evidence_verifier_unavailable"}


def normalize_assessments(value) -> list[dict]:
    """Malformed stored evidence is unresolved; never mutate the original record."""
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, dict):
            result.append({"point": "", "status": "unresolved", "needs_review": True,
                           "review_reason": "invalid_assessment"})
            continue
        point, status, code = item.get("point"), item.get("status"), item.get("review_reason")
        valid_point = isinstance(point, str) and bool(point.strip())
        valid_status = isinstance(status, str) and status in {
            "met", "partial", "missing", "contradicted", "unresolved"}
        normalized = dict(item)
        if not valid_point or not valid_status or (code is not None and not isinstance(code, str)):
            normalized.update(point=point if valid_point else "", status="unresolved",
                              needs_review=True, review_reason="invalid_assessment")
        result.append(normalized)
    return result


def verified_assessment_evidence(value, transcript: str) -> list[dict]:
    """Project literal transcript evidence without modifying saved grading decisions."""
    transcript = transcript if isinstance(transcript, str) else ""
    result = normalize_assessments(value)
    for item in result:
        primary = item.get("evidence_quote")
        quotes = item.get("evidence_quotes")
        candidates = ([primary] if isinstance(primary, str) else []) + (quotes if isinstance(quotes, list) else [])
        valid = list(dict.fromkeys(quote for quote in candidates if isinstance(quote, str)
                                  and quote.strip() and quote in transcript))
        if "evidence_quote" in item or "evidence_quotes" in item:
            item["evidence_quote"] = valid[0] if valid else ""
        if "evidence_quotes" in item:
            item["evidence_quotes"] = valid
        if "evidence_spans" in item:
            item["evidence_spans"] = [{"start": transcript.find(quote), "end": transcript.find(quote) + len(quote),
                                       "text": quote} for quote in valid]
    return result


def has_technical_grading_failure(assessments) -> bool:
    return isinstance(assessments, list) and any(
        isinstance(item, dict) and isinstance(item.get("review_reason"), str)
        and item["review_reason"] in TECHNICAL_GRADING_REASONS
        and (item.get("needs_review") or item.get("status") == "unresolved") for item in assessments)


def assessment_feedback(evaluation: dict, voice: dict | None = None, *, interview_mode: str | None = None) -> dict:
    voice = voice or {}
    reasons = []
    assessments = normalize_assessments(evaluation.get("point_assessments"))
    codes = {item.get("review_reason") for item in assessments}
    if codes & TECHNICAL_GRADING_REASONS:
        reasons.append({"code": "model_unavailable", "category": "system", "action": "retry_grading",
            "message": "Bộ chấm chưa hoàn tất xử lý. Hệ thống sẽ thử chấm lại bản trả lời đã lưu; không cần ghi âm lại."})
    scope, _ = voice_risk(voice)
    if voice_requires_review(voice, assessments):
        reasons.append({"code": "transcript_review", "category": "audio", "action": "check_audio",
            "message": "Bản chép lời còn đoạn chưa chắc chắn. Có thể ghi âm lại trước khi gửi nếu nội dung không đúng lời bạn nói."})
    pending = [item.get("point") for item in assessments
               if item.get("needs_review") or item.get("status") == "unresolved"]
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
            "recognition_status": ("partially_verified" if scope == "criteria" else "needs_review")
                if any(r["category"] == "audio" for r in reasons) else "processed",
            "recognition_scope": scope,
            "review_reasons": reasons, **policy}
