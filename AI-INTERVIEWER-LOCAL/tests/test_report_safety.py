import copy
import json

import pytest

from app.database import database
from app.services.assessment_feedback import verified_assessment_evidence
from app.services.interview_engine import (
    InterviewError, _row_to_question, _practice_source_matches, interview_report, start_practice_again,
)
from app.services.question_importer import import_question_bank
from app.services.rubric_contract import rubric_draft
from test_learning_feedback import seed_stack


@pytest.mark.parametrize("captured", [False, True])
@pytest.mark.parametrize("field,value", [
    ("subject", "OOP101"), ("topic", "Queue"), ("concept", "Queue"), ("competency", "Other competency"),
    ("difficulty", "Hard"), ("question", "How does a queue work?"),
    ("reference_answer", "A queue follows FIFO."), ("key_points", ["A queue follows FIFO"]),
])
def test_practice_again_rejects_changed_bank_source_without_creating_a_new_session(tmp_path, captured, field, value):
    settings = seed_stack(tmp_path)
    with database(settings.database_path) as connection:
        original = json.loads(connection.execute("SELECT question_json FROM interview_answers").fetchone()[0])
        if captured:
            current = _row_to_question(connection.execute("SELECT * FROM questions").fetchone())
            original["learning_source_sha256"] = current["learning_source_sha256"]
            original["learning_source_version"] = current["learning_source_version"]
            connection.execute("UPDATE interview_answers SET question_json=?", (json.dumps(original),))
        before = dict(connection.execute("SELECT * FROM interview_answers").fetchone())
    updated = {**original, field: value}
    import_question_bank(settings.database_path, json.dumps([updated], ensure_ascii=False).encode(), filename="changed.json")
    with pytest.raises(InterviewError, match="đã được cập nhật"):
        start_practice_again(settings, "session-1", user_id=2, candidate_name="Candidate", answer_id=1)
    with database(settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM interview_sessions").fetchone()[0] == 1
        assert dict(connection.execute("SELECT * FROM interview_answers").fetchone()) == before


def test_reimporting_identical_content_from_a_new_file_does_not_block_legacy_practice(tmp_path):
    settings = seed_stack(tmp_path)
    with database(settings.database_path) as connection:
        original = json.loads(connection.execute("SELECT question_json FROM interview_answers").fetchone()[0])
    import_question_bank(settings.database_path, json.dumps([original]).encode(), filename="renamed-source.json")
    result = start_practice_again(settings, "session-1", user_id=2, candidate_name="Candidate", answer_id=1)
    assert result["question"]["question"] == original["question"]
    with database(settings.database_path) as connection:
        question = json.loads(connection.execute("SELECT current_question_json FROM interview_sessions WHERE session_id=?",
                                                (result["session_id"],)).fetchone()[0])
    assert question["learning_source_sha256"]


def test_legacy_atomic_snapshot_matches_original_bank_source_and_rejects_meaning_changes(tmp_path):
    settings = seed_stack(tmp_path)
    with database(settings.database_path) as connection:
        current = _row_to_question(connection.execute("SELECT * FROM questions").fetchone())
    saved = copy.deepcopy(current)
    saved.pop("learning_source_sha256")
    saved["rubric_snapshot"] = {"contract": rubric_draft(current)}
    saved["key_points"] = ["A separately approved atomic claim"]
    assert _practice_source_matches(saved, current)
    assert not _practice_source_matches(saved, {**current, "question": "Changed question"})


def test_current_source_signature_survives_approved_rubric_projection(tmp_path):
    settings = seed_stack(tmp_path)
    with database(settings.database_path) as connection:
        current = _row_to_question(connection.execute("SELECT * FROM questions").fetchone())
    saved = {**current, "key_points": ["A separately approved atomic claim"]}
    assert _practice_source_matches(saved, current)
    assert not _practice_source_matches(saved, {**current, "reference_answer": "Changed reference"})


def test_evidence_projection_filters_bad_quotes_and_offsets_without_mutating_input():
    text = "Stack follows LIFO. PUSH adds to the top."
    raw = [{"point": "Stack follows LIFO", "status": "met", "evidence_quote": "FORGED",
        "evidence_quotes": ["FORGED", "Stack follows LIFO", None, "Stack follows LIFO"],
        "evidence_spans": [{"start": 0, "end": 6, "text": "FORGED"}]}]
    before = copy.deepcopy(raw)
    clean = verified_assessment_evidence(raw, text)
    assert raw == before
    assert clean[0]["status"] == "met"
    assert clean[0]["evidence_quote"] == "Stack follows LIFO"
    assert clean[0]["evidence_quotes"] == ["Stack follows LIFO"]
    assert clean[0]["evidence_spans"] == [{"start": 0, "end": 18, "text": "Stack follows LIFO"}]


def test_report_drops_invalid_legacy_quote_but_keeps_stored_grade_and_valid_evidence(tmp_path):
    settings = seed_stack(tmp_path, "correct")
    with database(settings.database_path) as connection:
        row = dict(connection.execute("SELECT * FROM interview_answers").fetchone())
        assessments = json.loads(row["assessment_json"])
        assessments[0]["evidence_quote"] = "FORGED QUOTE NOT IN TRANSCRIPT"
        connection.execute("UPDATE interview_answers SET assessment_json=?", (json.dumps(assessments),))
        before = dict(connection.execute("SELECT * FROM interview_answers").fetchone())
    report = interview_report(settings, "session-1")
    grade = report["answers"][0]["evaluation"]
    assert grade["point_assessments"][0]["evidence_quote"] == ""
    assert grade["point_assessments"][1]["evidence_quote"]
    assert grade["score_breakdown"]["score"] == 10
    with database(settings.database_path) as connection:
        assert dict(connection.execute("SELECT * FROM interview_answers").fetchone()) == before
