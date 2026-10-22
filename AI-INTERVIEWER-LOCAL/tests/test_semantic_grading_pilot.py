import json
from pathlib import Path

import numpy as np
import pytest

from tools import semantic_grading_pilot as pilot


def row(question="q1", answer="student words", claim="required meaning", label=0):
    return {"question_id": question, "question": "What is the idea?",
            "student_answer": answer, "reference_claim": claim, "label": label}


def test_context_does_not_insert_correct_reference_into_student_premise():
    premise, hypothesis = pilot.input_pair(row(), True)
    assert "What is the idea?" in premise and "student words" in premise
    assert "required meaning" not in premise
    assert hypothesis == "required meaning"
    assert pilot.input_pair(row(), False) == ("student words", "required meaning")


@pytest.mark.parametrize("field", ["question_id", "student_answer", "reference_claim"])
def test_no_question_answer_or_claim_overlap(field):
    splits = {}
    for name in ("train", "validation", "test"):
        splits[name] = [row(name, f"{name} answer {i}", f"{name} claim {i}", i) for i in range(3)]
    pilot.check_splits(splits)
    splits["test"][0][field] = splits["train"][0][field]
    with pytest.raises(ValueError, match="leakage"):
        pilot.check_splits(splits)


def test_existing_experiment_is_never_overwritten(tmp_path):
    marker = tmp_path / "keep.txt"
    marker.write_text("untouched")
    with pytest.raises(FileExistsError):
        pilot.prepare(tmp_path)
    assert marker.read_text() == "untouched"


def test_corrupt_frozen_dataset_is_rejected(tmp_path):
    path = tmp_path / "dataset/test.json"
    path.parent.mkdir()
    path.write_text("[]")
    (tmp_path / "manifest.json").write_text(json.dumps({"splits": {"test": {"sha256": "invalid"}}}))
    with pytest.raises(ValueError, match="Frozen test"):
        pilot.read_split(tmp_path, "test")


def test_threshold_never_relaxed_below_existing_point91_and_uses_validation_only():
    truth = [0, 1, 2] * 10
    logits = np.eye(3)[truth] * 10
    policy = pilot.calibrate(logits, truth)
    assert policy["min_confidence"] >= .91
    assert policy["fitted_on"] == "frozen_validation_only"
    assert not policy["production_ready"]


def test_uninformative_logits_disable_acceptance():
    policy = pilot.calibrate(np.zeros((30, 3)), [0, 1, 2] * 10)
    assert policy["min_confidence"] > 1


def test_truncated_and_low_confidence_items_always_abstain():
    probabilities = np.asarray([[.999, .0005, .0005], [.7, .2, .1], [.001, .998, .001]])
    result = pilot.selective(probabilities, [2, 0, 1], .91, [True, False, False])
    assert result["accepted"] == 1
    assert result["wrong_claim_accepted_as_supported"] == 0


def test_declared_quarantine_and_split_balance_are_valid():
    path = Path(__file__).resolve().parents[1] / "data/semantic_pilot_v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assigned = [g["id"] for g in data["groups"]]
    assert len(assigned) == len(set(assigned))
    assert not set(assigned) & set(data["quarantined_questions"])
    assert not data["teacher_validated"]
    assert len([g for g in data["groups"] if g["split"] == "test"]) == 8
