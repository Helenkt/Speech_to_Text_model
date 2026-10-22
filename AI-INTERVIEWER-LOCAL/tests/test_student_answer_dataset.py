import copy
import json

import pytest

from tools import student_answer_dataset as dataset


@pytest.fixture(scope="module")
def original_bundle(tmp_path_factory):
    path = tmp_path_factory.mktemp("answer-data") / "bundle"
    dataset.build(path)
    return path


@pytest.fixture
def editable_bundle(original_bundle, tmp_path):
    path = tmp_path / "bundle"
    path.mkdir()
    for name in ["manifest.json", *(f"{subject}.json" for subject in dataset.SUBJECTS)]:
        (path / name).write_bytes((original_bundle / name).read_bytes())
    return path


def load_payloads(path):
    return {subject: dataset.read_json(path / f"{subject}.json") for subject in dataset.SUBJECTS}


def save_payloads(path, payloads):
    for subject, payload in payloads.items():
        dataset.write_json(path / f"{subject}.json", payload)


def approve_example(question):
    question["rubric_review"].update(status="approved", reviewer_id="TEST_FIXTURE_NOT_REAL",
        reviewed_at="2026-10-22T12:00:00+07:00", comment="Test fixture only, not an actual approval")
    answer = question["answers"][0]
    for point in answer["point_assessments"]:
        point.update(review_status="approved", reviewed_relation=point["proposed_relation"],
            reviewed_evidence=copy.deepcopy(point["proposed_evidence"]),
            reviewed_reason="Synthetic test fixture, not an actual review",
            reviewer_id="TEST_FIXTURE_NOT_REAL", reviewed_at="2026-10-22T12:00:00+07:00")


def test_complete_bundle_and_exact_counts(original_bundle):
    manifest, payloads = dataset.load_bundle(original_bundle)
    stats = dataset.validate_payloads(payloads, manifest["frozen_question_splits"])
    assert stats["questions"] == 40 and stats["answers"] == 400
    assert stats["subjects"] == {subject: 100 for subject in dataset.SUBJECTS}
    assert stats["criterion_pairs"] == 1160
    assert stats["answer_splits"] == {"train": 180, "validation": 80, "test": 80, "regression_only": 60}
    assert stats["draft_label_counts"]["needs_review"] == 41
    assert not manifest["teacher_validated"] and not manifest["training_enabled"]


def test_no_production_file_changed(original_bundle):
    dataset.verify_protected(dataset.read_json(original_bundle / "manifest.json"))


def test_unicode_evidence_uses_code_points_not_bytes():
    text = "Tiếng Việt rồi: 😀 số 2TB. Em sửa lại: số 2TB."
    item = dataset.evidence(text, "số 2TB")
    assert item["start"] == text.rfind("số 2TB")
    assert text[item["start"]:item["end"]] == "số 2TB"
    dataset.validate_evidence(text, "supported", item)


def test_fabricated_evidence_is_rejected():
    with pytest.raises(ValueError, match="substring"):
        dataset.evidence("An actual statement", "Something never said")
    with pytest.raises(ValueError, match="offsets"):
        dataset.validate_evidence("Actual words", "supported", {
            "start": 1, "end": 7, "quote": "Actual", "offset_unit": "unicode_code_points", "end_exclusive": True})


def test_missing_cannot_be_given_invented_evidence():
    with pytest.raises(ValueError, match="Missing"):
        dataset.validate_evidence("Some words", "missing", dataset.evidence("Some words", "Some"))


def test_atomic_budgets_preserve_parent_points(original_bundle):
    payloads = load_payloads(original_bundle)
    q = payloads["DSA101"]["questions"][2]
    q["rubric_draft"][0]["proposed_max_points"] += .5
    with pytest.raises(ValueError, match="parent budget"):
        dataset.validate_payloads(payloads)


def test_frozen_test_questions_cannot_move_to_training(editable_bundle):
    payloads = load_payloads(editable_bundle)
    q = next(q for p in payloads.values() for q in p["questions"] if q["split"] == "test")
    q["split"] = "train"
    save_payloads(editable_bundle, payloads)
    with pytest.raises(ValueError, match="frozen question split"):
        dataset.load_bundle(editable_bundle)


def test_tampered_split_manifest_is_also_rejected(editable_bundle):
    manifest = dataset.read_json(editable_bundle / "manifest.json")
    manifest["frozen_question_splits"]["AI_002"] = "train"
    dataset.write_json(editable_bundle / "manifest.json", manifest)
    with pytest.raises(ValueError, match="original question quarantine"):
        dataset.load_bundle(editable_bundle)


def test_draft_export_blocked_and_no_output_created(editable_bundle, tmp_path):
    destination = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="No complete training answers"):
        dataset.export_reviewed(editable_bundle, destination)
    assert not destination.exists()


def test_teacher_validated_boolean_alone_does_not_approve(editable_bundle, tmp_path):
    payloads = load_payloads(editable_bundle)
    for p in payloads.values():
        for q in p["questions"]:
            for a in q["answers"]:
                a["teacher_validated"] = True
    save_payloads(editable_bundle, payloads)
    with pytest.raises(ValueError, match="No complete training answers"):
        dataset.export_reviewed(editable_bundle, tmp_path / "blocked")


def test_review_requires_reviewer_and_timezone():
    with pytest.raises(ValueError, match="reviewer_id"):
        dataset.validate_stamp({"reviewed_at": "2026-10-22T12:00:00+07:00"})
    with pytest.raises(ValueError, match="timezone"):
        dataset.validate_stamp({"reviewer_id": "TEST_ONLY", "reviewed_at": "2026-10-22T12:00:00"})


def test_review_without_evidence_is_rejected(original_bundle):
    payloads = load_payloads(original_bundle)
    q = payloads["AI101"]["questions"][0]
    approve_example(q)
    q["answers"][0]["point_assessments"][0]["reviewed_evidence"] = None
    with pytest.raises(ValueError, match="require source evidence"):
        dataset.validate_payloads(payloads)


def test_unresolved_is_never_a_fourth_training_label(original_bundle):
    payloads = load_payloads(original_bundle)
    q = payloads["AI101"]["questions"][0]
    approve_example(q)
    q["answers"][0]["point_assessments"][0]["reviewed_relation"] = "needs_review"
    with pytest.raises(ValueError, match="resolved"):
        dataset.validate_payloads(payloads)


def test_approved_exports_stay_separate_and_exclude_regressions(editable_bundle, tmp_path):
    payloads = load_payloads(editable_bundle)
    for split in ("train", "validation", "test", "regression_only"):
        q = next(q for p in payloads.values() for q in p["questions"] if q["split"] == split)
        approve_example(q)
    save_payloads(editable_bundle, payloads)
    destination = tmp_path / "reviewed"
    result = dataset.export_reviewed(editable_bundle, destination)
    assert set(result["rows"]) == {"train", "validation", "test"}
    for split in result["rows"]:
        rows = [json.loads(line) for line in (destination / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()]
        assert rows and all(row["split"] == split for row in rows)
        assert all(row["teacher_validated"] and row["reviewer_id"] == "TEST_FIXTURE_NOT_REAL" for row in rows)
        assert all(not row["independent_student_test"] for row in rows)
        assert all(row["label"] == dataset.LABEL_IDS[row["relation_label"]] for row in rows)
    assert not (destination / "regression_only.jsonl").exists()


def test_all_or_nothing_case_and_rubric_approval(editable_bundle, tmp_path):
    payloads = load_payloads(editable_bundle)
    q = next(q for p in payloads.values() for q in p["questions"] if q["split"] == "train")
    approve_example(q)
    q["answers"][0]["point_assessments"][-1]["review_status"] = "pending"
    save_payloads(editable_bundle, payloads)
    with pytest.raises(ValueError, match="No complete training answers"):
        dataset.export_reviewed(editable_bundle, tmp_path / "incomplete")
    q["answers"][0]["point_assessments"][-1]["review_status"] = "approved"
    q["rubric_review"]["status"] = "pending"
    save_payloads(editable_bundle, payloads)
    with pytest.raises(ValueError, match="No complete training answers"):
        dataset.export_reviewed(editable_bundle, tmp_path / "rubric-not-approved")


def test_never_overwrite_a_bundle_or_reviewed_export(original_bundle):
    with pytest.raises(FileExistsError):
        dataset.build(original_bundle)
    with pytest.raises(FileExistsError):
        dataset.export_reviewed(original_bundle, original_bundle)


def test_draft_jsonl_cannot_masquerade_as_approved_training(original_bundle):
    lines = (original_bundle / "draft_pairs_NOT_TRAINING.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1160
    rows = [json.loads(line) for line in lines]
    assert all("relation_label" not in r and "label" not in r for r in rows)
    assert all(not r["eligible_for_training"] and not r["teacher_validated"] for r in rows)
