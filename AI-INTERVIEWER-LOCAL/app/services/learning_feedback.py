"""Learning feedback projected from saved rubric decisions; no new inference."""
from __future__ import annotations

from collections import defaultdict

from app.services.assessment_feedback import verified_assessment_evidence


VERSION = "learning-feedback-v1"
PRIORITY = {"contradicted": 0, "inconsistent": 1, "partial": 2, "missing": 3}
TEXT = {
    "vi": {
        "met": "Bạn đã nêu đúng: {point}",
        "partial": "Bản trả lời mới đáp ứng một phần tiêu chí: {point}",
        "missing": "Bản trả lời chưa nêu đủ ý: {point}",
        "contradicted": "Bản trả lời mâu thuẫn với tiêu chí: {point}",
        "unresolved": "Chưa đủ bằng chứng để kết luận về tiêu chí: {point}",
        "correction": "Nội dung cần đối chiếu trong rubric: {point}",
        "pending": "Bài đã lưu và đang chờ chấm. Chưa có kết luận về câu trả lời.",
        "audio": "Bản chép lời chưa đủ chắc chắn. Chưa dùng câu này để kết luận về kiến thức; bạn có thể ghi âm trong lượt luyện mới.",
        "audio_partial": "Một số đoạn chép lời cần xác minh. Các tiêu chí có bằng chứng rõ vẫn được ghi nhận; phần chưa rõ chưa được coi là sai.",
        "system": "Bộ chấm chưa hoàn tất xử lý bản trả lời đã lưu. Không cần ghi âm lại vì lỗi này.",
        "invalid": "Điểm hoặc rubric cần được kiểm tra. Chưa dùng câu này để kết luận về kiến thức.",
        "unknown": "AI chưa đủ cơ sở xác minh một số ý. Đây chưa phải kết luận câu trả lời sai.",
        "legacy": "Bài có điểm tổng nhưng không có quyết định theo từng tiêu chí; chưa đủ dữ liệu để giải thích từng ý.",
        "inconsistent": "Kết quả chưa nhất quán giữa các câu về: {point}",
        "study": "Ôn lại tiêu chí và đáp án của câu này, sau đó luyện giải thích bằng lời của bạn.",
        "more": "Còn {count} tiêu chí trong phần chi tiết chấm điểm.",
    },
    "en": {
        "met": "You correctly stated: {point}",
        "partial": "Your response only partly addresses this criterion: {point}",
        "missing": "Your response does not yet cover: {point}",
        "contradicted": "Your response contradicts this criterion: {point}",
        "unresolved": "There is not enough verified evidence for this criterion: {point}",
        "correction": "Compare your response with this rubric statement: {point}",
        "pending": "Your response is saved and awaiting grading. No conclusion is available yet.",
        "audio": "The transcript is not reliable enough. This response is not used to judge your knowledge; you can record in a new practice attempt.",
        "audio_partial": "Some transcript spans need verification. Criteria with clear evidence are retained; unclear parts are not marked wrong.",
        "system": "Grading of your saved response is incomplete. This issue does not require a new recording.",
        "invalid": "The score or rubric needs checking. This response is not used to judge your knowledge yet.",
        "unknown": "AI could not verify some statements. This does not establish that your answer is wrong.",
        "legacy": "An overall score is available, but criterion decisions were not saved; individual statements cannot be explained.",
        "inconsistent": "Results differ across questions about: {point}",
        "study": "Review the criterion and reference answer, then practise explaining it in your own words.",
        "more": "Another {count} criteria are available in the grading details.",
    },
}


def question_feedback(question: dict, answer: str, evaluation: dict) -> dict:
    text = TEXT.get(question.get("language"), TEXT["vi"])
    breakdown = evaluation.get("score_breakdown") or {}
    reasons = evaluation.get("review_reasons") or []
    categories = {reason.get("category") for reason in reasons if isinstance(reason, dict)}
    pending = evaluation.get("grading_pending") or breakdown.get("status") == "pending"
    blocked = (("audio" in categories or evaluation.get("recognition_status") == "needs_review")
               and evaluation.get("recognition_scope") != "criteria"
               or breakdown.get("status") in {"invalid_rubric", "score_mismatch"})
    raw = verified_assessment_evidence(evaluation.get("point_assessments"), answer)
    grouped = defaultdict(list)
    for item in raw:
        grouped[item["point"]].append(item)
    criteria = breakdown.get("criteria") or []
    items = []
    for criterion in criteria:
        point = criterion["point"]
        matches = grouped[point]
        assessment = matches[0] if len(matches) == 1 else {}
        status = criterion["status"]
        if pending or blocked or not assessment or criterion.get("needs_verification"):
            status = "unresolved"
        # Quotes are evidence in the transcript used for grading, never reconstructed speech.
        quotes = assessment.get("evidence_quotes") or [assessment.get("evidence_quote", "")]
        if not isinstance(quotes, list):
            quotes = []
        evidence = list(dict.fromkeys(quote for quote in quotes if isinstance(quote, str)
                                     and quote.strip() and quote in answer)) if status != "unresolved" else []
        items.append({"criterion_id": criterion.get("criterion_id"), "point": point, "status": status,
            "message": text[status].format(point=point), "evidence_quotes": evidence,
            "correction": text["correction"].format(point=point) if status in PRIORITY else None,
            "earned_points": criterion.get("earned_points") if status != "unresolved" else None,
            "max_points": criterion.get("max_points"),
            "source": {"question_id": question.get("id"), "source_name": question.get("source_name"),
                       "rubric_sha256": breakdown.get("rubric_sha256"), "quote": point}})
    notices = []
    if pending:
        notices.append({"category": "pending", "action": None, "message": text["pending"]})
    else:
        if "system" in categories:
            notices.append({"category": "system", "action": "retry_grading", "message": text["system"]})
        if "audio" in categories or evaluation.get("recognition_status") == "needs_review":
            notices.append({"category": "audio", "action": "practice_again",
                "message": text["audio_partial" if evaluation.get("recognition_scope") == "criteria" else "audio"]})
        if breakdown.get("status") in {"invalid_rubric", "score_mismatch"}:
            notices.append({"category": "grading", "action": None, "message": text["invalid"]})
        elif not items:
            notices.append({"category": "grading", "action": None, "message": text["legacy"]})
        elif (any(item["status"] == "unresolved" for item in items)
              or evaluation.get("score_provisional")) and not notices:
            notices.append({"category": "grading", "action": "practice_again", "message": text["unknown"]})
    messages = [notice["message"] for notice in notices]
    met = [item for item in items if item["status"] == "met"]
    improvements = sorted((item for item in items if item["status"] in PRIORITY),
                          key=lambda item: PRIORITY[item["status"]])
    messages.extend(item["message"] for item in met[:2] + improvements[:3])
    remaining = max(0, len(met) - 2) + max(0, len(improvements) - 3)
    if remaining:
        messages.append(text["more"].format(count=remaining))
    focus = [item["point"] for item in items if item["status"] in PRIORITY]
    return {"schema_version": VERSION, "summary": " ".join(message.rstrip(".") + "." for message in messages), "items": items,
            "notices": notices, "focus_points": focus,
            "next_step": text["study"] if focus else None,
            "scope": "this_response", "generation": "saved_rubric_and_verified_transcript",
            "confidence_is_accuracy": False}


def session_feedback(answers: list[dict]) -> dict:
    groups = defaultdict(list)
    actions = []
    for answer in answers:
        question = answer["question"]
        feedback = answer["evaluation"].get("learning_feedback") or {}
        ref = {"answer_id": answer["answer_id"], "sequence_number": answer["sequence_number"]}
        for item in feedback.get("items", []):
            if item["status"] != "unresolved":
                groups[(question.get("subject"), question.get("language"), item["point"])].append((item, ref))
        notices = [notice for notice in feedback.get("notices", []) if notice.get("action")]
        technical = [notice for notice in notices if notice["action"] == "retry_grading"]
        if technical:
            actions.append({**ref, **technical[0], "focus_points": []})
        else:
            retry = next((notice for notice in notices if notice["action"] == "practice_again"), None)
            if feedback.get("focus_points") or retry:
                messages = ([retry["message"]] if retry else []) + ([feedback["next_step"]] if feedback.get("next_step") else [])
                actions.append({**ref, "action": "practice_again", "category": retry["category"] if retry else "knowledge",
                                "focus_points": feedback.get("focus_points", []), "message": " ".join(messages)})
    strengths, priorities = [], []
    for (subject, language, point), entries in groups.items():
        statuses = {item["status"] for item, _ in entries}
        if statuses == {"met"}:
            status = "met"
        elif "met" in statuses:
            status = "inconsistent"
        else:
            status = min(statuses, key=lambda value: PRIORITY.get(value, 9))
        item, _ = entries[0]
        message = TEXT.get(language, TEXT["vi"])[status].format(point=point)
        result = {"subject": subject, "point": point, "status": status, "message": message,
                  "answers": [ref for _, ref in entries], "source": item["source"]}
        (strengths if status == "met" else priorities).append(result)
    priorities.sort(key=lambda item: (PRIORITY[item["status"]], -len(item["answers"])))
    priority_by_answer = {}
    for item in priorities:
        for ref in item["answers"]:
            priority_by_answer[ref["answer_id"]] = min(priority_by_answer.get(ref["answer_id"], 9), PRIORITY[item["status"]])
    actions.sort(key=lambda item: (0 if item["category"] == "system" else 1 if item["category"] == "audio"
                                   else 2 if item["category"] == "grading" else 3,
                                   priority_by_answer.get(item["answer_id"], 9), item["sequence_number"]))
    return {"schema_version": VERSION, "scope": "this_session_only", "strengths": strengths[:5],
            "priorities": priorities[:5], "next_steps": actions,
            "unverified_answer_count": sum(any(item["status"] == "unresolved"
                for item in answer["evaluation"].get("learning_feedback", {}).get("items", []))
                for answer in answers)}
