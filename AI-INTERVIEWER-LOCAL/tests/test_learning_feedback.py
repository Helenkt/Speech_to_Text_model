import copy
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from app.database import database
from app.services.evaluator import _compose_result
from app.services.fact_guard import check_rubric_point
from app.services.interview_engine import interview_report, start_practice_again, InterviewError
from app.services.learning_feedback import question_feedback, session_feedback
from app.services.practice_grading import question_breakdown, practice_summary
from app.services.question_importer import import_question_bank
from app.services.rubric_contract import rubric_draft, digest
from test_practice_grading import QUESTION, evaluation
from test_teacher_strong_review import _seed_voice_answer, _settings


def feedback(statuses, *, language="en", answer="student evidence", **extra):
    question = {**copy.deepcopy(QUESTION), "language": language}
    grade = evaluation(statuses, **extra)
    for item in grade["point_assessments"]:
        item["evidence_quote"] = answer
    grade["score_breakdown"] = question_breakdown(question, grade, completed=True)
    return question_feedback(question, answer, grade)


@pytest.mark.parametrize("language", ["vi", "en"])
@pytest.mark.parametrize("status", ["met", "partial", "missing", "contradicted", "unresolved"])
def test_feedback_distinguishes_rubric_outcomes_without_new_inference(language, status):
    result = feedback([status] * 3, language=language)
    assert all(item["status"] == status for item in result["items"])
    assert result["scope"] == "this_response"
    assert result["confidence_is_accuracy"] is False
    assert result["items"][0]["point"] in result["summary"] or status == "unresolved"
    if status == "unresolved":
        assert not result["focus_points"]
        assert all(not item["evidence_quotes"] and item["earned_points"] is None for item in result["items"])
        assert result["notices"][0]["action"] == "practice_again"
    elif status in {"missing", "partial", "contradicted"}:
        assert result["focus_points"] == QUESTION["key_points"]


def test_never_quotes_text_not_in_the_transcript_used_for_grading():
    grade = evaluation(["met"] * 3, 100)
    grade["point_assessments"][0]["evidence_quotes"] = ["fabricated quote", "real quote", 13, None]
    grade["score_breakdown"] = question_breakdown(QUESTION, grade, completed=True)
    result = question_feedback(QUESTION, "A real quote here", grade)
    assert result["items"][0]["evidence_quotes"] == ["real quote"]


@pytest.mark.parametrize("cause,category,action", [
    ("audio", "audio", "practice_again"), ("system", "system", "retry_grading"),
])
def test_technical_and_audio_problems_have_different_actions(cause, category, action):
    result = feedback(["unresolved"] * 3, score_provisional=True,
                      review_reasons=[{"category": cause}])
    assert result["notices"] == [{"category": category, "action": action,
                                 "message": result["summary"]}]
    assert not result["focus_points"]


def test_untrusted_audio_never_becomes_a_knowledge_gap_or_strength():
    result = feedback(["contradicted", "met", "missing"], recognition_status="needs_review",
                      review_reasons=[{"category": "audio"}])
    assert all(item["status"] == "unresolved" for item in result["items"])
    assert not result["focus_points"]


def test_pending_feedback_does_not_publish_conclusions():
    result = feedback(["met"] * 3, grading_pending=True)
    assert all(item["status"] == "unresolved" for item in result["items"])
    assert result["notices"][0]["category"] == "pending"
    assert not result["focus_points"]


def test_atomic_partial_cannot_create_a_half_credit_learning_claim():
    question = copy.deepcopy(QUESTION)
    contract = rubric_draft(question)
    for criterion in contract["criteria"]:
        criterion["weight"] = question["key_point_weights"][criterion["claim"]]
    question["rubric_snapshot"] = {"contract": contract, "sha256": digest(contract)}
    grade = evaluation(["met", "partial", "missing"], score_provisional=True)
    grade["score_breakdown"] = question_breakdown(question, grade, completed=True)
    result = question_feedback(question, "answer", grade)
    assert result["items"][1]["status"] == "unresolved"
    assert result["items"][1]["criterion_id"] == "c2"
    assert result["items"][1]["point"] not in result["focus_points"]


def test_teacher_total_does_not_invent_criterion_feedback():
    result = question_feedback(QUESTION, "answer", {"score_breakdown": {"criteria": [], "basis": "teacher_total_only"}})
    assert not result["items"]
    assert result["notices"][0]["action"] is None


def test_one_known_answer_and_one_wrong_answer_do_not_create_conflicting_summary_lists():
    def answer(number, statuses):
        return {"answer_id": number, "sequence_number": number, "question": QUESTION,
                "evaluation": {"learning_feedback": feedback(statuses)}}
    result = session_feedback([answer(1, ["met"] * 3), answer(2, ["contradicted"] * 3)])
    assert not result["strengths"]
    assert all(item["status"] == "inconsistent" for item in result["priorities"])
    assert result["scope"] == "this_session_only"


def test_a_partly_unverified_answer_has_one_practice_action_and_technical_failure_has_retry_only():
    for category in ("grading", "system"):
        learned = feedback(["met", "missing", "unresolved"], score_provisional=True,
                           review_reasons=[{"category": category}])
        report = session_feedback([{"question": QUESTION, "answer_id": 1, "sequence_number": 1,
                                   "evaluation": {"learning_feedback": learned}}])
        assert len(report["next_steps"]) == 1
        assert report["next_steps"][0]["action"] == ("retry_grading" if category == "system" else "practice_again")


def test_published_split_rubric_keeps_weight_and_old_report_but_explains_push_and_pop_separately(tmp_path):
    from app.services.interview_engine import _row_to_question
    from app.services.rubric_contract import publish_contract
    settings = seed_stack(tmp_path)
    old = interview_report(settings, "session-1")
    with database(settings.database_path) as connection:
        question = _row_to_question(connection.execute("SELECT * FROM questions").fetchone())
        contract = rubric_draft(question)
        contract["criteria"] = [contract["criteria"][0],
            {"id": "push", "claim": "PUSH thêm một phần tử mới lên đỉnh Stack", "weight": .5,
             "credit_policy": "binary", "source_field": "reference_answer",
             "source_quote": "PUSH (thêm một phần tử mới lên đỉnh Stack)"},
            {"id": "pop", "claim": "POP lấy và loại bỏ phần tử đang ở đỉnh Stack", "weight": .5,
             "credit_policy": "binary", "source_field": "reference_answer",
             "source_quote": "POP (lấy và loại bỏ phần tử đang ở đỉnh Stack)"}]
        publish_contract(connection, question, contract, teacher_id=1,
                         attestation="Đã đối chiếu nguồn, tách thao tác và giữ tổng trọng số cũ.")
    new = start_practice_again(settings, "session-1", user_id=2, candidate_name="Candidate", answer_id=1)
    assert interview_report(settings, "session-1") == old
    with database(settings.database_path) as connection:
        row = connection.execute("SELECT current_question_json FROM interview_sessions WHERE session_id=?", (new["session_id"],)).fetchone()
    question = json.loads(row[0])
    assert sum(question["key_point_weights"].values()) == 2
    grade = _compose_result(question, [{"point": point, "status": status}
        for point, status in zip(question["key_points"], ["met", "met", "missing"])], evaluator="test")
    grade["final_score"] = grade["score"]
    grade["score_breakdown"] = question_breakdown(question, grade, completed=True)
    result = question_feedback(question, "LIFO and PUSH", grade)
    assert grade["score_breakdown"]["score"] == 7.5
    assert result["items"][1]["status"] == "met"
    assert result["items"][2]["status"] == "missing"
    assert result["focus_points"] == [question["key_points"][2]]


def test_practice_again_route_uses_candidate_dependency_and_returns_voice_plan(tmp_path, monkeypatch):
    from app.main import create_app
    from app.schemas import PracticeAgainRequest
    from app.services.runtime_readiness import RuntimeReadiness
    from pydantic import ValidationError
    settings = seed_stack(tmp_path)
    started = []
    monkeypatch.setattr(RuntimeReadiness, "start", lambda self: started.append(True))
    app = create_app(settings)
    route = next(route for route in app.routes if getattr(route, "path", "") == "/api/interviews/{session_id}/practice-again")
    assert route.status_code == 201
    assert "candidate_user" in {dependency.call.__name__ for dependency in route.dependant.dependencies}
    for invalid in (True, "1", 0, -1):
        with pytest.raises(ValidationError):
            PracticeAgainRequest(answer_id=invalid)
    # This route performs no awaited I/O. Test its binding without a networking event loop.
    operation = route.endpoint("session-1", PracticeAgainRequest(answer_id=1), {"user_id": 2, "full_name": "Candidate"})
    with pytest.raises(StopIteration) as done:
        operation.send(None)
    result = done.value.value
    assert started == [True]
    assert result["answer_mode"] == "voice" and result["question_selection"] == "fixed"
    assert result["grading_strategy"] == "end_of_session"


def seed_stack(tmp_path, case="incomplete"):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    bank = json.loads((Path(__file__).parents[1] / "data/question_bank_vi.json").read_text(encoding="utf-8"))
    question = next(item for item in bank if item["id"] == "Q_DSA_008")
    import_question_bank(settings.database_path, json.dumps([question], ensure_ascii=False).encode(), filename="approved.json")
    with database(settings.database_path) as connection:
        uid = connection.execute("SELECT uid FROM questions WHERE question_id=?", (question["id"],)).fetchone()[0]
    question = {**question, "uid": uid}
    answers = {
        "correct": "Theo em stack theo LIFO. Push để thêm phần tử lên đỉnh, pop lấy và xóa phần tử trên đỉnh.",
        "incomplete": "Stack theo LIFO. Hai thao tác tên gì thì em chưa nhớ.",
        "wrong": "Stack theo FIFO. PUSH lấy từ đỉnh và POP thêm lên đỉnh.",
    }
    text = answers.get(case, answers["incomplete"])
    assessments = []
    for point in question["key_points"]:
        check = check_rubric_point(question, text, point)
        status = {"supported": "met", "missing": "missing", "contradicted": "contradicted"}[check.status]
        assessments.append({"point": point, "status": status, "evidence_quote": check.evidence})
    if case in {"system", "uncertain"}:
        assessments = [{"point": p, "status": "unresolved", "needs_review": True,
                        "review_reason": "model_timeout" if case == "system" else "neutral_evidence"}
                       for p in question["key_points"]]
    grade = _compose_result(question, assessments, evaluator="factguard-v2")
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_sessions SET interview_mode='practice',subject=?,created_at='2026-10-28T08:00:00+00:00'", (question["subject"],))
        connection.execute("""UPDATE interview_answers SET question_json=?, question_uid=?, answer_text=?,
            score=?,ai_score=?,final_score=?,assessment_json=?,score_provisional=?,verdict=?,review_required=0""",
            (json.dumps(question, ensure_ascii=False), uid, text, grade["score"], grade["score"],
             None if grade["score_provisional"] else grade["score"], json.dumps(assessments, ensure_ascii=False),
             int(grade["score_provisional"]), grade["verdict"]))
    return settings


@pytest.mark.parametrize("case,score,label", [("correct", 10, "đã nêu đúng"),
    ("incomplete", 5, "chưa nêu đủ"), ("wrong", 0, "mâu thuẫn")])
def test_real_factguard_and_report_produce_different_helpful_feedback(tmp_path, case, score, label):
    settings = seed_stack(tmp_path, case)
    with database(settings.database_path) as connection:
        before = dict(connection.execute("SELECT * FROM interview_answers").fetchone())
    report = interview_report(settings, "session-1")
    assert report["summary"]["practice_grading"]["session"]["score"] == score
    feedback = report["answers"][0]["evaluation"]["learning_feedback"]
    assert label in feedback["summary"]
    assert "Đã đối chiếu từng ý rubric" not in feedback["summary"]
    assert all(item["source"]["quote"] in report["answers"][0]["key_points"] for item in feedback["items"])
    with database(settings.database_path) as connection:
        assert dict(connection.execute("SELECT * FROM interview_answers").fetchone()) == before


def test_practice_again_creates_a_new_fixed_plan_without_changing_the_old_grade(tmp_path):
    settings = seed_stack(tmp_path)
    settings.defer_grading_until_finish = False
    old = interview_report(settings, "session-1")
    result = start_practice_again(settings, "session-1", user_id=2, candidate_name="Candidate", answer_id=1)
    assert result["session_id"] != "session-1"
    assert result["answer_mode"] == "voice"
    assert result["question_selection"] == "fixed" and result["grading_strategy"] == "end_of_session"
    assert result["question"]["id"] == "Q_DSA_008"
    assert interview_report(settings, "session-1") == old
    with database(settings.database_path) as connection:
        row = connection.execute("SELECT * FROM interview_sessions WHERE session_id=?", (result["session_id"],)).fetchone()
        assert row["answered_count"] == 0 and row["mic_checked_at"] is None
        assert len(json.loads(row["question_plan_json"])) == 1


@pytest.mark.parametrize("change,user_id,answer_id", [
    (None, 3, 1), ("formal", 2, 1), ("active", 2, 1), ("inactive", 2, 1),
    ("test_scope", 2, 1), (None, 2, 999), ("correct", 2, 1), ("system", 2, 1),
])
def test_practice_again_rejects_foreign_formal_unavailable_or_ineligible_answers(tmp_path, change, user_id, answer_id):
    settings = seed_stack(tmp_path, change)
    with database(settings.database_path) as connection:
        if change == "formal":
            connection.execute("UPDATE interview_sessions SET interview_mode='real'")
        elif change == "active":
            connection.execute("UPDATE interview_sessions SET status='active'")
        elif change == "inactive":
            connection.execute("UPDATE questions SET active=0")
        elif change == "test_scope":
            connection.execute("UPDATE questions SET bank_scope='test'")
    with pytest.raises(InterviewError):
        start_practice_again(settings, "session-1", user_id=user_id, candidate_name="Candidate", answer_id=answer_id)
    with database(settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM interview_sessions").fetchone()[0] == 1


def report_fixtures(tmp_path):
    from test_report_render import Ids
    reports = {}
    for case in ("correct", "incomplete", "wrong", "system", "uncertain"):
        folder = tmp_path / case
        folder.mkdir()
        settings = seed_stack(folder, case)
        report = interview_report(settings, "session-1")
        report["grading"] = {"state": "completed", "report_ready": True, "report_available": True,
            "answer_count": 1, "processed_count": 1, "pending_count": 0, "can_retry": False}
        # The real question bank uses a descriptive subject name; exercise code labels too.
        report["answers"][0]["question"]["subject"] = "DSA101"
        report["summary"]["practice_grading"] = practice_summary(report["answers"], completed=True)
        reports[case] = report
    full = reports["correct"]
    def mixed_with(second_case):
        mixed = copy.deepcopy(full)
        second = copy.deepcopy(reports[second_case]["answers"][0])
        second.update(answer_id=2, sequence_number=2)
        mixed["answers"].append(second)
        mixed["session"].update(requested_count=2, answered_count=2)
        mixed["summary"]["practice_grading"] = practice_summary(mixed["answers"], completed=True)
        mixed["summary"]["learning_feedback"] = session_feedback(mixed["answers"])
        mixed["grading"].update(answer_count=2, processed_count=2)
        return mixed
    mixed = mixed_with("uncertain")
    failed = mixed_with("system")
    failed["grading"].update(state="failed", report_ready=False, pending_count=1, processed_count=1,
                             attempts=3, error="model_timeout")
    parser = Ids()
    root = Path(__file__).parents[1]
    parser.feed((root / "app/static/index.html").read_text(encoding="utf-8"))
    weighted = evaluation(["met", "met", "unresolved"], score_provisional=True)
    weighted["score_breakdown"] = question_breakdown(QUESTION, weighted, completed=True)
    history = {**mixed["session"], "score_status": "insufficient_evidence", "final_score": None,
        "scored_answer_count": 1, "stored_answer_count": 2, "can_view_report": True}
    return {"ids": parser.ids, "full": full, "mixed": mixed, "failed": failed,
            "history": history, "weighted": weighted, "scenarios": reports}


def test_report_rendering_and_button_lifecycle_from_saved_report_fixtures(tmp_path):
    node = os.environ.get("NODE_BINARY") or shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for report rendering checks")
    root = Path(__file__).parents[1]
    fixture = tmp_path / "feedback-report-fixtures.json"
    fixture.write_text(json.dumps(report_fixtures(tmp_path), ensure_ascii=False), encoding="utf-8")
    for script in ("report_render.cjs", "report_lifecycle.cjs", "auth_lifecycle.cjs"):
        result = subprocess.run([node, str(Path(__file__).with_name(script)),
            str(root / "app/static/app.js"), str(fixture)], capture_output=True,
            text=True, encoding="utf-8", timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr


def test_practice_again_api_auth_and_new_session_payload(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.services.auth import COOKIE_NAME, create_session
    from app.services.runtime_readiness import RuntimeReadiness
    settings = seed_stack(tmp_path)
    monkeypatch.setattr(RuntimeReadiness, "start", lambda self: None)
    with TestClient(create_app(settings)) as client:
        path = "/api/interviews/session-1/practice-again"
        assert client.post(path, json={"answer_id": 1}).status_code == 401
        teacher, _ = create_session(settings.database_path, user_id=1)
        client.cookies.set(COOKIE_NAME, teacher)
        assert client.post(path, json={"answer_id": 1}).status_code == 403
        candidate, _ = create_session(settings.database_path, user_id=2)
        client.cookies.set(COOKIE_NAME, candidate)
        for body in ({"answer_id": True}, {"answer_id": 0}, {"answer_id": "1"}, {"answer_id": 1, "score": 10}):
            assert client.post(path, json=body).status_code == 422
        response = client.post(path, json={"answer_id": 1})
        assert response.status_code == 201, response.text
        assert response.json()["question_selection"] == "fixed"
        assert response.json()["grading_strategy"] == "end_of_session"
        assert response.json()["answer_mode"] == "voice"
