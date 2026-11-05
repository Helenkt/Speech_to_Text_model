"""Closed rules must account for the entire answer before finalizing a criterion."""
import asyncio
import json

import pytest

from app.database import database, init_database
from app.services import evaluator, runtime_readiness, session_grading
from app.services.interview_engine import start_interview, submit_answer, interview_report
from app.services.question_importer import import_question_bank
from app.services.fact_guard import check_rubric_point
from app.services.transcription_store import save_microphone_check, save_transcription
from test_teacher_strong_review import _settings


CASES = [
    ("DSA101", "vi", "Stack theo LIFO",
     "Nói đơn giản là cái vào trước sẽ được lấy ra trước",
     "Nói đơn giản là cái vào sau sẽ được lấy ra trước", "Stack theo FIFO"),
    ("DB101", "vi", "NULL là không xác định/chưa có dữ liệu",
     "Nói đơn giản là nó chính là số 0",
     "Nói đơn giản là chưa biết giá trị ở ô đó", "NULL là số 0"),
    ("OOP101", "vi", "Lớp con kế thừa thuộc tính và phương thức từ lớp cha",
     "Cụ thể là những thuộc tính đó đi từ lớp con sang lớp cha",
     "Cụ thể là những thuộc tính đó đi từ lớp cha sang lớp con",
     "Lớp cha kế thừa thuộc tính và phương thức từ lớp con"),
    ("AI101", "vi", "Tham số được cập nhật theo hướng ngược với gradient",
     "Nói nôm na là đi cùng chiều gradient",
     "Nói nôm na là đi ngược chiều gradient",
     "Tham số được cập nhật theo hướng cùng với gradient"),
    ("DSA101", "en", "Stack uses LIFO",
     "In practice the first inserted item leaves first",
     "In practice the last inserted item leaves first", "Stack uses FIFO"),
    ("OOP101", "en", "Child class inherits attributes and methods from parent class",
     "Put simply, attributes flow from child to parent",
     "Put simply, attributes flow from parent to child",
     "Parent class inherits attributes and methods from child class"),
]


def question(case):
    subject, lang, point, *_ = case
    return {"id": f"audit-{lang}-{subject}", "uid": f"{lang}:{subject}:audit",
        "language": lang, "subject": subject, "difficulty": "Easy", "competency": "Concepts",
        "question": "Giải thích kiến thức này" if lang == "vi" else "Explain this concept",
        "reference_answer": point, "key_points": [point]}


def isolate_semantic_models(monkeypatch, status="unresolved"):
    calls = []
    def unresolved(_path, asked, text, **kwargs):
        calls.append(text)
        return evaluator._compose_result(asked, [{"point": p, "status": status,
            "needs_review": status == "unresolved", "evidence_quote": text} for p in asked["key_points"]],
            evaluator="test-semantic")
    async def llm(_settings, asked, text, **kwargs):
        return unresolved(None, asked, text)
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", unresolved)
    monkeypatch.setattr(evaluator, "evaluate_with_ollama", llm)
    return calls


@pytest.mark.parametrize("case", CASES, ids=[f"{c[0]}-{c[1]}" for c in CASES])
@pytest.mark.parametrize("mode", ["auto", "transformer", "ollama"])
def test_wrong_explanation_cannot_earn_full_final_grade(tmp_path, monkeypatch, case, mode):
    settings = _settings(tmp_path)
    settings.evaluator_mode = mode
    isolate_semantic_models(monkeypatch)
    text = f"{case[2]}. {case[3]}."
    result = asyncio.run(evaluator.evaluate_answer(settings, question(case), text))
    assert result["score_provisional"] or result["score"] < 100, {
        "text": text, "score": result["score"], "evaluator": result["evaluator"],
        "provisional": result["score_provisional"], "points": result["point_assessments"]}


@pytest.mark.parametrize("case", CASES, ids=[f"{c[0]}-{c[1]}" for c in CASES])
def test_control_correct_explanation_is_accepted(tmp_path, monkeypatch, case):
    settings = _settings(tmp_path)
    settings.evaluator_mode = "auto"
    calls = isolate_semantic_models(monkeypatch, status="met")
    text = f"{case[2]}. {case[4]}."
    result = asyncio.run(evaluator.evaluate_answer(settings, question(case), text))
    assert calls and all(value == text for value in calls)
    assert result["score"] == 100 and not result["score_provisional"], result


@pytest.mark.parametrize("prefix", ["Nói đơn giản là", "Cụ thể là", "Một cách khác là", "ZetaPhi là"])
@pytest.mark.parametrize("before", [False, True])
def test_unparsed_clause_coverage_does_not_depend_on_an_allowlist(prefix, before):
    point = "Stack theo LIFO"
    explanation = f"{prefix} cái vào trước sẽ được lấy ra trước."
    answer = f"{explanation} {point}." if before else f"{point}. {explanation}"
    check = check_rubric_point({"question": "Giải thích stack", "key_points": [point]}, answer, point)
    assert check.status == "unknown" and check.verification_rule.endswith(":unparsed_scope")


@pytest.mark.parametrize("point,answer", [
    ("Lớp là khuôn mẫu", "Lớp là khuôn mẫu. Cụ thể là chỉ có một đối tượng duy nhất."),
    ("Lớp là khuôn mẫu", "Lớp là khuôn mẫu của bất cứ câu giải thích nào cũng đúng."),
])
def test_generic_copula_fallback_cannot_recover_only_a_supported_fragment(point, answer):
    assert check_rubric_point({"key_points": [point]}, answer, point).status == "unknown"


def test_numeric_comparison_with_unparsed_explanation_requires_semantic_check():
    point = "A lớn hơn B"
    asked = {"question": "A có 2 TB, B có 1 TB.", "reference_answer": point, "key_points": [point]}
    assert check_rubric_point(asked, "A lớn hơn B. Cụ thể là nó nhỏ hơn cái còn lại.", point).status == "unknown"


def test_adding_behavior_is_not_proof_of_overriding_behavior():
    point = "Lớp con có thể bổ sung hoặc ghi đè hành vi riêng"
    assert check_rubric_point({"key_points": [point]},
        "Lớp con có thể thêm hành vi riêng. Phần còn lại em chưa biết.", point).status == "unknown"


@pytest.mark.parametrize("case", CASES, ids=[f"{c[0]}-{c[1]}" for c in CASES])
def test_control_explicit_reverse_claim_is_rejected(tmp_path, monkeypatch, case):
    settings = _settings(tmp_path)
    settings.evaluator_mode = "auto"
    isolate_semantic_models(monkeypatch)
    result = asyncio.run(evaluator.evaluate_answer(settings, question(case), case[5] + "."))
    assert result["score"] == 0 and not result["score_provisional"], result


@pytest.mark.parametrize("case", CASES[:4], ids=[c[0] for c in CASES[:4]])
def test_end_to_end_worker_cannot_persist_wrong_explanation_as_full_marks(tmp_path, monkeypatch, case):
    settings = _settings(tmp_path)
    settings.evaluator_mode = "auto"
    settings.defer_grading_until_finish = True
    isolate_semantic_models(monkeypatch)
    init_database(settings.database_path)
    with database(settings.database_path) as connection:
        connection.execute("""INSERT INTO users(user_id,username,password_hash,full_name,role,created_at,updated_at)
            VALUES (1,'teacher','hash','Audit Teacher','teacher','now','now'),
                   (2,'candidate','hash','Audit Student','candidate','now','now')""")
    asked = question(case)
    import_question_bank(settings.database_path, json.dumps([asked], ensure_ascii=False).encode(),
                         filename="audit-synthetic.json")
    session = start_interview(settings, user_id=2, candidate_name="Audit Student", language=case[1],
        subject=case[0], question_count=1, starting_difficulty="Easy")
    sid = session["session_id"]
    with database(settings.database_path) as connection:
        current = json.loads(connection.execute(
            "SELECT current_question_json FROM interview_sessions WHERE session_id=?", (sid,)).fetchone()[0])
    save_microphone_check(settings.database_path, session_id=sid, user_id=2, result={"ready": True})
    text = f"{case[2]}. {case[3]}."
    tid = save_transcription(settings.database_path, session_id=sid, user_id=2, question_uid=current["uid"],
        raw_text=text, corrected_text=text, model="audit", runtime="cpu/int8", confidence=.95,
        ambient_noise_dbfs=-60, metadata={"metrics": {"quality_score": .95}},
        audio_content=b"audit-not-real-audio", audio_filename="voice.wav")
    asyncio.run(submit_answer(settings, sid, "", user_id=2, transcription_id=tid))
    jobs = session_grading.SessionGrading(settings, runtime_readiness.RuntimeReadiness(settings))
    asyncio.run(jobs.run_once())
    report = interview_report(settings, sid)
    result = report["answers"][0]["evaluation"]
    assert result["final_score"] is None or result["final_score"] < 100, {
        "score": result["final_score"], "breakdown": result["score_breakdown"],
        "evaluator": result["evaluator"], "session_grade": report["summary"]["practice_grading"]["session"]}
