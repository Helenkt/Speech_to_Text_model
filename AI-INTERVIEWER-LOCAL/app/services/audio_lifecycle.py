"""Durable filesystem cleanup after database deletion, with bounded retries."""
from __future__ import annotations

import time
from pathlib import Path

from app.database import database


def safe_audio_path(storage_root, relative_path):
    root = Path(storage_root).resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root) or path == root or path != (root / relative_path).absolute():
        raise ValueError("Audio path is outside its storage root")
    return path


def audio_exists(storage_root, relative_path):
    try:
        return bool(relative_path and safe_audio_path(storage_root, relative_path).is_file())
    except (OSError, ValueError):
        return False


def schedule_session_audio(connection, session_id, storage_root):
    root = str(Path(storage_root).resolve())
    rows = connection.execute("""SELECT audio_path FROM speech_transcriptions WHERE session_id=? AND audio_path IS NOT NULL
        UNION SELECT audio_path FROM speech_jobs WHERE session_id=?""", (session_id, session_id)).fetchall()
    keys = []
    for row in rows:
        connection.execute("""INSERT OR IGNORE INTO audio_deletions(storage_root,audio_path,created_at)
            VALUES (?,?,CURRENT_TIMESTAMP)""", (root, row[0]))
        keys.append((root, row[0]))
    return keys


def drain_audio_deletions(database_path, *, limit=16):
    with database(database_path) as connection:
        rows = connection.execute("SELECT * FROM audio_deletions WHERE state='pending' AND retry_after<=? ORDER BY deletion_id LIMIT ?",
                                  (time.time(), limit)).fetchall()
    for row in rows:
        try:
            path = safe_audio_path(row["storage_root"], row["audio_path"])
        except (ValueError, OSError):
            with database(database_path) as connection:
                connection.execute("UPDATE audio_deletions SET state='blocked',last_error='unsafe_path' WHERE deletion_id=?", (row["deletion_id"],))
            continue
        with database(database_path) as connection:
            # Serialize with uploads/saves so a new reference cannot appear during unlink.
            connection.execute("BEGIN IMMEDIATE")
            referenced = connection.execute("""SELECT 1 FROM speech_transcriptions WHERE audio_path=?
                UNION ALL SELECT 1 FROM speech_jobs WHERE audio_path=? LIMIT 1""", (row["audio_path"], row["audio_path"])).fetchone()
            try:
                if referenced:
                    raise OSError("still_referenced")
                path.unlink(missing_ok=True)
            except OSError as exc:
                connection.execute("UPDATE audio_deletions SET attempts=attempts+1,last_error=?,retry_after=? WHERE deletion_id=?",
                    (type(exc).__name__, time.time() + min(300, 5 * 2 ** min(row["attempts"], 6)), row["deletion_id"]))
            else:
                connection.execute("DELETE FROM audio_deletions WHERE deletion_id=?", (row["deletion_id"],))


def deletion_result(database_path, keys):
    drain_audio_deletions(database_path)
    with database(database_path) as connection:
        pending = sum(bool(connection.execute("SELECT 1 FROM audio_deletions WHERE storage_root=? AND audio_path=?", key).fetchone())
                      for key in set(keys))
    return {"audio_cleanup_pending": pending, "audio_cleanup_complete": pending == 0}
