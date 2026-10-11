import json

from app.services.question_generation_rubric import (
    build_generation_prompt,
    load_question_rubric,
    next_difficulty,
    validate_generated_question,
)


def _candidate(difficulty: str) -> dict:
    profiles = {
        "Easy": ("understand", 1, 1, 0, 30, 2),
        "Medium": ("apply", 2, 2, 1, 60, 3),
        "Hard": ("evaluate", 3, 4, 3, 120, 5),
    }
    bloom, concepts, steps, constraints, seconds, point_count = profiles[difficulty]
    return {
        "id": f"GEN_{difficulty.upper()}_001",
        "language": "vi",
        "subject": "AI101",
        "competency": "Hiểu khái niệm",
        "topic": "Machine Learning",
        "concept": "Mô hình học máy",
        "difficulty": difficulty,
        "bloom_level": bloom,
        "learning_objective": "Đánh giá khả năng vận dụng khái niệm học máy",
        "question": "Hãy giải thích cách áp dụng khái niệm này trong một tình huống cụ thể?",
        "reference_answer": "Câu trả lời phải nêu đúng khái niệm và cách áp dụng theo dữ liệu nguồn.",
        "key_points": [f"Ý đánh giá {index}" for index in range(1, point_count + 1)],
        "source_question_ids": ["AI101_VI_001"],
        "source_evidence": [
            {
                "source_question_id": "AI101_VI_001",
                "supported_claim": "Khái niệm và đáp án đều có trong câu nguồn",
            }
        ],
        "difficulty_evidence": {
            "concept_count": concepts,
            "reasoning_steps": steps,
            "constraint_count": constraints,
            "expected_answer_seconds": seconds,
            "justification": "Các chỉ số nằm trong phạm vi của cấp độ yêu cầu.",
        },
    }


def test_rubric_is_valid_and_weights_total_100(project_root):
    rubric = load_question_rubric(
        project_root / "data" / "question_generation_rubric.json"
    )
    assert sum(item["weight"] for item in rubric["scoring_dimensions"]) == 100
    assert list(rubric["difficulty_levels"]) == ["Easy", "Medium", "Hard"]
    json.dumps(rubric, ensure_ascii=False)


def test_each_difficulty_profile_can_pass_structural_validation():
    for difficulty in ("Easy", "Medium", "Hard"):
        result = validate_generated_question(_candidate(difficulty))
        assert result["score"] == 100
        assert result["status"] == "practice_eligible"
        assert result["hard_gate_failures"] == []


def test_hard_label_is_rejected_when_evidence_is_easy():
    candidate = _candidate("Hard")
    candidate["difficulty_evidence"].update(
        concept_count=1,
        reasoning_steps=1,
        constraint_count=0,
        expected_answer_seconds=30,
    )
    candidate["key_points"] = candidate["key_points"][:2]

    result = validate_generated_question(candidate)

    assert result["status"] == "rejected"
    assert any("G4_DIFFICULTY" in failure for failure in result["hard_gate_failures"])


def test_unknown_source_and_duplicate_are_rejected():
    candidate = _candidate("Easy")
    result = validate_generated_question(
        candidate,
        existing_questions=[candidate["question"]],
        approved_source_ids={"OTHER_ID"},
    )

    assert result["status"] == "rejected"
    assert any("G1_SOURCE" in failure for failure in result["hard_gate_failures"])
    assert any("G6_UNIQUENESS" in failure for failure in result["hard_gate_failures"])


def test_evidence_quote_must_exist_verbatim_in_approved_source():
    candidate = _candidate("Easy")
    candidate["source_evidence"][0]["evidence_quote"] = "Nội dung không có trong nguồn"
    result = validate_generated_question(
        candidate,
        approved_source_ids={"AI101_VI_001"},
        approved_sources={
            "AI101_VI_001": {
                "reference_answer": "Mô hình học quy luật từ dữ liệu.",
                "key_points": ["Học từ dữ liệu"],
            }
        },
    )

    assert result["status"] == "rejected"
    assert any("evidence_quote" in failure for failure in result["hard_gate_failures"])


def test_progression_never_skips_a_level():
    assert next_difficulty("Easy", 90, 0.9) == "Medium"
    assert next_difficulty("Medium", 90, 0.9) == "Hard"
    assert next_difficulty("Easy", 90, 0.4) == "Easy"
    assert next_difficulty("Hard", 20, 0.9) == "Medium"
    assert next_difficulty("Medium", 60, 0.9) == "Medium"


def test_generation_prompt_limits_the_model_to_approved_sources():
    prompt = build_generation_prompt(
        source_questions=[
            {
                "id": "AI101_VI_001",
                "topic": "Machine Learning",
                "concept": "Mô hình",
                "question": "Mô hình học máy là gì?",
                "reference_answer": "Mô tả trong nguồn.",
                "key_points": ["Ý trong nguồn", "Ví dụ trong nguồn"],
            }
        ],
        target_difficulty="Medium",
        language="vi",
        subject="AI101",
    )

    assert "Không dùng Internet" in prompt
    assert "AI101_VI_001" in prompt
    assert 'mức \'Medium\'' in prompt
    assert "Chỉ trả về một JSON object hợp lệ" in prompt
