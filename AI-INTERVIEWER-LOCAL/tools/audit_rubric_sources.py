from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.question_importer import parse_question_bank
from app.services.rubric_contract import rubric_draft, validate_contract


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Audit supplied banks and prepare UNAPPROVED rubric drafts; never modifies the database.")
    parser.add_argument("--banks", nargs="+", type=Path,
                        default=[root / "data/question_bank_vi.json", root / "data/question_bank_en.json"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output file; audit history is not overwritten")
    drafts, seen, subjects, warnings_by_subject, sources = [], set(), Counter(), Counter(), []
    for bank in args.banks:
        questions, source_sha = parse_question_bank(bank.read_bytes(), filename=bank.name)
        sources.append({"name": bank.name, "sha256": source_sha, "question_count": len(questions)})
        for question in questions:
            if question["uid"] in seen:
                raise ValueError(f"Duplicate source question: {question['uid']}")
            seen.add(question["uid"])
            question["source_name"] = bank.name
            draft = rubric_draft(question)
            _, warnings = validate_contract(question, draft)
            group = f"{question['subject']}:{question['language']}"
            subjects[group] += 1
            warnings_by_subject[group] += bool(warnings)
            drafts.append({"question_uid": question["uid"], "subject": question["subject"],
                           "source_name": bank.name, "source_sha256": source_sha,
                           "status": "needs_teacher_review", "contract": draft, "warnings": warnings})
    report = {"sources": sources, "question_count": len(drafts), "by_subject_language": dict(subjects),
              "questions_with_rubric_warnings": dict(warnings_by_subject), "drafts": drafts,
              "auto_approved_count": 0, "database_modified": False,
              "notice": "Drafts retain existing points, do not invent knowledge or split meaning automatically. Source excerpts prove origin, not semantic correctness."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps({key: value for key, value in report.items() if key != "drafts"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
