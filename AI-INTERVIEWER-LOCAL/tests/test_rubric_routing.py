import asyncio
import hashlib
import json

import httpx

from app.services import evaluator, rubric_transformer


QUESTION = {"question": "Explain A and B", "reference_answer": "A claim and B claim",
            "language": "en", "key_points": ["A claim", "B claim"]}


def transformer_result():
    return {"score": 50, "confidence": 0.7, "review_required": True,
            "evaluator": "transformer:rubricguard-lite-v1",
            "point_assessments": [
                {"point": "A claim", "status": "met", "confidence": 0.96,
                 "needs_review": False, "reason": "supported", "evidence_quote": ""},
                {"point": "B claim", "status": "missing", "confidence": 0.6,
                 "needs_review": True, "reason": "uncertain", "evidence_quote": ""}]}


def test_llm_receives_only_unresolved_points_and_scores_are_merged(test_settings, monkeypatch):
    test_settings.evaluator_mode = "auto"
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", lambda *_args, **_kwargs: transformer_result())

    async def llm(_settings, question, answer):
        assert question["key_points"] == ["B claim"]
        assert answer == "A claim and B explanation"
        return {"confidence": 0.88, "review_required": False, "evaluator": "ollama:test",
                "feedback": "B supported", "point_assessments": [
                    {"point": "B claim", "status": "met", "reason": "supported", "evidence_quote": ""}]}

    monkeypatch.setattr(evaluator, "evaluate_with_ollama", llm)
    result = asyncio.run(evaluator.evaluate_answer(test_settings, QUESTION, "A claim and B explanation"))
    assert result["score"] == 100
    assert result["matched_points"] == QUESTION["key_points"]
    assert result["review_required"] is False
    assert result["evaluator"] == "hybrid:rubricguard+ollama:test"


def test_uncertain_points_remain_flagged_when_ollama_is_unavailable(test_settings, monkeypatch):
    test_settings.evaluator_mode = "auto"
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", lambda *_args, **_kwargs: transformer_result())

    async def offline(*_args):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(evaluator, "evaluate_with_ollama", offline)
    result = asyncio.run(evaluator.evaluate_answer(test_settings, QUESTION, "A claim and B explanation"))
    assert result["review_required"] is True
    assert result["evaluator"] == "model-pending"
    assert result["point_assessments"][0]["status"] == "met"
    assert result["point_assessments"][1]["status"] == "unresolved"


def test_confident_complete_answer_does_not_call_ollama(test_settings, monkeypatch):
    test_settings.evaluator_mode = "auto"
    complete = transformer_result()
    complete["review_required"] = False
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", lambda *_args, **_kwargs: complete)

    async def unexpected_call(*_args):
        raise AssertionError("Confident answer should be graded locally")

    monkeypatch.setattr(evaluator, "evaluate_with_ollama", unexpected_call)
    assert asyncio.run(evaluator.evaluate_answer(test_settings, QUESTION, "A claim and B explanation")) == complete


def test_selective_gate_requires_success_on_held_out_confident_predictions(tmp_path, monkeypatch):
    acceptance = {"accepted": 15, "accuracy": 1.0, "wrong_answers_accepted_as_met": 0}
    summary = {"runtime_evaluated": True, "model_stage": "fine_tuned_candidate",
               "validation_macro_f1": 0.81, "contradiction_recall": 0.73,
               "calibration": {"min_confidence": 0.91,
                   "validation_acceptance": acceptance, "test_acceptance": acceptance}}
    path = tmp_path / "training_summary.json"
    path.write_text(json.dumps(summary), encoding="utf-8")
    monkeypatch.setattr(rubric_transformer, "_verified_runtime", lambda *_args: True)
    quality = rubric_transformer._quality_metadata(tmp_path)
    assert quality["production_ready"] is False
    assert quality["selective_ready"] is True
    summary["calibration"]["test_acceptance"] = {**acceptance, "accuracy": 0.8}
    path.write_text(json.dumps(summary), encoding="utf-8")
    assert rubric_transformer._quality_metadata(tmp_path)["selective_ready"] is False


def test_quality_report_cannot_be_reused_for_different_weights(tmp_path):
    model = tmp_path / "model.int8.onnx"
    model.write_bytes(b"weights-v1")
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    calibration = {"temperature": 2.3, "min_confidence": 0.91}
    (tmp_path / "runtime_evaluation.json").write_text(json.dumps({"model_sha256": digest}), encoding="utf-8")
    (tmp_path / "calibration.json").write_text(json.dumps(calibration), encoding="utf-8")
    summary = {"runtime_evaluated": True, "model_sha256": digest, "calibration": calibration}
    assert rubric_transformer._verified_runtime(tmp_path, summary) is True
    model.write_bytes(b"different-weights-v2")
    assert rubric_transformer._verified_runtime(tmp_path, summary) is False
