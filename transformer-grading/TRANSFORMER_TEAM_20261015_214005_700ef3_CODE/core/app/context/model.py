from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any

from app.context.contracts import LABELS, SCHEMA_VERSION, decide, make_pair

_LOCK = threading.RLock()
_MODELS: dict[tuple[str, str], "ContextClassifier"] = {}


class ContextUnavailable(RuntimeError):
    pass


def model_identity(path: Path) -> str:
    manifest = path / "context_manifest.json"
    if not manifest.is_file():
        return "not-installed"
    return hashlib.sha256(manifest.read_bytes()).hexdigest()[:16]


class ContextClassifier:
    def __init__(self, path: Path, device: str = "cpu"):
        # Online downloads and training are never performed in a student's request.
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise ContextUnavailable("Chưa cài requirements-context.txt") from exc
        try:
            self.manifest = json.loads((path / "context_manifest.json").read_text(encoding="utf-8"))
            if self.manifest.get("schema_version") != SCHEMA_VERSION:
                raise ValueError("Sai phiên bản hợp đồng input")
            self.tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, trust_remote_code=False)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                str(path), local_files_only=True, trust_remote_code=False, use_safetensors=True,
            )
            mapping = {int(k): str(v) for k, v in self.model.config.id2label.items()}
            if set(mapping.values()) != set(LABELS) or len(mapping) != len(LABELS):
                raise ValueError("Checkpoint không có đủ 5 nhãn rubric")
            if getattr(self.model.config, "context_schema", None) != SCHEMA_VERSION:
                raise ValueError("Checkpoint chưa được huấn luyện bằng pipeline này")
            self.labels = mapping
            self.max_length = int(self.manifest["max_length"])
            if not 64 <= self.max_length <= 512:
                raise ValueError("max_length ngoài giới hạn 64..512")
            if device not in {"cpu", "cuda"}:
                raise ValueError("CONTEXT_DEVICE chỉ nhận cpu/cuda")
            if device == "cuda" and not torch.cuda.is_available():
                raise ValueError("CUDA không sẵn sàng; đổi CONTEXT_DEVICE=cpu")
            self.device = device
            self.model.to(device).eval()
            self.torch = torch
            self.identity = model_identity(path)
        except (OSError, ValueError, KeyError, RuntimeError) as exc:
            raise ContextUnavailable(f"Không nạp được contextual checkpoint: {exc}") from exc

    def predict(self, question: dict[str, Any], answer: str, threshold: float, margin: float) -> list[dict[str, Any]]:
        points = list(question.get("key_points") or [])
        if not points:
            raise ContextUnavailable("Câu hỏi chưa có rubric")
        pairs = [make_pair(question["question"], p, question["reference_answer"], answer) for p in points]
        # Never silently drop a late negation, a self-correction, or a rubric constraint.
        lengths = [len(self.tokenizer(a, b, truncation=False)["input_ids"]) for a, b in pairs]
        if max(lengths) > self.max_length:
            raise ContextUnavailable("Câu trả lời/rubric vượt giới hạn token; cần giáo viên đọc toàn văn")
        result = []
        with _LOCK, self.torch.inference_mode():
            for offset in range(0, len(pairs), 4):
                batch = pairs[offset:offset + 4]
                encoded = self.tokenizer([x[0] for x in batch], [x[1] for x in batch],
                                         padding=True, truncation=False, return_tensors="pt")
                encoded = {k: v.to(self.device) for k, v in encoded.items()}
                values = self.model(**encoded).logits.softmax(-1).cpu().tolist()
                for index, row in enumerate(values):
                    prediction = decide({self.labels[i]: float(v) for i, v in enumerate(row)}, threshold, margin)
                    prediction.update({"point": points[offset + index], "model_version": self.identity,
                                       "demo_only": bool(self.manifest.get("demo_only", True))})
                    result.append(prediction)
        return result


def predict_context(settings: Any, question: dict[str, Any], answer: str) -> list[dict[str, Any]]:
    path = settings.context_model_path.resolve()
    key = (str(path), settings.context_device)
    with _LOCK:
        if key not in _MODELS:
            _MODELS.clear()  # Bound memory; restart server after replacing a checkpoint.
            _MODELS[key] = ContextClassifier(path, settings.context_device)
        classifier = _MODELS[key]
        return classifier.predict(question, answer, settings.context_threshold, settings.context_margin)


def context_status(settings: Any) -> dict[str, Any]:
    return {"mode": settings.context_mode, "installed": (settings.context_model_path / "context_manifest.json").is_file(),
            "model_version": model_identity(settings.context_model_path), "device": settings.context_device,
            "confidence_threshold": settings.context_threshold,
            "note": "Softmax confidence chưa phải xác suất chấm đúng; cần hiệu chỉnh trên validation."}
