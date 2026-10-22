from app.services.fact_guard import (
    analyze_fact_consistency,
    contradiction_evaluation,
    extract_entity_values,
)


SCORE_QUESTION = {
    "language": "vi",
    "question": "Minh được 9 điểm, Lan được 7 điểm. Ai có điểm cao hơn?",
    "reference_answer": "Minh có điểm cao hơn Lan vì 9 lớn hơn 7.",
    "key_points": ["Xác định đúng Minh có điểm cao hơn Lan"],
}


def test_extracts_numbers_and_units_from_question():
    assert extract_entity_values(SCORE_QUESTION["question"]) == {
        "minh": (9.0, "point"),
        "lan": (7.0, "point"),
    }


def test_rejects_reversed_person_score_comparison():
    result = analyze_fact_consistency(SCORE_QUESTION, "Lan cao hơn Minh.")

    assert result.status == "contradicted"
    assert result.confidence >= 0.99
    assert set(result.entities) == {"minh", "lan"}


def test_accepts_correct_person_score_comparison():
    result = analyze_fact_consistency(SCORE_QUESTION, "Minh cao hơn Lan.")

    assert result.status == "supported"
    assert result.confidence >= 0.99


def test_rejects_changed_numeric_fact():
    result = analyze_fact_consistency(SCORE_QUESTION, "Minh được 6 điểm.")

    assert result.status == "contradicted"
    assert "6" in result.reason
    assert "9" in result.reason


def test_numeric_contradiction_produces_zero_score_and_teacher_review():
    check = analyze_fact_consistency(SCORE_QUESTION, "Lan cao hơn Minh.")
    result = contradiction_evaluation(SCORE_QUESTION, "Lan cao hơn Minh.", check)

    assert result["score"] == 0
    assert result["contradicted_points"] == SCORE_QUESTION["key_points"]
    assert result["review_required"] is True
    assert result["evaluator"] == "factguard-v1"


def test_rejects_direct_vietnamese_negation_of_rubric_claim():
    question = {
        "language": "vi",
        "question": "Lớp là gì?",
        "reference_answer": "Lớp là khuôn mẫu.",
        "key_points": ["Lớp là khuôn mẫu"],
    }

    result = analyze_fact_consistency(question, "Lớp không phải là khuôn mẫu.")

    assert result.status == "contradicted"
    assert result.confidence >= 0.99
