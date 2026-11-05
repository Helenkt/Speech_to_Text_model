"""Freeze and compare a local grading candidate without training or changing grades."""
from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.rubric_contract import digest
from app.services.rubric_transformer import release_transformer
from app.services.specialist_grader import SpecialistGrader, file_hash, freeze_candidate, validate_grading_input


def write_new(path: Path, payload: dict) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".specialist-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        # Windows rename refuses existing destinations and also supports volumes without hard links.
        if os.name == "nt":
            os.rename(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prepare_regression() -> dict:
    source = ROOT / "data/semantic_pilot_regression_cases_v1.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    samples = []
    for case in payload["cases"]:
        points = list(case["expected_relations"])
        parts = case["id"].split("_")
        subject = parts[1] if parts[0] == "new" else parts[0]
        subject = {"AI": "AI101", "DB": "DB101", "OOP": "OOP101", "DSA": "DSA101"}[subject]
        question = {**case["question"], "uid": "regression:" + digest(case["question"]["question"])[:16],
                    "language": "vi", "subject": subject, "key_points": points}
        samples.append({"sample_id": case["id"], "question": question, "answer": case["answer"],
                        "answer_language": "en" if case["id"] == "new_AI_english" else "vi",
                        "draft_expected_relations": case["expected_relations"]})
    return {"schema_version": "specialist-shadow-dataset-v1", "teacher_validated": False,
            "data_origin": "known_synthetic_regression_not_independent_test",
            "source_sha256": file_hash(source), "samples": samples,
            "notice": "Diagnostic only. Draft labels never enter the model input or approve a release."}


def validate_samples(payload: dict) -> list[dict]:
    if not isinstance(payload, dict) or payload.get("schema_version") not in (
        "specialist-shadow-dataset-v1", "grading-corpus-v1"
    ):
        raise ValueError("Expected a shadow dataset or exported grading corpus, not a question bank")
    samples = payload.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("Dataset needs non-empty samples")
    ids = set()
    for index, item in enumerate(samples, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Sample {index} must be an object")
        identifier = item.get("sample_id")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in ids:
            raise ValueError("Sample IDs must be non-empty and unique")
        ids.add(identifier)
        try:
            validate_grading_input(item.get("question"), item.get("answer"))
        except ValueError as exc:
            raise ValueError(f"Sample {index} ({identifier}): {exc}") from exc
        if payload["schema_version"] == "grading-corpus-v1":
            from app.services.grading_quality import validate_corpus_integrity
            validate_corpus_integrity(item)
        if "answer_hash" in item and digest(item["answer"]) != item["answer_hash"]:
            raise ValueError("Transcript hash mismatch")
    return samples


def summarize(samples: list[dict], results: list[dict]) -> dict:
    groups = defaultdict(list)
    for sample, result in zip(samples, results, strict=True):
        groups[(sample["question"].get("subject", "unknown"), sample["question"].get("language", "unknown"))].append(result)

    def stats(rows):
        times = sorted(row["latency_ms"] for row in rows)
        model_times = [row["latency_ms"] for row in rows if row["nli_pair_count"]]
        assessments = [p for row in rows for p in row["point_assessments"]]
        return {"answer_count": len(rows), "criterion_count": len(assessments),
                "rule_resolved_criteria": sum(p["source"] == "closed_rule" for p in assessments),
                "unresolved_criteria": sum(p["status"] == "unresolved" for p in assessments),
                "complete_proposals": sum(row["proposed_score"] is not None for row in rows),
                "nli_pair_count": sum(row["nli_pair_count"] for row in rows),
                "first_model_answer_ms": model_times[0] if model_times else None,
                "subsequent_model_answer_median_ms": statistics.median(model_times[1:]) if len(model_times) > 1 else None,
                "median_answer_ms": statistics.median(times),
                "p95_answer_ms": times[max(0, (95 * len(times) + 99) // 100 - 1)]}
    draft = {"compared_criteria": 0, "matches": 0, "wrong_draft_suggested_as_met": 0,
             "not_a_human_accuracy_estimate": True}
    for sample, result in zip(samples, results, strict=True):
        expected = sample.get("draft_expected_relations", {})
        for point in result["point_assessments"]:
            if point["point"] not in expected:
                continue
            draft["compared_criteria"] += 1
            draft["matches"] += point["suggested_status"] == expected[point["point"]]
            draft["wrong_draft_suggested_as_met"] += (expected[point["point"]] == "contradicted"
                                                       and point["suggested_status"] == "met")
    return {"overall": stats(results), "by_subject_language": [
        {"subject": subject, "language": language, **stats(rows)}
        for (subject, language), rows in sorted(groups.items())], "draft_diagnostics": draft}


def run(args) -> dict:
    dataset_bytes = args.dataset.read_bytes()
    payload = json.loads(dataset_bytes.decode("utf-8-sig"))
    samples = validate_samples(payload)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    grader = SpecialistGrader(args.model_dir, manifest)
    results = []
    try:
        for index, sample in enumerate(samples, 1):
            # No labels, proposed scores or reviewer information reach inference.
            result = grader.grade(sample["question"], sample["answer"])
            results.append({"sample_id": sample["sample_id"], **result})
            if index == 1 or index % 10 == 0 or index == len(samples):
                print(json.dumps({"stage": "candidate", "processed": index, "total": len(samples)}), file=sys.stderr)
    finally:
        release_transformer()
    report = {"schema_version": "specialist-shadow-report-v1", "created_at": datetime.now(timezone.utc).isoformat(),
              "implementation_sha256": {name: file_hash(path) for name, path in {
                  "specialist_grader": ROOT / "app/services/specialist_grader.py",
                  "nli_runtime": ROOT / "app/services/rubric_transformer.py",
                  "runner": Path(__file__)}.items()},
              "dataset_sha256": digest(payload), "dataset_file_sha256": file_hash(args.dataset),
              "candidate": manifest, "summary": summarize(samples, results), "predictions": results,
              "data_origin": payload.get("data_origin", "unverified_export"),
              "production_ready": False, "automatically_changes_model_or_threshold": False,
              "contains_personal_text": True,
              "notice": "Shadow-only. Reports may include transcript excerpts. Do not publish student data."}
    if payload["schema_version"] == "grading-corpus-v1":
        from app.services.grading_quality import evaluate_predictions
        predictions = [{**r, "answer_hash": r["answer_sha256"]} for r in results]
        report["human_label_diagnostics"] = evaluate_predictions(samples, predictions)
        report["human_label_diagnostics"]["eligible_for_release_review"] = False
        report["human_label_diagnostics"]["notice"] = (
            "Unresolved contributes zero only to this diagnostic calculation, never to a final student grade. "
            "The candidate has no independent release validation.")
    if args.compare_current:
        from app.config import Settings
        from app.services.evaluator import evaluate_answer
        settings = Settings.from_env(ROOT)
        settings.evaluator_mode = args.compare_current
        if args.current_model_dir:
            settings.rubric_transformer_path = args.current_model_dir
        comparison = []
        try:
            for index, sample in enumerate(samples, 1):
                started = perf_counter()
                current = asyncio.run(evaluate_answer(settings, sample["question"], sample["answer"]))
                comparison.append({"sample_id": sample["sample_id"], "score": current["score"],
                    "score_provisional": current.get("score_provisional", current.get("review_required", True)),
                    "evaluator": current["evaluator"], "point_assessments": current["point_assessments"],
                    "latency_ms": round((perf_counter() - started) * 1000, 2)})
                if index == 1 or index % 10 == 0 or index == len(samples):
                    print(json.dumps({"stage": "current", "processed": index, "total": len(samples)}), file=sys.stderr)
        finally:
            release_transformer()
        report["current_pipeline_comparison"] = {"mode": args.compare_current,
            "llm_explicitly_enabled": args.compare_current == "auto", "results": comparison,
            "notice": "Stages run sequentially; no second NLI model is intentionally held alongside the candidate."}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--model-dir", type=Path, required=True)
    freeze.add_argument("--output", type=Path, required=True)
    prepare = sub.add_parser("prepare-regression")
    prepare.add_argument("--output", type=Path, required=True)
    evaluate = sub.add_parser("run")
    evaluate.add_argument("--model-dir", type=Path, required=True)
    evaluate.add_argument("--manifest", type=Path, required=True)
    evaluate.add_argument("--dataset", type=Path, required=True)
    evaluate.add_argument("--compare-current", choices=["rule", "transformer", "auto"])
    evaluate.add_argument("--current-model-dir", type=Path)
    evaluate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new path to preserve history")
    if args.command == "freeze":
        payload = freeze_candidate(args.model_dir)
    elif args.command == "prepare-regression":
        payload = prepare_regression()
    else:
        payload = run(args)
    write_new(args.output, payload)
    print(json.dumps({"output": str(args.output), "production_ready": False,
                      "summary": payload.get("summary")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
