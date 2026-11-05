import copy
import json
import random

import pytest

from app.database import database
from app.services.interview_engine import interview_report
from app.services.practice_grading import practice_summary, question_breakdown
from app.services.rubric_contract import digest, rubric_draft
from test_teacher_strong_review import _seed_voice_answer, _settings


POINTS = ["The first required claim.", "The second required claim.", "The third required claim."]
QUESTION = {"uid": "q1", "question": "Explain the topic.", "reference_answer": "Reference.",
            "subject": "AI101", "language": "en", "competency": "Understanding", "key_points": POINTS,
            "key_point_weights": dict(zip(POINTS, [4, 3, 3]))}


def evaluation(statuses, score=None, **extra):
    return {"final_score": score, "point_assessments": [
        {"point": point, "status": status} for point, status in zip(POINTS, statuses)], **extra}


def test_verified_wrong_criterion_is_zero_but_keeps_its_weight():
    result = question_breakdown(QUESTION, evaluation(["met", "met", "contradicted"], 70), completed=True)
    assert result["score"] == result["confirmed_points"] == 7
    assert result["status"] == "final" and result["possible_score_interval"] == [7, 7]
    assert [c["earned_points"] for c in result["criteria"]] == [4, 3, 0]


def test_unresolved_is_neither_zero_nor_half_credit_and_does_not_renormalize():
    result = question_breakdown(QUESTION, evaluation(["met", "met", "unresolved"], score_provisional=True), completed=True)
    assert result["score"] is None and result["confirmed_points"] == 7
    assert result["possible_score_interval"] == [7, 10]
    assert result["criteria"][2]["earned_points"] is None
    assert result["unresolved_criterion_count"] == 1


@pytest.mark.parametrize("extra,completed", [({}, False), ({"grading_pending": True}, True),
    ({"recognition_status": "needs_review", "score_provisional": True}, True)])
def test_pending_or_untrusted_audio_does_not_publish_criterion_credit(extra, completed):
    result = question_breakdown(QUESTION, evaluation(["met"] * 3, 100, **extra), completed=completed)
    assert result["score"] is None and result["confirmed_points"] == 0
    assert result["possible_score_interval"] == [0, 10]
    assert all(c["earned_points"] is None for c in result["criteria"])


def test_atomic_partial_remains_unresolved():
    contract = rubric_draft(QUESTION)
    for item in contract["criteria"]:
        item["weight"] = QUESTION["key_point_weights"][item["claim"]]
    question = {**QUESTION, "rubric_snapshot": {"contract": contract, "sha256": digest(contract)}}
    result = question_breakdown(question, evaluation(["met", "met", "partial"], 85), completed=True)
    assert result["score"] is None and result["possible_score_interval"] == [7, 10]
    assert result["criteria"][2]["credit_policy"] == "binary"


def test_legacy_explicit_partial_is_not_silently_reinterpreted():
    result = question_breakdown(QUESTION, evaluation(["met", "met", "partial"], 85), completed=True)
    assert result["score"] == 8.5 and result["criteria"][2]["earned_points"] == 1.5


@pytest.mark.parametrize("weights", [{POINTS[0]: 4}, {p: float("nan") for p in POINTS},
    {p: True for p in POINTS}, {p: -1 for p in POINTS}, [], "", 0, False])
def test_invalid_weights_have_no_publishable_score(weights):
    result = question_breakdown({**QUESTION, "key_point_weights": weights}, evaluation(["met"] * 3, 100), completed=True)
    assert result["status"] == "invalid_rubric" and result["score"] is None


@pytest.mark.parametrize("assessments", [[], [{"point": POINTS[0], "status": "met"}] * 3,
    [{"point": p, "status": "met"} for p in [POINTS[0], POINTS[1], "unknown"]]])
def test_incomplete_or_duplicate_assessments_cannot_earn_points(assessments):
    result = question_breakdown(QUESTION, {"final_score": 100, "point_assessments": assessments}, completed=True)
    assert result["score"] is None and result["possible_score_interval"] == [0, 10]


def test_stored_score_must_match_saved_rubric_outcomes():
    result = question_breakdown(QUESTION, evaluation(["met", "met", "missing"], 100), completed=True)
    assert result["status"] == "score_mismatch" and result["score"] is None


@pytest.mark.parametrize("status", [[], {}, 0, None])
def test_malformed_status_is_unresolved_not_a_report_crash(status):
    result = question_breakdown(QUESTION, evaluation(["met", "met", status], 70), completed=True)
    assert result["score"] is None and result["possible_score_interval"] == [7, 10]


def test_null_optional_rubric_snapshot_keeps_legacy_scoring():
    result = question_breakdown({**QUESTION, "rubric_snapshot": None},
                                evaluation(["met", "met", "missing"], 70), completed=True)
    assert result["score"] == 7


def test_stale_snapshot_is_not_silently_scored_against_new_weights():
    question = {**QUESTION, "rubric_snapshot": {"contract": rubric_draft(QUESTION), "sha256": "forged"}}
    result = question_breakdown(question, evaluation(["met"] * 3, 100), completed=True)
    assert result["status"] == "invalid_rubric" and result["score"] is None


def detail(subject, statuses, score=None):
    question = {**QUESTION, "subject": subject}
    result = question_breakdown(question, evaluation(statuses, score), completed=True)
    return {"question": question, "evaluation": {"score_breakdown": result}}


def test_summary_does_not_present_the_finalized_subset_as_the_whole_session_score():
    answers = [detail("AI101", ["met", "met", "missing"], 70),
               detail("DB101", ["met", "met", "unresolved"])]
    result = practice_summary(answers, completed=True)
    assert result["session"]["score"] is None
    assert result["session"]["scored_only_average"] == 7
    assert result["session"]["possible_score_interval"] == [7, 8.5]
    assert [row["score"] for row in result["subjects"]] == [7, None]
    assert result["grading_owner"] == "ai"


def test_final_session_mean_is_equal_question_weight_not_total_criterion_weight():
    answers = [detail("AI101", ["met", "met", "missing"], 70), detail("DB101", ["met"] * 3, 100)]
    result = practice_summary(answers, completed=True)
    assert result["session"]["score"] == 8.5 and result["session"]["status"] == "final"
    assert result["session"]["scored_question_count"] == 2
    assert len(result["competencies"]) == 2


def test_empty_practice_is_not_zero_or_a_final_score():
    result = practice_summary([], completed=True)["session"]
    assert result["score"] is None and result["question_count"] == 0


def test_two_thousand_random_weighted_intervals_and_input_immutability():
    rng = random.Random(20261027)
    for _ in range(2000):
        count = rng.randrange(1, 31)
        points = [f"Rubric criterion {i}." for i in range(count)]
        weights = {p: rng.uniform(.1, 100) for p in points}
        statuses = {p: rng.choice(["met", "missing", "contradicted", "unresolved"]) for p in points}
        question = {**QUESTION, "key_points": points, "key_point_weights": weights}
        evaluation = {"final_score": None, "point_assessments": [{"point": p, "status": statuses[p]} for p in points]}
        before = copy.deepcopy((question, evaluation))
        result = question_breakdown(question, evaluation, completed=True)
        low = 10 * sum(weights[p] for p in points if statuses[p] == "met") / sum(weights.values())
        high = low + 10 * sum(weights[p] for p in points if statuses[p] == "unresolved") / sum(weights.values())
        assert result["possible_score_interval"] == [round(low, 2), round(high, 2)]
        assert result["score"] is None and (question, evaluation) == before


def seed_practice(settings):
    question = _seed_voice_answer(settings)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_sessions SET interview_mode='practice'")
        connection.execute("UPDATE interview_answers SET score=50,ai_score=50,final_score=50,score_provisional=0,assessment_json=?",
            (json.dumps([{"point": p, "status": "met" if i == 0 else "missing"}
                         for i, p in enumerate(question["key_points"])]),))
    return question


def test_report_exposes_scores_without_changing_saved_answer_or_schema(tmp_path):
    settings = _settings(tmp_path)
    seed_practice(settings)
    with database(settings.database_path) as connection:
        before = dict(connection.execute("SELECT * FROM interview_answers").fetchone())
    report = interview_report(settings, "session-1")
    assert report["answers"][0]["evaluation"]["score_breakdown"]["score"] == 5
    assert report["summary"]["practice_grading"]["session"]["score"] == 5
    assert report["summary"]["average_score"] == 50
    with database(settings.database_path) as connection:
        assert dict(connection.execute("SELECT * FROM interview_answers").fetchone()) == before


def test_pending_grading_is_not_counted_even_if_a_stale_final_score_exists(tmp_path):
    settings = _settings(tmp_path)
    seed_practice(settings)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET grading_pending=1")
    report = interview_report(settings, "session-1")
    assert report["summary"]["average_score"] is None
    assert report["summary"]["practice_grading"]["session"]["score"] is None
    assert report["answers"][0]["evaluation"]["score_breakdown"]["status"] == "pending"


def test_formal_exam_has_no_practice_grade_and_preserves_teacher_authority(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    report = interview_report(settings, "session-1")
    assert "practice_grading" not in report["summary"]
    assert "score_breakdown" not in report["answers"][0]["evaluation"]
    assert report["answers"][0]["evaluation"]["grading_owner"] == "teacher"


def test_report_endpoint_returns_new_backend_fields(client, test_settings, login_candidate):
    user_id = login_candidate["user_id"]
    question = {**QUESTION, "id": "q1", "difficulty": "Easy", "topic": "Learning", "concept": "Learning"}
    with database(test_settings.database_path) as connection:
        connection.execute("""INSERT INTO interview_sessions(session_id,user_id,candidate_name,interview_mode,
            answer_mode,language,subject,requested_count,answered_count,current_difficulty_rank,evaluator_requested,status,created_at)
            VALUES ('practice-score',?,'Candidate','practice','voice','en','AI101',1,1,1,'auto','completed','now')""", (user_id,))
        connection.execute("""INSERT INTO interview_answers(session_id,sequence_number,question_uid,question_json,
            answer_text,score,ai_score,final_score,verdict,matched_points_json,missing_points_json,feedback,confidence,
            evaluator,assessment_json,review_required,score_provisional,created_at)
            VALUES ('practice-score',1,'q1',?,'Answer',70,70,70,'Partial','[]','[]','Feedback',.9,'test',?,0,0,'now')""",
            (json.dumps(question), json.dumps(evaluation(["met", "met", "missing"])["point_assessments"])))
    response = client.get("/api/interviews/practice-score/report")
    assert response.status_code == 200, response.text
    assert response.json()["summary"]["practice_grading"]["session"]["score"] == 7
