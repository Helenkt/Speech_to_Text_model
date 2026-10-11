from __future__ import annotations

import ctypes
import importlib.util
import json
import math
import os
import subprocess
import tempfile
import threading
import wave
from dataclasses import asdict, dataclass, replace
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
_INFERENCE_LOCK = threading.Lock()
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
    label: str = "Tương thích"
    denoise_policy: str = "browser_only"
    overlap_policy: str = "retry"
    max_parallel_models: int = 1


@dataclass(frozen=True, slots=True)
class HardwareCapabilities:
    cpu_threads: int
    total_memory_gb: float
    available_memory_gb: float
    memory_load_percent: float
    cuda_available: bool
    cuda_device_count: int
    cuda_vram_gb: float | None


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


def _memory_stats_gb() -> tuple[float, float, float]:
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
            total = status.total_physical / (1024**3)
            available = status.available_physical / (1024**3)
            return round(total, 1), round(available, 1), round(float(status.memory_load), 1)

        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        total = (pages * page_size) / (1024**3)
        available_pages = os.sysconf("SC_AVPHYS_PAGES")
        available = (available_pages * page_size) / (1024**3)
        load = 100.0 * (1.0 - (available / max(total, 0.1)))
        return round(total, 1), round(available, 1), round(load, 1)
    except (AttributeError, OSError, ValueError):
        return 0.0, 0.0, 0.0


def _memory_gb() -> float:
    return _memory_stats_gb()[0]


def _cuda_available() -> bool:
    try:
        _configure_local_cuda_runtime()
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def _cuda_device_count() -> int:
    try:
        _configure_local_cuda_runtime()
        import ctranslate2

        return int(ctranslate2.get_cuda_device_count())
    except Exception:
        return 0


def _cuda_vram_gb() -> float | None:
    try:
        startup = None
        if os.name == "nt":
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
            startupinfo=startup,
        )
        values = [float(line.strip()) / 1024 for line in completed.stdout.splitlines() if line.strip()]
        return round(max(values), 1) if values else None
    except (FileNotFoundError, OSError, ValueError, subprocess.SubprocessError):
        return None


def detect_hardware() -> HardwareCapabilities:
    total, available, load = _memory_stats_gb()
    cuda = _cuda_available()
    count = _cuda_device_count() if cuda else 0
    return HardwareCapabilities(
        cpu_threads=os.cpu_count() or 1,
        total_memory_gb=total,
        available_memory_gb=available,
        memory_load_percent=load,
        cuda_available=cuda,
        cuda_device_count=count,
        cuda_vram_gb=_cuda_vram_gb() if cuda else None,
    )


def _profile_for_tier(tier: str, hardware: HardwareCapabilities) -> STTRuntimeProfile:
    if tier == "high_accuracy" and hardware.cuda_available:
        return STTRuntimeProfile(
            "medium", "cuda", "float16", "high_accuracy",
            "GPU và bộ nhớ đủ để Whisper medium giải mã chính xác khi cần.",
            "Độ chính xác cao", "deepfilter_on_demand",
            "detect_and_retry", 1,
        )
    if tier in {"performance", "high_accuracy"} and hardware.cuda_available:
        return STTRuntimeProfile(
            "medium", "cuda", "float16", "performance",
            "Có CUDA; dùng Whisper medium FP16 và chỉ bật xử lý nặng khi cần.",
            "Hiệu năng", "deepfilter_on_demand", "detect_and_retry", 1,
        )
    if tier in {"balanced", "performance", "high_accuracy"}:
        return STTRuntimeProfile(
            "medium", "cpu", "int8", "balanced",
            "CPU/RAM phù hợp với Whisper medium lượng tử hóa INT8.",
            "Cân bằng", "deepfilter_on_demand", "detect_and_retry", 1,
        )
    return STTRuntimeProfile(
        "small", "cpu", "int8", "low",
        "Tài nguyên hạn chế; dùng Whisper small INT8 và yêu cầu ghi lại khi âm thanh khó.",
        "Tiết kiệm", "browser_only", "retry", 1,
    )


def resolve_runtime_profile(
    settings: Settings, hardware: HardwareCapabilities | None = None
) -> STTRuntimeProfile:
    hardware = hardware or detect_hardware()
    requested_tier = settings.runtime_profile
    if requested_tier == "auto":
        if (
            hardware.cuda_available
            and hardware.cuda_vram_gb is not None
            and hardware.cuda_vram_gb >= 8.0
            and hardware.available_memory_gb >= 8.0
        ):
            requested_tier = "high_accuracy"
        elif hardware.cuda_available and (
            hardware.cuda_vram_gb is None or hardware.cuda_vram_gb >= 4.0
        ):
            requested_tier = "performance"
        elif (
            hardware.cpu_threads >= 8
            and hardware.total_memory_gb >= 12.0
            and hardware.available_memory_gb >= 4.0
        ):
            requested_tier = "balanced"
        else:
            requested_tier = "low"
    recommended = _profile_for_tier(requested_tier, hardware)

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
    if tier == recommended.tier:
        return recommended
    return STTRuntimeProfile(
        model,
        device,
        compute_type,
        tier,
        "Cấu hình model được đặt thủ công; hệ thống vẫn giám sát lỗi bộ nhớ để hạ cấp.",
        "Thủ công",
        recommended.denoise_policy,
        recommended.overlap_policy,
        1,
    )


def _marker_path(settings: Settings) -> Path:
    return settings.whisper_download_root / ".stt_ready.json"


def _requested_key(settings: Settings) -> list[str]:
    return [
        settings.runtime_profile,
        settings.whisper_model,
        settings.whisper_device,
        settings.whisper_compute_type,
    ]


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
    hardware = detect_hardware()
    selected = _ACTIVE_PROFILE or resolve_runtime_profile(settings, hardware)
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
                    label=str(data.get("label") or selected.label),
                    denoise_policy=str(
                        data.get("denoise_policy") or selected.denoise_policy
                    ),
                    overlap_policy=str(
                        data.get("overlap_policy") or selected.overlap_policy
                    ),
                    max_parallel_models=int(data.get("max_parallel_models") or 1),
                )
        except (OSError, json.JSONDecodeError):
            ready = False
    deepfilter_available = importlib.util.find_spec("df") is not None
    try:
        pyannote_available = importlib.util.find_spec("pyannote.audio") is not None
    except ModuleNotFoundError:
        pyannote_available = False
    return {
        "installed": installed,
        "ready": ready,
        "initialization_required": installed and not ready,
        **asdict(selected),
        "cpu_threads": hardware.cpu_threads,
        "memory_gb": hardware.total_memory_gb,
        "available_memory_gb": hardware.available_memory_gb,
        "memory_load_percent": hardware.memory_load_percent,
        "cuda_available": hardware.cuda_available,
        "cuda_device_count": hardware.cuda_device_count,
        "cuda_vram_gb": hardware.cuda_vram_gb,
        "noise_suppression": "browser",
        "adaptive_vad": True,
        "adaptive_decode": True,
        "features": {
            "denoise": {
                "policy": selected.denoise_policy,
                "engine": "deepfilternet" if deepfilter_available else "browser",
                "deepfilter_available": deepfilter_available,
                "load_on_demand": selected.denoise_policy == "deepfilter_on_demand",
            },
            "overlap_detection": {
                "policy": selected.overlap_policy,
                "engine": "pyannote" if pyannote_available else "quality_gate",
                "pyannote_available": pyannote_available,
            },
            "memory": {
                "max_parallel_models": selected.max_parallel_models,
                "release_between_stages": selected.max_parallel_models == 1,
            },
        },
        "acceptance_targets": {
            "clean_wer_max": 0.08,
            "noisy_wer_max": 0.15,
            "critical_error_max": 0,
        },
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


def adaptive_vad_profile(ambient_noise_dbfs: float | None) -> dict[str, Any]:
    """Choose conservative Silero VAD settings from the measured noise floor."""
    if ambient_noise_dbfs is None or ambient_noise_dbfs <= -45.0:
        name, threshold, silence, speech, padding = "quiet", 0.42, 650, 180, 250
    elif ambient_noise_dbfs <= -32.0:
        name, threshold, silence, speech, padding = "moderate", 0.50, 500, 220, 350
    elif ambient_noise_dbfs <= -20.0:
        name, threshold, silence, speech, padding = "noisy", 0.62, 350, 300, 500
    else:
        name, threshold, silence, speech, padding = "very_noisy", 0.72, 300, 350, 650
    return {
        "name": name,
        "ambient_noise_dbfs": ambient_noise_dbfs,
        "threshold": threshold,
        "neg_threshold": max(0.15, round(threshold - 0.15, 2)),
        "min_silence_duration_ms": silence,
        "min_speech_duration_ms": speech,
        "speech_pad_ms": padding,
    }


def _dbfs(value: float) -> float:
    if value <= 0:
        return -80.0
    return max(-80.0, min(0.0, 20.0 * math.log10(value)))


def _noise_level(dbfs: float | None) -> tuple[str, str]:
    if dbfs is None:
        return "unknown", "Chưa đo"
    if dbfs <= -45:
        return "quiet", "Yên tĩnh"
    if dbfs <= -32:
        return "moderate", "Trung bình"
    if dbfs <= -20:
        return "noisy", "Ồn"
    return "very_noisy", "Rất ồn"


def assess_microphone_quality(
    metrics: dict[str, Any], *, maximum_ambient_noise_dbfs: float = -28.0
) -> dict[str, Any]:
    """Score a short microphone sample without loading the speech model."""
    duration = float(metrics.get("duration_seconds") or 0.0)
    input_level = float(metrics.get("input_level_dbfs") or -80.0)
    peak = float(metrics.get("peak_dbfs") or -80.0)
    noise = float(metrics.get("ambient_noise_dbfs") or -80.0)
    clipping = float(metrics.get("clipping_ratio") or 0.0)
    silence = float(metrics.get("silence_ratio") or 0.0)
    snr = float(metrics.get("signal_to_noise_db") or 0.0)

    score = 100
    recommendations: list[str] = []
    if duration < 1.0:
        score -= 35
        recommendations.append("Hãy ghi thử ít nhất 2-3 giây.")
    if input_level < -42:
        score -= 25
        recommendations.append("Âm lượng quá nhỏ; hãy đưa microphone gần hơn.")
    elif input_level > -6:
        score -= 10
        recommendations.append("Âm lượng khá lớn; nên đưa microphone xa hơn một chút.")
    if peak > -1.0 or clipping > 0.01:
        score -= 35
        recommendations.append("Âm thanh bị vỡ; hãy giảm gain hoặc tăng khoảng cách tới microphone.")
    if noise > maximum_ambient_noise_dbfs:
        score -= 20 if noise <= -20 else 35
        recommendations.append("Tiếng nền cao; hãy giảm nguồn ồn hoặc đổi vị trí microphone.")
    if silence > 0.85:
        score -= 20
        recommendations.append("Mẫu thử có quá ít giọng nói.")
    if snr < 10:
        score -= 25
        recommendations.append("Giọng nói chưa tách rõ khỏi tiếng nền.")
    elif snr < 18:
        score -= 10
        recommendations.append("Tỷ lệ giọng nói trên tiếng nền ở mức trung bình.")

    score = max(0, min(100, score))
    status = "good" if score >= 80 else "acceptable" if score >= 60 else "poor"
    labels = {
        "good": "Mic hoạt động tốt",
        "acceptable": "Mic có thể sử dụng",
        "poor": "Mic chưa ổn định",
    }
    noise_code, noise_label = _noise_level(noise)
    return {
        "status": status,
        "status_label": labels[status],
        "ready": status != "poor",
        "microphone_score_percent": score,
        "noise": {
            "dbfs": round(noise, 1),
            "level": noise_code,
            "label": noise_label,
            "limit_dbfs": maximum_ambient_noise_dbfs,
        },
        "metrics": {
            **metrics,
            "duration_seconds": round(duration, 2),
            "input_level_dbfs": round(input_level, 1),
            "peak_dbfs": round(peak, 1),
            "clipping_ratio": round(clipping, 4),
            "silence_ratio": round(silence, 4),
            "signal_to_noise_db": round(snr, 1),
        },
        "recommendations": list(dict.fromkeys(recommendations)),
    }


def analyze_microphone_sample(
    content: bytes,
    *,
    filename: str,
    ambient_noise_dbfs: float | None = None,
    maximum_ambient_noise_dbfs: float = -28.0,
) -> dict[str, Any]:
    """Decode a browser recording and measure level, clipping, silence and SNR."""
    suffix = Path(filename).suffix or ".webm"
    temporary_path: str | None = None
    samples: list[int] = []
    sample_rate = 16_000
    try:
        import av

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary:
            temporary.write(content)
            temporary_path = temporary.name

        with av.open(temporary_path) as container:
            resampler = av.AudioResampler(format="s16", layout="mono", rate=sample_rate)
            for frame in container.decode(audio=0):
                for converted in resampler.resample(frame):
                    samples.extend(int(value) for value in converted.to_ndarray().reshape(-1))
                    if len(samples) >= sample_rate * 10:
                        break
                if len(samples) >= sample_rate * 10:
                    break
            for converted in resampler.resample(None):
                samples.extend(int(value) for value in converted.to_ndarray().reshape(-1))
    except Exception as exc:
        raise SpeechToTextError(f"Không thể phân tích mẫu microphone: {exc}") from exc
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)

    if not samples:
        raise SpeechToTextError("Mẫu microphone không có dữ liệu âm thanh.")

    normalized = [max(-1.0, min(1.0, value / 32768.0)) for value in samples]
    rms = math.sqrt(sum(value * value for value in normalized) / len(normalized))
    peak = max(abs(value) for value in normalized)
    clipping_ratio = sum(abs(value) >= 0.98 for value in normalized) / len(normalized)
    silence_ratio = sum(abs(value) < 0.01 for value in normalized) / len(normalized)
    ambient_count = min(len(normalized), max(1, sample_rate))
    ambient_samples = normalized[:ambient_count]
    ambient_rms = math.sqrt(
        sum(value * value for value in ambient_samples) / len(ambient_samples)
    )
    measured_noise = _dbfs(ambient_rms)
    # The browser reading is useful for diagnostics, but only the decoded audio
    # is authoritative for the microphone gate.
    noise = measured_noise
    signal_dbfs = _dbfs(rms)
    metrics = {
        "duration_seconds": len(normalized) / sample_rate,
        "sample_rate_hz": sample_rate,
        "input_level_dbfs": signal_dbfs,
        "peak_dbfs": _dbfs(peak),
        "ambient_noise_dbfs": noise,
        "measured_ambient_noise_dbfs": measured_noise,
        "client_ambient_noise_dbfs": ambient_noise_dbfs,
        "noise_measurement_source": "backend_audio",
        "clipping_ratio": clipping_ratio,
        "silence_ratio": silence_ratio,
        "signal_to_noise_db": max(0.0, signal_dbfs - noise),
    }
    result = assess_microphone_quality(
        metrics, maximum_ambient_noise_dbfs=maximum_ambient_noise_dbfs
    )
    result["recommended_vad"] = adaptive_vad_profile(noise)
    return result


def build_recording_report(
    metrics: dict[str, Any], *, maximum_ambient_noise_dbfs: float = -28.0
) -> dict[str, Any]:
    """Expose STT quality in stable, UI-ready percentages."""
    confidence = max(0.0, min(1.0, float(metrics.get("confidence") or 0.0)))
    quality = max(0.0, min(1.0, float(metrics.get("quality_score") or 0.0)))
    uncertain_ratio = max(
        0.0, min(1.0, float(metrics.get("uncertain_word_ratio") or 0.0))
    )
    noise_value = metrics.get("ambient_noise_dbfs")
    noise = float(noise_value) if noise_value is not None else None
    noise_code, noise_label = _noise_level(noise)
    estimated_accuracy = 0.70 * confidence + 0.20 * (1.0 - uncertain_ratio) + 0.10 * quality
    return {
        "recognition_confidence_percent": round(confidence * 100),
        "recording_quality_percent": round(quality * 100),
        "estimated_recognition_accuracy_percent": round(
            max(0.0, min(1.0, estimated_accuracy)) * 100
        ),
        "noise": {
            "dbfs": round(noise, 1) if noise is not None else None,
            "level": noise_code,
            "label": noise_label,
            "limit_dbfs": maximum_ambient_noise_dbfs,
        },
        "accuracy_note": (
            "Đây là độ chính xác ước tính từ độ tin cậy của model và chất lượng bản ghi; "
            "độ chính xác thực chỉ đo được khi có transcript chuẩn để đối chiếu."
        ),
    }


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


def _transcribe_bytes_locked(
    settings: Settings,
    content: bytes,
    *,
    filename: str,
    language: str | None = None,
    hotwords: list[str] | None = None,
    ambient_noise_dbfs: float | None = None,
    force_accurate: bool = False,
    write_ready_marker: bool = True,
) -> dict[str, Any]:
    suffix = Path(filename).suffix or ".webm"
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary:
            temporary.write(content)
            temporary_path = temporary.name

        selected_language = language if language in {"vi", "en"} else None
        vad_profile = adaptive_vad_profile(ambient_noise_dbfs)
        vad_parameters = {
            key: value
            for key, value in vad_profile.items()
            if key not in {"name", "ambient_noise_dbfs"}
        }
        def decode(beam_size: int, best_of: int) -> dict[str, Any]:
            segments, info = _decode_with_fallback(
                settings,
                lambda model: model.transcribe(
                    temporary_path,
                    language=selected_language,
                    beam_size=beam_size,
                    best_of=best_of,
                    temperature=0,
                    vad_filter=True,
                    vad_parameters=vad_parameters,
                    condition_on_previous_text=vad_profile["name"] in {"quiet", "moderate"},
                    word_timestamps=True,
                    hallucination_silence_threshold=2.0,
                    hotwords=" ".join(hotwords or []) or None,
                ),
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
            metrics = _quality_metrics(segments)
            metrics["vad_profile"] = vad_profile
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
                result,
                minimum_confidence=settings.stt_min_confidence,
                ambient_noise_dbfs=ambient_noise_dbfs,
                maximum_ambient_noise_dbfs=settings.stt_max_ambient_noise_dbfs,
            )

        selected_profile = resolve_runtime_profile(settings)
        if force_accurate:
            fast_beam = 5
        elif selected_profile.tier in {"low", "fallback_small"}:
            fast_beam = 2
        else:
            fast_beam = 3
        result = decode(fast_beam, fast_beam)
        metrics = result["metrics"]
        noisy = (
            ambient_noise_dbfs is not None
            and ambient_noise_dbfs > settings.stt_max_ambient_noise_dbfs
        )
        needs_accurate_pass = not force_accurate and (
            result.get("needs_retry")
            or float(metrics.get("confidence") or 0.0) < 0.70
            or float(metrics.get("uncertain_word_ratio") or 0.0) > 0.20
            or (
                noisy
                and float(metrics.get("quality_score") or 0.0) < 0.72
            )
        )
        if force_accurate:
            result["decode_passes"] = 1
            result["decode_strategy"] = "forced_accurate"
        elif needs_accurate_pass:
            result = decode(5, 5)
            result["decode_passes"] = 2
            result["decode_strategy"] = "quality_retry"
        else:
            result["decode_passes"] = 1
            result["decode_strategy"] = "adaptive_fast"
        result["metrics"]["initial_beam_size"] = fast_beam
        result["metrics"]["final_beam_size"] = 5 if needs_accurate_pass else fast_beam
        if write_ready_marker:
            _write_ready_marker(settings)
        return result
    except SpeechToTextError:
        raise
    except Exception as exc:
        raise SpeechToTextError(f"Không thể chuyển giọng nói thành văn bản: {exc}") from exc
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)


def _clear_loaded_model() -> None:
    global _MODEL, _MODEL_KEY, _REQUESTED_MODEL_KEY, _ACTIVE_PROFILE
    with _MODEL_LOCK:
        _MODEL = None
        _MODEL_KEY = None
        _REQUESTED_MODEL_KEY = None
        _ACTIVE_PROFILE = None


def transcribe_bytes(
    settings: Settings,
    content: bytes,
    *,
    filename: str,
    language: str | None = None,
    hotwords: list[str] | None = None,
    ambient_noise_dbfs: float | None = None,
    force_accurate: bool = False,
    release_after: bool = False,
    write_ready_marker: bool = True,
) -> dict[str, Any]:
    with _INFERENCE_LOCK:
        try:
            return _transcribe_bytes_locked(
                settings,
                content,
                filename=filename,
                language=language,
                hotwords=hotwords,
                ambient_noise_dbfs=ambient_noise_dbfs,
                force_accurate=force_accurate,
                write_ready_marker=write_ready_marker,
            )
        finally:
            if release_after:
                _clear_loaded_model()


def transcribe_review_audio(
    settings: Settings,
    content: bytes,
    *,
    filename: str,
    language: str,
    hotwords: list[str] | None = None,
    ambient_noise_dbfs: float | None = None,
) -> dict[str, Any]:
    review_settings = replace(
        settings,
        whisper_model=settings.review_whisper_model,
        whisper_device="auto",
        whisper_compute_type="auto",
    )
    hardware = detect_hardware()
    if settings.review_model_cache_policy == "keep":
        release_after = False
    elif settings.review_model_cache_policy == "release":
        release_after = True
    else:
        release_after = not (
            hardware.available_memory_gb >= 10.0
            or (
                hardware.cuda_available
                and (hardware.cuda_vram_gb or 0.0) >= 8.0
                and hardware.available_memory_gb >= 6.0
            )
        )
    result = transcribe_bytes(
        review_settings,
        content,
        filename=filename,
        language=language,
        hotwords=hotwords,
        ambient_noise_dbfs=ambient_noise_dbfs,
        force_accurate=True,
        release_after=release_after,
        write_ready_marker=False,
    )
    result["purpose"] = "teacher_review"
    result["model_cache_policy"] = (
        "released_after_request" if release_after else "kept_for_next_review"
    )
    return result
