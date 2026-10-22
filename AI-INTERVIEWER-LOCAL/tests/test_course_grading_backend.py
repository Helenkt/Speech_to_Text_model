import asyncio
import json

import httpx
import pytest

from app.services import evaluator
from app.services.fact_guard import check_rubric_point


@pytest.mark.parametrize("point", [
    "Stack là cấu trúc LIFO", "Khóa chính là định danh duy nhất",
    "Lớp là khuôn mẫu", "Gradient descent là phương pháp tối ưu",
])
def test_direct_negation_is_scoped_to_one_course_point(point):
    question = {"question": "Giải thích khái niệm", "reference_answer": point, "key_points": [point]}
    negative = point.replace(" là ", " không phải là ")
    assert check_rubric_point(question, negative, point).status == "contradicted"
    assert check_rubric_point(question, f"Phát biểu '{negative}' là sai. {point}.", point).status == "supported"
    assert check_rubric_point(question, f"Nếu {negative} thì sao?", point).status == "unknown"


def test_one_wrong_point_does_not_erase_other_correct_points(test_settings, monkeypatch):
    test_settings.evaluator_mode = "ollama"
    points = ["Lớp là khuôn mẫu", "Đối tượng là thể hiện cụ thể"]
    question = {"question": "Lớp và đối tượng khác nhau thế nào?", "language": "vi",
                "reference_answer": "; ".join(points), "key_points": points}

    async def llm(_settings, pending, answer):
        assert pending["key_points"] == [points[1]]
        return evaluator._coerce_llm_result({"confidence": 0.9, "point_assessments": [
            {"point": points[1], "status": "met", "evidence_quote": "Đối tượng là thể hiện cụ thể"}]},
            pending, "test", answer)

    monkeypatch.setattr(evaluator, "evaluate_with_ollama", llm)
    answer = "Lớp không phải là khuôn mẫu. Đối tượng là thể hiện cụ thể của lớp."
    result = asyncio.run(evaluator.evaluate_answer(test_settings, question, answer))
    assert result["score"] == 50
    assert result["contradicted_points"] == [points[0]]
    assert result["matched_points"] == [points[1]]


def test_numeric_rules_do_not_reward_unrelated_course_point():
    question = {"question": "Bộ nhớ A có 2 TB, B có 1 TB. So sánh và giải thích index.",
                "reference_answer": "A lớn hơn B. Index tăng tốc truy vấn.",
                "key_points": ["A lớn hơn B", "Index tăng tốc truy vấn"]}
    assert check_rubric_point(question, "B nhỏ hơn A.", question["key_points"][0]).status == "supported"
    assert check_rubric_point(question, "B nhỏ hơn A.", question["key_points"][1]).status == "unknown"
    assert check_rubric_point(question, "A lớn hơn B. B lớn hơn A.", question["key_points"][0]).status == "conflicted"


def test_comparison_negation_is_not_a_strict_inverse():
    question = {"question": "A có 2 GB, B có 2 GB.", "reference_answer": "A bằng B", "key_points": ["A bằng B"]}
    assert check_rubric_point(question, "A không lớn hơn B.", "A bằng B").status == "supported"
    question["question"] = "A có 3 GB, B có 2 GB."
    assert check_rubric_point(question, "A không lớn hơn B.", "A lớn hơn B").status == "contradicted"


def test_duplicate_llm_points_are_rejected():
    item = {"point": "P", "status": "missing", "evidence_quote": ""}
    with pytest.raises(ValueError, match="duplicate"):
        evaluator._coerce_llm_result({"point_assessments": [item, item]}, {"key_points": ["P"]}, "test", "answer")


def test_course_regressions_cover_all_four_supplied_subjects(project_root):
    from tools.course_regressions import course_cases
    cases = course_cases(project_root / "data" / "rubricguard_training")
    assert len(cases) == 20
    assert {case["question"]["subject_code"] for case in cases} == {"AI101", "DB101", "DSA101", "OOP101"}
    assert all(case["source"]["question_id"] for case in cases)


def test_terminology_hints_are_traceable_to_supplied_data(project_root):
    terms = json.loads((project_root / "data" / "grading_terminology.json").read_text(encoding="utf-8"))["terms"]
    for term in terms:
        rows = json.loads((project_root / "data" / "rubricguard_training" / term["source"]).read_text(encoding="utf-8"))
        source = json.dumps([row for row in rows if row["question_id"] == term["question_id"]], ensure_ascii=False).casefold()
        assert all(alias.casefold() in source for alias in term["aliases"])
        assert term["canonical"].casefold() in source


def test_complete_assertion_not_substring_or_keyword_overlap():
    question = {"question": "Lớp là gì?", "reference_answer": "Lớp là khuôn mẫu", "key_points": ["Lớp là khuôn mẫu"]}
    assert check_rubric_point(question, "Lớp là khuôn mẫu.", "Lớp là khuôn mẫu").status == "supported"
    for answer in ("Khuôn mẫu là lớp.", "Tôi nghĩ sai khi nói lớp là khuôn mẫu.",
                   "Lớp là khuôn mẫu nhưng nhận định này là sai.", "Nếu lớp là khuôn mẫu thì sao?"):
        assert check_rubric_point(question, answer, "Lớp là khuôn mẫu").status == "unknown"


def test_however_prefix_keeps_a_correct_independent_assertion():
    point = "Đối tượng là thể hiện cụ thể"
    question = {"question": "Giải thích", "reference_answer": point, "key_points": [point]}
    assert check_rubric_point(question, f"Em không nhớ phần khác. Tuy nhiên {point} của lớp.", point).status == "supported"


def test_disagreement_on_evidence_blocks_automatic_credit(test_settings, tmp_path, monkeypatch):
    test_settings.rubric_transformer_path = tmp_path
    (tmp_path / "tokenizer.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", lambda *_args, **_kwargs: {
        "point_assessments": [{"probabilities": {"entailment": 0.05, "neutral": 0.04, "contradiction": 0.91}}]})
    question = {"key_points": ["Lớp là khuôn mẫu"]}
    result = evaluator._coerce_llm_result({"confidence": 0.99, "point_assessments": [
        {"point": "Lớp là khuôn mẫu", "status": "met", "evidence_quote": "Đối tượng là khuôn mẫu"}]},
        question, "test", "Đối tượng là khuôn mẫu.")
    verified = asyncio.run(evaluator._verify_llm_evidence(test_settings, question, result))
    assert verified["score"] == 0
    assert verified["review_required"] is True
    assert verified["score_provisional"] is True


def test_inconsistent_assertions_cannot_be_automatically_finalized(test_settings):
    question = {"question": "Lớp là gì?", "reference_answer": "Lớp là khuôn mẫu", "key_points": ["Lớp là khuôn mẫu"]}
    result = asyncio.run(evaluator.evaluate_answer(test_settings, question,
                        "Lớp là khuôn mẫu. Lớp không phải là khuôn mẫu."))
    assert result["review_required"] is True
    assert result["score_provisional"] is True
    assert result["point_assessments"][0]["status"] == "unresolved"


def test_llm_generation_is_bounded_and_truncation_is_not_graded(test_settings, monkeypatch):
    question = {"language": "vi", "question": "Stack là gì?", "reference_answer": "Stack là LIFO",
                "key_points": ["Stack là LIFO"]}

    def respond(request):
        payload = json.loads(request.content)
        assert payload["options"]["num_predict"] <= 1536
        assert payload["options"]["temperature"] == 0
        schema = payload["format"]["properties"]["point_assessments"]
        assert schema["minItems"] == schema["maxItems"] == 1
        return httpx.Response(200, json={"done_reason": "length", "message": {"content": "{}"}})

    actual_client = httpx.AsyncClient
    monkeypatch.setattr(evaluator.httpx, "AsyncClient", lambda **kwargs:
                        actual_client(transport=httpx.MockTransport(respond), **kwargs))
    with pytest.raises(ValueError, match="token budget"):
        asyncio.run(evaluator.evaluate_with_ollama(test_settings, question, "Stack là LIFO."))
