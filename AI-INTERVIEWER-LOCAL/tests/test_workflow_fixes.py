import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from app.database import database
from app.services.interview_engine import InterviewError, start_interview
from app.services.question_importer import QuestionBankError, import_question_bank
from app.services.rubric_contract import validate_rubric_points
from app.services.transcript_corrector import correct_transcript, _validate_correction
from test_learning_feedback import report_fixtures
from test_teacher_strong_review import _seed_voice_answer, _settings
from test_transcript_corrector import _run_without_await


BASE = {"id": "workflow-stack", "language": "en", "subject": "DSA101", "difficulty": "Easy",
        "question": "What is a stack?", "reference_answer": "A stack follows LIFO.",
        "key_points": ["A stack follows LIFO."]}


@pytest.mark.parametrize("points", [
    [f"Criterion {i}" for i in range(31)],
    ["Stack uses LIFO", "STACK USES LIFO"],
    ["Stack uses LIFO", "Stack uses LIFO"],
    ["Stack uses LIFO", "Stack  uses LIFO"],
    ["Cấu trúc", "Ca\u0302\u0301u tru\u0301c"],
])
def test_import_refuses_ungradable_criteria_before_writing_any_question(tmp_path, points):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    import_question_bank(settings.database_path, json.dumps([BASE]).encode(), filename="original.json")
    with database(settings.database_path) as connection:
        before = [tuple(row) for row in connection.execute("SELECT * FROM questions")]
        sources = connection.execute("SELECT COUNT(*) FROM question_sources").fetchone()[0]
    payload = [{**BASE, "id": "new-valid"}, {**BASE, "id": "invalid", "key_points": points}]
    with pytest.raises(QuestionBankError, match="Câu #2"):
        import_question_bank(settings.database_path, json.dumps(payload).encode(), filename="bad.json", mode="replace")
    with database(settings.database_path) as connection:
        assert [tuple(row) for row in connection.execute("SELECT * FROM questions")] == before
        assert connection.execute("SELECT COUNT(*) FROM question_sources").fetchone()[0] == sources


@pytest.mark.parametrize("explicit", [False, True])
def test_invalid_existing_bank_is_blocked_before_creating_a_session(tmp_path, explicit):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    import_question_bank(settings.database_path, json.dumps([BASE]).encode(), filename="original.json")
    with database(settings.database_path) as connection:
        connection.execute("UPDATE questions SET key_points_json=?", (json.dumps(["LIFO", "lifo"]),))
        count = connection.execute("SELECT COUNT(*) FROM interview_sessions").fetchone()[0]
    options = {"practice_question_uids": ["en:workflow-stack"]} if explicit else {}
    with pytest.raises(InterviewError, match="Rubric.*không hợp lệ"):
        start_interview(settings, user_id=2, candidate_name="Candidate", language="en", subject="DSA101",
                        question_count=1, starting_difficulty="Easy", **options)
    with database(settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM interview_sessions").fetchone()[0] == count


@pytest.mark.parametrize("weights", [{"A": 1}, {"A": True, "B": 1}, {"A": float("nan"), "B": 1},
                                    {"A": 0, "B": 1}, {"A": 101, "B": 1}, []])
def test_shared_rubric_contract_rejects_invalid_weights(weights):
    with pytest.raises(ValueError):
        validate_rubric_points(["A", "B"], weights)


def test_thirty_distinct_criteria_remain_valid():
    validate_rubric_points([f"Criterion {i}" for i in range(30)])


@pytest.mark.parametrize("opening", ["À", "Á", "Ạ", "Ả", "Ã"])
def test_accented_ordinary_words_are_not_turned_into_letter_names(tmp_path, opening):
    raw = f"{opening} ai là người tạo ra hệ thống này?"
    result = _run_without_await(correct_transcript(_settings(tmp_path), raw, language="vi",
        approved_terms=["AI"], uncertain_spans=[], allow_llm=False))
    assert result["corrected_text"] == raw
    assert not result["correction_applied"]


@pytest.mark.parametrize("boundary", [". ", ", ", "! ", "? ", "; ", ": ", "\n", "\r\n", "。 "])
def test_technical_units_never_merge_words_across_sentence_boundaries(tmp_path, boundary):
    raw = f"Em đã nêu hai{boundary}tê bê là ký hiệu đơn vị lưu trữ."
    result = _run_without_await(correct_transcript(_settings(tmp_path), raw, language="vi",
        approved_terms=["2TB"], uncertain_spans=[], allow_llm=False))
    assert result["corrected_text"] == raw


@pytest.mark.parametrize("raw,term,expected", [
    ("Máy có dung lượng hai tê bê để lưu tài liệu.", "2TB", "Máy có dung lượng 2TB để lưu tài liệu."),
    ("Giao thức hát tê tê pê được sử dụng.", "HTTP", "Giao thức HTTP được sử dụng."),
    ("Mô hình ây ai được sử dụng trong hệ thống.", "AI", "Mô hình AI được sử dụng trong hệ thống."),
    ("An A P I is useful.", "API", "An API is useful."),
])
def test_clear_spoken_technical_terms_still_normalize_without_loading_an_llm(tmp_path, raw, term, expected):
    result = _run_without_await(correct_transcript(_settings(tmp_path), raw, language="vi",
        approved_terms=[term], uncertain_spans=[], allow_llm=False))
    assert result["corrected_text"] == expected


def test_frontend_workflow_ownership_and_controls(tmp_path):
    node = os.environ.get("NODE_BINARY") or shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for workflow checks")
    root = Path(__file__).parents[1]
    fixture = tmp_path / "workflow-fixtures.json"
    fixture.write_text(json.dumps(report_fixtures(tmp_path), ensure_ascii=False), encoding="utf-8")
    result = subprocess.run([node, str(root / "tests/workflow_lifecycle.cjs"),
        str(root / "app/static/app.js"), str(fixture)], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("raw,changed", [
    ("API không có 10 phương thức", "API có 10 phương thức"),
    ("API có 10 phương thức", "API có 11 phương thức"),
])
def test_letter_name_contraction_does_not_allow_changed_numbers_or_negation(raw, changed):
    assert not _validate_correction(raw, changed, allow_phonetic_contraction=True)[0]
