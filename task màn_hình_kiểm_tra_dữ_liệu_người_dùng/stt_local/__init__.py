"""Local speech-to-text module based on Faster Whisper."""

from .engine import LocalWhisperEngine, TranscriptionResult
from .runtime import RuntimeProfile, recommend_runtime, select_runtime

__all__ = [
    "LocalWhisperEngine",
    "RuntimeProfile",
    "TranscriptionResult",
    "recommend_runtime",
    "select_runtime",
]
