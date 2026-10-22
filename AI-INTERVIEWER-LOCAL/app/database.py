from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.services.grade_state import original_is_provisional


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
    bank_scope TEXT NOT NULL DEFAULT 'learning' CHECK (bank_scope IN ('learning', 'test')),
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

CREATE TABLE IF NOT EXISTS grading_retry_events (
    retry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    answer_id INTEGER NOT NULL REFERENCES interview_answers(answer_id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    previous_json TEXT NOT NULL,
    evaluation_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(answer_id, attempt_number)
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
    mic_checked_at TEXT,
    mic_check_result_json TEXT,
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
    transcription_id TEXT,
    ai_score REAL,
    final_score REAL,
    teacher_score REAL,
    teacher_feedback TEXT,
    review_ai_score REAL,
    review_ai_feedback TEXT,
    review_ai_evaluation_json TEXT,
    review_ai_at TEXT,
    reviewed_by INTEGER,
    reviewed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id),
    FOREIGN KEY (transcription_id) REFERENCES speech_transcriptions(transcription_id),
    FOREIGN KEY (reviewed_by) REFERENCES users(user_id),
    UNIQUE (session_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS session_grading_jobs (
    session_id TEXT PRIMARY KEY REFERENCES interview_sessions(session_id) ON DELETE CASCADE,
    state TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    processed_count INTEGER NOT NULL DEFAULT 0,
    worker_id TEXT,
    lease_until REAL,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    audio_path TEXT,
    audio_sha256 TEXT,
    audio_mime_type TEXT,
    audio_size INTEGER,
    accepted INTEGER NOT NULL DEFAULT 1,
    consumed INTEGER NOT NULL DEFAULT 0,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    retry_reason TEXT,
    superseded_by TEXT,
    review_transcript TEXT,
    review_model TEXT,
    review_runtime TEXT,
    review_confidence REAL,
    review_metadata_json TEXT,
    review_processed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS generated_questions (
    generated_id TEXT PRIMARY KEY,
    question_json TEXT NOT NULL,
    rubric_result_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft', 'approved', 'rejected')),
    generated_by INTEGER NOT NULL,
    approved_by INTEGER,
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    FOREIGN KEY (generated_by) REFERENCES users(user_id),
    FOREIGN KEY (approved_by) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS answer_reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    answer_id INTEGER NOT NULL,
    previous_final_score REAL NOT NULL,
    teacher_score REAL NOT NULL,
    feedback TEXT NOT NULL,
    reviewed_by INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (answer_id) REFERENCES interview_answers(answer_id),
    FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS rubric_revisions (
    revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_uid TEXT NOT NULL,
    question_fingerprint TEXT NOT NULL,
    contract_sha256 TEXT NOT NULL,
    contract_json TEXT NOT NULL,
    approved_by INTEGER NOT NULL REFERENCES users(user_id),
    attestation TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (question_uid, contract_sha256)
);

CREATE TABLE IF NOT EXISTS grading_labels (
    label_id INTEGER PRIMARY KEY AUTOINCREMENT,
    answer_id INTEGER NOT NULL REFERENCES interview_answers(answer_id) ON DELETE CASCADE,
    transcript_source TEXT NOT NULL CHECK (transcript_source IN ('original', 'strong')),
    transcript_sha256 TEXT NOT NULL,
    rubric_sha256 TEXT NOT NULL,
    labels_json TEXT NOT NULL,
    annotation_mode TEXT NOT NULL CHECK (annotation_mode IN ('independent', 'assisted')),
    reviewed_by INTEGER NOT NULL REFERENCES users(user_id),
    created_at TEXT NOT NULL
);
"""


SCHEMA += """
CREATE TABLE IF NOT EXISTS speech_jobs (
    job_id TEXT PRIMARY KEY,
    request_key TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    session_id TEXT NOT NULL REFERENCES interview_sessions(session_id) ON DELETE CASCADE,
    question_uid TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    context_json TEXT NOT NULL,
    audio_path TEXT NOT NULL,
    audio_sha256 TEXT NOT NULL,
    audio_size INTEGER NOT NULL,
    audio_mime_type TEXT,
    ambient_noise_dbfs REAL,
    retry_reason TEXT,
    state TEXT NOT NULL DEFAULT 'queued',
    stage TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    worker_id TEXT,
    lease_until REAL,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    retryable INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    error_status INTEGER,
    result_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, request_key)
);
CREATE INDEX IF NOT EXISTS idx_speech_jobs_queue ON speech_jobs(state, created_at);
CREATE TABLE IF NOT EXISTS submission_receipts (
    session_id TEXT NOT NULL REFERENCES interview_sessions(session_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    request_key TEXT NOT NULL,
    response_json TEXT NOT NULL,
    PRIMARY KEY(session_id, user_id, request_key)
);
CREATE TABLE IF NOT EXISTS audio_deletions (
    deletion_id INTEGER PRIMARY KEY,
    storage_root TEXT NOT NULL,
    audio_path TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    retry_after REAL NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(storage_root,audio_path)
);
CREATE TABLE IF NOT EXISTS app_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_audio_deletions_retry ON audio_deletions(state,retry_after);
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

CREATE INDEX IF NOT EXISTS idx_answers_review_queue
ON interview_answers (review_required, reviewed_at, final_score);

CREATE INDEX IF NOT EXISTS idx_generated_questions_status
ON generated_questions (status, created_at);

CREATE INDEX IF NOT EXISTS idx_rubric_revision_source
ON rubric_revisions (question_uid, question_fingerprint, revision_id);

CREATE INDEX IF NOT EXISTS idx_grading_labels_answer
ON grading_labels (answer_id, transcript_source, reviewed_by, label_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_real_attempt
ON interview_sessions (exam_round_id, user_id)
WHERE exam_round_id IS NOT NULL AND user_id IS NOT NULL;
"""


SESSION_COLUMNS = {
    "grading_strategy": "TEXT NOT NULL DEFAULT 'per_answer'",
    "starting_difficulty_rank": "INTEGER",
    "question_plan_json": "TEXT",
    "user_id": "INTEGER REFERENCES users(user_id)",
    "interview_mode": "TEXT NOT NULL DEFAULT 'practice'",
    "exam_round_id": "TEXT REFERENCES exam_rounds(exam_round_id)",
    "answer_mode": "TEXT NOT NULL DEFAULT 'voice'",
    "mic_checked_at": "TEXT",
    "mic_check_result_json": "TEXT",
}


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.create_function("grade_is_provisional", 3, original_is_provisional, deterministic=True)
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
    question_columns = {row["name"] for row in connection.execute("PRAGMA table_info(questions)")}
    if "bank_scope" not in question_columns:
        connection.execute("ALTER TABLE questions ADD COLUMN bank_scope TEXT NOT NULL DEFAULT 'learning'")
    connection.execute("""UPDATE questions SET bank_scope='test'
        WHERE source_name='cau_hoi_import.json' AND subject GLOB 'CTX[0-9][0-9] -*'
          AND bank_scope='learning'""")
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
        "grading_pending": "INTEGER NOT NULL DEFAULT 0",
        "grading_retry_count": "INTEGER NOT NULL DEFAULT 0",
        "grading_retry_at": "REAL",
        "final_decision_json": "TEXT",
        "score_provisional": "INTEGER NOT NULL DEFAULT 0",
        "assessment_json": "TEXT NOT NULL DEFAULT '{}'",
        "review_required": "INTEGER NOT NULL DEFAULT 0",
        "rubric_version": "TEXT NOT NULL DEFAULT 'key-points-v2'",
        "transcription_id": "TEXT",
        "ai_score": "REAL",
        "final_score": "REAL",
        "teacher_score": "REAL",
        "teacher_feedback": "TEXT",
        "review_ai_score": "REAL",
        "review_ai_feedback": "TEXT",
        "review_ai_evaluation_json": "TEXT",
        "review_ai_at": "TEXT",
        "reviewed_by": "INTEGER",
        "reviewed_at": "TEXT",
    }
    new_answer_columns: set[str] = set()
    for name, definition in answer_additions.items():
        if name not in answer_columns:
            connection.execute(
                f"ALTER TABLE interview_answers ADD COLUMN {name} {definition}"
            )
            new_answer_columns.add(name)

    connection.execute(
        "UPDATE interview_answers SET ai_score = score WHERE ai_score IS NULL"
    )
    if "final_score" in new_answer_columns:
        connection.execute(
            "UPDATE interview_answers SET final_score = score WHERE final_score IS NULL"
        )
    connection.execute(
        """
        UPDATE interview_answers
        SET final_score = NULL, review_required = 1
        WHERE reviewed_at IS NULL
          AND session_id IN (
              SELECT session_id FROM interview_sessions
              WHERE interview_mode = 'real' AND answer_mode = 'voice'
          )
        """
    )

    transcription_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(speech_transcriptions)").fetchall()
    }
    transcription_additions = {
        "confirmed_at": "TEXT",
        "confirmed_text_sha256": "TEXT",
        "audio_path": "TEXT",
        "audio_sha256": "TEXT",
        "audio_mime_type": "TEXT",
        "audio_size": "INTEGER",
        "attempt_number": "INTEGER NOT NULL DEFAULT 1",
        "retry_reason": "TEXT",
        "superseded_by": "TEXT",
        "review_transcript": "TEXT",
        "review_model": "TEXT",
        "review_runtime": "TEXT",
        "review_confidence": "REAL",
        "review_metadata_json": "TEXT",
        "review_processed_at": "TEXT",
    }
    for name, definition in transcription_additions.items():
        if name not in transcription_columns:
            connection.execute(
                f"ALTER TABLE speech_transcriptions ADD COLUMN {name} {definition}"
            )

    review_columns = {row["name"] for row in connection.execute("PRAGMA table_info(answer_reviews)")}
    if "decision_json" not in review_columns:
        connection.execute("ALTER TABLE answer_reviews ADD COLUMN decision_json TEXT")
    if not connection.execute("SELECT 1 FROM app_migrations WHERE name='grade-state-v2'").fetchone():
        connection.execute("""UPDATE interview_answers SET score_provisional=1,review_required=1
            WHERE reviewed_at IS NULL AND score_provisional=0 AND grade_is_provisional(
                score_provisional, assessment_json,
                (SELECT metadata_json FROM speech_transcriptions t WHERE t.transcription_id=interview_answers.transcription_id))=1""")
        connection.execute("INSERT INTO app_migrations VALUES ('grade-state-v2',CURRENT_TIMESTAMP)")

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
            "SELECT COUNT(*) AS total FROM questions WHERE active = 1 AND bank_scope = 'learning'"
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
