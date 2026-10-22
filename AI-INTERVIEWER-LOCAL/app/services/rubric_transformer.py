from __future__ import annotations

import hashlib
import gc
import json
import math
import re
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np


_SESSION: Any | None = None
_TOKENIZER: Any | None = None
_MODEL_PATH: Path | None = None
_MODEL_STAMP: tuple | None = None
_LOAD_ERROR = ""
_LOCK = threading.Lock()


def release_transformer() -> None:
    global _SESSION, _TOKENIZER, _MODEL_PATH, _MODEL_STAMP
    with _LOCK:
        _SESSION = _TOKENIZER = _MODEL_PATH = _MODEL_STAMP = None
    gc.collect()


def _softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values, axis=-1, keepdims=True)
    exponent = np.exp(shifted)
    return exponent / np.sum(exponent, axis=-1, keepdims=True)


def _model_file(model_dir: Path) -> Path | None:
    quantized = model_dir / "model.int8.onnx"
    original = model_dir / "model.onnx"
    if quantized.exists():
        return quantized
    return original if original.exists() else None


def _runtime_stamp(model_dir: Path, model: Path | None) -> tuple | None:
    if model is None:
        return None
    try:
        return tuple((path.stat().st_size, path.stat().st_mtime_ns)
                     for path in (model, model_dir / "tokenizer.json", model_dir / "config.json"))
    except OSError:
        return None


@lru_cache(maxsize=4)
def _weight_hash(path: str, size: int, modified_ns: int) -> str:
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _verified_runtime(model_dir: Path, summary: dict[str, Any]) -> bool:
    if summary.get("runtime_evaluated") is not True:
        return False
    try:
        model = _model_file(model_dir)
        if model is None:
            return False
        report = json.loads((model_dir / "runtime_evaluation.json").read_text(encoding="utf-8"))
        calibration = json.loads((model_dir / "calibration.json").read_text(encoding="utf-8"))
        stat = model.stat()
        return (
            report["model_sha256"] == summary["model_sha256"]
            and report["model_sha256"] == _weight_hash(str(model), stat.st_size, stat.st_mtime_ns)
            and calibration == summary.get("calibration")
        )
    except (OSError, KeyError, TypeError, ValueError):
        return False


def transformer_status(model_dir: Path) -> dict[str, Any]:
    model = _model_file(model_dir)
    tokenizer = model_dir / "tokenizer.json"
    quality = _quality_metadata(model_dir)
    return {
        "installed": bool(model and tokenizer.exists()),
        "loaded": _SESSION is not None and _MODEL_PATH == model
                  and _MODEL_STAMP == _runtime_stamp(model_dir, model),
        "model": "multilingual-MiniLMv2-L6-mnli-xnli",
        "runtime": "onnxruntime-cpu-int8" if model and ".int8." in model.name else "onnxruntime-cpu",
        "path": str(model_dir),
        "size_mb": round(model.stat().st_size / (1024 * 1024), 1) if model else 0.0,
        "last_error": _LOAD_ERROR,
        "production_ready": quality["production_ready"],
        "selective_ready": quality.get("selective_ready", False),
        "model_stage": quality.get("model_stage", "pretrained_baseline"),
        "validated_languages": quality.get("validated_languages", []),
        "validation_macro_f1": quality.get("validation_macro_f1"),
        "contradiction_recall": quality.get("contradiction_recall"),
    }


def _quality_metadata(model_dir: Path) -> dict[str, Any]:
    summary_path = model_dir / "training_summary.json"
    if not summary_path.exists():
        return {"production_ready": False}
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if not isinstance(summary, dict):
            return {"production_ready": False}
        verified_runtime = _verified_runtime(model_dir, summary)
        macro_f1 = float(summary.get("validation_macro_f1", 0))
        contradiction_recall = float(summary.get("contradiction_recall", 0))
        test = summary.get("test") or {}
        test_macro_f1 = float(test.get("macro_f1", 0))
        test_recall = float(test.get("contradiction_recall", 0))
        false_met = float(test.get("false_met_on_wrong", 1))
        calibration = summary.get("calibration") or {}
        validation_acceptance = calibration.get("validation_acceptance") or {}
        test_acceptance = calibration.get("test_acceptance") or {}
        selective_ready = (
            verified_runtime
            and summary.get("model_stage") == "fine_tuned_candidate"
            and float(calibration.get("min_confidence", 2)) < 1.0
            and int(validation_acceptance.get("accepted", 0)) >= 10
            and int(test_acceptance.get("accepted", 0)) >= 10
            and float(validation_acceptance.get("accuracy", 0)) >= 0.98
            and float(test_acceptance.get("accuracy", 0)) >= 0.98
            and int(validation_acceptance.get("wrong_answers_accepted_as_met", 1)) == 0
            and int(test_acceptance.get("wrong_answers_accepted_as_met", 1)) == 0
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {"production_ready": False}
    summary["production_ready"] = (
        verified_runtime
        and macro_f1 >= 0.8
        and contradiction_recall >= 0.9
        and test_macro_f1 >= 0.8
        and test_recall >= 0.9
        and false_met <= 0.02
    )
    summary["selective_ready"] = selective_ready
    return summary


def _calibration(model_dir: Path) -> tuple[float, float]:
    path = model_dir / "calibration.json"
    if not path.exists():
        return 1.0, 0.68
    try:
        calibration = json.loads(path.read_text(encoding="utf-8"))
        temperature = float(calibration["temperature"])
        threshold = float(calibration["min_confidence"])
        if not math.isfinite(temperature) or not 0.1 <= temperature <= 10:
            raise ValueError("Invalid temperature")
        if not math.isfinite(threshold) or not 0.5 <= threshold <= 1.01:
            raise ValueError("Invalid confidence threshold")
        return temperature, threshold
    except (OSError, KeyError, TypeError, ValueError):
        # Broken calibration must not silently enable automatic grading.
        return 1.0, 1.01


def _load(model_dir: Path) -> tuple[Any, Any, dict[str, str]]:
    global _SESSION, _TOKENIZER, _MODEL_PATH, _MODEL_STAMP, _LOAD_ERROR
    model = _model_file(model_dir)
    if model is None or not (model_dir / "tokenizer.json").exists():
        raise RuntimeError("RubricGuard Transformer is not installed")
    with _LOCK:
        stamp = _runtime_stamp(model_dir, model)
        if _SESSION is not None and _TOKENIZER is not None and _MODEL_PATH == model and _MODEL_STAMP == stamp:
            config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
            return _SESSION, _TOKENIZER, config.get("id2label", {})
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer

            options = ort.SessionOptions()
            options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            from app.services.resource_policy import detect_resource_policy
            options.intra_op_num_threads = detect_resource_policy().cpu_threads
            options.inter_op_num_threads = 1
            options.enable_cpu_mem_arena = False
            options.enable_mem_pattern = False
            _SESSION = ort.InferenceSession(
                str(model), options, providers=["CPUExecutionProvider"]
            )
            _TOKENIZER = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
            config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
            _TOKENIZER.enable_truncation(max_length=config.get("rubric_max_length", 256))
            _TOKENIZER.enable_padding(pad_id=1, pad_token="<pad>")
            _MODEL_PATH = model
            _MODEL_STAMP = stamp
            _LOAD_ERROR = ""
        except Exception as exc:
            _LOAD_ERROR = str(exc)[:500]
            _SESSION = None
            _TOKENIZER = None
            _MODEL_PATH = None
            _MODEL_STAMP = None
            raise RuntimeError(f"Cannot load RubricGuard Transformer: {exc}") from exc
    config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    return _SESSION, _TOKENIZER, config.get("id2label", {})


def os_cpu_count() -> int | None:
    import os

    return os.cpu_count()


def _verdict(score: float, language: str) -> str:
    if language == "vi":
        return "Đạt tốt" if score >= 80 else "Đạt một phần" if score >= 50 else "Cần bổ sung"
    return "Strong" if score >= 80 else "Partial" if score >= 50 else "Needs improvement"


def evaluate_with_transformer(
    model_dir: Path,
    question: dict[str, Any],
    answer: str,
    *,
    min_confidence: float = 0.68,
) -> dict[str, Any]:
    session, tokenizer, id2label = _load(model_dir)
    if set(str(label).lower() for label in id2label.values()) != {"entailment", "neutral", "contradiction"}:
        raise ValueError("Expected an entailment/neutral/contradiction classifier")
    points = list(question.get("key_points") or [])
    if not points:
        raise ValueError("Question has no rubric points")

    premise = answer
    encodings = tokenizer.encode_batch([(premise, point) for point in points])
    input_names = {item.name for item in session.get_inputs()}
    inputs: dict[str, np.ndarray] = {}
    if "input_ids" in input_names:
        inputs["input_ids"] = np.asarray([item.ids for item in encodings], dtype=np.int64)
    if "attention_mask" in input_names:
        inputs["attention_mask"] = np.asarray(
            [item.attention_mask for item in encodings], dtype=np.int64
        )
    if "token_type_ids" in input_names:
        inputs["token_type_ids"] = np.asarray(
            [item.type_ids for item in encodings], dtype=np.int64
        )
    temperature, calibrated_threshold = _calibration(model_dir)
    min_confidence = max(min_confidence, calibrated_threshold)
    probabilities = _softmax(session.run(None, inputs)[0] / temperature)
    quality = _quality_metadata(model_dir)
    production_ready = quality["production_ready"]
    selective_ready = quality.get("selective_ready", False)
    language_validated = question.get("language", "vi") in quality.get("validated_languages", ["vi"])
    can_accept = (production_ready or selective_ready) and language_validated

    assessments: list[dict[str, Any]] = []
    statuses: list[str] = []
    confidences: list[float] = []
    for point, row, encoding in zip(points, probabilities, encodings, strict=True):
        distribution = {
            str(id2label.get(str(index), id2label.get(index, index))).lower(): float(value)
            for index, value in enumerate(row)
        }
        entailment = distribution.get("entailment", 0.0)
        neutral = distribution.get("neutral", 0.0)
        contradiction = distribution.get("contradiction", 0.0)
        confidence = max(entailment, neutral, contradiction)
        label = max(distribution, key=distribution.get)
        status = {"entailment": "met", "contradiction": "contradicted", "neutral": "missing"}.get(label, "missing")
        statuses.append(status)
        confidences.append(confidence)
        assessments.append(
            {
                "point": point,
                "status": status,
                "reason": (
                    "Transformer NLI: "
                    f"đúng {entailment:.0%}, chưa đủ {neutral:.0%}, mâu thuẫn {contradiction:.0%}."
                ),
                "evidence_quote": "",
                "confidence": round(confidence, 4),
                "needs_review": (not can_accept or confidence < min_confidence or bool(encoding.overflowing)
                                 or bool(re.search(r"\d|[<>]|\b(?:hơn|không|chưa|not|never|than)\b|[\"'\u201c\u2018]",
                                                   answer, re.IGNORECASE))),
                "probabilities": {
                    "entailment": round(entailment, 4),
                    "neutral": round(neutral, 4),
                    "contradiction": round(contradiction, 4),
                },
            }
        )

    score = round(
        100
        * sum(1.0 if item == "met" else 0.5 if item == "partial" else 0.0 for item in statuses)
        / len(statuses),
        1,
    )
    confidence = sum(confidences) / len(confidences)
    needs_review = any(item["needs_review"] for item in assessments)
    language = question.get("language", "vi")
    if language == "vi":
        feedback = "Transformer đã đối chiếu từng ý với rubric."
        if needs_review:
            feedback += " Có ý chưa đủ độ tin cậy và cần bộ chấm phụ hoặc giảng viên xác nhận."
    else:
        feedback = "The Transformer compared each answer claim with the rubric."
        if needs_review:
            feedback += " At least one claim needs secondary or teacher review."
    return {
        "score": score,
        "verdict": _verdict(score, language),
        "matched_points": [point for point, status in zip(points, statuses) if status == "met"],
        "partial_points": [point for point, status in zip(points, statuses) if status == "partial"],
        "contradicted_points": [point for point, status in zip(points, statuses) if status == "contradicted"],
        "missing_points": [point for point, status in zip(points, statuses) if status != "met"],
        "point_assessments": assessments,
        "feedback": feedback,
        "confidence": round(confidence, 3),
        "acceptance_threshold": min_confidence,
        "evaluator": "transformer:rubricguard-lite-v1",
        "review_required": needs_review,
        "score_provisional": needs_review,
        "rubric_version": "rubricguard-lite-v1",
    }
