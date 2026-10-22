"""Isolated, question-disjoint grading experiment. Never loads the application DB."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
import hashlib
import json
from pathlib import Path
import random
import statistics
import time

if __package__:
    from .finetune_rubricguard import ID2LABEL, load_rows, metrics, normalize, save_json
else:
    from finetune_rubricguard import ID2LABEL, load_rows, metrics, normalize, save_json

ROOT = Path(__file__).resolve().parents[1]
INPUT_FORMAT = "question_answer_pair_v1"
LABEL_IDS = {"S": 0, "M": 1, "C": 2}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_pair(row: dict, contextual: bool) -> tuple[str, str]:
    # The correct reference is only the hypothesis, never part of the student's premise.
    premise = (f"Question: {row['question']}\nStudent answer: {row['student_answer']}"
               if contextual else row["student_answer"])
    return premise, row["reference_claim"]


def check_splits(splits: dict[str, list[dict]]) -> None:
    names = list(splits)
    for field in ("question_id", "student_answer", "reference_claim"):
        values = [{normalize(row[field]) for row in splits[name]} for name in names]
        if any(values[i] & values[j] for i in range(len(names)) for j in range(i)):
            raise ValueError(f"Cross-split leakage: {field}")
    for name, rows in splits.items():
        if set(row["label"] for row in rows) != {0, 1, 2}:
            raise ValueError(f"All three classes required in {name}")


def prepare(output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite experiment: {output}")
    source_dir = ROOT / "data/rubricguard_training"
    pilot_path = ROOT / "data/semantic_pilot_v1.json"
    pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
    originals, sources = load_rows(source_dir)
    rubrics = defaultdict(dict)
    for path in sorted(source_dir.glob("*.json")):
        for item in json.loads(path.read_text(encoding="utf-8-sig")):
            existing = rubrics[item["question_id"]].setdefault(item["rubric_criterion_id"], item)
            if any(existing[field] != item[field] for field in ("reference_claim", "max_points")):
                raise ValueError("Inconsistent source rubric")
    splits = {name: [] for name in ("train", "validation", "test")}
    assigned = {}
    for group in pilot["groups"]:
        qid, split = group["id"], group["split"]
        if qid in assigned or qid in pilot["quarantined_questions"] or split not in splits:
            raise ValueError(f"Invalid assignment: {qid}")
        assigned[qid] = split
        criteria = sorted(rubrics[qid].values(), key=lambda r: int(r["rubric_criterion_id"].rsplit("R", 1)[1]))
        if sum(float(c["max_points"]) for c in criteria) != 10:
            raise ValueError(f"Unexpected source point total: {qid}")
        for answer_index, (answer, labels) in enumerate(group["answers"]):
            if len(labels) != len(criteria):
                raise ValueError(f"Label count: {qid}")
            for criterion, label in zip(criteria, labels):
                splits[split].append({"question_id": qid, "question": criteria[0]["question"],
                    "case_id": f"{qid}_natural_{answer_index:02d}",
                    "criterion_id": criterion["rubric_criterion_id"],
                    "max_points": criterion["max_points"],
                    "reference_claim": criterion["reference_claim"],
                    "student_answer": answer, "label": LABEL_IDS[label],
                    "data_origin": "agent_authored_course_paraphrase_not_teacher_gold",
                    "teacher_validated": False})
    # Existing uncertain labels are NOT silently converted to missing/wrong.
    for row in originals:
        if assigned.get(row["question_id"]) != "train":
            continue
        raw = [c for c in rubrics[row["question_id"]].values()
               if c["reference_claim"] == row["reference_claim"]][0]
        source_items = json.loads((source_dir / row["source"]).read_text(encoding="utf-8-sig"))
        if any(normalize(x["student_answer"]) == normalize(row["student_answer"])
               and x["reference_claim"] == row["reference_claim"]
               and x["relation_label"] == "uncertain" for x in source_items):
            continue
        splits["train"].append({**row, "case_id": "source_" + hashlib.sha256(
            row["student_answer"].encode()).hexdigest()[:12],
            "criterion_id": raw["rubric_criterion_id"], "max_points": raw["max_points"],
            "teacher_validated": False})
    for name in splits:
        unique = {}
        for row in splits[name]:
            key = (normalize(row["student_answer"]), normalize(row["reference_claim"]))
            if key in unique and unique[key]["label"] != row["label"]:
                raise ValueError("Conflicting experiment labels")
            unique[key] = row
        splits[name] = list(unique.values())
    check_splits(splits)
    output.mkdir(parents=True)
    for name, rows in splits.items():
        save_json(output / "dataset" / f"{name}.json", rows)
    protected = [p for folder in (ROOT / "app/static", ROOT / "models/rubricguard-lite")
                 for p in folder.rglob("*") if p.is_file()]
    protected += list((ROOT / "data").glob("question_bank*.json"))
    save_json(output / "manifest.json", {"input_format": INPUT_FORMAT,
        "pilot_sha256": digest(pilot_path), "sources": sources,
        "splits": {name: {"rows": len(rows), "questions": sorted({r["question_id"] for r in rows}),
            "labels": dict(Counter(ID2LABEL[r["label"]] for r in rows)),
            "sha256": digest(output / "dataset" / f"{name}.json")} for name, rows in splits.items()},
        "quarantined_questions": pilot["quarantined_questions"],
        "protected_files": {str(p.relative_to(ROOT)): digest(p) for p in protected},
        "production_ready": False, "teacher_validated": False,
        "limitations": ["Agent-authored synthetic VI pilot, not real student accuracy.",
            "Active model may previously have seen these source question topics.",
            "Test questions excluded from candidate training and calibration.",
            "No external curriculum, active model, database or frontend modified."]})
    print(json.dumps({name: len(rows) for name, rows in splits.items()}), flush=True)


def read_split(output: Path, name: str) -> list[dict]:
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    path = output / "dataset" / f"{name}.json"
    if digest(path) != manifest["splits"][name]["sha256"]:
        raise ValueError(f"Frozen {name} dataset changed")
    return json.loads(path.read_text(encoding="utf-8"))


def train(output: Path, epochs: int, threads: int) -> None:
    import numpy as np
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    checkpoint = output / "checkpoint"
    if checkpoint.exists():
        raise FileExistsError("Refusing to overwrite an existing checkpoint")
    torch.set_num_threads(threads)
    torch.manual_seed(20261021)
    random.seed(20261021)
    np.random.seed(20261021)
    tokenizer = AutoTokenizer.from_pretrained(ROOT / "models/rubricguard-base", local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        ROOT / "models/rubricguard-base", local_files_only=True)
    model.config.rubric_input_format = INPUT_FORMAT
    model.config.rubric_max_length = 192
    model.config.id2label = ID2LABEL
    model.config.label2id = {name: label for label, name in ID2LABEL.items()}
    for parameter in model.roberta.embeddings.parameters():
        parameter.requires_grad = False

    def encode(rows):
        return [{**tokenizer(*input_pair(row, True), truncation=True, max_length=192),
                 "label": row["label"]} for row in rows]

    training = read_split(output, "train")
    train_rows = encode(training)
    validation = encode(read_split(output, "validation"))

    def batches(rows, shuffle=False):
        indexes = list(range(len(rows)))
        if shuffle:
            random.shuffle(indexes)
        for start in range(0, len(indexes), 12):
            selected = [rows[i] for i in indexes[start:start + 12]]
            yield tokenizer.pad([{k: v for k, v in r.items() if k != "label"} for r in selected],
                padding=True, return_tensors="pt"), torch.tensor([r["label"] for r in selected])

    trainable = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=2e-5, weight_decay=0.01)
    counts = Counter(row["label"] for row in train_rows)
    weights = torch.tensor([len(training) / (3 * counts[i]) for i in range(3)])
    history, best, stale = [], -1.0, 0
    started = time.perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        losses = []
        for inputs, labels in batches(train_rows, True):
            optimizer.zero_grad(set_to_none=True)
            loss = torch.nn.functional.cross_entropy(model(**inputs).logits, labels, weight=weights)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable, 1)
            optimizer.step()
            losses.append(loss.item())
        model.eval()
        logits, truth = [], []
        with torch.inference_mode():
            for inputs, labels in batches(validation):
                logits.extend(model(**inputs).logits.numpy())
                truth.extend(labels.tolist())
        scores = metrics(truth, np.asarray(logits).argmax(1).tolist())
        history.append({"epoch": epoch, "loss": statistics.mean(losses), "validation": scores,
                        "elapsed_seconds": round(time.perf_counter() - started, 2)})
        save_json(output / "history.json", history)
        print(json.dumps(history[-1]), flush=True)
        if scores["macro_f1"] > best + 0.0001:
            best, stale = scores["macro_f1"], 0
            model.save_pretrained(checkpoint, safe_serialization=True)
            tokenizer.save_pretrained(checkpoint)
            save_json(checkpoint / "training_summary.json", {"best_epoch": epoch,
                "validation": scores, "input_format": INPUT_FORMAT, "max_length": 192,
                "base_model": "local multilingual-MiniLMv2-L6-mnli-xnli",
                "training_device": "cpu", "threads": threads, "learning_rate": 2e-5,
                "train_rows": len(training), "total_parameters": sum(p.numel() for p in model.parameters()),
                "trainable_parameters": sum(p.numel() for p in trainable),
                "production_ready": False, "teacher_validated": False,
                "test_used_for_selection": False, "validated_languages": ["vi_synthetic_pilot_only"]})
        else:
            stale += 1
            if stale >= 3:
                break
    save_json(output / "training_run.json", {"elapsed_seconds": time.perf_counter() - started,
        "epochs_completed": len(history), "test_opened_during_training": False})


def probabilities(logits, temperature):
    import numpy as np
    scaled = np.asarray(logits) / temperature
    values = np.exp(scaled - scaled.max(axis=1, keepdims=True))
    return values / values.sum(axis=1, keepdims=True)


def calibrate(logits, truth: list[int]) -> dict:
    import numpy as np
    # Validation only. No confidence threshold is selected from the final test.
    best = min((float(-np.log(probabilities(logits, t)[np.arange(len(truth)), truth]
                      .clip(1e-12)).mean()), t) for t in np.arange(0.5, 4.01, 0.1))
    probs = probabilities(logits, best[1])
    confidence, predictions = probs.max(1), probs.argmax(1)
    eligible = []
    for threshold in (0.91, 0.95, 0.97, 0.99, 0.995, 0.999):
        accepted = confidence >= threshold
        count = int(accepted.sum())
        if count >= 20 and bool((predictions[accepted] == np.asarray(truth)[accepted]).all()):
            eligible.append((count, threshold))
    threshold = max(eligible, key=lambda v: (v[0], -v[1]))[1] if eligible else 1.01
    return {"temperature": best[1], "min_confidence": threshold,
            "validation_nll": best[0], "fitted_on": "frozen_validation_only",
            "min_validation_accepts": 20, "observed_validation_error_budget": 0,
            "production_ready": False,
            "warning": "Zero observed errors in a small synthetic sample is not a safety guarantee."}


def selective(probs, truth: list[int], threshold: float, truncated: list[bool]) -> dict:
    import numpy as np
    pred = probs.argmax(1)
    accepted = (probs.max(1) >= threshold) & ~np.asarray(truncated)
    count = int(accepted.sum())
    errors = int(((pred != truth) & accepted).sum())
    return {"accepted": count, "total": len(truth), "coverage": count / len(truth),
        "accuracy_when_accepted": (count - errors) / count if count else None,
        "errors_when_accepted": errors,
        "wrong_claim_accepted_as_supported": int(((np.asarray(truth) == 2) & (pred == 0) & accepted).sum()),
        "correct_claim_accepted_as_non_supported": int(((np.asarray(truth) == 0) & (pred != 0) & accepted).sum())}


def infer(session, tokenizer, rows: list[dict], contextual: bool):
    import numpy as np
    logits, truncated, times = [], [], []
    for row in rows:
        start = time.perf_counter()
        encoded = tokenizer.encode(*input_pair(row, contextual))
        ids = encoded.ids
        truncated.append(len(ids) > 192)
        # Use the same pair-aware truncation as training; overflow always abstains.
        tokenizer.enable_truncation(max_length=192)
        encoded = tokenizer.encode(*input_pair(row, contextual))
        tokenizer.no_truncation()
        inputs = {"input_ids": np.asarray([encoded.ids], dtype=np.int64),
                  "attention_mask": np.asarray([encoded.attention_mask], dtype=np.int64)}
        logits.append(session.run(None, inputs)[0][0])
        times.append(time.perf_counter() - start)
    return np.asarray(logits), truncated, times


def process_memory() -> dict:
    import os
    if os.name != "nt":
        return {"unavailable": True}
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize",
                "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {"working_set_mib": counters.WorkingSetSize / 1024**2,
            "peak_working_set_mib": counters.PeakWorkingSetSize / 1024**2}


def regression_check(session, tokenizer, contextual: bool, policy: dict) -> dict:
    path = ROOT / "data/semantic_pilot_regression_cases_v1.json"
    if not path.exists():
        path = ROOT / "reports/student_grading_fix_20261020/release-v6/results.json"
    source = json.loads(path.read_text(encoding="utf-8"))
    labels = {"met": 0, "missing": 1, "contradicted": 2}
    rows = []
    for case in source["cases"]:
        for point, relation in case["expected_relations"].items():
            rows.append({"case_id": case["id"], "question": case["question"]["question"],
                "reference_claim": point, "student_answer": case["answer"],
                "label": labels.get(relation, -1)})
    logits, truncated, _ = infer(session, tokenizer, rows, contextual)
    probs = probabilities(logits, policy["temperature"])
    predictions = probs.argmax(1).tolist()
    accepted = [not truncated[i] and float(probs[i].max()) >= policy["min_confidence"]
                for i in range(len(rows))]
    known = [i for i, row in enumerate(rows) if row["label"] >= 0]
    return {"scope": "Known rehearsal, raw classifier only, NOT the production rules/LLM pipeline or independent test",
        "source_sha256": digest(path),
        "raw_metrics": metrics([rows[i]["label"] for i in known], [predictions[i] for i in known]),
        "unresolved_conflicts_accepted": sum(accepted[i] for i, row in enumerate(rows) if row["label"] == -1),
        "predictions": [{**r, "prediction": predictions[i], "accepted": accepted[i],
            "confidence": float(probs[i].max())} for i, r in enumerate(rows)]}


def evaluate(output: Path, arm: str, threads: int) -> None:
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer
    suffix = "" if threads == 4 else f"_t{threads}"
    destination = output / f"evaluation_{arm}{suffix}.json"
    if destination.exists():
        raise FileExistsError("Refusing to overwrite a held-out result")
    directory = ROOT / "models/rubricguard-lite" if arm == "active" else output / "onnx"
    contextual = arm == "candidate"
    if contextual and json.loads((directory / "config.json").read_text())["rubric_input_format"] != INPUT_FORMAT:
        raise ValueError("Candidate input contract does not match its checkpoint")
    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    memory_before = process_memory()
    started = time.perf_counter()
    tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
    tokenizer.no_padding()
    tokenizer.no_truncation()
    session = ort.InferenceSession(str(directory / "model.int8.onnx"), sess_options=options,
                                   providers=["CPUExecutionProvider"])
    load_seconds = time.perf_counter() - started
    validation = read_split(output, "validation")
    val_logits, val_truncated, _ = infer(session, tokenizer, validation, contextual)
    if contextual:
        calibration_path = output / "candidate_calibration.json"
        if calibration_path.exists():
            policy = json.loads(calibration_path.read_text(encoding="utf-8"))
        else:
            policy = calibrate(val_logits, [r["label"] for r in validation])
            # Calibration is fixed before the first final-test forward pass.
            save_json(calibration_path, policy)
    else:
        policy = json.loads((directory / "calibration.json").read_text(encoding="utf-8"))
    test = read_split(output, "test")
    logits, truncated, times = infer(session, tokenizer, test, contextual)
    truth = [r["label"] for r in test]
    probs = probabilities(logits, policy["temperature"])
    pred = probs.argmax(1).tolist()
    val_probs = probabilities(val_logits, policy["temperature"])
    score = metrics(truth, pred)
    accepted = (probs.max(1) >= policy["min_confidence"]) & ~np.asarray(truncated)
    per_answer = defaultdict(list)
    for i, row in enumerate(test):
        per_answer[row["case_id"]].append(i)
    finals = [indexes for indexes in per_answer.values() if all(accepted[i] for i in indexes)]
    score["fully_accepted_answers"] = len(finals)
    score["fully_accepted_answers_with_any_wrong_criterion"] = sum(
        any(pred[i] != truth[i] for i in indexes) for indexes in finals)
    score["answers"] = len(per_answer)
    score["raw_answer_score_mae_out_of_10"] = statistics.mean(abs(sum(
        (int(pred[i] == 0) - int(truth[i] == 0)) * test[i]["max_points"] for i in indexes))
        for indexes in per_answer.values())
    rows = [{**row, "prediction": pred[i], "confidence": float(probs[i].max()),
        "probabilities": probs[i].tolist(), "accepted": bool(accepted[i]),
        "truncated": truncated[i]} for i, row in enumerate(test)]
    result = {"arm": arm, "input_format": INPUT_FORMAT if contextual else "answer_claim_pair_v0",
        "threads": threads, "backend": "ONNX Runtime CPU, single-criterion requests",
        "load_seconds": load_seconds, "int8_mib": (directory / "model.int8.onnx").stat().st_size / 1024**2,
        "policy": policy, "test": score,
        "validation_raw_metrics": metrics([r["label"] for r in validation], val_probs.argmax(1).tolist()),
        "validation_selective": selective(val_probs, [r["label"] for r in validation],
                                          policy["min_confidence"], val_truncated),
        "test_selective": selective(probs, truth, policy["min_confidence"], truncated),
        "latency_seconds": {"median": statistics.median(times), "p95": float(np.percentile(times, 95)),
            "total": sum(times), "note": "Warm CPU latency on this machine, not a 4/8GB device benchmark."},
        "process_memory_before_model": memory_before, "process_memory_after_inference": process_memory(),
        "per_subject": {subject: metrics([truth[i] for i, r in enumerate(test) if r["question_id"].startswith(subject)],
                                       [pred[i] for i, r in enumerate(test) if r["question_id"].startswith(subject)])
                        for subject in ("AI_", "DB_", "DSA_", "OOP_")},
        "predictions": rows, "production_ready": False, "teacher_validated": False}
    result["known_rehearsal"] = regression_check(session, tokenizer, contextual, policy)
    save_json(destination, result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("predictions", "per_subject", "known_rehearsal")}), flush=True)
    del session
    gc.collect()


def verify(output: Path) -> None:
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["protected_files"].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f"Protected production file changed: {name}")
    for name in manifest["splits"]:
        read_split(output, name)
    for source in manifest["sources"]:
        if digest(ROOT / "data/rubricguard_training" / source["name"]) != source["sha256"]:
            raise ValueError(f"Approved training source changed: {source['name']}")
    if digest(ROOT / "data/semantic_pilot_v1.json") != manifest["pilot_sha256"]:
        raise ValueError("Pilot definition changed after freeze")
    print("Frozen datasets and protected production files unchanged.", flush=True)


def summarize(output: Path) -> None:
    import numpy as np
    active = json.loads((output / "evaluation_active.json").read_text(encoding="utf-8"))
    candidate = json.loads((output / "evaluation_candidate.json").read_text(encoding="utf-8"))
    by_question = defaultdict(list)
    review = []
    for old, new in zip(active["predictions"], candidate["predictions"], strict=True):
        if (old["case_id"], old["criterion_id"]) != (new["case_id"], new["criterion_id"]):
            raise ValueError("Comparison rows do not align")
        by_question[new["question_id"]].append((int(new["prediction"] == new["label"])
                                                - int(old["prediction"] == old["label"])))
        if old["prediction"] != new["label"] or new["prediction"] != new["label"]:
            review.append({**new, "active_prediction": old["prediction"],
                "proposed_synthetic_label": new["label"], "reviewer_label": None,
                "review_status": "pending_independent_teacher_review",
                "usage": "evaluation_only_not_training; never recycle into this frozen test"})
    groups = list(by_question.values())
    rng = random.Random(20261021)
    deltas = []
    for _ in range(5000):
        samples = [groups[rng.randrange(len(groups))] for _ in groups]
        deltas.append(sum(sum(g) for g in samples) / sum(map(len, samples)))
    gates = json.loads((output / "predeclared_gates.json").read_text(encoding="utf-8"))
    failures = []
    for metric, minimum in (("accuracy", gates["criterion_accuracy_minimum"]),
                            ("macro_f1", gates["criterion_macro_f1_minimum"])):
        if candidate["test"][metric] < minimum:
            failures.append(f"test_{metric}_below_gate")
    if candidate["test"]["per_class"]["entailment"]["recall"] < gates["correct_claim_recall_minimum"]:
        failures.append("correct_claim_recall_below_gate")
    selection = candidate["test_selective"]
    if selection["coverage"] < gates["selective_coverage_minimum"]:
        failures.append("selective_coverage_below_gate")
    if selection["errors_when_accepted"] > gates["selective_errors_maximum"]:
        failures.append("selective_errors_above_gate")
    if selection["wrong_claim_accepted_as_supported"] > gates["wrong_claims_accepted_as_supported_maximum"]:
        failures.append("selective_wrong_claims_credited")
    failures.extend(gates["required_before_production"])
    save_json(output / "decision.json", {"production_ready": False, "active_model_replaced": False,
        "input_contract_changed_in_production": False, "failure_reasons": failures,
        "raw_accuracy_delta": candidate["test"]["accuracy"] - active["test"]["accuracy"],
        "question_cluster_bootstrap_95_percent_interval": np.percentile(deltas, [2.5, 97.5]).tolist(),
        "bootstrap_unit": "8 held-out question groups, 5000 paired resamples; descriptive synthetic pilot only",
        "teacher_validated": False, "stt_evaluated": False})
    save_json(output / "teacher_review_queue.json", review)
    print(json.dumps({"review_items": len(review), "production_ready": False,
        "raw_accuracy_delta": candidate["test"]["accuracy"] - active["test"]["accuracy"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "train", "evaluate", "verify", "summarize"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--arm", choices=["active", "candidate"], default="candidate")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.output)
    elif args.action == "train":
        train(args.output, args.epochs, args.threads)
    elif args.action == "evaluate":
        evaluate(args.output, args.arm, args.threads)
    elif args.action == "summarize":
        summarize(args.output)
    else:
        verify(args.output)


if __name__ == "__main__":
    main()
