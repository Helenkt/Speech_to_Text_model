"""Build and validate a review-only course answer dataset; never trains a model."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import hashlib
import json
from pathlib import Path
import shutil
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
AUTHORING = ROOT / "data/student_answer_authoring_v1"
SUBJECTS = {"AI101": "AI_", "DB101": "DB_", "DSA101": "DSA_", "OOP101": "OOP_"}
RELATIONS = {"S": "supported", "M": "missing", "C": "contradicted", "U": "needs_review"}
MODEL_LABELS = {"supported", "missing", "contradicted"}
LABEL_IDS = {"supported": 0, "missing": 1, "contradicted": 2}
VERSION = "student-answers-v1-20261022"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split()).strip(" .")


def evidence(text: str, quote: str | None) -> dict | None:
    if quote is None:
        return None
    # Prefer the last matching assertion, so an explicit final correction wins.
    start = text.rfind(quote)
    if start < 0 or not quote.strip():
        raise ValueError(f"Evidence is not a nonempty substring: {quote!r}")
    return {"quote": quote, "start": start, "end": start + len(quote),
            "offset_unit": "unicode_code_points", "end_exclusive": True}


def validate_evidence(text: str, relation: str, item: dict | None) -> None:
    if relation == "missing":
        if item is not None:
            raise ValueError("Missing must not invent evidence")
        return
    if not isinstance(item, dict):
        raise ValueError("Support, contradiction and ambiguity require source evidence")
    start, end, quote = item.get("start"), item.get("end"), item.get("quote")
    if (type(start) is not int or type(end) is not int or not isinstance(quote, str)
            or not quote.strip() or not 0 <= start < end <= len(text)
            or text[start:end] != quote or item.get("offset_unit") != "unicode_code_points"
            or item.get("end_exclusive") is not True):
        raise ValueError("Invalid evidence offsets or quotation")


def source_questions() -> tuple[dict, dict]:
    questions, hashes = {}, {}
    for path in sorted((ROOT / "data/rubricguard_training").glob("*.json")):
        hashes[str(path.relative_to(ROOT))] = sha(path)
        for item in read_json(path):
            qid = item["question_id"]
            question = questions.setdefault(qid, {"question": item["question"], "criteria": {},
                "source_path": str(path.relative_to(ROOT)), "source_sha256": sha(path)})
            previous = question["criteria"].setdefault(item["rubric_criterion_id"], {
                "id": item["rubric_criterion_id"], "reference_claim": item["reference_claim"],
                "max_points": item["max_points"], "source_label_ids": []})
            if previous["reference_claim"] != item["reference_claim"] or previous["max_points"] != item["max_points"]:
                raise ValueError("Conflicting source rubric")
            previous["source_label_ids"].append(item["label_id"])
    return questions, hashes


def allocate_points(total, count: int) -> list[float]:
    total = Decimal(str(total))
    step = (total / count).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
    return [float(step)] * (count - 1) + [float(total - step * (count - 1))]


def proposed_reason(relation: str, claim: str, kind: str) -> str:
    reasons = {
        "supported": "Đoạn trích đề xuất diễn đạt ý rubric bằng lời tương đương",
        "missing": "Chưa thấy câu trả lời trình bày ý rubric này; không đồng nghĩa với phát biểu sai",
        "contradicted": "Đoạn trích đề xuất phát biểu trái ý rubric hoặc đảo quan hệ/điều kiện",
        "needs_review": "Có mâu thuẫn chưa được rút lại hoặc thiếu điều kiện để kết luận; không ép thành nhãn học",
    }
    return f"{reasons[relation]}. Đối chiếu: {claim} Dạng ví dụ: {kind}. Nhãn AI dự thảo, cần người duyệt."


def build(output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite dataset: {output}")
    sources, source_hashes = source_questions()
    prior_path = ROOT / "data/semantic_pilot_v1.json"
    prior = read_json(prior_path)
    splits = {g["id"]: g["split"] for g in prior["groups"]}
    splits.update({qid: "regression_only" for qid in prior["quarantined_questions"]})
    payloads, seed_hashes = {}, {}
    for subject, prefix in SUBJECTS.items():
        seed_path = AUTHORING / f"{subject}.json"
        seed = read_json(seed_path)
        seed_hashes[str(seed_path.relative_to(ROOT))] = sha(seed_path)
        if seed["subject"] != subject or len(seed["questions"]) != 10:
            raise ValueError(f"Expected ten questions for {subject}")
        prepared = []
        for draft in seed["questions"]:
            qid = draft["id"]
            if not qid.startswith(prefix) or qid not in sources:
                raise ValueError(f"Question has no matching course source: {qid}")
            source = sources[qid]
            counts = Counter(parent for parent, _ in draft["atoms"])
            atom_counts = Counter()
            atoms = []
            for parent_index, claim in draft["atoms"]:
                parent = source["criteria"][f"{qid}_R{parent_index}"]
                position = atom_counts[parent_index]
                atom_counts[parent_index] += 1
                atoms.append({"id": f"{parent['id']}.a{position + 1}", "parent_id": parent["id"],
                    "reference_claim": claim, "proposed_max_points": allocate_points(
                        parent["max_points"], counts[parent_index])[position],
                    "weight_status": "equal_allocation_within_original_parent_pending_review"})
            if {a["parent_id"] for a in atoms} != set(source["criteria"]):
                raise ValueError(f"A source criterion was dropped: {qid}")
            if len(draft["answers"]) != 10:
                raise ValueError(f"Expected ten answers: {qid}")
            answers = []
            for number, (kind, labels, text, quotes) in enumerate(draft["answers"], 1):
                if len(labels) != len(atoms) or len(quotes) != len(atoms):
                    raise ValueError(f"Criterion label count mismatch: {qid} answer {number}")
                assessments = []
                lower = upper = 0.0
                for atom, label, quote in zip(atoms, labels, quotes, strict=True):
                    relation = RELATIONS[label]
                    cited = evidence(text, quote)
                    validate_evidence(text, relation, cited)
                    if relation == "supported":
                        lower += atom["proposed_max_points"]
                        upper += atom["proposed_max_points"]
                    elif relation == "needs_review":
                        upper += atom["proposed_max_points"]
                    assessments.append({"criterion_id": atom["id"], "proposed_relation": relation,
                        "proposed_evidence": cited, "proposed_reason": proposed_reason(relation, atom["reference_claim"], kind),
                        "reviewed_relation": None, "reviewed_evidence": None, "reviewed_reason": None,
                        "review_status": "pending", "reviewer_id": None, "reviewed_at": None})
                answers.append({"id": f"{qid}_DRAFT_{number:02d}", "student_answer": text,
                    "language": "vi", "style": kind, "data_origin": "agent_authored_synthetic",
                    "real_student": False, "teacher_validated": False,
                    "audio_path": None, "asr_error_tested": False,
                    "point_assessments": assessments,
                    "proposed_score_range": {"minimum": round(lower, 4), "maximum": round(upper, 4),
                        "scale": 10, "status": "draft_not_a_teacher_score"}, "teacher_points": None})
            prepared.append({"id": qid, "question": source["question"], "split": splits[qid],
                "evaluation_status": "development_only_not_independent_of_prior_work",
                "source": {k: source[k] for k in ("source_path", "source_sha256")},
                "source_criteria": list(source["criteria"].values()), "rubric_draft": atoms,
                "source_review_note": draft.get("review_note", "Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt."),
                "rubric_review": {"status": "pending", "reviewer_id": None, "reviewed_at": None, "comment": None},
                "answers": answers})
        payloads[subject] = {"dataset_version": VERSION, "subject": subject,
            "source_language": "vi", "includes_english_terms": True, "fully_english_validated": False,
            "data_origin": "agent_authored_synthetic", "teacher_validated": False,
            "production_ready": False, "questions": prepared}
    # Validate in memory before creating any output directory.
    stats = validate_payloads(payloads)
    output.mkdir(parents=True)
    all_pairs = []
    for subject, payload in payloads.items():
        write_json(output / f"{subject}.json", payload)
        review_lines = [f"# Bản đọc duyệt {subject}", "", "Nhãn và điểm đều là AI đề xuất; chưa có giảng viên duyệt.", ""]
        for question in payload["questions"]:
            atoms = {a["id"]: a for a in question["rubric_draft"]}
            review_lines.extend([f"## {question['id']}: {question['question']}", "",
                f"Nhóm: `{question['split']}`. {question['source_review_note']}", ""])
            for atom in atoms.values():
                review_lines.append(f"- {atom['id']} ({atom['proposed_max_points']} điểm dự thảo): {atom['reference_claim']}")
            review_lines.append("")
            for answer in question["answers"]:
                score = answer["proposed_score_range"]
                review_lines.extend([f"### {answer['id']} / {answer['style']}", "", answer["student_answer"], "",
                    f"Khoảng điểm đề xuất: {score['minimum']}–{score['maximum']}/10. Không phải điểm đã duyệt.", ""])
                for point in answer["point_assessments"]:
                    quote = point["proposed_evidence"]
                    shown = quote["quote"] if quote else "Không trích dẫn vì chưa nêu ý."
                    review_lines.append(f"- {point['criterion_id']}: `{point['proposed_relation']}`. Bằng chứng: {shown}")
                    all_pairs.append({"subject": subject, "question_id": question["id"],
                        "answer_id": answer["id"], "criterion_id": point["criterion_id"],
                        "split": question["split"], "question": question["question"],
                        "student_answer": answer["student_answer"],
                        "reference_claim": atoms[point["criterion_id"]]["reference_claim"],
                        "draft_relation": point["proposed_relation"],
                        "draft_evidence": point["proposed_evidence"],
                        "data_origin": "agent_authored_synthetic", "teacher_validated": False,
                        "eligible_for_training": False})
                review_lines.extend(["", "Ghi chú người duyệt: ____________________", ""])
        (output / f"review_{subject}.md").write_text("\n".join(review_lines), encoding="utf-8")
    write_jsonl(output / "draft_pairs_NOT_TRAINING.jsonl", all_pairs)
    protected = dict(source_hashes)
    for path in [*(ROOT / "app/static").glob("*"), *(ROOT / "models/rubricguard-lite").glob("*"),
                 *(ROOT / "data").glob("question_bank*.json")]:
        if path.is_file():
            protected[str(path.relative_to(ROOT))] = sha(path)
    manifest = {"dataset_version": VERSION, "date_local": "2026-10-22", "stats": stats,
        "source_files_sha256": source_hashes, "authoring_files_sha256": seed_hashes,
        "protected_production_files_sha256": protected,
        "original_draft_sha256": {f"{s}.json": sha(output / f"{s}.json") for s in SUBJECTS},
        "frozen_question_splits": {q["id"]: q["split"] for p in payloads.values() for q in p["questions"]},
        "prior_split_file": str(prior_path.relative_to(ROOT)), "prior_split_sha256": sha(prior_path),
        "holdout_policy": "Preserve earlier question assignments; quarantined questions remain regression-only.",
        "evaluation_limitation": "Same course topics as prior experiments; synthetic development holdouts, not independent student test accuracy.",
        "training_enabled": False, "teacher_validated": False,
        "knowledge_from_internet": False, "student_audio_included": False,
        "warning": "Draft labels, draft atomic rubrics and proposed scores require independent review; never auto-promote."}
    write_json(output / "manifest.json", manifest)
    shutil.copyfile(AUTHORING / "README_DATASET.md", output / "README.md")
    shutil.copyfile(AUTHORING / "HUONG_DAN_GAN_NHAN.md", output / "HUONG_DAN_GAN_NHAN.md")
    sample = ["# Mẫu dữ liệu để đọc nhanh", "", "Tất cả đều là ví dụ AI soạn, chưa có giảng viên duyệt.", ""]
    for subject, payload in payloads.items():
        q = payload["questions"][0]
        sample.extend([f"## {subject}: {q['question']}", ""])
        for a in q["answers"][:4]:
            sample.extend([f"### {a['id']} ({a['style']})", "", a["student_answer"], ""])
            for point in a["point_assessments"]:
                sample.append(f"- {point['criterion_id']}: `{point['proposed_relation']}`")
            sample.append("")
    (output / "MAU_DOC_NHANH.md").write_text("\n".join(sample), encoding="utf-8")
    return stats


def reviewed(point: dict) -> bool:
    return point.get("review_status") == "approved" and point.get("reviewed_relation") in MODEL_LABELS


def validate_stamp(item: dict) -> None:
    if not isinstance(item.get("reviewer_id"), str) or not item["reviewer_id"].strip():
        raise ValueError("Approval requires reviewer_id")
    try:
        date = datetime.fromisoformat(item["reviewed_at"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ValueError("Approval requires an ISO-8601 reviewed_at timestamp") from exc
    if date.tzinfo is None:
        raise ValueError("Approval timestamp must include a timezone")


def validate_payloads(payloads: dict, frozen_splits: dict | None = None) -> dict:
    seen_questions, seen_answers = set(), set()
    answer_owners, claim_owners = {}, {}
    labels, split_counts, subject_counts = Counter(), Counter(), {}
    pairs = 0
    for subject, payload in payloads.items():
        if payload.get("subject") != subject:
            raise ValueError("Dataset subject mismatch")
        if payload.get("production_ready") is not False or payload.get("data_origin") != "agent_authored_synthetic":
            raise ValueError("Draft origin/readiness must not be changed")
        count = 0
        for q in payload["questions"]:
            if q["id"] in seen_questions or q["split"] not in {"train", "validation", "test", "regression_only"}:
                raise ValueError("Duplicate question or invalid split")
            if not q["id"].startswith(SUBJECTS[subject]):
                raise ValueError("Subject/question mismatch")
            if frozen_splits is not None and frozen_splits.get(q["id"]) != q["split"]:
                raise ValueError("A frozen question split was changed")
            seen_questions.add(q["id"])
            source = {r["id"]: r for r in q["source_criteria"]}
            atoms = {r["id"]: r for r in q["rubric_draft"]}
            if len(atoms) != len(q["rubric_draft"]) or {a["parent_id"] for a in atoms.values()} != set(source):
                raise ValueError("Duplicate atom or missing source criterion")
            for parent, original in source.items():
                weights = [Decimal(str(a["proposed_max_points"])) for a in atoms.values() if a["parent_id"] == parent]
                if any(not w.is_finite() or w <= 0 for w in weights) or sum(weights) != Decimal(str(original["max_points"])):
                    raise ValueError("Atomic weights must preserve each original parent budget")
            if sum(Decimal(str(r["max_points"])) for r in source.values()) != 10:
                raise ValueError("Source rubric must sum to ten")
            for atom in atoms.values():
                key = normalized(atom["reference_claim"])
                previous = claim_owners.setdefault(key, q["split"])
                if not key or previous != q["split"]:
                    raise ValueError("Cross-split duplicate claim")
            if q["rubric_review"]["status"] == "approved":
                validate_stamp(q["rubric_review"])
                if not q["rubric_review"].get("comment"):
                    raise ValueError("Rubric approval requires a source/weight review comment")
            if len(q["answers"]) != 10:
                raise ValueError("Each question must have exactly ten answers")
            for answer in q["answers"]:
                text = answer["student_answer"]
                key = normalized(text)
                if not key or answer["id"] in seen_answers or key in answer_owners:
                    raise ValueError("Duplicate/empty answer")
                answer_owners[key] = q["split"]
                seen_answers.add(answer["id"])
                assessments = answer["point_assessments"]
                if len(assessments) != len(atoms) or {p["criterion_id"] for p in assessments} != set(atoms):
                    raise ValueError("Every atom must have exactly one assessment")
                lo = hi = Decimal(0)
                for point in assessments:
                    relation = point["proposed_relation"]
                    if relation not in RELATIONS.values():
                        raise ValueError("Invalid draft relation")
                    validate_evidence(text, relation, point["proposed_evidence"])
                    if not point.get("proposed_reason"):
                        raise ValueError("Draft labels require a review explanation")
                    if point.get("review_status") not in {"pending", "approved", "needs_review", "rejected"}:
                        raise ValueError("Invalid review status")
                    if point["review_status"] == "approved":
                        if not reviewed(point) or not point.get("reviewed_reason"):
                            raise ValueError("Approved labels must be resolved and explained")
                        validate_stamp(point)
                        validate_evidence(text, point["reviewed_relation"], point["reviewed_evidence"])
                    weight = Decimal(str(atoms[point["criterion_id"]]["proposed_max_points"]))
                    if relation == "supported":
                        lo += weight
                        hi += weight
                    elif relation == "needs_review":
                        hi += weight
                    labels[relation] += 1
                    pairs += 1
                score = answer["proposed_score_range"]
                if Decimal(str(score["minimum"])) != lo or Decimal(str(score["maximum"])) != hi:
                    raise ValueError("Draft score does not follow atomic labels and weights")
                count += 1
                split_counts[q["split"]] += 1
        subject_counts[subject] = count
    if frozen_splits is not None and seen_questions != set(frozen_splits):
        raise ValueError("A frozen question was removed or added")
    return {"subjects": subject_counts, "questions": len(seen_questions), "answers": len(seen_answers),
            "criterion_pairs": pairs, "draft_label_counts": dict(labels), "answer_splits": dict(split_counts)}


def load_bundle(bundle: Path) -> tuple[dict, dict]:
    manifest = read_json(bundle / "manifest.json")
    prior_path = ROOT / "data/semantic_pilot_v1.json"
    if sha(prior_path) != manifest["prior_split_sha256"]:
        raise ValueError("Prior split provenance changed")
    prior = read_json(prior_path)
    expected = {q["id"]: q["split"] for q in prior["groups"]}
    expected.update({qid: "regression_only" for qid in prior["quarantined_questions"]})
    if manifest["frozen_question_splits"] != expected:
        raise ValueError("Frozen splits do not match the original question quarantine")
    payloads = {subject: read_json(bundle / f"{subject}.json") for subject in SUBJECTS}
    validate_payloads(payloads, manifest["frozen_question_splits"])
    # A reviewed file may differ from the initial draft. Source and split provenance stay immutable.
    sources, _ = source_questions()
    for payload in payloads.values():
        for q in payload["questions"]:
            if q["question"] != sources[q["id"]]["question"]:
                raise ValueError("Original question was modified")
            if q["source"]["source_path"] != sources[q["id"]]["source_path"]:
                raise ValueError("Question provenance was modified")
            if q["source_criteria"] != list(sources[q["id"]]["criteria"].values()):
                raise ValueError("Original source criteria were modified")
            if q["source"]["source_sha256"] != sha(ROOT / q["source"]["source_path"]):
                raise ValueError("Question source hash does not match")
    return manifest, payloads


def verify_protected(manifest: dict) -> None:
    for relative, expected in manifest["protected_production_files_sha256"].items():
        if sha(ROOT / relative) != expected:
            raise ValueError(f"Protected production file changed: {relative}")


def export_reviewed(bundle: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Refusing to overwrite a reviewed export")
    manifest, payloads = load_bundle(bundle)
    rows = {split: [] for split in ("train", "validation", "test")}
    for subject, payload in payloads.items():
        for q in payload["questions"]:
            if q["split"] == "regression_only" or q["rubric_review"]["status"] != "approved":
                continue
            atoms = {r["id"]: r for r in q["rubric_draft"]}
            for answer in q["answers"]:
                if not all(reviewed(p) for p in answer["point_assessments"]):
                    continue
                for point in answer["point_assessments"]:
                    rows[q["split"]].append({"subject": subject, "question_id": q["id"],
                        "question": q["question"], "answer_id": answer["id"],
                        "student_answer": answer["student_answer"], "criterion_id": point["criterion_id"],
                        "reference_claim": atoms[point["criterion_id"]]["reference_claim"],
                        "criterion": atoms[point["criterion_id"]]["reference_claim"],
                        "max_points": atoms[point["criterion_id"]]["proposed_max_points"],
                        "relation_label": point["reviewed_relation"], "split": q["split"],
                        "label": LABEL_IDS[point["reviewed_relation"]],
                        "evidence": point["reviewed_evidence"], "reviewer_id": point["reviewer_id"],
                        "reviewed_at": point["reviewed_at"], "review_reason": point["reviewed_reason"],
                        "data_origin": "agent_authored_synthetic_individually_reviewed",
                        "teacher_validated": True, "independent_student_test": False})
    if not rows["train"]:
        raise ValueError("No complete training answers have approved labels AND an approved rubric; refusing draft training export")
    output.mkdir(parents=True)
    for split, subset in rows.items():
        write_jsonl(output / f"{split}.jsonl", subset)
    summary = {"rows": {name: len(subset) for name, subset in rows.items()},
        "label_to_id": LABEL_IDS,
        "model_label_names": {"0": "entailment", "1": "neutral", "2": "contradiction"},
        "allowed_model_input_fields": ["question", "student_answer", "reference_claim"],
        "format": "JSONL split files; do not re-split by answer or feed labels/evidence as features",
        "source_dataset_version": manifest["dataset_version"],
        "reviewed_files_sha256": {f"{s}.json": sha(bundle / f"{s}.json") for s in SUBJECTS},
        "evaluation_warning": manifest["evaluation_limitation"], "model_trained": False,
        "note": "Review stamps are offline metadata, not an authenticated application approval system."}
    write_json(output / "export_manifest.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "validate", "export-reviewed"])
    parser.add_argument("--bundle", type=Path, default=ROOT / "data/student_answer_dataset_v1")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-production", action="store_true",
                        help="Also audit this machine's original model/static file hashes; requires local model artifacts")
    args = parser.parse_args()
    if args.action == "build":
        result = build(args.bundle)
    elif args.action == "validate":
        manifest, payloads = load_bundle(args.bundle)
        if args.verify_production:
            verify_protected(manifest)
        result = {**validate_payloads(payloads, manifest["frozen_question_splits"]),
                  "source_provenance_verified": True,
                  "protected_production_files_unchanged": True if args.verify_production else None,
                  "production_audit_requested": args.verify_production,
                  "validation_scope": "Structure, evidence, weights and provenance; NOT semantic correctness of AI labels"}
        write_json(args.bundle / "validation_report.json", result)
    else:
        if args.output is None:
            parser.error("export-reviewed requires --output")
        result = export_reviewed(args.bundle, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
