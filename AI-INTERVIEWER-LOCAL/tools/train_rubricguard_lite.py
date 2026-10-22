from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path


LABELS = {"supported": 0, "missing": 1, "uncertain": 1, "contradicted": 2}
ID2LABEL = {0: "entailment", 1: "neutral", 2: "contradiction"}


def load_rows(data_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(data_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            rows.extend(item for item in payload if item.get("relation_label") in LABELS)
    return rows


def numeric_hard_cases(seed: int, count: int = 240) -> list[dict]:
    rng = random.Random(seed)
    names = [("Minh", "Lan"), ("An", "Bình"), ("Nam", "Hà"), ("Alice", "Bob")]
    rows: list[dict] = []
    for index in range(count):
        left, right = names[index % len(names)]
        a, b = rng.sample(range(1, 101), 2)
        high, low = (left, right) if a > b else (right, left)
        relation = f"{high} có điểm cao hơn {low}"
        facts = f"{left} được {a} điểm và {right} được {b} điểm."
        rows.extend(
            [
                {
                    "question_id": f"NUM_{index}",
                    "student_answer": f"{facts} Vì vậy {relation}.",
                    "reference_claim": relation,
                    "label": 0,
                },
                {
                    "question_id": f"NUM_{index}",
                    "student_answer": f"{facts} Vì vậy {low} có điểm cao hơn {high}.",
                    "reference_claim": relation,
                    "label": 2,
                },
                {
                    "question_id": f"NUM_{index}",
                    "student_answer": "Điểm số dùng để so sánh kết quả học tập.",
                    "reference_claim": relation,
                    "label": 1,
                },
            ]
        )
    return rows


def macro_f1(truth: list[int], predicted: list[int]) -> float:
    scores = []
    for label in range(3):
        tp = sum(a == label and b == label for a, b in zip(truth, predicted))
        fp = sum(a != label and b == label for a, b in zip(truth, predicted))
        fn = sum(a == label and b != label for a, b in zip(truth, predicted))
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        scores.append(2 * precision * recall / max(1e-12, precision + recall))
    return sum(scores) / len(scores)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--base-model",
        default="MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli",
    )
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20261016)
    args = parser.parse_args()

    import torch
    from torch.nn.utils import clip_grad_norm_
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    original = load_rows(args.data_dir)
    question_ids = sorted({str(row.get("question_id")) for row in original})
    rng = random.Random(args.seed)
    rng.shuffle(question_ids)
    validation_ids = set(question_ids[: max(1, len(question_ids) // 5)])

    train_rows: list[dict] = []
    validation_rows: list[dict] = []
    for row in original:
        sample = {
            "question_id": row.get("question_id"),
            "student_answer": str(row["student_answer"]),
            "reference_claim": str(row["reference_claim"]),
            "label": LABELS[str(row["relation_label"])],
        }
        (validation_rows if str(row.get("question_id")) in validation_ids else train_rows).append(sample)
    train_rows.extend(numeric_hard_cases(args.seed))
    rng.shuffle(train_rows)

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)

    class PairDataset(Dataset):
        def __init__(self, rows: list[dict]):
            self.rows = rows

        def __len__(self) -> int:
            return len(self.rows)

        def __getitem__(self, index: int) -> dict:
            row = self.rows[index]
            encoded = tokenizer(
                row["student_answer"],
                row["reference_claim"],
                truncation=True,
                max_length=256,
            )
            encoded["labels"] = row["label"]
            return encoded

    def collate(batch: list[dict]) -> dict:
        labels = torch.tensor([item.pop("labels") for item in batch], dtype=torch.long)
        padded = tokenizer.pad(batch, padding=True, return_tensors="pt")
        padded["labels"] = labels
        return padded

    train_loader = DataLoader(
        PairDataset(train_rows), batch_size=args.batch_size, shuffle=True, collate_fn=collate
    )
    validation_loader = DataLoader(
        PairDataset(validation_rows), batch_size=args.batch_size * 2, collate_fn=collate
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        num_labels=3,
        id2label=ID2LABEL,
        label2id={value: key for key, value in ID2LABEL.items()},
    ).to(device)
    counts = Counter(item["label"] for item in train_rows)
    weights = torch.tensor(
        [len(train_rows) / (3 * max(1, counts[index])) for index in range(3)],
        dtype=torch.float,
        device=device,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    best_f1 = -1.0
    stale_epochs = 0
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            labels = batch.pop("labels").to(device)
            inputs = {key: value.to(device) for key, value in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
                logits = model(**inputs).logits
                loss = torch.nn.functional.cross_entropy(logits, labels, weight=weights)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            total_loss += float(loss.detach())

        model.eval()
        truth: list[int] = []
        predicted: list[int] = []
        with torch.inference_mode():
            for batch in validation_loader:
                labels = batch.pop("labels")
                inputs = {key: value.to(device) for key, value in batch.items()}
                output = model(**inputs).logits.argmax(dim=-1).cpu()
                truth.extend(labels.tolist())
                predicted.extend(output.tolist())
        score = macro_f1(truth, predicted)
        accuracy = sum(a == b for a, b in zip(truth, predicted)) / max(1, len(truth))
        contradiction_total = sum(item == 2 for item in truth)
        contradiction_recall = sum(
            expected == 2 and actual == 2
            for expected, actual in zip(truth, predicted)
        ) / max(1, contradiction_total)
        print(
            json.dumps(
                {
                    "epoch": epoch,
                    "loss": round(total_loss / max(1, len(train_loader)), 4),
                    "validation_accuracy": round(accuracy, 4),
                    "validation_macro_f1": round(score, 4),
                    "contradiction_recall": round(contradiction_recall, 4),
                    "device": str(device),
                }
            ),
            flush=True,
        )
        if score > best_f1 + 1e-4:
            best_f1 = score
            stale_epochs = 0
            model.save_pretrained(args.output_dir, safe_serialization=True)
            tokenizer.save_pretrained(args.output_dir)
            (args.output_dir / "training_summary.json").write_text(
                json.dumps(
                    {
                        "base_model": args.base_model,
                        "seed": args.seed,
                        "train_rows": len(train_rows),
                        "validation_rows": len(validation_rows),
                        "validation_accuracy": accuracy,
                        "validation_macro_f1": score,
                        "contradiction_recall": contradiction_recall,
                        "labels": ID2LABEL,
                        "limitations": [
                            "Dữ liệu hiện chủ yếu là synthetic và cần giảng viên kiểm định thêm.",
                            "FactGuard vẫn là lớp bắt buộc cho số và quan hệ so sánh.",
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        else:
            stale_epochs += 1
            if stale_epochs >= 2:
                break

    print(f"best_validation_macro_f1={best_f1:.4f}")


if __name__ == "__main__":
    main()
