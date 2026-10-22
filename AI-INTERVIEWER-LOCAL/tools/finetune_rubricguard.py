from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


LABELS = {"supported": 0, "missing": 1, "uncertain": 1, "contradicted": 2}
ID2LABEL = {0: "entailment", 1: "neutral", 2: "contradiction"}
REVISION = "0a71e92a985b6e1ad1828cf67ce9c459639c1dca"


def normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split()).rstrip(" .")


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def load_rows(data_dir: Path) -> tuple[list[dict], list[dict]]:
    rows, sources, seen = [], [], {}
    for path in sorted(data_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list):
            continue
        sources.append({"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        for item in payload:
            if item.get("relation_label") not in LABELS:
                continue
            answer = str(item["student_answer"]).strip()
            claim = str(item["reference_claim"]).strip()
            label = LABELS[item["relation_label"]]
            if not answer or not claim:
                raise ValueError(f"Empty answer or claim in {path.name}")
            key = (normalize(answer), normalize(claim))
            if key in seen:
                if seen[key] != label:
                    raise ValueError(f"Conflicting labels in {path.name}")
                continue
            seen[key] = label
            rows.append({"question_id": str(item["question_id"]),
                "question": str(item.get("question", "")),
                "criterion": str(item.get("criterion", claim)),
                "student_answer": answer, "reference_claim": claim, "label": label,
                "source": path.name, "data_origin": item.get("data_origin", "unknown")})
    if not rows:
        raise ValueError("No labelled data found")
    return rows, sources


def split_rows(rows: list[dict], seed: int) -> dict[str, list[dict]]:
    # Related answers and claims stay together even across question IDs.
    parent = {row["question_id"]: row["question_id"] for row in rows}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    owners = {}
    for row in rows:
        for field in ("student_answer", "reference_claim"):
            key = (field, normalize(row[field]))
            if key in owners:
                parent[find(row["question_id"])] = find(owners[key])
            else:
                owners[key] = row["question_id"]
    groups = defaultdict(list)
    for row in rows:
        groups[find(row["question_id"])].append(row)
    by_topic = defaultdict(list)
    for key, group in groups.items():
        by_topic[group[0]["source"]].append(key)
    rng = random.Random(seed)
    partitions = {"train": [], "validation": [], "test": []}
    for topic in sorted(by_topic):
        keys = sorted(by_topic[topic])
        rng.shuffle(keys)
        held_out = max(1, len(keys) // 5)
        for index, key in enumerate(keys):
            split = "test" if index < held_out else "validation" if index < held_out * 2 else "train"
            partitions[split].extend(groups[key])
    for split, samples in partitions.items():
        if len(Counter(row["label"] for row in samples)) != 3:
            raise ValueError(f"{split} lacks a class")
    for field in ("question_id", "student_answer", "reference_claim"):
        sets = [{normalize(row[field]) for row in partitions[name]} for name in partitions]
        if any(sets[i] & sets[j] for i in range(3) for j in range(i)):
            raise ValueError(f"Split leakage in {field}")
    return partitions


def augment_training(rows: list[dict]) -> list[dict]:
    augmented = list(rows)
    # Production rubrics may use short criteria rather than full reference claims.
    augmented.extend({**row, "reference_claim": row["criterion"],
                      "data_origin": "train_only_short_criterion"}
                     for row in rows if normalize(row["criterion"]) != normalize(row["reference_claim"]))
    claims = {row["reference_claim"]: row for row in rows}
    for claim, origin in claims.items():
        for answer, label in ((claim, 0), (f"Đúng là {claim}.", 0),
                (f"Em không nhớ phần khác. Tuy nhiên {claim}.", 0),
                (f"Nhận định '{claim}' là đúng.", 0),
                (f"Nhận định 'không đúng là {claim}' là sai. {claim}.", 0),
                (f"Không đúng là {claim}.", 2),
                (f"Tôi phủ định khẳng định sau: {claim}.", 2)):
            augmented.append({**origin, "student_answer": answer, "label": label,
                              "data_origin": "train_only_template"})
        if " là " in claim and not re.search(r"\b(không|chưa)\b", claim.casefold()):
            augmented.append({**origin,
                "student_answer": claim.replace(" là ", " không phải là ", 1),
                "label": 2, "data_origin": "train_only_copula_negation"})
            augmented.append({**origin,
                "student_answer": f"Phát biểu '{claim.replace(' là ', ' không phải là ', 1)}' là sai. {claim}.",
                "label": 0, "data_origin": "train_only_refuted_misconception"})
    unique = {}
    for row in augmented:
        key = (normalize(row["student_answer"]), normalize(row["reference_claim"]))
        if key in unique and unique[key]["label"] != row["label"]:
            raise ValueError("Augmentation introduced conflicting labels")
        unique[key] = row
    return list(unique.values())


def metrics(truth: list[int], predicted: list[int]) -> dict:
    matrix = [[sum(a == i and b == j for a, b in zip(truth, predicted))
               for j in range(3)] for i in range(3)]
    per_class = {}
    for label, name in ID2LABEL.items():
        tp, support = matrix[label][label], sum(matrix[label])
        precision = tp / max(1, sum(row[label] for row in matrix))
        recall = tp / max(1, support)
        per_class[name] = {"precision": precision, "recall": recall,
            "f1": 2 * precision * recall / max(1e-12, precision + recall), "support": support}
    return {"accuracy": sum(matrix[i][i] for i in range(3)) / max(1, len(truth)),
        "macro_f1": sum(item["f1"] for item in per_class.values()) / 3,
        "contradiction_recall": per_class["contradiction"]["recall"],
        "false_met_on_wrong": matrix[2][0] / max(1, sum(matrix[2])),
        "count": len(truth), "confusion_matrix": matrix, "per_class": per_class}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-model", default="MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli")
    parser.add_argument("--epochs", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20261016)
    parser.add_argument("--learning-rate", type=float, default=3e-5)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=192)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--no-augment", action="store_true")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    args = parser.parse_args()

    import numpy as np
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.set_num_threads(args.threads)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and args.device != "cpu" else "cpu")
    if args.device == "cuda" and device.type != "cuda":
        raise RuntimeError("CUDA requested but unavailable")
    rows, sources = load_rows(args.data_dir)
    splits = split_rows(rows, args.seed)
    training = splits["train"] if args.no_augment else augment_training(splits["train"])
    train_claims = {normalize(row["reference_claim"]) for row in training}
    for name in ("validation", "test"):
        held_out_claims = {normalize(row[field]) for row in splits[name]
                           for field in ("reference_claim", "criterion")}
        if train_claims & held_out_claims:
            raise ValueError(f"Augmented claim leakage into {name}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, subset in splits.items():
        save_json(args.output_dir / "dataset" / f"{name}.json", subset)
    save_json(args.output_dir / "dataset" / "train_augmented.json", training)
    save_json(args.output_dir / "dataset_manifest.json", {"seed": args.seed, "sources": sources,
        "grouping": "question+duplicate_answer+duplicate_claim",
        "splits": {name: {"rows": len(subset),
            "question_ids": sorted({row["question_id"] for row in subset}),
            "labels": dict(Counter(ID2LABEL[row["label"]] for row in subset))}
            for name, subset in splits.items()}, "augmented_train_rows": len(training)})
    load_options = {"local_files_only": True} if Path(args.base_model).exists() else {"revision": REVISION}
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, **load_options)
    model = AutoModelForSequenceClassification.from_pretrained(args.base_model, **load_options).to(device)
    model.config.id2label = ID2LABEL
    model.config.label2id = {v: k for k, v in ID2LABEL.items()}
    model.config.rubric_max_length = args.max_length
    # Freeze the large vocabulary table to reduce training memory and overfitting.
    for parameter in model.roberta.embeddings.parameters():
        parameter.requires_grad = False

    def encode(samples: list[dict]) -> list[dict]:
        return [dict(tokenizer(row["student_answer"], row["reference_claim"],
            truncation=True, max_length=args.max_length), labels=row["label"]) for row in samples]

    def batches(encoded: list[dict], shuffle: bool = False):
        indexes = list(range(len(encoded)))
        if shuffle:
            random.shuffle(indexes)
        for start in range(0, len(indexes), args.batch_size):
            selected = [encoded[index] for index in indexes[start:start + args.batch_size]]
            inputs = tokenizer.pad([{k: v for k, v in row.items() if k != "labels"}
                for row in selected], padding=True, return_tensors="pt")
            yield ({k: v.to(device) for k, v in inputs.items()},
                   torch.tensor([row["labels"] for row in selected], device=device))

    train_encoded = encode(training)
    validation_encoded = encode(splits["validation"])
    test_encoded = encode(splits["test"])

    def predict(encoded: list[dict]) -> tuple[list[int], np.ndarray]:
        model.eval()
        truth, logits = [], []
        with torch.inference_mode():
            for inputs, labels in batches(encoded):
                logits.extend(model(**inputs).logits.cpu().numpy())
                truth.extend(labels.cpu().tolist())
        return truth, np.asarray(logits)

    validation_truth, base_logits = predict(validation_encoded)
    baseline_validation = metrics(validation_truth, base_logits.argmax(1).tolist())
    test_truth, base_test_logits = predict(test_encoded)
    baseline_test = metrics(test_truth, base_test_logits.argmax(1).tolist())
    save_json(args.output_dir / "baseline_metrics.json", {"validation": baseline_validation, "test": baseline_test})
    print(json.dumps({"baseline_validation": baseline_validation, "baseline_test": baseline_test}), flush=True)
    counts = Counter(row["label"] for row in training)
    weights = torch.tensor([len(training) / (3 * counts[i]) for i in range(3)], device=device)
    trainable = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=args.learning_rate, weight_decay=0.01)
    total_steps = math.ceil(len(training) / args.batch_size) * args.epochs
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda step:
        min((step + 1) / max(1, total_steps * 0.08), 1.0)
        * max(0.05, 1.0 - step / max(1, total_steps)))
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    history, best_f1, stale_epochs = [], -1.0, 0
    started = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss, count = 0.0, 0
        epoch_started = time.perf_counter()
        for inputs, labels in batches(train_encoded, shuffle=True):
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
                loss = torch.nn.functional.cross_entropy(model(**inputs).logits, labels, weight=weights)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(trainable, 1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            total_loss += loss.item()
            count += 1
        truth, logits = predict(validation_encoded)
        validation = metrics(truth, logits.argmax(1).tolist())
        record = {"epoch": epoch, "loss": total_loss / max(1, count),
            "seconds": round(time.perf_counter() - epoch_started, 2), "validation": validation}
        history.append(record)
        print(json.dumps(record), flush=True)
        save_json(args.output_dir / "history.json", history)
        if validation["macro_f1"] > best_f1 + 1e-4:
            best_f1, stale_epochs = validation["macro_f1"], 0
            model.save_pretrained(args.output_dir, safe_serialization=True)
            tokenizer.save_pretrained(args.output_dir)
            np.save(args.output_dir / "validation_logits.npy", logits)
            save_json(args.output_dir / "training_summary.json", {
                "model_stage": "fine_tuned_candidate", "base_model": args.base_model,
                "revision": REVISION, "seed": args.seed, "best_epoch": epoch,
                "train_rows": len(training), "validation_rows": len(truth),
                "validation_accuracy": validation["accuracy"],
                "validation_macro_f1": validation["macro_f1"],
                "contradiction_recall": validation["contradiction_recall"],
                "validation": validation, "baseline_validation": baseline_validation,
                "baseline_test": baseline_test, "training_device": str(device),
                "learning_rate": args.learning_rate, "max_length": args.max_length,
                "trainable_parameters": sum(p.numel() for p in trainable),
                "total_parameters": sum(p.numel() for p in model.parameters()),
                "production_ready": False,
                "limitations": ["Synthetic data only; no independently labelled real student test set.",
                    "Vietnamese training only; English quality not validated.",
                    "Numeric reasoning remains delegated to FactGuard."]})
        else:
            stale_epochs += 1
            if stale_epochs >= args.patience:
                break
    del model
    model = AutoModelForSequenceClassification.from_pretrained(args.output_dir, local_files_only=True).to(device)
    truth, logits = predict(test_encoded)
    test = metrics(truth, logits.argmax(1).tolist())
    summary_path = args.output_dir / "training_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update({"test": test, "elapsed_seconds": round(time.perf_counter() - started, 2)})
    save_json(summary_path, summary)
    save_json(args.output_dir / "test_predictions.json", [
        {**row, "predicted_label": int(pred), "logits": values.tolist()}
        for row, pred, values in zip(splits["test"], logits.argmax(1), logits)])
    print(json.dumps({"best_epoch": summary["best_epoch"], "test": test,
        "elapsed_seconds": summary["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
