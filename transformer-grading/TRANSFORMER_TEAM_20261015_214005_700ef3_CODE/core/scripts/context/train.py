from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random

from app.context.contracts import LABEL2ID, LABELS, SCHEMA_VERSION, make_pair
from scripts.context.metrics import classification_metrics


def load_split(folder: Path, name: str, manifest: dict) -> list[dict]:
    path = folder / f"{name}.jsonl"
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["files_sha256"][path.name]:
        raise ValueError(f"{name}: dữ liệu đã thay đổi, chạy lại prepare")
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def main():
    parser = argparse.ArgumentParser(description="Offline supervised rubric cross-encoder fine-tuning; never trains during an exam.")
    parser.add_argument("--data", default="data/context/prepared")
    parser.add_argument("--output", default="models/context-grader")
    parser.add_argument("--base-model", default="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--accumulation", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--demo", action="store_true", help="Explicitly allow synthetic/draft data; resulting checkpoint always requires teacher review")
    parser.add_argument("--freeze-encoder", action="store_true", help="Quick head-only experiment, not a quality guarantee")
    parser.add_argument("--max-steps", type=int, default=0, help="Smoke test only; limits optimizer steps per epoch")
    args = parser.parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.accumulation < 1 or not 64 <= args.max_length <= 512:
        parser.error("epochs/batch-size/accumulation phải >0, max-length 64..512")
    output, folder = Path(args.output), Path(args.data)
    if output.exists() and any(output.iterdir()):
        parser.error("Output đã có dữ liệu; chọn thư mục mới để tránh ghi đè model đang chạy")
    manifest = json.loads((folder / "dataset_manifest.json").read_text(encoding="utf-8"))
    if manifest["schema_version"] != SCHEMA_VERSION:
        parser.error("Sai dataset schema")
    if manifest["demo_only"] and not args.demo:
        parser.error("Dữ liệu synthetic/draft: chỉ chạy với --demo")
    train_rows, val_rows = load_split(folder, "train", manifest), load_split(folder, "val", manifest)
    counts = Counter(r["label"] for r in train_rows)
    if set(counts) != set(LABELS):
        parser.error(f"Train phải có đủ 5 nhãn; hiện có {dict(counts)}")
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if args.device == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA chưa sẵn sàng. Chạy --device cpu")
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model, num_labels=len(LABELS), id2label=dict(enumerate(LABELS)), label2id=LABEL2ID,
        ignore_mismatched_sizes=True, trust_remote_code=False, use_safetensors=True,
    )
    model.config.context_schema = SCHEMA_VERSION
    if args.freeze_encoder:
        for p in model.base_model.parameters():
            p.requires_grad = False
    model.to(args.device)

    def encode(rows):
        encoded = []
        for row in rows:
            a, b = make_pair(row["question"], row["criterion"], row["reference_answer"], row["student_answer"])
            item = tokenizer(a, b, truncation=False)
            if len(item["input_ids"]) > args.max_length:
                raise ValueError(f"{row['source']}: vượt giới hạn token. Chuẩn hóa dữ liệu; không cắt mất ngữ cảnh")
            item["labels"] = LABEL2ID[row["label"]]
            encoded.append(item)
        return encoded

    collator = DataCollatorWithPadding(tokenizer=tokenizer, return_tensors="pt")
    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(encode(train_rows), batch_size=args.batch_size, shuffle=True,
                              collate_fn=collator, generator=generator, num_workers=0)
    val_loader = DataLoader(encode(val_rows), batch_size=args.batch_size, collate_fn=collator, num_workers=0)
    weights = torch.tensor([min(5.0, len(train_rows) / (len(LABELS) * counts[l])) for l in LABELS], device=args.device)
    loss_fn = torch.nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.learning_rate, weight_decay=0.01)
    output.mkdir(parents=True, exist_ok=True)
    history, best, stale = [], -1.0, 0
    for epoch in range(args.epochs):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        losses, steps = [], 0
        for index, batch in enumerate(train_loader):
            batch = {k: v.to(args.device) for k, v in batch.items()}
            labels = batch.pop("labels")
            loss = loss_fn(model(**batch).logits, labels)
            if not torch.isfinite(loss):
                raise RuntimeError("Loss không hữu hạn; kiểm tra learning rate/dữ liệu")
            # Scale the last incomplete accumulation group correctly.
            window_start = (index // args.accumulation) * args.accumulation
            window_size = min(args.accumulation, len(train_loader) - window_start)
            (loss / window_size).backward()
            losses.append(float(loss.detach().cpu()))
            if (index + 1) % args.accumulation == 0 or index + 1 == len(train_loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                steps += 1
                print(f"epoch={epoch+1} optimizer_step={steps} loss={losses[-1]:.4f}", flush=True)
                if args.max_steps and steps >= args.max_steps:
                    break
        model.eval()
        predicted, truth = [], []
        with torch.inference_mode():
            for batch in val_loader:
                labels = batch.pop("labels")
                logits = model(**{k: v.to(args.device) for k, v in batch.items()}).logits
                predicted.extend(LABELS[i] for i in logits.argmax(-1).cpu().tolist())
                truth.extend(LABELS[i] for i in labels.tolist())
        metrics = classification_metrics(truth, predicted)
        history.append({"epoch": epoch + 1, "mean_train_loss": sum(losses) / len(losses), "validation": metrics})
        print(json.dumps({"epoch": epoch + 1, "validation_macro_f1": metrics["macro_f1"]}), flush=True)
        if metrics["macro_f1"] > best:
            best, stale = metrics["macro_f1"], 0
            model.save_pretrained(output, safe_serialization=True)
            tokenizer.save_pretrained(output)
        else:
            stale += 1
        if stale >= 2:
            break
    weights_path = output / "model.safetensors"
    with weights_path.open("rb") as handle:
        weights_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    result = {"schema_version": SCHEMA_VERSION, "base_model": args.base_model, "labels": LABELS,
              "max_length": args.max_length, "demo_only": bool(manifest["demo_only"] or args.demo or args.max_steps),
              "smoke_only": bool(args.max_steps), "freeze_encoder": args.freeze_encoder,
              "created_at": datetime.now(timezone.utc).isoformat(), "weights_sha256": weights_hash,
              "dataset_files_sha256": manifest["files_sha256"], "best_validation_macro_f1": best,
              "seed": args.seed, "train_labels": dict(counts),
              "note": "Validation selects checkpoint; test is not read during training. Confidence is uncalibrated."}
    (output / "context_manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "training_history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {output}. Next: python -m scripts.context.evaluate --model \"{output}\"")


if __name__ == "__main__":
    main()
