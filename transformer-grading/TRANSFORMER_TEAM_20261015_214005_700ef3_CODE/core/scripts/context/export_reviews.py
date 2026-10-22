from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3


def main():
    parser = argparse.ArgumentParser(description="Export teacher-reviewed real answers as DRAFT criterion labels for human annotation.")
    parser.add_argument("--database", default="data/ai_interviewer.db")
    parser.add_argument("--output", default="data/context/human_annotation.draft.jsonl")
    args = parser.parse_args()
    db = Path(args.database).resolve()
    if not db.is_file():
        parser.error("Chưa có database")
    output = Path(args.output)
    if output.exists():
        parser.error("Output đã tồn tại; chọn tên mới để giữ nhãn GV đã sửa")
    # Read-only SQLite connection; no writes to interviews or grades.
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT answer_id, question_json, answer_text, teacher_score, assessment_json "
                                  "FROM interview_answers WHERE reviewed_at IS NOT NULL ORDER BY answer_id").fetchall()
    exported = []
    for row in rows:
        q = json.loads(row["question_json"])
        suggested = {a["point"]: a.get("status") for a in json.loads(row["assessment_json"] or "[]")}
        for i, point in enumerate(q["key_points"], 1):
            exported.append({"label_id": f"H_{row['answer_id']}_R{i}", "answer_id": f"H_{row['answer_id']}",
                             "question_id": q.get("id", q.get("uid", "unknown")), "question": q["question"],
                             "rubric_criterion_id": f"R{i}", "criterion": point,
                             "reference_claim": point, "student_answer": row["answer_text"],
                             "relation_label": "", "coverage_level": "", "evidence_quote": "",
                             "teacher_points": None, "max_points": 2,
                             "teacher_total_score_context_only": row["teacher_score"],
                             "ai_suggestion_do_not_treat_as_ground_truth": suggested.get(point),
                             "data_origin": "human", "reviewer_status": "draft"})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in exported), encoding="utf-8")
    print(f"Exported {len(exported)} DRAFT labels to {output}. Teacher must label each criterion; total score cannot infer these labels.")


if __name__ == "__main__":
    main()
