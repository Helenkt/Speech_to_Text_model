from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path(root_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root_dir / path


@dataclass(slots=True)
class Settings:
    root_dir: Path
    database_path: Path
    static_dir: Path
    demo_data_dir: Path
    whisper_download_root: Path
    auto_seed_demo: bool = True
    evaluator_mode: str = "auto"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: float = 120.0
    ollama_evaluator_timeout_seconds: float = 20.0
    ollama_keep_alive: str = "30m"
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    transcript_correction_mode: str = "auto"
    stt_min_confidence: float = 0.48
    stt_max_ambient_noise_dbfs: float = -28.0
    max_upload_mb: int = 25

    @classmethod
    def from_env(cls, root_dir: Path | None = None) -> "Settings":
        root = (root_dir or Path(__file__).resolve().parent.parent).resolve()
        load_dotenv(root / ".env", override=False)

        evaluator_mode = os.getenv("EVALUATOR_MODE", "auto").strip().lower()
        if evaluator_mode not in {"auto", "ollama", "rule"}:
            evaluator_mode = "auto"

        correction_mode = os.getenv("TRANSCRIPT_CORRECTION_MODE", "auto").strip().lower()
        if correction_mode not in {"auto", "ollama", "off"}:
            correction_mode = "auto"

        return cls(
            root_dir=root,
            database_path=_resolve_path(
                root, os.getenv("AI_DATABASE_PATH", "data/ai_interviewer.db")
            ),
            static_dir=root / "app" / "static",
            demo_data_dir=root / "data",
            whisper_download_root=_resolve_path(
                root, os.getenv("WHISPER_DOWNLOAD_ROOT", "models/whisper")
            ),
            auto_seed_demo=_as_bool(os.getenv("AUTO_SEED_DEMO"), True),
            evaluator_mode=evaluator_mode,
            ollama_base_url=os.getenv(
                "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
            ).rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
            ollama_timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")),
            ollama_evaluator_timeout_seconds=float(
                os.getenv("OLLAMA_EVALUATOR_TIMEOUT_SECONDS", "20")
            ),
            ollama_keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "30m").strip() or "30m",
            whisper_model=os.getenv("WHISPER_MODEL", "auto").strip().lower(),
            whisper_device=os.getenv("WHISPER_DEVICE", "auto").strip().lower(),
            whisper_compute_type=os.getenv(
                "WHISPER_COMPUTE_TYPE", "auto"
            ).strip().lower(),
            transcript_correction_mode=correction_mode,
            stt_min_confidence=min(
                0.95, max(0.1, float(os.getenv("STT_MIN_CONFIDENCE", "0.48")))
            ),
            stt_max_ambient_noise_dbfs=min(
                -5.0,
                max(-80.0, float(os.getenv("STT_MAX_AMBIENT_NOISE_DBFS", "-28"))),
            ),
            max_upload_mb=max(1, int(os.getenv("MAX_UPLOAD_MB", "25"))),
        )
