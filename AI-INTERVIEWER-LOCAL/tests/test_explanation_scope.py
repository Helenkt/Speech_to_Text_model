"""A known term is not proof when its explanation changes the meaning."""
import asyncio

import pytest

from app.services import evaluator
from app.services.fact_guard import check_rubric_point
from app.services.interview_engine import interview_report, list_practice_history
from test_grading_reliability import saved_practice
from test_teacher_strong_review import _settings


@pytest.mark.parametrize("point,tail", [
    ("Stack là cấu trúc LIFO", "Nó lấy cái vào trước ra trước"),
    ("Stack uses LIFO", "That means the first item inserted is removed first"),
    ("Stack uses LIFO", "It removes the oldest item first"),
    ("NULL là không xác định/chưa có dữ liệu", "Ý em là nó bằng số 0"),
    ("Lớp con kế thừa thuộc tính và phương thức từ lớp cha",
     "Tức là những thứ đó đi từ con sang cha"),
    ("Parameters are updated in the opposite gradient direction",
     "In other words they follow the gradient"),
    ("Primary key cannot be NULL", "It can be NULL when no record exists"),
])
def test_unparsed_explanation_defers_whole_claim_including_generic_copula(point, tail):
    answer = f"{point}. {tail}."
    question = {"question": "Explain this concept", "key_points": [point]}
    result = check_rubric_point(question, answer, point)
    assert result.status == "unknown"
    assert result.verification_rule.endswith(":unparsed_scope")


@pytest.mark.parametrize("tail,status", [
    ("Nghĩa là cái vào sau sẽ được lấy ra trước", "supported"),
    ("Nghĩa là cái vào trước sẽ được lấy ra trước", "conflicted"),
    ("Queue theo FIFO", "supported"),
])
def test_closed_continuations_and_independent_subjects_remain_fast(tail, status):
    point = "Stack theo LIFO"
    assert check_rubric_point({"question": "Stack là gì", "key_points": [point]},
                              f"{point}. {tail}.", point).status == status


@pytest.mark.parametrize("mode", ["auto", "transformer", "ollama"])
@pytest.mark.parametrize("model_status", ["met", "contradicted", "unresolved"])
def test_semantic_model_can_adjudicate_deferred_scope(tmp_path, monkeypatch, mode, model_status):
    settings = _settings(tmp_path)
    settings.evaluator_mode = mode
    point = "NULL là không xác định/chưa có dữ liệu"
    answer = point + ". Ý em là nó bằng số 0."
    question = {"question": "NULL là gì", "language": "vi", "key_points": [point]}
    calls = []

    def semantic(_path, asked, text, **_kwargs):
        calls.append(text)
        return evaluator._compose_result(asked, [{"point": point, "status": model_status,
            "needs_review": model_status == "unresolved", "evidence_quote": text}],
            evaluator="test-semantic", confidence=.99)

    async def llm(_settings, asked, text, **kwargs):
        return semantic(None, asked, text, **kwargs)

    monkeypatch.setattr(evaluator, "evaluate_with_transformer", semantic)
    monkeypatch.setattr(evaluator, "evaluate_with_ollama", llm)
    result = asyncio.run(evaluator.evaluate_answer(settings, question, answer))
    assert calls and all(text == answer for text in calls)
    assert result["point_assessments"][0]["status"] == model_status
    assert result["score_provisional"] is (model_status == "unresolved")


@pytest.mark.parametrize("score,expected", [(50, 50), (80, None)])
def test_history_distinguishes_verified_mean_from_whole_grade(tmp_path, score, expected):
    settings = _settings(tmp_path)
    saved_practice(settings, score=score)
    item = list_practice_history(settings.database_path, user_id=2)[0]
    grade = interview_report(settings, "session-1")["summary"]["practice_grading"]["session"]
    assert item["final_score"] == expected
    assert item["scored_answer_count"] == grade["scored_question_count"]
    assert item["unscored_answer_count"] == grade["unscored_question_count"]
    assert item["score_status"] == ("final" if expected is not None else "incomplete")
    assert item["scored_only_average"] == item["average_score"]
