from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.grading_quality import evaluate_predictions
from app.services.stt_benchmark import build_benchmark_report


async def predict(samples: list[dict], evaluator_mode: str | None) -> dict:
    from app.config import Settings
    from app.services.evaluator import evaluate_answer
    from app.services.grading_quality import digest, rubric_hash

    settings = Settings.from_env()
    if evaluator_mode:
        settings.evaluator_mode = evaluator_mode
    predictions = []
    for sample in samples:
        question, answer = sample["question"], sample["answer"]
        if digest(answer) != sample["answer_hash"] or rubric_hash(question) != sample["rubric_sha256"]:
            raise ValueError("Corpus content hash mismatch")
        result = await evaluate_answer(settings, question, answer)
        predictions.append({**result, "sample_id": sample["sample_id"], "answer_hash": sample["answer_hash"],
                            "rubric_sha256": sample["rubric_sha256"]})
    return {"predictions": predictions, "evaluator_mode": settings.evaluator_mode,
            "teacher_labels_in_model_input": False}


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline backend evaluation. Does not alter models, thresholds or student records.")
    parser.add_argument("mode", choices=["grading", "stt", "predict"])
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--evaluator-mode", choices=["auto", "transformer", "ollama", "rule"])
    parser.add_argument("--minimum-blind-samples", type=int, default=100)
    parser.add_argument("--required-languages", nargs="+", default=["vi", "en"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new report path to preserve evaluation history")
    dataset = json.loads(args.dataset.read_text(encoding="utf-8-sig"))
    samples = dataset["samples"] if isinstance(dataset, dict) else dataset
    if args.mode == "predict":
        report = asyncio.run(predict(samples, args.evaluator_mode))
    elif args.mode == "grading":
        if args.predictions is None:
            parser.error("--predictions is required for grading")
        data = json.loads(args.predictions.read_text(encoding="utf-8-sig"))
        predictions = data["predictions"] if isinstance(data, dict) else data
        report = evaluate_predictions(samples, predictions, minimum_blind_samples=args.minimum_blind_samples)
    else:
        report = build_benchmark_report(samples, required_languages=args.required_languages)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Generated evaluation artifact, not application configuration.
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({"output": str(args.output.resolve()), "samples": len(samples),
                      "production_certified": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
