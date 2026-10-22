"""Source-grounded rule and preparation tests, not independent model accuracy."""
import asyncio
import hashlib
import json

import httpx
import pytest

from app.services import evaluator
from app.services.course_verifier import check_course_point, parse_course_fact
from app.services.fact_guard import check_rubric_point
from app.services.rubric_guidance import grading_guidance
from tools.prepare_course_grading import check_rule_cases, contrastive_cases, prepare


CASES = [
    ("DSA101", "Stack hoạt động theo nguyên tắc vào sau ra trước (LIFO)",
     "Ngăn xếp theo LIFO.", "Stack theo FIFO."),
    ("DB101", "Giá trị khóa chính không được NULL",
     "Khóa chính không được NULL.", "Khóa chính cho phép NULL."),
    ("OOP101", "Lớp con thừa hưởng thuộc tính và phương thức của lớp cha",
     "Lớp con nhận thuộc tính và phương thức từ lớp cha.",
     "Lớp cha thừa hưởng thuộc tính và phương thức của lớp con."),
    ("AI101", "Tham số được cập nhật theo hướng ngược với gradient",
     "Tham số cập nhật theo hướng ngược với gradient.", "Tham số được cập nhật theo hướng cùng với gradient."),
]


@pytest.mark.parametrize("subject,point,correct,wrong", CASES)
def test_course_relations_accept_equivalents_and_reject_wrong_values(subject, point, correct, wrong):
    assert check_course_point(correct, point).status == "supported"
    assert check_course_point(wrong, point).status == "contradicted"
    result = check_course_point(correct + " " + wrong, point)
    assert result.status == "conflicted"
    assert result.verification_rule.startswith("course-facts-v1:")
    assert result.evidence in correct + " " + wrong


@pytest.mark.parametrize("point,answer", [
    ("A stack uses LIFO", "Stack uses FIFO."),
    ("Primary key cannot be NULL", "Primary key can be NULL."),
    ("Child class inherits attributes and methods from parent class", "Parent class inherits attributes and methods from child class."),
    ("Parameters are updated in the opposite gradient direction", "Parameters are updated in the same gradient direction."),
])
def test_english_closed_forms(point, answer):
    assert check_course_point(answer, point).status == "contradicted"


@pytest.mark.parametrize("answer", [
    "Nếu stack theo FIFO thì sao?", '"Stack theo LIFO" là sai.',
    "Stack theo LIFO nhưng phát biểu này sai.", "LIFO, FIFO, stack, queue.",
    "Stack có thể theo LIFO trong một số trường hợp.", "Stack theo LIFO (FIFO).",
])
def test_fragments_keywords_quotations_and_conditions_never_receive_rule_credit(answer):
    assert check_course_point(answer, "Stack theo LIFO").status != "supported"


def test_rule_uses_reference_not_a_hardcoded_stack_answer():
    assert check_course_point("Queue theo LIFO.", "Queue theo LIFO").status == "supported"
    assert check_course_point("Stack theo LIFO.", "Queue theo FIFO").status == "unknown"
    assert check_course_point("Stack theo LIFO.", "Stack theo LIFO và queue theo FIFO").status == "unknown"


def test_unparsed_same_subject_tail_cannot_be_silently_discarded():
    result = check_course_point("Stack theo LIFO. Stack có thể lấy phần tử đầu tiên.", "Stack theo LIFO")
    assert result.status == "conflicted"


@pytest.mark.parametrize("subject,point,correct,wrong", CASES)
def test_complete_course_fact_can_be_graded_without_loading_an_llm(test_settings, monkeypatch, subject, point, correct, wrong):
    test_settings.evaluator_mode = "auto"
    question = {"question": "Giải thích kiến thức đã học", "reference_answer": point,
                "key_points": [point], "language": "vi", "subject": subject}
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", lambda *_, **__:
                        pytest.fail("A complete formal relation needs no Transformer"))
    async def no_llm(*_, **__):
        pytest.fail("A complete formal relation needs no LLM")
    monkeypatch.setattr(evaluator, "evaluate_with_ollama", no_llm)
    good = asyncio.run(evaluator.evaluate_answer(test_settings, question, correct))
    bad = asyncio.run(evaluator.evaluate_answer(test_settings, question, wrong))
    assert good["score"] == 100 and not good["score_provisional"]
    assert bad["score"] == 0 and not bad["score_provisional"]
    assert good["point_assessments"][0]["evidence_quote"] in correct
    assert good["point_assessments"][0]["reference_quote"] == point


def test_stack_and_queue_earn_independent_weights(test_settings):
    points = ["Stack theo LIFO", "Queue theo FIFO"]
    question = {"question": "Phân biệt stack và queue", "reference_answer": "; ".join(points),
                "key_points": points, "key_point_weights": {points[0]: 3, points[1]: 1}}
    result = asyncio.run(evaluator.evaluate_answer(test_settings, question, "Ngăn xếp theo LIFO. Hàng đợi theo LIFO."))
    assert result["score"] == 75
    assert result["matched_points"] == [points[0]]
    assert result["contradicted_points"] == [points[1]]


def test_guidance_preserves_compound_meaning_and_source():
    question = {"question": "Phân biệt", "key_points": ["Stack theo LIFO", "A và B đều phải có"]}
    result = grading_guidance(question)
    assert not result["changes_weights"] and result["approval_status"] == "derived_hints_not_teacher_approval"
    assert [c["source_quote"] for c in result["criteria"]] == question["key_points"]
    assert result["criteria"][0]["accepted_expression_examples"]
    assert result["criteria"][1]["possible_compound"]
    assert result["criteria"][1]["verification"] is None
    assert result["criteria"][1]["accepted_expression_examples"] == []


@pytest.mark.parametrize("language,question_id,answer,expected", [
    ("vi", "Q_DSA_008", "Ngăn xếp theo LIFO.", "supported"),
    ("vi", "Q_DSA_008", "Stack theo FIFO.", "contradicted"),
    ("vi", "Q_DSA_009", "Hàng đợi theo FIFO.", "supported"),
    ("en", "Q_DSA_008", "A stack uses LIFO.", "supported"),
    ("en", "Q_DSA_008", "Stack uses FIFO.", "contradicted"),
    ("vi", "Q_OOP2_001", "Lớp con thừa hưởng thuộc tính và phương thức của lớp cha.", "supported"),
    ("vi", "Q_OOP2_001", "Lớp cha thừa hưởng thuộc tính và phương thức của lớp con.", "contradicted"),
])
def test_closed_rules_match_real_banks_not_only_training_wording(project_root, language, question_id, answer, expected):
    bank = json.loads((project_root / "data" / f"question_bank_{language}.json").read_text(encoding="utf-8"))
    question = next(q for q in bank if q["id"] == question_id)
    assert check_course_point(answer, question["key_points"][0]).status == expected


def test_contradictory_abbreviation_is_not_normalized_away():
    assert parse_course_fact("Stack theo LIFO (First In, First Out)") is None
    assert parse_course_fact("Stack hoạt động theo nguyên lý LIFO: phần tử thêm vào đầu tiên được lấy ra đầu tiên") is None


def test_llm_receives_compact_exact_student_clauses_not_duplicated_guidance(test_settings, tmp_path, monkeypatch):
    test_settings.rubric_transformer_path = tmp_path / "absent"
    point = "Stack theo LIFO"
    question = {"question": "Giải thích stack", "reference_answer": point, "key_points": [point]}
    answer = "Theo em thì stack hoạt động theo thứ tự đó."
    def respond(request):
        data = json.loads(json.loads(request.content)["messages"][1]["content"])
        assert data["candidate_statements"][0]["text"] == answer.rstrip(".")
        assert data["candidate_statements"][0]["id"] == "s1"
        assert data["rubric_points"] == [point]
        assert "criterion_guidance" not in data and "reference_answer" not in data
        return httpx.Response(200, json={"message": {"content": json.dumps({"confidence": .9,
            "point_assessments": [{"point": point, "status": "unresolved", "evidence_ids": []}]})}})
    actual = httpx.AsyncClient
    monkeypatch.setattr(evaluator.httpx, "AsyncClient", lambda **kwargs:
                        actual(transport=httpx.MockTransport(respond), **kwargs))
    result = asyncio.run(evaluator.evaluate_with_ollama(test_settings, question, answer))
    assert result["score_provisional"]


def test_contrastive_groups_are_traceable_and_do_not_leak_variants_across_splits(project_root):
    cases = contrastive_cases(project_root / "data" / "rubricguard_training")
    assert len(cases) > 300
    assert {c["question"]["subject_code"] for c in cases} == {c[0] for c in CASES}
    groups = {}
    for case in cases:
        groups.setdefault(case["group_id"], set()).add(case["split"])
        source = project_root / "data" / "rubricguard_training" / case["source"]["file"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == case["source"]["sha256"]
        assert not case["independent_student_accuracy_benchmark"]
        assert not case["independently_teacher_validated"]
        assert set(case["expected_relations"]) == set(case["question"]["key_points"])
        low, high = case["expected_score_range"]
        assert 0 <= low <= high <= 100
    assert len(groups) == 40 and all(len(splits) == 1 for splits in groups.values())


def test_preparation_never_publishes_rubrics_or_overwrites_history(project_root, tmp_path):
    result = prepare(project_root, tmp_path / "prepared")
    assert result["rubric_drafts"] == 1800 and result["auto_approved_count"] == 0
    assert not result["database_modified"] and not result["training_performed"]
    assert not result["external_knowledge_added"]
    drafts = json.loads((tmp_path / "prepared" / "rubric_drafts.json").read_text(encoding="utf-8"))
    assert all(d["status"] == "draft_not_approved" for d in drafts)
    rule_report = json.loads((tmp_path / "prepared" / "rule_regressions.json").read_text(encoding="utf-8"))
    assert rule_report["counts"]["mismatches"] == 0
    assert result["closed_form_criteria"] > 0
    with pytest.raises(ValueError, match="never overwritten"):
        prepare(project_root, tmp_path / "prepared")


def test_generated_rule_regressions_report_abstentions_not_fake_accuracy(project_root):
    cases = contrastive_cases(project_root / "data" / "rubricguard_training")
    report = check_rule_cases(cases)
    counts = report["counts"]
    assert counts["mismatches"] == 0 and not report["failures"]
    assert counts["rule_resolved"] > 0 and counts["rule_abstained"] > 0
    assert counts["point_checks"] == counts["rule_resolved"] + counts["rule_abstained"] + counts["deferred_to_semantic_audit"]
    assert not report["independent_student_accuracy_benchmark"]
