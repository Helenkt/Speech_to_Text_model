from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable


DIFFICULTY_ORDER = ("Easy", "Medium", "Hard")
DEFAULT_RUBRIC_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "question_generation_rubric.json"
)


class QuestionRubricError(ValueError):
    pass


def load_question_rubric(path: Path | None = None) -> dict[str, Any]:
    rubric_path = path or DEFAULT_RUBRIC_PATH
    try:
        rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QuestionRubricError(f"Không đọc được rubric: {exc}") from exc

    total_weight = sum(
        int(dimension.get("weight", 0))
        for dimension in rubric.get("scoring_dimensions", [])
    )
    if total_weight != 100:
        raise QuestionRubricError("Tổng trọng số rubric phải bằng 100")
    if tuple(rubric.get("difficulty_levels", {}).keys()) != DIFFICULTY_ORDER:
        raise QuestionRubricError("Rubric phải khai báo theo thứ tự Easy, Medium, Hard")
    return rubric


def next_difficulty(
    current: str,
    score: float,
    confidence: float,
    rubric: dict[str, Any] | None = None,
) -> str:
    config = (rubric or load_question_rubric())["progression"]
    if current not in DIFFICULTY_ORDER:
        raise QuestionRubricError("Độ khó hiện tại không hợp lệ")

    rank = DIFFICULTY_ORDER.index(current)
    if (
        score >= float(config["promotion_score"])
        and confidence >= float(config["minimum_evaluation_confidence"])
    ):
        rank = min(rank + 1, len(DIFFICULTY_ORDER) - 1)
    elif score < float(config["demotion_score"]):
        rank = max(rank - 1, 0)

    proposed = DIFFICULTY_ORDER[rank]
    if proposed not in config["allowed_transitions"][current]:
        raise QuestionRubricError(f"Chuyển cấp không hợp lệ: {current} -> {proposed}")
    return proposed


def build_generation_prompt(
    *,
    source_questions: list[dict[str, Any]],
    target_difficulty: str,
    language: str,
    subject: str,
    rubric: dict[str, Any] | None = None,
) -> str:
    config = rubric or load_question_rubric()
    profile = config["difficulty_levels"].get(target_difficulty)
    if not profile:
        raise QuestionRubricError("Độ khó cần sinh không hợp lệ")
    if language not in {"vi", "en"}:
        raise QuestionRubricError("Ngôn ngữ cần sinh phải là vi hoặc en")
    if not source_questions:
        raise QuestionRubricError("Cần ít nhất một câu nguồn đã duyệt")

    compact_sources = [
        {
            "id": item.get("id"),
            "topic": item.get("topic"),
            "concept": item.get("concept"),
            "question": item.get("question"),
            "reference_answer": item.get("reference_answer"),
            "key_points": item.get("key_points"),
        }
        for item in source_questions
    ]
    required_fields = config["required_output_fields"]
    evidence_fields = config["difficulty_evidence_fields"]
    return (
        "Bạn là bộ sinh câu hỏi phỏng vấn kiến thức chạy local.\n"
        "Chỉ được sử dụng thông tin trong SOURCE_QUESTIONS bên dưới. "
        "Không dùng Internet, kiến thức nền của model hoặc tự thêm dữ kiện.\n"
        f"Hãy sinh đúng 1 câu hỏi bằng ngôn ngữ '{language}' cho môn '{subject}' "
        f"ở mức '{target_difficulty}'.\n"
        "Câu hỏi phải phù hợp để nghe một lần và trả lời bằng giọng nói.\n"
        f"Hồ sơ độ khó bắt buộc: {json.dumps(profile, ensure_ascii=False)}\n"
        f"Các trường JSON bắt buộc: {json.dumps(required_fields, ensure_ascii=False)}\n"
        f"difficulty_evidence phải có: {json.dumps(evidence_fields, ensure_ascii=False)}\n"
        "source_question_ids chỉ được chứa ID xuất hiện trong SOURCE_QUESTIONS.\n"
        "source_evidence phải chỉ ra từng ý trong đáp án được hỗ trợ bởi ID nguồn nào.\n"
        "Không đưa đáp án vào câu hỏi. Chỉ trả về một JSON object hợp lệ, không Markdown.\n"
        f"SOURCE_QUESTIONS={json.dumps(compact_sources, ensure_ascii=False)}"
    )


def _in_range(value: Any, limits: dict[str, int]) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and limits["min"] <= value <= limits["max"]
    )


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalized_text(left), _normalized_text(right)).ratio()


def validate_generated_question(
    candidate: dict[str, Any],
    *,
    existing_questions: Iterable[str] = (),
    approved_source_ids: set[str] | None = None,
    rubric: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = rubric or load_question_rubric()
    failures: list[str] = []
    findings: list[str] = []
    required = config["required_output_fields"]

    missing = [field for field in required if not candidate.get(field)]
    if missing:
        failures.append(f"G2_SCHEMA: thiếu {', '.join(missing)}")

    difficulty = candidate.get("difficulty")
    profile = config["difficulty_levels"].get(difficulty)
    evidence = candidate.get("difficulty_evidence")
    if not profile:
        failures.append("G4_DIFFICULTY: difficulty phải là Easy, Medium hoặc Hard")
    if not isinstance(evidence, dict):
        failures.append("G4_DIFFICULTY: thiếu difficulty_evidence")
        evidence = {}

    source_ids = candidate.get("source_question_ids")
    if not isinstance(source_ids, list) or not source_ids:
        failures.append("G1_SOURCE: cần ít nhất một source_question_id")
        source_ids = []
    elif approved_source_ids is not None:
        unknown_ids = sorted(set(map(str, source_ids)) - approved_source_ids)
        if unknown_ids:
            failures.append(f"G1_SOURCE: ID nguồn không hợp lệ: {', '.join(unknown_ids)}")

    source_evidence = candidate.get("source_evidence")
    if not isinstance(source_evidence, list) or not source_evidence:
        failures.append("G1_SOURCE: thiếu bằng chứng truy vết về nguồn")

    difficulty_checks: list[bool] = []
    if profile:
        bloom_valid = candidate.get("bloom_level") in profile["bloom_levels"]
        difficulty_checks.append(bloom_valid)
        if not bloom_valid:
            findings.append("Mức Bloom không phù hợp với độ khó đã chọn")

        for field in ("concept_count", "reasoning_steps", "constraint_count"):
            valid = _in_range(evidence.get(field), profile[field])
            difficulty_checks.append(valid)
            if not valid:
                findings.append(f"{field} nằm ngoài phạm vi của mức {difficulty}")

        duration_valid = _in_range(
            evidence.get("expected_answer_seconds"),
            profile["expected_answer_seconds"],
        )
        difficulty_checks.append(duration_valid)
        if not duration_valid:
            findings.append("Thời lượng trả lời dự kiến không phù hợp")

        key_points = candidate.get("key_points")
        key_point_count = len(key_points) if isinstance(key_points, list) else 0
        key_points_valid = profile["key_points"]["min"] <= key_point_count <= profile["key_points"]["max"]
        difficulty_checks.append(key_points_valid)
        if not key_points_valid:
            findings.append("Số key points không phù hợp với độ khó")

        if not evidence.get("justification"):
            difficulty_checks.append(False)
            findings.append("Thiếu giải thích vì sao câu hỏi thuộc cấp độ đã chọn")

    if profile and not all(difficulty_checks):
        failures.append("G4_DIFFICULTY: bằng chứng độ khó không đạt")

    question = str(candidate.get("question") or "").strip()
    reference = str(candidate.get("reference_answer") or "").strip()
    if reference and len(reference) >= 20 and _normalized_text(reference) in _normalized_text(question):
        failures.append("G5_NO_LEAKAGE: câu hỏi chứa nguyên đáp án tham chiếu")

    duplicate_threshold = float(config["generation_policy"]["duplicate_similarity_threshold"])
    max_similarity = max(
        (_similarity(question, existing) for existing in existing_questions),
        default=0.0,
    )
    if max_similarity >= duplicate_threshold:
        failures.append(
            f"G6_UNIQUENESS: độ tương đồng {max_similarity:.2f} vượt ngưỡng {duplicate_threshold:.2f}"
        )

    language = str(candidate.get("language") or "").lower()
    clarity_valid = 20 <= len(question) <= 500 and question.endswith("?")
    if not clarity_valid:
        failures.append("G7_ORAL_SUITABILITY: câu hỏi chưa phù hợp để hỏi bằng lời nói")

    key_points = candidate.get("key_points")
    key_points_valid = (
        isinstance(key_points, list)
        and bool(key_points)
        and all(isinstance(point, str) and point.strip() for point in key_points)
        and len({_normalized_text(point) for point in key_points}) == len(key_points)
    )
    if not key_points_valid:
        failures.append("G3_ALIGNMENT: key_points rỗng, trùng hoặc sai định dạng")

    dimensions = {
        "source_grounding": 20 if source_ids and source_evidence else 0,
        "learning_objective": 10 if candidate.get("learning_objective") and candidate.get("concept") else 0,
        "difficulty_alignment": 25 if difficulty_checks and all(difficulty_checks) else 0,
        "reference_correctness": 15 if reference else 0,
        "key_points_quality": 10 if key_points_valid else 0,
        "clarity_oral": 10 if clarity_valid else 0,
        "language_quality": 5 if language in {"vi", "en"} else 0,
        "uniqueness": 5 if max_similarity < duplicate_threshold else 0,
    }
    score = sum(dimensions.values())
    if failures or score < int(config["generation_policy"]["teacher_review_min_score"]):
        status = "rejected"
    elif score < int(config["generation_policy"]["practice_auto_approval_min_score"]):
        status = "teacher_review"
    else:
        status = "practice_eligible"

    return {
        "rubric_id": config["rubric_id"],
        "score": score,
        "status": status,
        "hard_gate_failures": failures,
        "dimension_scores": dimensions,
        "findings": findings,
        "maximum_duplicate_similarity": round(max_similarity, 4),
        "semantic_review_required": True,
        "real_exam_teacher_approval_required": bool(
            config["generation_policy"]["real_exam_requires_teacher_approval"]
        ),
    }
