import json
from types import SimpleNamespace

import numpy as np

from app.services import rubric_transformer as module


QUESTION = {"language": "vi", "question": "Lớp là gì?",
            "reference_answer": "Lớp là khuôn mẫu", "key_points": ["Lớp là khuôn mẫu"]}


def fake_backend(monkeypatch, logits, *, overflowing=False):
    class Session:
        def get_inputs(self):
            return [SimpleNamespace(name="input_ids"), SimpleNamespace(name="attention_mask")]

        def run(self, *_args):
            return [np.array([logits], dtype=np.float32)]

    class Tokenizer:
        def encode_batch(self, _pairs):
            return [SimpleNamespace(ids=[0, 1], attention_mask=[1, 1],
                                    overflowing=[object()] if overflowing else [])]

    monkeypatch.setattr(module, "_load", lambda _path:
        (Session(), Tokenizer(), {"0": "entailment", "1": "neutral", "2": "contradiction"}))
    monkeypatch.setattr(module, "_quality_metadata", lambda _path: {"production_ready": True})


def test_repeated_keyword_does_not_override_transformer_contradiction(monkeypatch, tmp_path):
    fake_backend(monkeypatch, [-3, -3, 5])
    result = module.evaluate_with_transformer(tmp_path, QUESTION, "Sai khi nói: Lớp là khuôn mẫu.")
    assert result["score"] == 0
    assert result["contradicted_points"] == QUESTION["key_points"]


def test_uncertain_prediction_is_reviewed_without_inventing_half_credit(monkeypatch, tmp_path):
    fake_backend(monkeypatch, [0.2, 0.1, 0.0])
    result = module.evaluate_with_transformer(tmp_path, QUESTION, "Một cấu trúc nào đó.")
    assert result["review_required"] is True
    assert result["partial_points"] == []
    assert result["confidence"] < 0.5


def test_truncated_answer_cannot_be_automatically_accepted(monkeypatch, tmp_path):
    fake_backend(monkeypatch, [5, -3, -3], overflowing=True)
    assert module.evaluate_with_transformer(tmp_path, QUESTION, "câu trả lời dài")["review_required"] is True


def test_invalid_calibration_requires_secondary_review(monkeypatch, tmp_path):
    fake_backend(monkeypatch, [5, -3, -3])
    (tmp_path / "calibration.json").write_text('{"temperature": -1, "min_confidence": 0}', encoding="utf-8")
    assert module.evaluate_with_transformer(tmp_path, QUESTION, "Đúng.")["review_required"] is True


def test_fp32_validation_alone_does_not_enable_int8_automatic_grading(tmp_path):
    (tmp_path / "training_summary.json").write_text(json.dumps({
        "validation_macro_f1": 1, "contradiction_recall": 1,
        "test": {"macro_f1": 1, "contradiction_recall": 1, "false_met_on_wrong": 0}
    }), encoding="utf-8")
    assert module._quality_metadata(tmp_path)["production_ready"] is False


def test_unvalidated_language_uses_secondary_grader(monkeypatch, tmp_path):
    fake_backend(monkeypatch, [5, -3, -3])
    result = module.evaluate_with_transformer(tmp_path, {**QUESTION, "language": "en"}, "A class is a blueprint.")
    assert result["review_required"] is True
