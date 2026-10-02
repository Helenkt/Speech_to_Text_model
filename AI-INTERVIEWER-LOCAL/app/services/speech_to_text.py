from __future__ import annotations

import ctypes
import importlib.util
import json
import math
import os
import tempfile
import threading
import wave
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings


_MODEL: Any = None
_MODEL_KEY: tuple[str, str, str] | None = None
_REQUESTED_MODEL_KEY: tuple[str, str, str] | None = None
_ACTIVE_PROFILE: "STTRuntimeProfile | None" = None
_FAILED_PROFILE_KEYS: set[tuple[str, str, str]] = set()
_MODEL_LOCK = threading.Lock()
_DLL_DIRECTORY_HANDLES: list[Any] = []


class SpeechToTextError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class STTRuntimeProfile:
    model: str
    device: str
    compute_type: str
    tier: str
    reason: str


def is_installed() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


def _configure_local_cuda_runtime() -> None:
    if os.name != "nt":
        return
    project_root = Path(__file__).resolve().parent.parent.parent
    cuda_runtime = project_root / "tools" / "ollama" / "lib" / "ollama" / "cuda_v12"
    if not (cuda_runtime / "cublas64_12.dll").exists():
        return
    runtime_text = str(cuda_runtime)
    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    if runtime_text.casefold() not in {item.casefold() for item in path_parts}:
        os.environ["PATH"] = runtime_text + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory") and not _DLL_DIRECTORY_HANDLES:
        _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(runtime_text))


def _memory_gb() -> float:
    try:
        if os.name == "nt":
            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_ulong),
                    ("memory_load", ctypes.c_ulong),
                    ("total_physical", ctypes.c_ulonglong),
                    ("available_physical", ctypes.c_ulonglong),
                    ("total_page_file", ctypes.c_ulonglong),
                    ("available_page_file", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong),
                    ("available_virtual", ctypes.c_ulonglong),
                    ("available_extended_virtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.length = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return round(status.total_physical / (1024**3), 1)

        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round((pages * page_size) / (1024**3), 1)
    except (AttributeError, OSError, ValueError):
        return 0.0


def _cuda_available() -> bool:
    try:
        _configure_local_cuda_runtime()
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def resolve_runtime_profile(settings: Settings) -> STTRuntimeProfile:
    cpu_threads = os.cpu_count() or 1
    memory_gb = _memory_gb()
    has_cuda = _cuda_available()

    if has_cuda:
        recommended = STTRuntimeProfile(
            "medium", "cuda", "float16", "validated_gpu",
            "Có GPU CUDA; dùng Whisper medium đã cho WER tốt nhất trên bộ kiểm thử cục bộ.",
        )
    elif cpu_threads >= 8 and memory_gb >= 12:
        recommended = STTRuntimeProfile(
            "medium", "cpu", "int8", "balanced_cpu",
            "CPU/RAM đủ dùng model medium lượng tử hóa INT8.",
        )
    else:
        recommended = STTRuntimeProfile(
            "small", "cpu", "int8", "compatible_cpu",
            "Máy không có CUDA hoặc tài nguyên hạn chế; dùng small INT8.",
        )

    model = recommended.model if settings.whisper_model == "auto" else settings.whisper_model
    device = recommended.device if settings.whisper_device == "auto" else settings.whisper_device
    default_compute = "float16" if device == "cuda" else "int8"
    compute_type = (
        default_compute
        if settings.whisper_compute_type == "auto"
        else settings.whisper_compute_type
    )
    tier = recommended.tier if all(
        value == "auto"
        for value in (
            settings.whisper_model,
            settings.whisper_device,
            settings.whisper_compute_type,
        )
    ) else "manual"
    return STTRuntimeProfile(model, device, compute_type, tier, recommended.reason)


def _marker_path(settings: Settings) -> Path:
    return settings.whisper_download_root / ".stt_ready.json"


def _requested_key(settings: Settings) -> list[str]:
    return [settings.whisper_model, settings.whisper_device, settings.whisper_compute_type]


def _write_ready_marker(
    settings: Settings, profile: STTRuntimeProfile | None = None
) -> None:
    selected = profile or _ACTIVE_PROFILE or resolve_runtime_profile(settings)
    marker = _marker_path(settings)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps(
            {
                "requested": _requested_key(settings),
                **asdict(selected),
                "verified_at": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def stt_status(settings: Settings) -> dict[str, Any]:
    installed = is_installed()
    selected = _ACTIVE_PROFILE or resolve_runtime_profile(settings)
    marker = _marker_path(settings)
    ready = False
    if installed and marker.exists():
        try:
            data = json.loads(marker.read_text(encoding="utf-8"))
            requested = data.get("requested")
            ready = (
                requested == _requested_key(settings)
                if requested is not None
                else (
                    data.get("model") == settings.whisper_model
                    and data.get("device") == settings.whisper_device
                    and data.get("compute_type") == settings.whisper_compute_type
                )
            )
            if ready and all(
                data.get(key) for key in ("model", "device", "compute_type", "tier")
            ):
                selected = STTRuntimeProfile(
                    model=str(data["model"]),
                    device=str(data["device"]),
                    compute_type=str(data["compute_type"]),
                    tier=str(data["tier"]),
                    reason=str(data.get("reason") or selected.reason),
                )
        except (OSError, json.JSONDecodeError):
            ready = False
    return {
        "installed": installed,
        "ready": ready,
        "initialization_required": installed and not ready,
        **asdict(selected),
        "cpu_threads": os.cpu_count() or 1,
        "memory_gb": _memory_gb(),
        "noise_suppression": "browser",
    }


def _fallback_profiles(primary: STTRuntimeProfile) -> list[STTRuntimeProfile]:
    profiles = [primary]
    if primary.device == "cuda":
        profiles.append(
            STTRuntimeProfile(
                "medium", "cpu", "int8", "fallback_cpu",
                "GPU không khởi tạo được; chuyển sang medium INT8 trên CPU.",
            )
        )
    if primary.model != "small" or primary.device != "cpu":
        profiles.append(
            STTRuntimeProfile(
                "small", "cpu", "int8", "compatible_cpu",
                "Cấu hình dự phòng tương thích với máy yếu.",
            )
        )
    unique: dict[tuple[str, str, str], STTRuntimeProfile] = {}
    for profile in profiles:
        unique[(profile.model, profile.device, profile.compute_type)] = profile
    return list(unique.values())


def _get_model(settings: Settings) -> Any:
    global _MODEL, _MODEL_KEY, _REQUESTED_MODEL_KEY, _ACTIVE_PROFILE
    if not is_installed():
        raise SpeechToTextError(
            "Chưa cài speech-to-text. Hãy cài requirements.txt rồi chạy "
            "'python -m app.stt_setup'."
        )

    _configure_local_cuda_runtime()
    primary = resolve_runtime_profile(settings)
    with _MODEL_LOCK:
        if _MODEL is not None and _REQUESTED_MODEL_KEY == (
            primary.model, primary.device, primary.compute_type
        ):
            return _MODEL

        errors: list[str] = []
        # Xet downloads can stall on some Windows installations; regular HTTP resumes
        # partial model files reliably and is only needed during the first setup.
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        from faster_whisper import WhisperModel

        settings.whisper_download_root.mkdir(parents=True, exist_ok=True)
        for profile in _fallback_profiles(primary):
            key = (profile.model, profile.device, profile.compute_type)
            if key in _FAILED_PROFILE_KEYS:
                continue
            try:
                _MODEL = WhisperModel(
                    profile.model,
                    device=profile.device,
                    compute_type=profile.compute_type,
                    download_root=str(settings.whisper_download_root),
                )
                _MODEL_KEY = key
                _REQUESTED_MODEL_KEY = (
                    primary.model, primary.device, primary.compute_type
                )
                _ACTIVE_PROFILE = profile
                return _MODEL
            except Exception as exc:
                errors.append(f"{'/'.join(key)}: {exc}")

        raise SpeechToTextError(
            "Không thể khởi tạo model Voice/STT. Lần đầu cần Internet để tải model. "
            "Các cấu hình đã thử: " + " | ".join(errors)
        )


def _invalidate_active_model(exc: Exception) -> bool:
    global _MODEL, _MODEL_KEY, _REQUESTED_MODEL_KEY, _ACTIVE_PROFILE
    if not _MODEL_KEY:
        return False
    message = str(exc).lower()
    runtime_failure = (
        _MODEL_KEY[1] == "cuda"
        or "out of memory" in message
        or "failed to allocate" in message
    )
    if not runtime_failure:
        return False
    _FAILED_PROFILE_KEYS.add(_MODEL_KEY)
    _MODEL = None
    _MODEL_KEY = None
    _REQUESTED_MODEL_KEY = None
    _ACTIVE_PROFILE = None
    return True


def _decode_with_fallback(settings: Settings, decode: Any) -> tuple[list[Any], Any]:
    last_error: Exception | None = None
    for _ in range(3):
        model = _get_model(settings)
        try:
            segments, info = decode(model)
            return list(segments), info
        except Exception as exc:
            last_error = exc
            if not _invalidate_active_model(exc):
                raise
    raise SpeechToTextError(
        f"Các cấu hình STT đều lỗi khi xử lý âm thanh: {last_error}"
    )


def verify_stt_setup(settings: Settings) -> dict[str, Any]:
    """Download/load the model and decode a short WAV before marking STT ready."""
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temporary:
            temporary_path = temporary.name
        with wave.open(temporary_path, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16_000)
            audio.writeframes(b"\x00\x00" * 8_000)

        _decode_with_fallback(
            settings,
            lambda model: model.transcribe(
                temporary_path, language="vi", beam_size=1, vad_filter=False
            ),
        )
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)

    _write_ready_marker(settings)
    return stt_status(settings)


def _quality_metrics(segments: list[Any]) -> dict[str, Any]:
    if not segments:
        return {
            "confidence": 0.0,
            "speech_duration_seconds": 0.0,
            "average_log_probability": -10.0,
            "average_no_speech_probability": 1.0,
            "maximum_no_speech_probability": 1.0,
            "maximum_compression_ratio": 0.0,
        }

    durations = [
        max(0.1, float(getattr(item, "end", 1.0)) - float(getattr(item, "start", 0.0)))
        for item in segments
    ]
    total_duration = sum(durations)
    average_log_probability = sum(
        float(getattr(item, "avg_logprob", -0.2)) * duration
        for item, duration in zip(segments, durations)
    ) / total_duration
    no_speech_probabilities = [
        float(getattr(item, "no_speech_prob", 0.0)) for item in segments
    ]
    average_no_speech = sum(
        probability * duration
        for probability, duration in zip(no_speech_probabilities, durations)
    ) / total_duration
    maximum_no_speech = max(no_speech_probabilities)
    maximum_compression = max(
        float(getattr(item, "compression_ratio", 1.0)) for item in segments
    )
    confidence = math.exp(max(-5.0, min(0.0, average_log_probability)))
    confidence *= max(0.0, 1.0 - average_no_speech * 0.7)
    return {
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "speech_duration_seconds": round(total_duration, 2),
        "average_log_probability": round(average_log_probability, 3),
        "average_no_speech_probability": round(average_no_speech, 3),
        "maximum_no_speech_probability": round(maximum_no_speech, 3),
        "maximum_compression_ratio": round(maximum_compression, 3),
    }


WORD_CONFIDENCE_THRESHOLD = 0.45


def _segment_diagnostics(
    segments: list[Any], *, word_threshold: float = WORD_CONFIDENCE_THRESHOLD
) -> tuple[list[dict[str, Any]], list[str]]:
    details: list[dict[str, Any]] = []
    uncertain_spans: list[str] = []
    for index, segment in enumerate(segments):
        text = str(getattr(segment, "text", "")).strip()
        word_items = list(getattr(segment, "words", None) or [])
        words_detail: list[dict[str, Any]] = []
        pending: list[str] = []
        word_probabilities: list[float] = []
        for word in word_items:
            token = str(getattr(word, "word", "")).strip()
            probability = max(
                0.0, min(1.0, float(getattr(word, "probability", 0.0)))
            )
            if not token:
                continue
            word_probabilities.append(probability)
            words_detail.append(
                {
                    "text": token,
                    "start": round(float(getattr(word, "start", 0.0)), 2),
                    "end": round(float(getattr(word, "end", 0.0)), 2),
                    "confidence": round(probability, 3),
                    "uncertain": probability < word_threshold,
                }
            )
            if probability < word_threshold:
                pending.append(token)
            elif pending:
                uncertain_spans.append(" ".join(pending))
                pending = []
        if pending:
            uncertain_spans.append(" ".join(pending))

        segment_confidence = (
            sum(word_probabilities) / len(word_probabilities)
            if word_probabilities
            else math.exp(
                max(-5.0, min(0.0, float(getattr(segment, "avg_logprob", -0.2))))
            )
        )
        if text and not word_items and segment_confidence < word_threshold:
            uncertain_spans.append(text)
        details.append(
            {
                "index": index,
                "text": text,
                "start": round(float(getattr(segment, "start", 0.0)), 2),
                "end": round(float(getattr(segment, "end", 0.0)), 2),
                "confidence": round(segment_confidence, 3),
                "words": words_detail,
            }
        )
    return details, list(dict.fromkeys(span for span in uncertain_spans if span))


def assess_transcription_quality(
    result: dict[str, Any],
    *,
    minimum_confidence: float,
    ambient_noise_dbfs: float | None = None,
    maximum_ambient_noise_dbfs: float = -28.0,
) -> dict[str, Any]:
    """Apply a deterministic quality gate before a transcript can be graded."""
    text = str(result.get("text") or "").strip()
    metrics = dict(result.get("metrics") or {})
    word_count = int(metrics.get("word_count") or 0)
    uncertain_ratio = float(metrics.get("uncertain_word_ratio") or 0.0)
    confidence = float(metrics.get("confidence") or 0.0)
    no_speech = float(metrics.get("average_no_speech_probability") or 0.0)
    compression = float(metrics.get("maximum_compression_ratio") or 0.0)
    duration = float(metrics.get("speech_duration_seconds") or 0.0)

    reasons: list[str] = []
    warnings: list[str] = []
    if not text:
        reasons.append("Không phát hiện được giọng nói rõ ràng.")
    if text and "speech_duration_seconds" in metrics and duration < 0.5:
        reasons.append("Đoạn nói quá ngắn để chấm chính xác.")
    if text and "confidence" in metrics and confidence < minimum_confidence and (
        "word_count" not in metrics or word_count == 0 or uncertain_ratio > 0.25
    ):
        warnings.append("Độ tin cậy nhận dạng thấp; hệ thống đã chuyển các vùng chưa chắc chắn sang bước hiệu chỉnh.")
    if "average_no_speech_probability" in metrics and no_speech > 0.85:
        reasons.append("Âm thanh chủ yếu là im lặng hoặc tiếng nền.")
    elif "average_no_speech_probability" in metrics and no_speech > 0.65:
        warnings.append("Bản ghi có nhiều khoảng im lặng hoặc tiếng nền.")
    if "maximum_compression_ratio" in metrics and compression > 2.6:
        reasons.append("Kết quả có dấu hiệu lặp từ bất thường.")
    if word_count >= 4 and uncertain_ratio > 0.45:
        warnings.append("Nhiều từ có độ tin cậy nhận dạng thấp; đã chuyển sang bước hiệu chỉnh.")
    noisy_environment = (
        ambient_noise_dbfs is not None
        and ambient_noise_dbfs > maximum_ambient_noise_dbfs
    )
    unreliable_under_noise = (
        confidence < max(minimum_confidence + 0.12, 0.65)
        or uncertain_ratio > 0.30
        or no_speech > 0.50
    )
    if noisy_environment and unreliable_under_noise:
        warnings.append(
            "Tiếng nền ảnh hưởng đến độ tin cậy; hệ thống đã giữ bản gốc để đối chiếu."
        )

    word_quality = 1.0 - uncertain_ratio if word_count else confidence
    silence_quality = 1.0 - no_speech
    noise_quality = 1.0
    if ambient_noise_dbfs is not None:
        noise_quality = max(0.0, min(1.0, (maximum_ambient_noise_dbfs - ambient_noise_dbfs + 18.0) / 18.0))
    quality_score = (
        0.40 * confidence
        + 0.30 * word_quality
        + 0.15 * silence_quality
        + 0.15 * noise_quality
    )
    metrics["ambient_noise_dbfs"] = ambient_noise_dbfs
    metrics["noisy_environment"] = noisy_environment
    metrics["quality_warning_count"] = len(warnings)
    metrics["quality_score"] = round(max(0.0, min(1.0, quality_score)), 3)
    metrics["quality_gate_version"] = "stt-quality-v3"
    return {
        **result,
        "metrics": metrics,
        "needs_retry": bool(reasons),
        "quality_reasons": list(dict.fromkeys(reasons)),
        "quality_warnings": list(dict.fromkeys(warnings)),
    }


def transcribe_bytes(
    settings: Settings,
    content: bytes,
    *,
    filename: str,
    language: str | None = None,
    hotwords: list[str] | None = None,
) -> dict[str, Any]:
    suffix = Path(filename).suffix or ".webm"
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary:
            temporary.write(content)
            temporary_path = temporary.name

        selected_language = language if language in {"vi", "en"} else None
        segments, info = _decode_with_fallback(
            settings,
            lambda model: model.transcribe(
                temporary_path,
                language=selected_language,
                beam_size=5,
                best_of=5,
                temperature=0,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
                condition_on_previous_text=True,
                word_timestamps=True,
                hallucination_silence_threshold=2.0,
                hotwords=" ".join(hotwords or []) or None,
            ),
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        metrics = _quality_metrics(segments)
        segment_details, uncertain_spans = _segment_diagnostics(segments)
        word_details = [
            word for segment in segment_details for word in segment["words"]
        ]
        uncertain_word_count = sum(word["uncertain"] for word in word_details)
        metrics["word_count"] = len(word_details)
        metrics["uncertain_word_count"] = uncertain_word_count
        metrics["word_confidence_threshold"] = WORD_CONFIDENCE_THRESHOLD
        metrics["uncertain_word_ratio"] = round(
            uncertain_word_count / max(1, len(word_details)), 3
        )
        _write_ready_marker(settings)
        active = _ACTIVE_PROFILE or resolve_runtime_profile(settings)
        result = {
            "text": text,
            "language": getattr(info, "language", selected_language),
            "language_probability": round(
                float(getattr(info, "language_probability", 0.0)), 3
            ),
            "model": active.model,
            "runtime": f"{active.device}/{active.compute_type}",
            "profile": active.tier,
            "metrics": metrics,
            "segments": segment_details,
            "uncertain_spans": uncertain_spans,
        }
        return assess_transcription_quality(
            result, minimum_confidence=settings.stt_min_confidence
        )
    except SpeechToTextError:
        raise
    except Exception as exc:
        raise SpeechToTextError(f"Không thể chuyển giọng nói thành văn bản: {exc}") from exc
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
