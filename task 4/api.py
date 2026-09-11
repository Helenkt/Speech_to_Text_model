from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path
import tempfile
from threading import RLock

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from stt_local import LocalWhisperEngine, recommend_runtime


PROJECT_ROOT = Path(__file__).parent
MODEL_ROOT = PROJECT_ROOT / "models"
WEB_ROOT = PROJECT_ROOT / "web"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
SUPPORTED_MODELS = {"auto", "tiny", "base", "small", "medium"}


def resolve_model(requested: str) -> str:
    profile = recommend_runtime()
    selected = profile.model if requested == "auto" else requested
    local_model = MODEL_ROOT / selected
    if local_model.is_dir():
        return str(local_model)

    if requested == "auto":
        for fallback in ("small", "base", "tiny"):
            candidate = MODEL_ROOT / fallback
            if candidate.is_dir():
                return str(candidate)
    return selected


class ModelService:
    def __init__(self) -> None:
        self.engines: dict[str, LocalWhisperEngine] = {}
        self.active_engine: LocalWhisperEngine | None = None
        self.active_model_path = ""
        self.default_model_path = ""
        self.lock = RLock()

    def _get_engine(self, requested_model: str) -> LocalWhisperEngine:
        model_path = resolve_model(requested_model)
        local_path = Path(model_path)
        key = str(local_path.resolve()) if local_path.exists() else model_path
        engine = self.engines.get(key)
        if engine is None:
            engine = LocalWhisperEngine(
                model_path,
                device=os.getenv("STT_DEVICE", "auto"),
                compute_type=os.getenv("STT_COMPUTE_TYPE", "auto"),
                download_root=MODEL_ROOT,
            )
            self.engines[key] = engine

        self.active_engine = engine
        self.active_model_path = model_path
        return engine

    def load(self) -> None:
        requested_model = os.getenv("STT_MODEL", "auto")
        with self.lock:
            self._get_engine(requested_model)
            self.default_model_path = self.active_model_path

    def transcribe(
        self,
        path: Path,
        language: str | None,
        beam_size: int,
        model: str,
        hotwords: str | None,
    ):
        with self.lock:
            engine = self._get_engine(model)
            return engine.transcribe(
                path,
                language=language,
                beam_size=beam_size,
                vad_filter=True,
                hotwords=hotwords,
            )


service = ModelService()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.to_thread(service.load)
    yield


app = FastAPI(
    title="Local Transcription Studio API",
    description="Local-first speech recognition service for AI Interviewer.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)
app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")


@app.get("/", include_in_schema=False)
def web_console() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/docs", include_in_schema=False)
def legacy_docs_redirect() -> RedirectResponse:
    return RedirectResponse("/", status_code=307)


@app.get("/health", tags=["System"])
def health() -> dict:
    profile = recommend_runtime()
    engine = service.active_engine
    installed_models = sorted(
        path.name for path in MODEL_ROOT.iterdir()
        if path.is_dir() and (path / "model.bin").is_file()
    ) if MODEL_ROOT.is_dir() else []
    return {
        "status": "ready" if engine is not None else "loading",
        "model": Path(service.default_model_path).name if service.default_model_path else None,
        "active_model": Path(service.active_model_path).name if service.active_model_path else None,
        "device": engine.device if engine else profile.device,
        "compute_type": engine.compute_type if engine else profile.compute_type,
        "cpu_threads": profile.cpu_threads,
        "cuda_ready": profile.cuda_ready,
        "installed_models": installed_models,
    }


@app.post("/v1/audio/transcriptions", tags=["Transcription"])
async def create_transcription(
    file: UploadFile = File(...),
    language: str = Form("vi"),
    beam_size: int = Form(1, ge=1, le=5),
    model: str = Form("auto"),
    hotwords: str = Form(""),
) -> dict:
    if model not in SUPPORTED_MODELS:
        raise HTTPException(400, f"Unsupported model: {model}")
    if len(hotwords) > 1000:
        raise HTTPException(400, "Hotwords cannot exceed 1000 characters")

    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = Path(temp_file.name)
            total_bytes = 0
            while chunk := await file.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Audio file exceeds the 100 MB limit")
                temp_file.write(chunk)

        selected_language = None if language == "auto" else language
        result = await asyncio.to_thread(
            service.transcribe,
            temp_path,
            selected_language,
            beam_size,
            model,
            hotwords.strip() or None,
        )
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, f"Transcription failed: {exc}") from exc
    finally:
        await file.close()
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
