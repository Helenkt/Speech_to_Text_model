import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from app.services import rubric_transformer as runtime
from app.services import specialist_grader as specialist
from app.services.fact_guard import FactCheck
from tools import specialist_grading as cli


QUESTION = {"question": "What does the system do?", "language": "en", "subject": "AI101",
            "key_points": ["It learns patterns from data.", "It improves a task with experience."],
            "key_point_weights": {"It learns patterns from data.": 3, "It improves a task with experience.": 1}}


@pytest.fixture
def model_dir(tmp_path):
    path = tmp_path / "model"
    path.mkdir()
    (path / "model.int8.onnx").write_bytes(b"test fixture, not an actual model")
    (path / "tokenizer.json").write_text("{}", encoding="utf-8")
    (path / "config.json").write_text(json.dumps({
        "id2label": {"0": "entailment", "1": "neutral", "2": "contradiction"},
        "rubric_max_length": 192}), encoding="utf-8")
    return path


@pytest.fixture
def grader(model_dir, monkeypatch):
    monkeypatch.setattr(specialist, "check_rubric_point", lambda *args: FactCheck("unknown", 0))
    return specialist.SpecialistGrader(model_dir, specialist.freeze_candidate(model_dir))


def prediction(label="entailment", truncated=False):
    return {"probabilities": {name: .98 if name == label else .01 for name in specialist.NLI_LABELS},
            "truncated": truncated, "token_count": 10}


def mock_predictions(monkeypatch, *rows):
    monkeypatch.setattr(specialist, "predict_nli_pairs", lambda *_: list(rows))


def test_manifest_freezes_weights_tokenizer_and_config(model_dir):
    manifest = specialist.freeze_candidate(model_dir)
    assert set(manifest["files"]) == specialist.REQUIRED_FILES
    assert manifest["production_ready"] is False
    assert manifest["input_format"] == specialist.INPUT_FORMAT
    assert manifest == specialist.freeze_candidate(model_dir)


@pytest.mark.parametrize("field,value", [("production_ready", True), ("input_format", "other"),
                                        ("artifact_sha256", "forged")])
def test_manifest_tampering_is_rejected(model_dir, field, value):
    manifest = specialist.freeze_candidate(model_dir)
    manifest[field] = value
    with pytest.raises(ValueError, match="manifest"):
        specialist.SpecialistGrader(model_dir, manifest)


@pytest.mark.parametrize("filename", sorted(specialist.REQUIRED_FILES))
def test_runtime_file_change_requires_new_candidate(model_dir, filename):
    grader = specialist.SpecialistGrader(model_dir, specialist.freeze_candidate(model_dir))
    with (model_dir / filename).open("ab") as handle:
        handle.write(b" ")
    with pytest.raises(ValueError, match="Runtime changed"):
        grader.grade(QUESTION, "An answer")


def test_question_aware_checkpoint_is_not_used_as_answer_only(model_dir):
    config = json.loads((model_dir / "config.json").read_text())
    config["rubric_input_format"] = "question_answer_pair_v1"
    (model_dir / "config.json").write_text(json.dumps(config))
    with pytest.raises(ValueError, match="different input contract"):
        specialist.freeze_candidate(model_dir)


def test_weighted_proposal_is_never_a_real_grade(grader, monkeypatch):
    mock_predictions(monkeypatch, prediction(), prediction("contradiction"))
    result = grader.grade(QUESTION, "The answer in my own words.")
    assert result["proposed_score"] == 75
    assert result["final_score"] is None and result["production_ready"] is False
    assert result["rule_resolved_score_interval"] == [0, 100]
    assert result["review_required"] and not result["used_llm"]
    assert not result["trained_during_grading"] and not result["changes_final_grade"]
    assert all(p["status"] == "unresolved" for p in result["point_assessments"])


def test_neutral_is_not_missing_or_half_credit(grader, monkeypatch):
    mock_predictions(monkeypatch, prediction("neutral"), prediction())
    result = grader.grade(QUESTION, "Something about data.")
    assert result["proposed_score"] is None
    point = result["point_assessments"][0]
    assert point["suggested_status"] == point["status"] == "unresolved"
    assert point["reason"] == "neutral_is_not_proof_of_missing"


@pytest.mark.parametrize("answer,truncated,reason", [
    ("A long answer", True, "input_truncated"),
    ("I meant: I learn patterns from data.", False, "complex_assertion_scope"),
])
def test_truncation_and_correction_cannot_be_automatically_scored(grader, monkeypatch, answer, truncated, reason):
    mock_predictions(monkeypatch, prediction(truncated=truncated), prediction())
    result = grader.grade(QUESTION, answer)
    assert result["proposed_score"] is None
    assert result["point_assessments"][0]["reason"] == reason


def test_closed_contradiction_overrides_keyword_or_model_guess(grader, monkeypatch):
    monkeypatch.setattr(specialist, "check_rubric_point", lambda *args:
        FactCheck("contradicted", .99, "A closed relation was reversed", "data"))
    monkeypatch.setattr(specialist, "predict_nli_pairs", lambda *_: pytest.fail("No model needed"))
    result = grader.grade(QUESTION, "data data data")
    assert result["proposed_score"] == 0
    assert result["rule_resolved_score_interval"] == [0, 0]
    assert all(p["status"] == "contradicted" for p in result["point_assessments"])


def test_conflicting_rule_cannot_be_overridden_by_model(grader, monkeypatch):
    monkeypatch.setattr(specialist, "check_rubric_point", lambda *args: FactCheck("conflicted", 0, "conflict"))
    monkeypatch.setattr(specialist, "predict_nli_pairs", lambda *_: pytest.fail("Do not overwrite a conflict"))
    result = grader.grade(QUESTION, "Two incompatible claims.")
    assert result["proposed_score"] is None


@pytest.mark.parametrize("weights", [{"typo": 1}, {p: True for p in QUESTION["key_points"]},
    {p: float("nan") for p in QUESTION["key_points"]}, {p: -1 for p in QUESTION["key_points"]}])
def test_invalid_weights_fail_before_inference(grader, weights):
    with pytest.raises(ValueError, match="Weights"):
        grader.grade({**QUESTION, "key_point_weights": weights}, "An answer")


def test_model_receives_only_transcript_and_claims(grader, monkeypatch):
    calls = []
    def predict(_directory, pairs):
        calls.extend(pairs)
        return [prediction() for _ in pairs]
    monkeypatch.setattr(specialist, "predict_nli_pairs", predict)
    question = {**QUESTION, "reference_answer": "SECRET_REFERENCE", "expected_label": "SECRET_LABEL"}
    result = grader.grade(question, "Original student text")
    assert calls == [("Original student text", p) for p in QUESTION["key_points"]]
    for point in result["point_assessments"]:
        assert "Original student text"[point["evidence_start"]:point["evidence_end"]] == point["evidence_quote"]


def test_invalid_probabilities_are_not_silently_graded(grader, monkeypatch):
    row = prediction()
    row["probabilities"]["entailment"] = float("nan")
    mock_predictions(monkeypatch, row, prediction())
    with pytest.raises(ValueError, match="probabilities"):
        grader.grade(QUESTION, "An answer")


def test_native_inference_batch_is_one_pair(monkeypatch, tmp_path):
    pairs_seen = []
    sizes = []
    class Tokenizer:
        def encode_batch(self, pairs):
            pairs_seen.extend(pairs)
            assert len(pairs) == 1
            return [SimpleNamespace(ids=[0, 1], attention_mask=[1, 1], overflowing=[])]
    class Session:
        def get_inputs(self):
            return [SimpleNamespace(name=name) for name in ("input_ids", "attention_mask")]
        def run(self, _, inputs):
            sizes.append(inputs["input_ids"].shape)
            return [np.array([[5, 0, -1]], dtype=np.float32)]
    monkeypatch.setattr(runtime, "_load", lambda _: (Session(), Tokenizer(),
        {"0": "entailment", "1": "neutral", "2": "contradiction"}))
    result = runtime.predict_nli_pairs(tmp_path, [("answer", "claim1"), ("answer", "claim2")])
    assert len(result) == 2 and sizes == [(1, 2), (1, 2)]
    assert len(pairs_seen) == 2


@pytest.mark.parametrize("pairs", [[], [("", "claim")], ["not a pair"], [("one",)], [("a", "b")] * 31])
def test_native_inference_rejects_invalid_pairs(pairs, tmp_path):
    with pytest.raises(ValueError, match="pairs"):
        runtime.predict_nli_pairs(tmp_path, pairs)


def test_regression_preparation_is_explicitly_not_human_gold():
    payload = cli.prepare_regression()
    assert payload["teacher_validated"] is False
    assert len(cli.validate_samples(payload)) == 28
    for sample in payload["samples"]:
        assert not set(sample["question"]) & {"draft_expected_relations", "labels"}


def test_duplicate_samples_or_changed_transcript_are_rejected():
    payload = cli.prepare_regression()
    payload["samples"].append(copy.deepcopy(payload["samples"][0]))
    with pytest.raises(ValueError, match="unique"):
        cli.validate_samples(payload)
    payload["samples"].pop()
    payload["samples"][0]["answer_hash"] = "incorrect"
    with pytest.raises(ValueError, match="hash mismatch"):
        cli.validate_samples(payload)


def test_outputs_are_append_only(tmp_path):
    output = tmp_path / "result.json"
    cli.write_new(output, {"old": True})
    with pytest.raises(FileExistsError):
        cli.write_new(output, {"new": True})
    assert json.loads(output.read_text()) == {"old": True}


def test_freezing_does_not_write_or_change_model(model_dir):
    before = {path.name: path.read_bytes() for path in model_dir.iterdir()}
    specialist.freeze_candidate(model_dir)
    assert before == {path.name: path.read_bytes() for path in model_dir.iterdir()}


def test_stale_rubric_snapshot_is_rejected(grader):
    question = {**QUESTION, "rubric_snapshot": {"contract": {"criteria": []}, "sha256": "forged"}}
    with pytest.raises(ValueError, match="snapshot"):
        grader.grade(question, "An answer")


def test_regression_variants_keep_the_same_question_group_and_real_subjects():
    samples = cli.prepare_regression()["samples"]
    by_id = {s["sample_id"]: s for s in samples}
    assert by_id["DSA_paraphrase"]["question"]["uid"] == by_id["DSA_wrong_order"]["question"]["uid"]
    assert by_id["new_AI_english"]["answer_language"] == "en"
    assert {s["question"]["subject"] for s in samples} == {"AI101", "DB101", "DSA101", "OOP101"}


def test_runner_does_not_pass_expected_labels_or_invoke_current_grader(tmp_path, monkeypatch):
    dataset = cli.prepare_regression()
    dataset["samples"] = dataset["samples"][:1]
    dataset_path, manifest_path = tmp_path / "input.json", tmp_path / "manifest.json"
    cli.write_new(dataset_path, dataset)
    cli.write_new(manifest_path, {"fixture": True})
    received = []
    class Grader:
        def __init__(self, *_):
            pass
        def grade(self, question, answer):
            received.append((question, answer))
            return {"latency_ms": 1, "nli_pair_count": 0, "point_assessments": [], "proposed_score": None}
    monkeypatch.setattr(cli, "SpecialistGrader", Grader)
    monkeypatch.setattr(cli, "release_transformer", lambda: None)
    import app.services.evaluator as current
    monkeypatch.setattr(current, "evaluate_answer", lambda *_: pytest.fail("No implicit old grader/LLM"))
    report = cli.run(SimpleNamespace(dataset=dataset_path, manifest=manifest_path, model_dir=tmp_path,
                                   compare_current=None))
    assert received == [(dataset["samples"][0]["question"], dataset["samples"][0]["answer"])]
    assert report["production_ready"] is False and "current_pipeline_comparison" not in report
