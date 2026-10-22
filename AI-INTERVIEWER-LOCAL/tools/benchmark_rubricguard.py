from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from finetune_rubricguard import metrics, save_json


def memory_usage_mb() -> dict:
    import ctypes
    import sys

    if sys.platform != "win32":
        return {}

    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in (
                "peak_working_set", "working_set", "peak_paged_pool", "paged_pool",
                "peak_nonpaged_pool", "nonpaged_pool", "pagefile", "peak_pagefile")]

    value = Counters()
    value.cb = ctypes.sizeof(value)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    query = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    query.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    query.restype = ctypes.c_int
    if query(kernel.GetCurrentProcess(), ctypes.byref(value), value.cb):
        return {"working_set": round(value.working_set / 1024**2, 1),
                "peak_working_set": round(value.peak_working_set / 1024**2, 1)}
    return {}


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    logits = logits / temperature
    values = np.exp(logits - logits.max(axis=1, keepdims=True))
    return values / values.sum(axis=1, keepdims=True)


def infer(session: ort.InferenceSession, tokenizer: Tokenizer, rows: list[dict]) -> np.ndarray:
    logits = []
    names = {item.name for item in session.get_inputs()}
    for start in range(0, len(rows), 12):
        chunk = rows[start:start + 12]
        encoded = tokenizer.encode_batch([(row["student_answer"], row["reference_claim"]) for row in chunk])
        values = {"input_ids": [e.ids for e in encoded],
                  "attention_mask": [e.attention_mask for e in encoded],
                  "token_type_ids": [e.type_ids for e in encoded]}
        logits.extend(session.run(None, {name: np.asarray(value, dtype=np.int64)
                                       for name, value in values.items() if name in names})[0])
    return np.asarray(logits)


def acceptance(truth: list[int], probs: np.ndarray, threshold: float) -> dict:
    predicted = probs.argmax(1)
    accepted = probs.max(1) >= threshold
    indexes = np.where(accepted)[0]
    count = len(indexes)
    return {"accepted": count, "total": len(truth), "coverage": count / max(1, len(truth)),
            "accuracy": sum(bool(predicted[i] == truth[i]) for i in indexes) / max(1, count),
            "wrong_answers_accepted_as_met": sum(bool(truth[i] == 2 and predicted[i] == 0) for i in indexes)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    path = args.model_dir / "model.int8.onnx"
    config = json.loads((args.model_dir / "config.json").read_text(encoding="utf-8"))
    options = ort.SessionOptions()
    options.intra_op_num_threads = args.threads
    options.inter_op_num_threads = 1
    options.enable_cpu_mem_arena = False
    options.enable_mem_pattern = False
    start = time.perf_counter()
    session = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
    tokenizer = Tokenizer.from_file(str(args.model_dir / "tokenizer.json"))
    tokenizer.enable_truncation(max_length=config.get("rubric_max_length", 192))
    tokenizer.enable_padding(pad_id=1, pad_token="<pad>")
    load_seconds = time.perf_counter() - start
    validation = json.loads((args.checkpoint / "dataset" / "validation.json").read_text(encoding="utf-8"))
    test = json.loads((args.checkpoint / "dataset" / "test.json").read_text(encoding="utf-8"))
    validation_logits = infer(session, tokenizer, validation)
    test_logits = infer(session, tokenizer, test)
    validation_truth = [row["label"] for row in validation]
    test_truth = [row["label"] for row in test]
    short_validation_logits = infer(session, tokenizer,
        [{**row, "reference_claim": row["criterion"]} for row in validation])
    short_rows = [{**row, "reference_claim": row["criterion"]} for row in test]
    short_logits = infer(session, tokenizer, short_rows)
    calibration_logits = np.concatenate([validation_logits, short_validation_logits])
    calibration_truth = validation_truth * 2
    temperatures = np.linspace(0.5, 4.0, 71)
    temperature = float(min(temperatures, key=lambda t:
        -np.log(softmax(calibration_logits, t)[np.arange(len(calibration_truth)), calibration_truth] + 1e-12).mean()))
    validation_probs = softmax(calibration_logits, temperature)
    test_probs = softmax(np.concatenate([test_logits, short_logits]), temperature)
    candidates = []
    for threshold in np.linspace(0.68, 0.995, 64):
        result = acceptance(calibration_truth, validation_probs, threshold)
        if result["accepted"] >= 10 and result["accuracy"] >= 0.98 and not result["wrong_answers_accepted_as_met"]:
            candidates.append((result["accepted"], float(threshold)))
    threshold = max(candidates, key=lambda row: (row[0], -row[1]))[1] if candidates else 1.01
    validation_metrics = metrics(validation_truth, validation_logits.argmax(1).tolist())
    test_metrics = metrics(test_truth, test_logits.argmax(1).tolist())
    fp32_predictions = json.loads((args.checkpoint / "test_predictions.json").read_text(encoding="utf-8"))
    agreement = sum(int(p) == row["predicted_label"] for p, row in zip(test_logits.argmax(1), fp32_predictions)) / len(test)
    latencies = []
    for row in test:
        start = time.perf_counter()
        infer(session, tokenizer, [row])
        latencies.append(time.perf_counter() - start)
    calibration = {"temperature": temperature, "min_confidence": threshold,
                   "fitted_on": "validation_full_and_short_only",
                   "validation_acceptance": acceptance(calibration_truth, validation_probs, threshold),
                   "test_acceptance": acceptance(test_truth * 2, test_probs, threshold)}
    with path.open("rb") as stream:
        model_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    report = {"model_sha256": model_hash, "format": "ONNX INT8 weights / FP32 activations", "threads": args.threads,
        "size_mb": path.stat().st_size / 1024**2, "load_seconds": load_seconds,
        "cpu_memory_arena": False,
        "memory_mb": memory_usage_mb(),
        "warm_latency_ms": {"median": float(np.median(latencies) * 1000),
                            "p95": float(np.percentile(latencies, 95) * 1000)},
        "validation": validation_metrics, "test": test_metrics,
        "short_criteria_test": metrics(test_truth, short_logits.argmax(1).tolist()),
        "fp32_int8_prediction_agreement": agreement, "calibration": calibration}
    save_json(args.model_dir / "runtime_evaluation.json", report)
    save_json(args.model_dir / "calibration.json", calibration)
    summary_path = args.model_dir / "training_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update({"runtime_evaluated": True, "model_sha256": model_hash,
        "validated_languages": ["vi"],
        "validation_accuracy": validation_metrics["accuracy"],
        "validation_macro_f1": validation_metrics["macro_f1"],
        "contradiction_recall": validation_metrics["contradiction_recall"],
        "test": test_metrics, "short_criteria_test": report["short_criteria_test"],
        "calibration": calibration})
    save_json(summary_path, summary)
    save_json(args.model_dir / "int8_test_predictions.json", [
        {**row, "predicted_label": int(pred), "probabilities": probs.tolist()}
        for row, pred, probs in zip(test, test_probs[:len(test)].argmax(1), test_probs[:len(test)])])
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
