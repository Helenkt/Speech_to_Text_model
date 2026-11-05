import copy
import json

import pytest

from app.database import database
from app.services.interview_engine import (
    InterviewError, PRACTICE_SOURCE_VERSION, _practice_source_hash, _practice_source_matches,
    _row_to_question, start_practice_again,
)
from app.services.question_importer import import_question_bank
from app.services.rubric_contract import attach_published_contract, publish_contract, rubric_draft, digest
from test_learning_feedback import seed_stack


BEFORE = "def f(x):\n    if x:\n        return 1\n    return 2\n"
AFTER = "def f(x):\n    if x:\n        return 1\n        return 2\n"
SOURCE = {"uid": "vi:layout", "language": "vi", "subject": "DSA101", "competency": "Execution",
          "topic": "Python", "concept": "Return value", "difficulty": "Easy",
          "question": "Analyse the function.", "reference_answer": "Explain its return value.",
          "key_points": ["A stack uses LIFO"], "source_name": "approved.json"}


def saved_version(source, version):
    saved = copy.deepcopy(source)
    if version == "v2":
        saved.update(learning_source_sha256=_practice_source_hash(source), learning_source_version=PRACTICE_SOURCE_VERSION)
    elif version in {"v1", "atomic-v1"}:
        # The deployed 1.18.5 format collapsed all whitespace, before projecting a rubric.
        fields = ("uid", "language", "subject", "competency", "topic", "concept", "difficulty", "question", "reference_answer")
        legacy = {key: " ".join(str(source.get(key) or "").split()) for key in fields}
        legacy["key_points"] = [" ".join(point.split()) for point in source["key_points"]]
        saved["learning_source_sha256"] = digest(legacy)
    if version in {"atomic", "atomic-v1"}:
        contract = rubric_draft(source)
        for index, criterion in enumerate(contract["criteria"]):
            criterion["claim"] = f"Approved atomic criterion {index}"
        saved["rubric_snapshot"] = {"contract": contract, "sha256": digest(contract)}
        saved["key_points"] = [criterion["claim"] for criterion in contract["criteria"]]
        saved["key_point_weights"] = {point: 1.0 for point in saved["key_points"]}
    return saved


@pytest.mark.parametrize("version", ["v2", "v1", "atomic", "atomic-v1"])
@pytest.mark.parametrize("field", ["question", "reference_answer", "key_points"])
def test_changed_code_layout_is_rejected_in_all_source_text_fields_and_legacy_versions(version, field):
    original = copy.deepcopy(SOURCE)
    original[field] = [BEFORE] if field == "key_points" else BEFORE
    saved = saved_version(original, version)
    updated = copy.deepcopy(original)
    updated[field] = [AFTER] if field == "key_points" else AFTER
    before = copy.deepcopy(saved)
    assert not _practice_source_matches(saved, updated)
    assert saved == before


@pytest.mark.parametrize("version", ["v2", "v1", "atomic", "atomic-v1"])
def test_unchanged_sources_remain_usable_without_rewriting_history(version):
    saved = saved_version(SOURCE, version)
    assert _practice_source_matches(saved, SOURCE)


def test_v2_accepts_windows_line_endings_but_preserves_indentation():
    question = {**SOURCE, "question": BEFORE}
    saved = saved_version(question, "v2")
    assert _practice_source_matches(saved, {**question, "question": BEFORE.replace("\n", "\r\n")})
    assert not _practice_source_matches(saved, {**question, "question": AFTER})


def test_unknown_source_hash_version_is_not_silently_trusted():
    saved = saved_version(SOURCE, "v2")
    saved["learning_source_version"] = "unknown-version"
    assert not _practice_source_matches(saved, SOURCE)


@pytest.mark.parametrize("field,value", [("difficulty", "Hard"), ("topic", "Changed topic"),
    ("concept", "Changed concept"), ("competency", "Changed competency")])
def test_published_old_atomic_rubric_cannot_bypass_changed_source_metadata(tmp_path, field, value):
    settings = seed_stack(tmp_path)
    with database(settings.database_path) as connection:
        current = _row_to_question(connection.execute("SELECT * FROM questions").fetchone())
        publish_contract(connection, current, rubric_draft(current), teacher_id=1,
                         attestation="Đã kiểm tra nguồn và ý nghĩa từng tiêu chí trong dữ liệu thử.")
        frozen = attach_published_contract(connection, current)
        frozen.pop("learning_source_sha256")
        frozen.pop("learning_source_version")
        connection.execute("UPDATE interview_answers SET question_json=?", (json.dumps(frozen),))
    import_question_bank(settings.database_path, json.dumps([{**current, field: value}]).encode(), filename=current["source_name"])
    with pytest.raises(InterviewError, match="đã được cập nhật"):
        start_practice_again(settings, "session-1", user_id=2, candidate_name="Candidate", answer_id=1)
    with database(settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM interview_sessions").fetchone()[0] == 1
