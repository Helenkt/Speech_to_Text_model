import asyncio
import copy
import json
from pathlib import Path

import pytest

from app.context.contracts import LABELS, decide, make_pair
from app.context.hybrid import reconcile
from app.context.model import ContextClassifier, ContextUnavailable, model_identity
from app.services.evaluator import _coerce_llm_result, _guard_evaluation, evaluate_answer
from scripts.context.prepare import prepare
from scripts.context.metrics import classification_metrics

Q = {"question": "Lớp là gì?", "reference_answer": "Lớp là khuôn mẫu.",
     "language": "vi", "key_points": ["Lớp là khuôn mẫu"]}
ANSWER = "Lớp là khuôn mẫu; tôi nói đây là một nhận định đúng."


def base():
    return _coerce_llm_result({"point_assessments": [{"point": Q["key_points"][0], "status": "met",
                             "evidence_quote": "Lớp là khuôn mẫu", "reason": "Đạt"}],
                             "confidence": 0.9}, Q, "test", ANSWER)


def prediction(label="met", demo=False):
    probabilities = {l: 0.01 for l in LABELS}
    probabilities[label] = 0.96
    return {**decide(probabilities, .85, .2), "point": Q["key_points"][0],
            "demo_only": demo, "model_version": "test"}


@pytest.mark.parametrize("answer", [
    "Em không biết tên tiếng Anh nhưng lớp là khuôn mẫu để tạo đối tượng.",
    "I don't know the name, but a class is a blueprint for objects.",
    "Tất cả đều sai, nhưng em xin đính chính: lớp là khuôn mẫu.",
])
def test_contextual_unknown_or_self_correction_is_not_zeroed_by_guard(answer):
    assert _guard_evaluation(Q, answer, evaluator="test") is None


def test_reference_quote_does_not_override_contradicted_llm_assessment():
    answer = '"Lớp là khuôn mẫu" là phát biểu tôi cho là sai.'
    result = _coerce_llm_result({"point_assessments": [{"point": Q["key_points"][0],
                               "status": "contradicted", "reason": "Bác bỏ", "evidence_quote": answer}],
                               "confidence": .9}, Q, "test", answer)
    assert result["score"] == 0
    assert result["contradicted_points"] == Q["key_points"]


def test_invalid_quote_never_awards_points_even_with_high_confidence():
    result = _coerce_llm_result({"point_assessments": [{"point": Q["key_points"][0], "status": "met",
                              "evidence_quote": "Lớp là khuôn mẫu"}], "confidence": 1}, Q, "test", "Em chỉ nói về du lịch.")
    assert result["score"] == 0
    assert result["review_required"]


def test_nonfinite_llm_confidence_requires_review():
    result = _coerce_llm_result({"confidence": float("nan")}, Q, "test", ANSWER)
    assert result["confidence"] == 0
    assert result["review_required"]


def test_low_margin_abstains_and_probability_validation():
    p = dict(zip(LABELS, [.48, .47, .02, .02, .01]))
    assert decide(p, .5, .2)["status"] == "uncertain"
    with pytest.raises(ValueError):
        decide({**p, "met": float("nan")}, .5, .2)


def test_shadow_keeps_score_but_flags_disagreement_and_persists_context():
    result = reconcile(base(), [prediction("contradicted")], ANSWER, "shadow")
    assert result["score"] == 100
    assert result["review_required"]
    assert result["point_assessments"][0]["context"]["status"] == "contradicted"


def test_hybrid_requires_agreement_and_never_finalizes_uncertainty():
    result = reconcile(base(), [prediction("contradicted")], ANSWER, "hybrid")
    assert result["score"] == 0  # provisional lower bound, not an automatic failing grade
    assert result["point_assessments"][0]["status"] == "uncertain"
    assert result["review_required"]
    agreed = reconcile(base(), [prediction()], ANSWER, "hybrid")
    assert agreed["score"] == 100
    assert not agreed["review_required"]
    demo = reconcile(base(), [prediction(demo=True)], ANSWER, "hybrid")
    assert demo["review_required"]


def test_rule_output_is_not_semantically_verified_by_transformer():
    output = base()
    output["evaluator"] = "rule-fallback"
    result = reconcile(output, [prediction()], ANSWER, "hybrid")
    assert result["review_required"]
    assert result["matched_points"] == []


def test_optional_failure_is_explicit_and_does_not_crash(test_settings, monkeypatch):
    test_settings.context_mode = "shadow"
    def fail(*args):
        raise ContextUnavailable("not installed")
    monkeypatch.setattr("app.context.model.predict_context", fail)
    result = asyncio.run(evaluate_answer(test_settings, Q, ANSWER))
    assert result["review_required"]
    assert result["evaluator"].endswith("context-unavailable")
    assert result["point_assessments"][0]["context"]["status"] == "unavailable"


def test_live_evaluation_calls_hybrid_and_retains_metadata(test_settings, monkeypatch):
    async def llm(*args):
        return base()
    monkeypatch.setattr("app.services.evaluator.evaluate_with_ollama", llm)
    monkeypatch.setattr("app.context.model.predict_context", lambda *a: [prediction("contradicted")])
    test_settings.evaluator_mode = "ollama"
    test_settings.context_mode = "hybrid"
    result = asyncio.run(evaluate_answer(test_settings, Q, ANSWER))
    assert result["review_required"]
    assert result["score"] == 0
    assert result["point_assessments"][0]["context"]["model_version"] == "test"


def test_prepared_splits_are_disjoint_and_have_all_training_labels(tmp_path, project_root):
    paths = sorted((project_root / "data/training/rubric_labels").glob("*.jsonl"))
    paths.append(project_root / "data/context/context_cases.draft.jsonl")
    report = prepare(paths, tmp_path, demo=True)
    assert report["rejected"] == []
    groups = []
    for name in ("train", "val", "test"):
        rows = [json.loads(x) for x in (tmp_path / f"{name}.jsonl").read_text().splitlines()]
        groups.append({r["group"] for r in rows})
    assert not groups[0] & groups[1]
    assert not groups[0] & groups[2]
    assert not groups[1] & groups[2]
    assert set(report["summary"]["train"]["labels"]) == set(LABELS)
    with pytest.raises(ValueError, match="Không có dữ liệu hợp lệ"):
        prepare(paths, tmp_path / "human-only", demo=False)


def test_pair_keeps_question_reference_and_answer_separate():
    teacher, student = make_pair("Q?", "Criterion", "Reference", "Student says reference is wrong")
    assert "Q?" in teacher and "Criterion" in teacher and "Reference" in teacher
    assert student.endswith("reference is wrong")
    assert "Student says" not in teacher


def test_metrics_exposes_false_credit():
    report = classification_metrics(["contradicted", "missing", "met"], ["met", "missing", "met"])
    assert report["false_met_on_wrong_rate"] == .5
    assert report["per_label"]["partial"]["support"] == 0
