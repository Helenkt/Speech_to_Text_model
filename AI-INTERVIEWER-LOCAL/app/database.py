from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS questions (
    uid TEXT PRIMARY KEY,
    question_id TEXT NOT NULL,
    language TEXT NOT NULL,
    subject TEXT NOT NULL,
    competency TEXT NOT NULL,
    topic TEXT NOT NULL,
    concept TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    difficulty_rank INTEGER NOT NULL CHECK (difficulty_rank BETWEEN 1 AND 3),
    question TEXT NOT NULL,
    reference_answer TEXT NOT NULL,
    key_points_json TEXT NOT NULL,
    source_name TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'unverified',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS question_sources (
    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    languages TEXT NOT NULL,
    question_count INTEGER NOT NULL,
    import_mode TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'unverified',
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('teacher', 'candidate')),
    email TEXT,
    student_id TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS account_sources (
    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    account_count INTEGER NOT NULL,
    import_mode TEXT NOT NULL,
    imported_by INTEGER,
    imported_at TEXT NOT NULL,
    FOREIGN KEY (imported_by) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS exam_rounds (
    exam_round_id TEXT PRIMARY KEY,
    exam_code TEXT NOT NULL COLLATE NOCASE UNIQUE,
    title TEXT NOT NULL,
    language TEXT NOT NULL,
    subject TEXT NOT NULL,
    question_count INTEGER NOT NULL CHECK (question_count BETWEEN 1 AND 30),
    starting_difficulty TEXT NOT NULL CHECK (starting_difficulty IN ('Easy', 'Medium', 'Hard')),
    answer_mode TEXT NOT NULL CHECK (answer_mode IN ('text', 'voice', 'both')),
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('draft', 'open', 'closed')),
    created_by INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS exam_round_questions (
    exam_round_id TEXT NOT NULL,
    question_uid TEXT NOT NULL,
    question_json TEXT NOT NULL,
    difficulty_rank INTEGER NOT NULL,
    topic TEXT NOT NULL,
    concept TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (exam_round_id, question_uid),
    FOREIGN KEY (exam_round_id) REFERENCES exam_rounds(exam_round_id),
    FOREIGN KEY (question_uid) REFERENCES questions(uid)
);

CREATE TABLE IF NOT EXISTS interview_sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER,
    candidate_name TEXT NOT NULL,
    interview_mode TEXT NOT NULL DEFAULT 'practice' CHECK (interview_mode IN ('practice', 'real')),
    exam_round_id TEXT,
    answer_mode TEXT NOT NULL DEFAULT 'voice' CHECK (answer_mode IN ('text', 'voice', 'both')),
    language TEXT NOT NULL,
    subject TEXT,
    requested_count INTEGER NOT NULL,
    answered_count INTEGER NOT NULL DEFAULT 0,
    current_question_uid TEXT,
    current_question_json TEXT,
    current_difficulty_rank INTEGER NOT NULL,
    evaluator_requested TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    finish_reason TEXT,
    created_at TEXT NOT NULL,
    finished_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (exam_round_id) REFERENCES exam_rounds(exam_round_id)
);

CREATE TABLE IF NOT EXISTS interview_answers (
    answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    question_uid TEXT NOT NULL,
    question_json TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    score REAL NOT NULL,
    verdict TEXT NOT NULL,
    matched_points_json TEXT NOT NULL,
    missing_points_json TEXT NOT NULL,
    feedback TEXT NOT NULL,
    confidence REAL NOT NULL,
    evaluator TEXT NOT NULL,
    assessment_json TEXT NOT NULL DEFAULT '{}',
    review_required INTEGER NOT NULL DEFAULT 0,
    rubric_version TEXT NOT NULL DEFAULT 'key-points-v2',
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id),
    UNIQUE (session_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS speech_transcriptions (
    transcription_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    question_uid TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    corrected_text TEXT NOT NULL,
    model TEXT NOT NULL,
    runtime TEXT NOT NULL,
    confidence REAL NOT NULL,
    ambient_noise_dbfs REAL,
    metadata_json TEXT NOT NULL,
    accepted INTEGER NOT NULL DEFAULT 1,
    consumed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
"""


INDEXES = """
CREATE INDEX IF NOT EXISTS idx_questions_filter
ON questions (active, language, subject, difficulty_rank);

CREATE INDEX IF NOT EXISTS idx_answers_session
ON interview_answers (session_id, sequence_number);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user
ON auth_sessions (user_id, expires_at);

CREATE INDEX IF NOT EXISTS idx_exam_rounds_window
ON exam_rounds (status, starts_at, ends_at);

CREATE INDEX IF NOT EXISTS idx_interview_sessions_user
ON interview_sessions (user_id, interview_mode, created_at);

CREATE INDEX IF NOT EXISTS idx_transcriptions_question
ON speech_transcriptions (session_id, user_id, question_uid, consumed, created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_real_attempt
ON interview_sessions (exam_round_id, user_id)
WHERE exam_round_id IS NOT NULL AND user_id IS NOT NULL;
"""


SESSION_COLUMNS = {
    "user_id": "INTEGER REFERENCES users(user_id)",
    "interview_mode": "TEXT NOT NULL DEFAULT 'practice'",
    "exam_round_id": "TEXT REFERENCES exam_rounds(exam_round_id)",
    "answer_mode": "TEXT NOT NULL DEFAULT 'voice'",
}


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


@contextmanager
def database(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(database_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _migrate_existing_database(connection: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(interview_sessions)").fetchall()
    }
    for name, definition in SESSION_COLUMNS.items():
        if name not in columns:
            connection.execute(
                f"ALTER TABLE interview_sessions ADD COLUMN {name} {definition}"
            )

    exam_question_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(exam_round_questions)").fetchall()
    }
    exam_question_additions = {
        "question_json": "TEXT NOT NULL DEFAULT '{}'",
        "difficulty_rank": "INTEGER NOT NULL DEFAULT 1",
        "topic": "TEXT NOT NULL DEFAULT ''",
        "concept": "TEXT NOT NULL DEFAULT ''",
    }
    for name, definition in exam_question_additions.items():
        if name not in exam_question_columns:
            connection.execute(
                f"ALTER TABLE exam_round_questions ADD COLUMN {name} {definition}"
            )
    connection.execute(
        """
        UPDATE exam_round_questions
        SET concept = COALESCE(json_extract(question_json, '$.concept'), '')
        WHERE concept = ''
        """
    )

    answer_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(interview_answers)").fetchall()
    }
    answer_additions = {
        "assessment_json": "TEXT NOT NULL DEFAULT '{}'",
        "review_required": "INTEGER NOT NULL DEFAULT 0",
        "rubric_version": "TEXT NOT NULL DEFAULT 'key-points-v2'",
    }
    for name, definition in answer_additions.items():
        if name not in answer_columns:
            connection.execute(
                f"ALTER TABLE interview_answers ADD COLUMN {name} {definition}"
            )

    connection.execute(
        "UPDATE interview_sessions SET answer_mode = 'voice' WHERE status = 'active'"
    )
    connection.execute(
        "UPDATE exam_rounds SET answer_mode = 'voice' WHERE answer_mode <> 'voice'"
    )


def init_database(database_path: Path) -> None:
    with database(database_path) as connection:
        connection.executescript(SCHEMA)
        _migrate_existing_database(connection)
        connection.executescript(INDEXES)


def active_question_count(database_path: Path) -> int:
    with database(database_path) as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM questions WHERE active = 1"
        ).fetchone()
    return int(row["total"])


def active_user_count(database_path: Path) -> int:
    with database(database_path) as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM users WHERE active = 1"
        ).fetchone()
    return int(row["total"])


def total_user_count(database_path: Path) -> int:
    with database(database_path) as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM users").fetchone()
    return int(row["total"])
