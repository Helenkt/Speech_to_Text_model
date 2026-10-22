"""Isolated UI fixture server. Never starts against the student's real database."""
import asyncio
import json
import os
import time
from pathlib import Path

from app import main as main_module
from app.config import Settings
from app.database import init_database
from app.services.account_importer import seed_demo_accounts
from app.services.question_importer import import_question_bank


root = Path(__file__).resolve().parents[1]
temporary = Path(os.environ["UX_SMOKE_ROOT"]).resolve()
if not temporary.is_relative_to(root) or not temporary.name.startswith(".pytest-quality-ui-"):
    raise RuntimeError("UX_SMOKE_ROOT must be an isolated UI test directory")
temporary.mkdir(parents=True, exist_ok=True)
settings = Settings(root_dir=root, database_path=temporary / "ui.db", static_dir=root / "app/static",
    demo_data_dir=root / "data", whisper_download_root=temporary / "models", audio_storage_dir=temporary / "audio",
    auto_seed_demo=False, evaluator_mode="rule")
init_database(settings.database_path)
seed_demo_accounts(settings.database_path, settings.demo_data_dir)
import_question_bank(settings.database_path, json.dumps([{
    "id": "STACK", "language": "en", "subject": "DSA101", "difficulty": "Easy", "question": "What is a stack?",
    "reference_answer": "A stack is LIFO", "key_points": ["A stack is LIFO"]}]).encode(), filename="ui_fixture.json")
counts = {"stt": 0, "microphone": 0}


def transcribe(*_args, **_kwargs):
    counts["stt"] += 1
    time.sleep(.25)
    if counts["stt"] == 1:
        raise main_module.SpeechToTextError("Simulated transient decoder failure")
    return {"text": "A stack is LIFO", "model": "UI-test-stub", "runtime": "test", "uncertain_spans": ["LIFO"],
            "metrics": {"confidence": .9, "speech_duration_seconds": 3, "word_count": 4, "uncertain_word_ratio": .25}}


def microphone(*_args, **_kwargs):
    counts["microphone"] += 1
    return {"ready": True, "status": "good", "status_label": "Mic sẵn sàng", "microphone_score_percent": 90,
            "noise": {"dbfs": -45, "label": "Yên tĩnh"}, "metrics": {"duration_seconds": 3}}


async def correct(_settings, text, **_kwargs):
    await asyncio.sleep(.1)
    return {"raw_text": text, "corrected_text": text, "correction_applied": False}


async def ollama(_settings):
    return {"running": True, "model_available": True, "model": "UI-test-stub"}


main_module.transcribe_bytes = transcribe
main_module.analyze_microphone_sample = microphone
main_module.correct_transcript = correct
main_module.ollama_status = ollama
main_module.stt_status = lambda _: {"installed": True, "ready": True, "model": "UI-test-stub", "label": "Test"}
app = main_module.create_app(settings)


@app.get("/fixture/counts")
def fixture_counts():
    return counts
