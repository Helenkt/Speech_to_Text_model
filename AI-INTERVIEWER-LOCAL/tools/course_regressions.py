"""Course-grounded behavioral checks; not an independent student accuracy benchmark."""
from __future__ import annotations

import json
from pathlib import Path


def course_cases(data_dir: Path) -> list[dict]:
    chosen = {"AI_002": "AI101", "DB_008": "DB101", "DSA_001": "DSA101", "OOP_006": "OOP101"}
    cases = []
    for path in sorted(data_dir.glob("*.json")):
        rows = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(rows, list):
            continue
        for question_id, subject in chosen.items():
            selected = [row for row in rows if row.get("question_id") == question_id]
            points = list(dict.fromkeys(row["reference_claim"] for row in selected))[:2]
            if len(points) != 2:
                continue
            question = {"question": selected[0]["question"], "reference_answer": "; ".join(points),
                        "key_points": points, "language": "vi", "subject_code": subject}
            first, second = points
            variants = [
                ("complete", f"{first}. {second}.", 100),
                ("missing_one", f"{first}.", 50),
                ("partial_disclaimer", f"Em không nhớ phần còn lại. Tuy nhiên {second}.", 50),
                ("refuted_misconception", f"Phát biểu 'không đúng là {first}' là sai. {first}. {second}.", 100),
                ("both_rejected", f"Không đúng là {first}. Không đúng là {second}.", 0),
            ]
            for kind, answer, score in variants:
                cases.append({"id": f"{subject}_{kind}", "question": question, "answer": answer,
                              "expected_score": [score, score],
                              "source": {"file": path.name, "question_id": question_id},
                              "data_origin": "derived_course_regression_not_teacher_validated"})
    if len(cases) != 20:
        raise ValueError("Expected five behavioral cases for each of four approved course sources")
    return cases
