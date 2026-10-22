from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.config import Settings
from app.context.model import ContextClassifier


def main():
    parser = argparse.ArgumentParser(description="Inspect predictions on one answer without changing the database.")
    parser.add_argument("--questions", default="data/context/questions_context_demo.json")
    parser.add_argument("--id", default="CTX_OVERFIT")
    parser.add_argument("--answer", required=True)
    parser.add_argument("--model", default="models/context-grader")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--with-llm", action="store_true")
    args = parser.parse_args()
    questions = json.loads(Path(args.questions).read_text(encoding="utf-8-sig"))
    question = next((q for q in questions if q["id"] == args.id), None)
    if not question:
        parser.error("Không tìm thấy ID câu hỏi")
    settings = Settings.from_env()
    classifier = ContextClassifier(Path(args.model), args.device)
    predictions = classifier.predict(question, args.answer, settings.context_threshold, settings.context_margin)
    output = {"transformer": predictions}
    if args.with_llm:
        from app.context.hybrid import reconcile
        from app.services.evaluator import evaluate_with_ollama
        base = asyncio.run(evaluate_with_ollama(settings, question, args.answer))
        output["hybrid_proposal"] = reconcile(base, predictions, args.answer, "hybrid")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
