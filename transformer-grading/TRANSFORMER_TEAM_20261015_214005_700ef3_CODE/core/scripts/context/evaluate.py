from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
import json
from pathlib import Path
import statistics
import time

from app.context.contracts import FACTORS
from app.context.model import ContextClassifier
from scripts.context.metrics import classification_metrics
from scripts.context.train import load_split


def main():
    parser = argparse.ArgumentParser(description="Held-out test: independent of training/checkpoint selection.")
    parser.add_argument("--data", default="data/context/prepared")
    parser.add_argument("--model", default="models/context-grader")
    parser.add_argument("--output", default="data/context/test_report.json")
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--margin", type=float, default=0.2)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--compare-llm", action="store_true", help="Call existing Ollama grader on the SAME test answers; no silent rules fallback")
    args = parser.parse_args()
    folder = Path(args.data)
    manifest = json.loads((folder / "dataset_manifest.json").read_text(encoding="utf-8"))
    rows = load_split(folder, "test", manifest)
    classifier = ContextClassifier(Path(args.model), args.device)
    if classifier.manifest["dataset_files_sha256"] != manifest["files_sha256"]:
        parser.error("Checkpoint/dataset khác nhau: dùng đúng holdout đã giữ khi train")
    truth, raw_predictions, accepted_pairs, details, times = [], [], [], [], []
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["group"], row["answer_id"], row["student_answer"])].append(row)
    absolute_errors, selective_errors, llm_errors, llm_unavailable = [], [], [], []
    for (_, answer_id, answer), group in grouped.items():
        q = {"question": group[0]["question"], "reference_answer": group[0]["reference_answer"],
             "key_points": [r["criterion"] for r in group], "language": "vi"}
        start = time.perf_counter()
        predictions = classifier.predict(q, answer, args.threshold, args.margin)
        times.append(time.perf_counter() - start)
        max_points = sum(float(r["max_points"]) for r in group)
        teacher = 100 * sum(float(r["teacher_points"]) for r in group) / max_points
        proposal = 100 * sum(float(r["max_points"]) * FACTORS[p["predicted_label"]] for r, p in zip(group, predictions)) / max_points
        absolute_errors.append(abs(teacher - proposal))
        accepted = all(not p["abstained"] for p in predictions)
        if accepted:
            selective_errors.append(abs(teacher - proposal))
        item = {"answer_id": answer_id, "teacher_score": teacher, "transformer_raw_proposal": proposal,
                "accepted_all_criteria": accepted, "criteria": predictions}
        for row, prediction in zip(group, predictions):
            truth.append(row["label"])
            raw_predictions.append(prediction["predicted_label"])
            if not prediction["abstained"]:
                accepted_pairs.append((row["label"], prediction["predicted_label"]))
        if args.compare_llm:
            from app.config import Settings
            from app.services.evaluator import evaluate_with_ollama
            try:
                llm = asyncio.run(evaluate_with_ollama(Settings.from_env(), q, answer))
                # Existing app rubric uses equal weights; convert each status to teacher weights for fair comparison.
                statuses = {a["point"]: a["status"] for a in llm["point_assessments"]}
                score = 100 * sum(float(r["max_points"]) * FACTORS.get(statuses[r["criterion"]], 0) for r in group) / max_points
                llm_errors.append(abs(score - teacher))
                item["llm_score"] = score
                item["llm_review_required"] = llm["review_required"]
            except Exception as exc:
                llm_unavailable.append({"answer_id": answer_id, "error": type(exc).__name__})
        details.append(item)
    report = {"demo_only": bool(manifest["demo_only"]), "model_version": classifier.identity,
              "test_rows": len(rows), "test_answers": len(grouped),
              "raw_classification": classification_metrics(truth, raw_predictions),
              "criterion_coverage": len(accepted_pairs) / len(rows),
              "accepted_classification": classification_metrics([a for a, _ in accepted_pairs], [b for _, b in accepted_pairs]) if accepted_pairs else None,
              "raw_score_mae_0_100": statistics.mean(absolute_errors),
              "accepted_answer_coverage": len(selective_errors) / len(grouped),
              "accepted_answer_mae_0_100": statistics.mean(selective_errors) if selective_errors else None,
              "latency_seconds": {"p50": statistics.median(times), "p95": sorted(times)[min(len(times)-1, int(len(times)*0.95))],
                                   "includes_first_inference": True, "includes_model_loading": False},
              "llm_mae_0_100": statistics.mean(llm_errors) if llm_errors else None,
              "llm_unavailable": llm_unavailable, "answers": details,
              "limitations": ["Softmax chưa hiệu chỉnh; không phải xác suất câu trả lời được chấm đúng.",
                              "Nếu một nhãn không có trong test thì chưa đo được chất lượng nhãn đó.",
                              "MAE tổng hợp không thay thế kiểm định bằng câu trả lời sinh viên và giáo viên độc lập.",
                              "Khi LLM lỗi ở một phần test, MAE LLM/Transformer không còn là so sánh cặp đầy đủ."]}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "answers"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
