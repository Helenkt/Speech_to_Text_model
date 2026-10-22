"""Prepare source-bound rubric drafts and synthetic contrasts, never train or publish."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.course_verifier import fact_examples, parse_course_fact
from app.services.fact_guard import check_rubric_point
from app.services.grading_semantics import requires_semantic_audit
from app.services.question_importer import parse_question_bank
from app.services.rubric_contract import rubric_draft, validate_contract
from app.services.rubric_guidance import grading_guidance


def contrastive_cases(data_dir: Path) -> list[dict]:
    cases = []
    for path in sorted(data_dir.glob("*.json")):
        content = path.read_bytes()
        rows = json.loads(content.decode("utf-8-sig"))
        groups = {}
        for row in rows:
            group = groups.setdefault(row["question_id"], {"question": row["question"], "claims": {}, "ids": []})
            if group["question"] != row["question"]:
                raise ValueError("Question ID refers to different source questions")
            claim, weight = row["reference_claim"], row["max_points"]
            if not isinstance(claim, str) or not claim.strip():
                raise ValueError("Reference claims must be nonempty text")
            if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight <= 0:
                raise ValueError("Source weights must be finite and positive")
            previous = group["claims"].setdefault(claim, weight)
            if previous != weight:
                raise ValueError("Inconsistent source weights")
            group["ids"].append(row["label_id"])
        for qid, group in sorted(groups.items()):
            points, weights = list(group["claims"]), group["claims"]
            prefix = qid.split("_", 1)[0]
            subject = {"AI": "AI101", "DB": "DB101", "DSA": "DSA101", "OOP": "OOP101"}[prefix]
            group_id = path.name + ":" + qid
            bucket = int(hashlib.sha256(group_id.encode()).hexdigest()[:8], 16) % 10
            split = "test" if bucket < 2 else "validation" if bucket < 4 else "train"
            question = {"question": group["question"], "reference_answer": "; ".join(points),
                        "key_points": points, "key_point_weights": weights, "language": "vi", "subject_code": subject}

            def append(kind, answer, relations):
                total = sum(weights.values())
                earned = sum(weights[p] for p, status in relations.items() if status == "met")
                pending = sum(weights[p] for p, status in relations.items() if status == "unresolved")
                cases.append({"id": group_id + ":" + kind, "group_id": group_id, "split": split,
                    "question": question, "answer": answer, "expected_relations": relations,
                    "expected_score_range": [round(100 * earned / total, 4), round(100 * (earned + pending) / total, 4)],
                    "source": {"file": path.name, "sha256": hashlib.sha256(content).hexdigest(),
                               "question_id": qid, "label_ids": sorted(group["ids"])},
                    "data_origin": "mechanically_derived_course_contrast",
                    "independently_teacher_validated": False,
                    "independent_student_accuracy_benchmark": False})

            complete = {p: "met" for p in points}
            append("complete", ". ".join(points) + ".", complete)
            for index, point in enumerate(points):
                rest = [p for p in points if p != point]
                append(f"missing_{index}", ". ".join(rest) + "." if rest else "Em chưa có câu trả lời.",
                       {**complete, point: "missing"})
                append(f"negated_{index}", f"Không đúng là {point}. " + ". ".join(rest),
                       {**complete, point: "contradicted"})
                append(f"conflicted_{index}", ". ".join(points) + f". Không đúng là {point}.",
                       {**complete, point: "unresolved"})
                append(f"corrected_{index}", f"Không đúng là {point}. Em xin sửa lại: {point}. " + ". ".join(rest), complete)
                fact = parse_course_fact(point)
                examples = fact_examples(fact, "vi") if fact else []
                if examples:
                    append(f"equivalent_{index}", examples[-1] + ". " + ". ".join(rest), complete)
    if not cases:
        raise ValueError("No course reference data found")
    return cases


def prepare(root: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("Choose a new output directory; preparation history is never overwritten")
    drafts, sources = [], []
    for name in ("question_bank_vi.json", "question_bank_en.json"):
        content = (root / "data" / name).read_bytes()
        questions, sha = parse_question_bank(content, filename=name)
        sources.append({"file": name, "sha256": sha, "questions": len(questions)})
        for question in questions:
            question["source_name"] = name
            contract = rubric_draft(question)
            _, warnings = validate_contract(question, contract)
            drafts.append({"question_uid": question["uid"], "source_file": name, "source_sha256": sha,
                           "status": "draft_not_approved", "contract": contract, "warnings": warnings,
                           "guidance": grading_guidance(question)})
    contrasts = contrastive_cases(root / "data" / "rubricguard_training")
    rule_report = check_rule_cases(contrasts)
    manifest = {"version": "course-preparation-v1", "bank_sources": sources,
        "rubric_drafts": len(drafts), "questions_with_warnings": sum(bool(d["warnings"]) for d in drafts),
        "closed_form_criteria": sum(c["verification"] is not None for d in drafts for c in d["guidance"]["criteria"]),
        "closed_form_is_not_general_semantic_coverage": True,
        "contrastive_cases": len(contrasts), "contrastive_question_groups": len({c["group_id"] for c in contrasts}),
        "by_subject": dict(Counter(c["question"]["subject_code"] for c in contrasts)),
        "by_split": dict(Counter(c["split"] for c in contrasts)),
        "split_policy": "all variants of one source question remain in one split; source may overlap prior training",
        "independent_student_accuracy_benchmark": False, "auto_approved_count": 0,
        "database_modified": False, "training_performed": False, "external_knowledge_added": False}
    output.mkdir(parents=True)
    for name, value in (("rubric_drafts.json", drafts), ("manifest.json", manifest), ("rule_regressions.json", rule_report)):
        with (output / name).open("x", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
    with (output / "contrastive_cases.jsonl").open("x", encoding="utf-8") as handle:
        for case in contrasts:
            handle.write(json.dumps(case, ensure_ascii=False, allow_nan=False) + "\n")
    return manifest


def check_rule_cases(cases: list[dict]) -> dict:
    counts, failures = Counter(), []
    for case in cases:
        for point, expected in case["expected_relations"].items():
            counts["point_checks"] += 1
            if requires_semantic_audit(case["answer"]):
                counts["deferred_to_semantic_audit"] += 1
                continue
            decision = check_rubric_point(case["question"], case["answer"], point)
            if decision.status not in {"supported", "contradicted"}:
                counts["rule_abstained"] += 1
                continue
            counts["rule_resolved"] += 1
            actual = "met" if decision.status == "supported" else "contradicted"
            if actual != expected:
                counts["mismatches"] += 1
                failures.append({"case_id": case["id"], "point": point, "expected": expected,
                                 "actual": actual, "source": case["source"]})
    counts.setdefault("mismatches", 0)
    return {"counts": dict(counts), "failures": failures,
            "scope": "Deterministic rules on generated contrasts only; abstention is not success; no LLM/STT inference.",
            "independent_student_accuracy_benchmark": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(Path(__file__).resolve().parents[1], args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
