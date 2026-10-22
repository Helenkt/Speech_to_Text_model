"""Isolated UX exercise using a read-only copy of real question data and real models."""
import json
import asyncio
import os
import signal
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

from fastapi import Depends, HTTPException

from app.config import Settings
from app.database import database, init_database
from app.main import create_app
from app.services.account_importer import seed_demo_accounts
from app.services.auth import get_user_by_token, COOKIE_NAME
from fastapi import Request


root = Path(__file__).resolve().parents[1]
temporary = Path(os.environ["UX_REAL_ROOT"]).resolve()
if not temporary.is_relative_to(root) or not temporary.name.startswith(".pytest-quality-ui-ux-"):
    raise RuntimeError("UX_REAL_ROOT must be a private project test directory")
temporary.mkdir(parents=True, exist_ok=True)
original = Settings.from_env(root)
settings = replace(original, database_path=temporary / "ux.db", audio_storage_dir=temporary / "audio", auto_seed_demo=False)
init_database(settings.database_path)
seed_demo_accounts(settings.database_path, settings.demo_data_dir)
with sqlite3.connect(original.database_path.resolve().as_uri() + "?mode=ro", uri=True) as source, database(settings.database_path) as destination:
    for table in ("questions", "question_sources"):
        columns = [row[1] for row in source.execute(f"PRAGMA table_info({table})")]
        rows = source.execute(f"SELECT * FROM {table}").fetchall()
        if rows:
            destination.executemany(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", rows)

init_database(settings.database_path)

app = create_app(settings)
fixed_question_uid = os.environ.get("UX_FIXED_QUESTION_UID")
if fixed_question_uid:
    with database(settings.database_path) as connection:
        selected = connection.execute("SELECT * FROM questions WHERE uid=? AND bank_scope='learning'", (fixed_question_uid,)).fetchone()
        if not selected:
            raise RuntimeError("Controlled question must exist in the supplied bank")
        connection.execute("UPDATE questions SET active=0 WHERE language=? AND subject=? AND uid<>?",
                           (selected["language"], selected["subject"], fixed_question_uid))


def fixture_user(request: Request):
    user = get_user_by_token(settings.database_path, request.cookies.get(COOKIE_NAME))
    if not user:
        raise HTTPException(401, "Test account login required")
    return user


@app.post("/fixture/shutdown")
async def shutdown_fixture(user=Depends(fixture_user)):
    asyncio.get_running_loop().call_later(.1, signal.raise_signal, signal.SIGTERM)
    return {"stopping": True, "test_only": True}


@app.get("/fixture/context/{session_id}")
def context(session_id: str, user=Depends(fixture_user)):
    with database(settings.database_path) as connection:
        row = connection.execute("SELECT * FROM interview_sessions WHERE session_id=? AND user_id=?", (session_id, user["user_id"])).fetchone()
    if not row:
        raise HTTPException(404)
    return {"question": json.loads(row["current_question_json"]), "test_only": True}


@app.get("/fixture/inventory")
def inventory(user=Depends(fixture_user)):
    with database(settings.database_path) as connection:
        questions = [dict(row) for row in connection.execute("SELECT * FROM questions WHERE active=1")]
    duplicate = defaultdict(list)
    for question in questions:
        text = " ".join(unicodedata.normalize("NFC", question["question"]).casefold().split())
        duplicate[(question["language"], text)].append(question["uid"])
    code_terms = ("write a", "write an", "write sql", "implement ", "viết câu", "viết mã", "viết chương", "viết hàm", "cài đặt hàm")
    code_questions = [q for q in questions if any(term in q["question"].casefold() for term in code_terms)]
    long_questions = sorted(questions, key=lambda q: len(q["question"]), reverse=True)
    samples = {}
    for question in sorted(questions, key=lambda q: q["uid"]):
        if question["subject"].startswith("CTX"):
            continue
        group = f"{question['language']}:{question['subject']}:{question['difficulty']}"
        samples.setdefault(group, {k: question[k] for k in (
            "uid", "question", "reference_answer", "key_points_json", "difficulty", "verification_status")})
    return {"question_count": len(questions), "by_subject_language": dict(Counter(f"{q['language']}:{q['subject']}" for q in questions)),
        "by_difficulty": dict(Counter(q["difficulty"] for q in questions)),
        "samples_by_subject_language_difficulty": samples,
        "exact_duplicate_groups": [ids for ids in duplicate.values() if len(ids) > 1],
        "questions_over_500_chars": sum(len(q["question"]) > 500 for q in questions),
        "longest_questions": [{k: q[k] for k in ("uid", "question", "difficulty", "source_name")} for q in long_questions[:5]],
        "code_wording_candidates": len(code_questions),
        "code_examples": [{k: q[k] for k in ("uid", "question", "difficulty")} for q in code_questions[:8]],
        "sources": sorted({q["source_name"] for q in questions}), "real_models": True, "real_student_answers_copied": False}
