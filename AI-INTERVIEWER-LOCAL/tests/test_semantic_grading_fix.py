"""Backend contracts only; real-model observations live in the rehearsal reports."""
import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app.services import evaluator
from app.services.course_verifier import check_course_point
from app.services.grading_semantics import requires_semantic_audit
from app.services.llm_response import ModelResponseError, validate_point_decisions


POINTS = ["A required idea", "Another independent idea"]
QUESTION = {"question": "Explain both", "reference_answer": "; ".join(POINTS),
            "key_points": POINTS, "language": "en"}


def test_low_self_confidence_does_not_discard_a_separately_evidenced_point():
    result = evaluator._coerce_llm_result({"confidence": 0, "point_assessments": [
        {"point": POINTS[0], "status": "met", "evidence_quote": "Actual equivalent explanation"},
        {"point": POINTS[1], "status": "missing"}]}, QUESTION, "test", "Actual equivalent explanation.")
    assert result["score"] == 50 and not result["score_provisional"]
    assert result["confidence_source"] == "uncalibrated_model_self_report"


@pytest.mark.parametrize("probabilities,blocked", [
    ({"entailment": .12, "neutral": .85, "contradiction": .03}, True),
    ({"entailment": .05, "neutral": .04, "contradiction": .91}, True),
    ({"entailment": .95, "neutral": .03, "contradiction": .02}, False),
])
def test_weak_evidence_is_not_a_final_wrong_answer_and_strong_support_can_finalize(
        test_settings, tmp_path, monkeypatch, probabilities, blocked):
    test_settings.rubric_transformer_path = tmp_path
    (tmp_path / "tokenizer.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", lambda *_args, **_kwargs: {
        "point_assessments": [{"probabilities": probabilities}]})
    question = {**QUESTION, "key_points": POINTS[:1]}
    result = evaluator._coerce_llm_result({"point_assessments": [
        {"point": POINTS[0], "status": "met", "evidence_quote": "A plain explanation"}]},
        question, "test", "A plain explanation.")
    checked = asyncio.run(evaluator._verify_llm_evidence(test_settings, question, result))
    assert checked["score_provisional"] is blocked
    assert checked["point_assessments"][0]["evidence_verification"]["probabilities"] == probabilities


def test_invalid_missing_label_is_isolated_not_silently_fixed_or_used_as_credit():
    data = {"point_assessments": [
        {"point": POINTS[0], "status": "met", "evidence_ids": ["s1"]},
        {"point": POINTS[1], "status": "missing", "evidence_ids": ["s2"]}]}
    statements = {"s1": "Correct meaning", "s2": "The opposite of the other idea"}
    result = validate_point_decisions(data, POINTS, statements, isolate_local_errors=True)
    assert [p["status"] for p in result["point_assessments"]] == ["met", "unresolved"]
    assert result["point_assessments"][1]["review_reason"] == "invalid_missing_evidence"
    with pytest.raises(ModelResponseError):
        validate_point_decisions(data, POINTS, statements)


@pytest.mark.parametrize("ids", [["invented"], ["s1", "s1"], [["s1"]]])
def test_local_recovery_never_accepts_invalid_evidence_ids(ids):
    with pytest.raises(ModelResponseError):
        validate_point_decisions({"point_assessments": [
            {"point": POINTS[0], "status": "met", "evidence_ids": ids}]},
            POINTS[:1], {"s1": "real words"}, isolate_local_errors=True)


def test_local_protocol_repair_is_bounded_and_can_recover_missing_without_an_nli_model(test_settings, tmp_path, monkeypatch):
    test_settings.rubric_transformer_path = tmp_path / "absent"
    calls = []
    def respond(request):
        payload = json.loads(request.content)
        body = json.loads(payload["messages"][1]["content"])
        calls.append(body)
        points = body["rubric_points"]
        if len(calls) == 1:
            items = [{"point": points[0], "status": "met", "evidence_ids": ["s1"]},
                     {"point": points[1], "status": "missing", "evidence_ids": ["s2"]}]
        else:
            assert points == POINTS[1:]
            items = [{"point": points[0], "status": "missing", "evidence_ids": []}]
        return httpx.Response(200, json={"message": {"content": json.dumps({"point_assessments": items})}})
    client = httpx.AsyncClient
    monkeypatch.setattr(evaluator.httpx, "AsyncClient", lambda **kw: client(transport=httpx.MockTransport(respond), **kw))
    result = asyncio.run(evaluator.evaluate_with_ollama(test_settings, QUESTION,
        "Correct first idea. I forgot the other idea."))
    assert len(calls) == 2 and result["score"] == 50 and not result["score_provisional"]
    assert result["evidence_repair_passes"] == 1


def test_failed_secondary_judge_cannot_publish_an_unverified_100_point_proposal(test_settings, monkeypatch):
    test_settings.evaluator_mode = "auto"
    monkeypatch.setattr(evaluator, "check_rubric_point", lambda *_: SimpleNamespace(status="unknown"))
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", lambda *_args, **_kwargs: {
        "score": 100, "confidence": .8, "review_required": True, "evaluator": "test",
        "point_assessments": [{"point": p, "status": "met", "needs_review": True} for p in POINTS]})
    async def failed(*_args, **_kwargs):
        raise ValueError("invalid wire response")
    monkeypatch.setattr(evaluator, "evaluate_with_ollama", failed)
    result = asyncio.run(evaluator.evaluate_answer(test_settings, QUESTION, "An unverified answer"))
    assert result["score"] == 0 and result["score_provisional"]
    assert result["matched_points"] == []
    assert all(p["status"] == "unresolved" for p in result["point_assessments"])


@pytest.mark.parametrize("answer,needs_audit", [
    ("NULL không phải số không hay chuỗi rỗng. Khi lọc không dùng bằng NULL.", False),
    ("Không phải stack không dùng LIFO.", True),
    ("It is not true that the stack does not use LIFO.", True),
    ("It is not true. The queue does not use LIFO.", False),
    ("Stack theo FIFO. Xin sửa lại: stack theo LIFO.", True),
])
def test_nested_negation_has_local_scope(answer, needs_audit):
    assert requires_semantic_audit(answer) is needs_audit


@pytest.mark.parametrize("answer,expected", [
    ("Em hiểu stack lấy cái vào đầu tiên ra trước.", "contradicted"),
    ("Theo em queue lấy phần tử vào sau ra trước.", "contradicted"),
    ("Em nghĩ lớp cha lấy lại các thuộc tính và phương thức từ lớp con.", "contradicted"),
])
def test_closed_relations_preserve_roles_and_order_in_natural_prefaces(answer, expected):
    point = "Queue theo FIFO" if "queue" in answer else (
        "Lớp con tái sử dụng thuộc tính/phương thức của lớp cha" if "lớp" in answer else "Stack theo LIFO")
    assert check_course_point(answer, point).status == expected


def test_an_independent_extension_idea_does_not_conflict_with_inheritance_direction():
    point = "Lớp con tái sử dụng thuộc tính/phương thức của lớp cha"
    answer = "Lớp con sử dụng lại thuộc tính và phương thức của lớp cha. Lớp con có thể thêm hành vi riêng."
    assert check_course_point(answer, point).status == "supported"
    assert check_course_point(answer + " Nhận định đó là sai.", point).status == "conflicted"


@pytest.mark.parametrize("answer,expected", [
    ("Push là thêm lên trên cùng, còn pop lấy cái trên cùng ra và bỏ nó khỏi chồng.", "supported"),
    ("Push để thêm phần tử lên đỉnh, pop lấy và xóa phần tử trên đỉnh.", "supported"),
    ("PUSH lấy từ đỉnh và POP thêm lên đỉnh.", "contradicted"),
    ("PUSH thêm vào đỉnh.", "unknown"),
    ("PUSH, POP, đỉnh, thêm, lấy.", "unknown"),
    ("PUSH thêm vào đỉnh và POP lấy ra từ đỉnh nhưng phát biểu này sai.", "unknown"),
])
def test_both_operations_require_full_scoped_meaning(answer, expected):
    point = "Hai thao tác cơ bản là PUSH (thêm vào đỉnh) và POP (lấy ra từ đỉnh)"
    assert check_course_point(answer, point).status == expected


@pytest.mark.parametrize("answer,expected", [
    ("Em nghĩ NULL chính là số 0.", "contradicted"),
    ("NULL là chuỗi rỗng, tức đã có một giá trị cụ thể.", "contradicted"),
    ("NULL là số không.", "contradicted"),
    ("NULL theo em là chuỗi rỗng, nhưng em chưa chắc điều đó.", "unknown"),
])
def test_null_value_comparison_is_not_keyword_coverage(answer, expected):
    assert check_course_point(answer, "NULL đại diện cho giá trị không xác định/chưa có dữ liệu").status == expected


def test_null_rule_compares_source_values_not_a_cached_expected_answer():
    assert check_course_point("NULL là số 0.", "NULL là số không").status == "supported"
    assert check_course_point("NULL là chuỗi rỗng.", "NULL là số không").status == "contradicted"


def test_implicit_order_does_not_silently_switch_queue_and_stack():
    point = "Stack theo LIFO"
    question = {"question": "Giải thích stack", "key_points": [point]}
    answer = "Theo em là phần tử mới bỏ vào sẽ được lấy ra trước, giống một chồng sách."
    assert check_course_point(answer, point, question=question).status == "supported"
    assert check_course_point("Queue theo FIFO. " + answer, point, question=question).status == "unknown"


def test_closed_absence_requires_accounting_for_every_candidate_clause():
    point = "Lớp con có thể bổ sung hoặc ghi đè hành vi riêng"
    answer = "Lớp con dùng lại thuộc tính và phương thức của lớp cha. Phần còn lại em chưa biết."
    assert check_course_point(answer, point).status == "missing"
    assert check_course_point(answer + " Nó còn tự viết lại cách chạy.", point).status == "unknown"
    assert check_course_point("Lớp con có thể bổ sung hoặc ghi đè hành vi riêng. " + answer, point).status == "supported"


def test_unremembered_operations_do_not_invalidate_a_correct_implicit_order(test_settings):
    points = ["Stack hoạt động theo nguyên lý LIFO: phần tử thêm vào sau cùng được lấy ra đầu tiên",
              "Hai thao tác cơ bản là PUSH (thêm vào đỉnh) và POP (lấy ra từ đỉnh)"]
    question = {"question": "Giải thích nguyên lý và hai thao tác Stack", "reference_answer": "; ".join(points),
                "key_points": points}
    answer = "Theo em là phần tử mới bỏ vào sẽ được lấy ra trước, giống một chồng sách. Hai thao tác tên gì thì em chưa nhớ."
    result = asyncio.run(evaluator.evaluate_answer(test_settings, question, answer))
    assert result["score"] == 50 and not result["score_provisional"]
    assert [p["status"] for p in result["point_assessments"]] == ["met", "missing"]


def test_partial_is_not_an_unverified_half_point_shortcut():
    result = evaluator._coerce_llm_result({"point_assessments": [
        {"point": POINTS[0], "status": "partial", "evidence_quote": "Some actual words"}]},
        {**QUESTION, "key_points": POINTS[:1]}, "test", "Some actual words.")
    assert result["score_provisional"] and result["point_assessments"][0]["status"] == "unresolved"


@pytest.mark.parametrize("value", [{}, {"entailment": 1},
    {"entailment": float("nan"), "neutral": 0, "contradiction": 0},
    {"entailment": .9, "neutral": .9, "contradiction": .1},
    {"entailment": True, "neutral": 0, "contradiction": 0}])
def test_invalid_verifier_probabilities_are_never_support(value):
    assert not evaluator._valid_evidence_probabilities(value)


def test_saved_calibration_is_not_bypassed_for_llm_evidence(test_settings, tmp_path, monkeypatch):
    test_settings.rubric_transformer_path = tmp_path
    (tmp_path / "tokenizer.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", lambda *_args, **_kwargs: {
        "acceptance_threshold": .95, "point_assessments": [
            {"probabilities": {"entailment": .93, "neutral": .05, "contradiction": .02}}]})
    question = {**QUESTION, "key_points": POINTS[:1]}
    result = evaluator._coerce_llm_result({"point_assessments": [
        {"point": POINTS[0], "status": "met", "evidence_quote": "A plain explanation"}]},
        question, "test", "A plain explanation.")
    checked = asyncio.run(evaluator._verify_llm_evidence(test_settings, question, result))
    assert checked["score_provisional"]
