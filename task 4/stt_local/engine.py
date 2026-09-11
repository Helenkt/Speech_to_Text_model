from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from .runtime import recommend_runtime


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    model: str
    language: str
    language_probability: float
    duration_seconds: float
    processing_seconds: float
    real_time_factor: float
    device: str
    compute_type: str
    segments: tuple[TranscriptSegment, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LocalWhisperEngine:
    """Loads one local model instance and reuses it across transcriptions."""

    def __init__(
        self,
        model: str | Path,
        *,
        device: str = "auto",
        compute_type: str = "auto",
        cpu_threads: int = 0,
        download_root: str | Path | None = None,
    ) -> None:
        from faster_whisper import WhisperModel

        self._whisper_model_class = WhisperModel
        self._model_source = str(model)
        self._download_root = str(download_root) if download_root is not None else None
        profile = recommend_runtime()
        self._cpu_threads = cpu_threads or profile.cpu_threads
        self._auto_device = device == "auto"
        selected_device, selected_compute_type = self._select_runtime(
            device, compute_type
        )

        try:
            self._model = self._create_model(selected_device, selected_compute_type)
        except Exception:
            if not self._auto_device or selected_device != "cuda":
                raise
            selected_device = "cpu"
            selected_compute_type = "int8"
            self._model = self._create_model(selected_device, selected_compute_type)

        self.device = selected_device
        self.compute_type = selected_compute_type

    def _create_model(self, device: str, compute_type: str):
        model_kwargs: dict[str, Any] = {
            "device": device,
            "compute_type": compute_type,
            "cpu_threads": self._cpu_threads,
        }
        if self._download_root is not None:
            model_kwargs["download_root"] = self._download_root
        return self._whisper_model_class(self._model_source, **model_kwargs)

    @staticmethod
    def _select_runtime(device: str, compute_type: str) -> tuple[str, str]:
        if device not in {"auto", "cpu", "cuda"}:
            raise ValueError("device must be auto, cpu, or cuda")

        selected_device = device
        if device == "auto":
            selected_device = recommend_runtime().device

        if compute_type == "auto":
            compute_type = "float16" if selected_device == "cuda" else "int8"

        return selected_device, compute_type

    def transcribe(
        self,
        audio_path: str | Path,
        *,
        language: str | None = "vi",
        beam_size: int = 1,
        vad_filter: bool = True,
        word_timestamps: bool = False,
        hotwords: str | None = None,
    ) -> TranscriptionResult:
        audio_path = Path(audio_path)
        if not audio_path.is_file():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        def run_inference():
            segment_iterator, transcription_info = self._model.transcribe(
                str(audio_path),
                language=language,
                beam_size=beam_size,
                best_of=1,
                vad_filter=vad_filter,
                word_timestamps=word_timestamps,
                condition_on_previous_text=False,
                hotwords=hotwords or None,
            )
            transcript_segments = tuple(
                TranscriptSegment(
                    start=round(segment.start, 3),
                    end=round(segment.end, 3),
                    text=segment.text.strip(),
                )
                for segment in segment_iterator
            )
            return transcript_segments, transcription_info

        started_at = perf_counter()
        try:
            segments, info = run_inference()
        except RuntimeError:
            if not self._auto_device or self.device != "cuda":
                raise
            self.device = "cpu"
            self.compute_type = "int8"
            self._model = self._create_model(self.device, self.compute_type)
            segments, info = run_inference()
        processing_seconds = perf_counter() - started_at
        duration_seconds = float(getattr(info, "duration", 0.0) or 0.0)
        real_time_factor = (
            processing_seconds / duration_seconds if duration_seconds > 0 else 0.0
        )

        return TranscriptionResult(
            text=" ".join(segment.text for segment in segments).strip(),
            model=Path(self._model_source).name,
            language=str(getattr(info, "language", language or "unknown")),
            language_probability=float(
                getattr(info, "language_probability", 0.0) or 0.0
            ),
            duration_seconds=round(duration_seconds, 3),
            processing_seconds=round(processing_seconds, 3),
            real_time_factor=round(real_time_factor, 4),
            device=self.device,
            compute_type=self.compute_type,
            segments=segments,
        )
