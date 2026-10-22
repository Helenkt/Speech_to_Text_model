"""Isolated integration fixture; fake inference, real auth/storage/confirmation/jobs."""
import asyncio
import json
import os
import signal
import time
from pathlib import Path

from app import main
from app.config import Settings
from app.database import database, init_database
from app.services import evaluator, session_grading
from app.services.account_importer import seed_demo_accounts
from app.services.question_importer import import_question_bank


root = Path(__file__).resolve().parents[1]
temporary = Path(os.environ["UX_SMOKE_ROOT"]).resolve()
if not temporary.is_relative_to(root) or not temporary.name.startswith(".pytest-preview-ui-"):
    raise RuntimeError("Fixture requires an isolated test directory")
temporary.mkdir(parents=True, exist_ok=True)
settings = Settings(root_dir=root, database_path=temporary / "ui.db", static_dir=root / "app/static",
    demo_data_dir=root / "data", whisper_download_root=temporary / "models",
    audio_storage_dir=temporary / "audio", auto_seed_demo=False, evaluator_mode="rule",
    defer_grading_until_finish=True)
init_database(settings.database_path)
seed_demo_accounts(settings.database_path, settings.demo_data_dir)
import_question_bank(settings.database_path, json.dumps([
    {"id": "preview-stack", "language": "en", "subject": "DSA101", "difficulty": "Easy",
     "question": "What is a stack?", "reference_answer": "A stack is LIFO.", "key_points": ["A stack is LIFO"]},
    {"id": "preview-queue", "language": "en", "subject": "DSA101", "difficulty": "Medium",
     "question": "What is a queue?", "reference_answer": "A queue is FIFO.", "key_points": ["A queue is FIFO"]},
]).encode(), filename="preview_fixture.json")
counts = {"stt": 0, "microphone": 0, "correction": 0, "grading": 0, "fail_next": False}


def transcribe(*_args, **_kwargs):
    counts["stt"] += 1
    time.sleep(.2)
    text = "A stack is lee foe." if counts["stt"] == 1 else "A stack uses last in first out."
    return {"text": text, "model": "fixture-stt", "runtime": "test", "uncertain_spans": [],
        "metrics": {"confidence": .98, "speech_duration_seconds": 3, "word_count": 8,
                    "uncertain_word_ratio": 0, "average_no_speech_probability": .01}}


def microphone(*_args, **_kwargs):
    counts["microphone"] += 1
    return {"ready": True, "status": "good", "status_label": "Mic ready", "microphone_score_percent": 90,
            "noise": {"dbfs": -45, "label": "Quiet"}, "metrics": {"duration_seconds": 3}}


async def correct(_settings, text, **_kwargs):
    counts["correction"] += 1
    await asyncio.sleep(.1)
    return {"raw_text": text, "corrected_text": text.replace("lee foe", "LIFO"),
            "correction_applied": "lee foe" in text}


async def grade(_settings, question, text, **_kwargs):
    counts["grading"] += 1
    await asyncio.sleep(2)
    if counts["fail_next"]:
        counts["fail_next"] = False
        raise RuntimeError("Intentional grading interruption")
    return evaluator._compose_result(question,
        [{"point": point, "status": "met"} for point in question["key_points"]], evaluator="fixture-grade")


async def ollama(_settings):
    return {"running": False, "model_available": False, "model": "fixture"}


main.transcribe_bytes = transcribe
main.analyze_microphone_sample = microphone
main.correct_transcript = correct
main.ollama_status = ollama
main.stt_status = lambda _: {"installed": True, "ready": True, "model": "fixture", "label": "Test"}
session_grading.evaluate_answer = grade
app = main.create_app(settings)


@app.get("/fixture/counts")
def fixture_counts():
    with database(settings.database_path) as connection:
        return {**counts, "answers": connection.execute("SELECT COUNT(*) FROM interview_answers").fetchone()[0],
                "transcripts": connection.execute("SELECT COUNT(*) FROM speech_transcriptions").fetchone()[0]}


@app.post("/fixture/fail-next")
def fail_next():
    counts["fail_next"] = True
    return {"ok": True}


@app.post("/fixture/shutdown")
async def shutdown():
    asyncio.get_running_loop().call_later(.1, signal.raise_signal, signal.SIGINT)
    return {"ok": True}
