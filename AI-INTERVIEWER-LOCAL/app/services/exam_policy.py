"""Server-received recordings may finish their current question after closure."""
from datetime import datetime, timezone

from app.services.grade_state import json_object


def now_utc():
    return datetime.now(timezone.utc)


def exam_is_open(connection, session):
    if session["interview_mode"] != "real":
        return True
    exam = connection.execute("SELECT * FROM exam_rounds WHERE exam_round_id=?", (session["exam_round_id"],)).fetchone()
    return bool(exam and exam["status"] == "open" and
                datetime.fromisoformat(exam["starts_at"]) <= now_utc() <= datetime.fromisoformat(exam["ends_at"]))


def admit_recording(connection, session):
    if session["interview_mode"] != "real":
        return None
    exam = connection.execute("SELECT * FROM exam_rounds WHERE exam_round_id=?", (session["exam_round_id"],)).fetchone()
    accepted_at = now_utc()
    if not exam or exam["status"] != "open" or not (
            datetime.fromisoformat(exam["starts_at"]) <= accepted_at <= datetime.fromisoformat(exam["ends_at"])):
        raise ValueError("Đợt Interview đã đóng hoặc hết thời gian")
    return {"version": 1, "exam_round_id": session["exam_round_id"], "question_uid": session["current_question_uid"],
            "accepted_at": accepted_at.isoformat(), "starts_at": exam["starts_at"], "ends_at": exam["ends_at"]}


def valid_admission(session, admission):
    try:
        return bool(admission and admission.get("version") == 1 and
            admission["exam_round_id"] == session["exam_round_id"] and
            admission["question_uid"] == session["current_question_uid"] and
            datetime.fromisoformat(admission["starts_at"]) <= datetime.fromisoformat(admission["accepted_at"]) <=
            datetime.fromisoformat(admission["ends_at"]))
    except (TypeError, ValueError, KeyError, AttributeError):
        return False


def received_admission(connection, session, job_id):
    row = connection.execute("SELECT context_json FROM speech_jobs WHERE job_id=? AND session_id=? AND user_id=? AND question_uid=?",
        (job_id, session["session_id"], session["user_id"], session["current_question_uid"])).fetchone()
    admission = json_object(row[0]).get("admission") if row else None
    return admission if valid_admission(session, admission) else None


def submission_admission(connection, session, transcription_id=None, admitted=None):
    if session["interview_mode"] != "real":
        return None
    if valid_admission(session, admitted):
        return admitted
    received = received_admission(connection, session, transcription_id)
    return received or admit_recording(connection, session)
