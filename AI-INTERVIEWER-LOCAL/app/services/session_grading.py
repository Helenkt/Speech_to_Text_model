"""Durable end-of-session grading, sharing the application's inference lane."""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid

from app.database import database
from app.services.evaluator import evaluate_answer
from app.services.interview_engine import apply_voice_assurance, queue_session_grading
from app.services.transcription_store import transcript_sha256


log = logging.getLogger(__name__)


class SessionGrading:
    def __init__(self, settings, readiness):
        self.settings, self.readiness = settings, readiness
        self.owner = str(uuid.uuid4())
        self.task = None
        self.wake = asyncio.Event()

    def recover(self):
        with database(self.settings.database_path) as connection:
            for row in connection.execute("""SELECT session_id FROM interview_sessions
                    WHERE status='completed' AND grading_strategy='end_of_session'""").fetchall():
                queue_session_grading(connection, row[0])

    def status(self, session_id):
        with database(self.settings.database_path) as connection:
            session = connection.execute("SELECT grading_strategy,status FROM interview_sessions WHERE session_id=?",
                                         (session_id,)).fetchone()
            job = connection.execute("SELECT state,attempts,processed_count,error,updated_at FROM session_grading_jobs WHERE session_id=?",
                                     (session_id,)).fetchone()
            pending, total = connection.execute("SELECT COALESCE(SUM(grading_pending),0),COUNT(*) FROM interview_answers WHERE session_id=?",
                                                (session_id,)).fetchone()
        if not session:
            raise ValueError("Không tìm thấy phiên phỏng vấn")
        state = job["state"] if job else "collecting" if session["status"] == "active" else "completed"
        return {"session_id": session_id, "strategy": session["grading_strategy"],
                "state": state, "pending_count": pending, "processed_count": total - pending,
                "answer_count": total, "report_ready": session["status"] == "completed" and pending == 0,
                "attempts": job["attempts"] if job else 0, "error": job["error"] if job else None}

    def retry(self, session_id):
        with database(self.settings.database_path) as connection:
            changed = connection.execute("""UPDATE session_grading_jobs SET state='queued',error=NULL,
                updated_at=CURRENT_TIMESTAMP WHERE session_id=? AND state='failed' AND attempts<3""", (session_id,)).rowcount
            if not changed:
                raise ValueError("Phiên này không thể yêu cầu chấm lại tự động")
        self.wake.set()
        return self.status(session_id)

    def claim(self):
        with database(self.settings.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("""UPDATE session_grading_jobs SET state='failed',
                error='Đã hết số lượt chấm tự động; kết quả chưa đủ cơ sở để tính điểm'
                WHERE state='queued' AND attempts>=3""")
            connection.execute("""UPDATE session_grading_jobs SET state=CASE WHEN attempts<3 THEN 'queued' ELSE 'failed' END,
                error='Lượt chấm bị gián đoạn; câu trả lời vẫn được giữ',worker_id=NULL,lease_until=NULL
                WHERE state='processing' AND lease_until<?""", (time.time(),))
            if connection.execute("SELECT 1 FROM session_grading_jobs WHERE state='processing'").fetchone():
                return None
            row = connection.execute("""SELECT j.session_id FROM session_grading_jobs j
                JOIN interview_sessions s ON s.session_id=j.session_id
                WHERE j.state='queued' AND j.attempts<3 AND s.status='completed'
                ORDER BY j.created_at,j.rowid LIMIT 1""").fetchone()
            if not row:
                return None
            connection.execute("""UPDATE session_grading_jobs SET state='processing',attempts=attempts+1,
                worker_id=?,lease_until=?,error=NULL,updated_at=CURRENT_TIMESTAMP WHERE session_id=?""",
                (self.owner, time.time() + 30, row[0]))
            return row[0]

    async def heartbeat(self, session_id):
        while True:
            await asyncio.sleep(5)
            with database(self.settings.database_path) as connection:
                connection.execute("""UPDATE session_grading_jobs SET lease_until=?
                    WHERE session_id=? AND worker_id=? AND state='processing'""",
                    (time.time() + 30, session_id, self.owner))

    async def grade(self, session_id):
        with database(self.settings.database_path) as connection:
            session = connection.execute("SELECT * FROM interview_sessions WHERE session_id=?", (session_id,)).fetchone()
            rows = connection.execute("""SELECT a.*,t.metadata_json,t.confirmed_text_sha256 FROM interview_answers a
                LEFT JOIN speech_transcriptions t ON t.transcription_id=a.transcription_id
                WHERE a.session_id=? AND a.grading_pending=1 ORDER BY a.sequence_number""", (session_id,)).fetchall()
        if not session or session["status"] != "completed":
            return
        await self.readiness.begin_grading()
        for row in rows:
            with database(self.settings.database_path) as connection:
                current = connection.execute("SELECT grading_pending,reviewed_at FROM interview_answers WHERE answer_id=?",
                                             (row["answer_id"],)).fetchone()
                if not current or not current["grading_pending"]:
                    continue
                if current["reviewed_at"]:
                    connection.execute("UPDATE interview_answers SET grading_pending=0 WHERE answer_id=?", (row["answer_id"],))
                    continue
            question = json.loads(row["question_json"])
            metadata = json.loads(row["metadata_json"] or "{}")
            # Confirmation freezes the candidate's preview. Grading may not rewrite it.
            if (row["confirmed_text_sha256"]
                    and transcript_sha256(row["answer_text"]) != row["confirmed_text_sha256"]):
                raise ValueError("Confirmed transcript fingerprint does not match")
            evaluation = await evaluate_answer(self.settings, question, row["answer_text"],
                ensure_model=self.readiness.ensure_llm, inference_runner=self.readiness.run_inference)
            apply_voice_assurance(self.settings, evaluation, question, metadata, session["interview_mode"])
            with database(self.settings.database_path) as connection:
                connection.execute("BEGIN IMMEDIATE")
                lease = connection.execute("SELECT 1 FROM session_grading_jobs WHERE session_id=? AND state='processing' AND worker_id=?",
                                           (session_id, self.owner)).fetchone()
                if not lease:
                    raise RuntimeError("Session grading ownership changed")
                final = None if evaluation.get("score_provisional") or session["interview_mode"] == "real" else evaluation["score"]
                changed = connection.execute("""UPDATE interview_answers SET score=?,ai_score=?,final_score=?,
                    verdict=?,matched_points_json=?,missing_points_json=?,feedback=?,confidence=?,evaluator=?,
                    assessment_json=?,review_required=?,rubric_version=?,score_provisional=?,grading_pending=0
                    WHERE answer_id=? AND grading_pending=1 AND reviewed_at IS NULL AND answer_text=? AND question_json=?""",
                    (evaluation["score"], evaluation["score"], final,
                     evaluation["verdict"], json.dumps(evaluation["matched_points"], ensure_ascii=False),
                     json.dumps(evaluation["missing_points"], ensure_ascii=False), evaluation["feedback"],
                     evaluation["confidence"], evaluation["evaluator"],
                     json.dumps(evaluation.get("point_assessments", []), ensure_ascii=False),
                     int(bool(evaluation.get("review_required"))), evaluation.get("rubric_version", "key-points-v2"),
                     int(bool(evaluation.get("score_provisional"))), row["answer_id"],
                     row["answer_text"], row["question_json"])).rowcount
                if not changed:
                    # A teacher's decision made while AI was running always wins.
                    connection.execute("UPDATE interview_answers SET grading_pending=0 WHERE answer_id=? AND reviewed_at IS NOT NULL",
                                       (row["answer_id"],))
                    if connection.execute("SELECT 1 FROM interview_answers WHERE answer_id=? AND grading_pending=1",
                                          (row["answer_id"],)).fetchone():
                        raise ValueError("The answer changed while grading")
                connection.execute("""UPDATE session_grading_jobs SET processed_count=(SELECT COUNT(*) FROM interview_answers
                    WHERE session_id=? AND grading_pending=0),updated_at=CURRENT_TIMESTAMP WHERE session_id=? AND worker_id=?""",
                    (session_id, session_id, self.owner))

    async def run_once(self):
        session_id = await asyncio.to_thread(self.claim)
        if not session_id:
            return False
        heartbeat = asyncio.create_task(self.heartbeat(session_id))
        state, error = "completed", None
        try:
            async with self.readiness.inference_lock:
                try:
                    await self.grade(session_id)
                finally:
                    try:
                        await self.readiness.end_grading()
                    except Exception:
                        log.exception("Could not release grading models: %s", session_id)
        except asyncio.CancelledError:
            state, error = "queued", "Lượt chấm bị gián đoạn; sẽ tiếp tục khi khởi động lại"
            raise
        except Exception:
            log.exception("Session grading failed: %s", session_id)
            state, error = "failed", "Chấm cuối phiên bị lỗi; câu trả lời và voice vẫn được giữ để thử lại"
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            with database(self.settings.database_path) as connection:
                connection.execute("""UPDATE session_grading_jobs SET state=?,error=?,worker_id=NULL,lease_until=NULL,
                    updated_at=CURRENT_TIMESTAMP WHERE session_id=? AND worker_id=? AND state='processing'""",
                    (state, error, session_id, self.owner))
        return True

    async def run(self):
        while True:
            try:
                if await self.run_once():
                    continue
                self.wake.clear()
                try:
                    await asyncio.wait_for(self.wake.wait(), timeout=2)
                except asyncio.TimeoutError:
                    pass
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Session grading queue error")
                await asyncio.sleep(2)

    def start(self):
        self.recover()
        self.task = asyncio.create_task(self.run())

    async def stop(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None
