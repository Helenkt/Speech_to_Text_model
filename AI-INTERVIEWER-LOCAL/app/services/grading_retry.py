"""Bounded technical retry; never advances a session or changes teacher decisions."""
import json
import time
from datetime import datetime, timezone

from app.database import database
from app.services.assessment_feedback import assessment_feedback, voice_requires_review
from app.services.evaluator import evaluate_answer


async def retry_practice_grade(settings, session_id, transcription_id, user_id, *, ensure_model=None, inference_runner=None):
    with database(settings.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("""SELECT a.*, s.interview_mode, s.user_id, t.metadata_json
            FROM interview_answers a JOIN interview_sessions s ON s.session_id=a.session_id
            LEFT JOIN speech_transcriptions t ON t.transcription_id=a.transcription_id
            WHERE a.session_id=? AND a.transcription_id=? AND s.user_id=?""",
            (session_id, transcription_id, user_id)).fetchone()
        if not row or row["interview_mode"] != "practice" or row["reviewed_at"]:
            raise ValueError("Không có lượt luyện tập phù hợp để thử chấm lại")
        if row["grading_pending"]:
            raise ValueError("Câu trả lời đang chờ chấm cuối phiên; không chấm riêng giữa phiên")
        assessments = json.loads(row["assessment_json"])
        if not isinstance(assessments, list) or any(not isinstance(item, dict) for item in assessments):
            raise ValueError("Dữ liệu đối chiếu không hợp lệ; không tự chấm lại")
        if not any(item.get("review_reason") in {"model_unavailable", "model_timeout", "model_output_invalid"}
                   for item in assessments):
            raise ValueError("Câu trả lời không có lỗi kỹ thuật cần thử chấm lại")
        now = time.time()
        if row["grading_retry_count"] >= 2:
            return {"retried": False, "retryable": False, "reason": "retry_limit"}
        if row["grading_retry_at"] and now - row["grading_retry_at"] < 30:
            return {"retried": False, "retryable": True, "reason": "cooldown"}
        connection.execute("UPDATE interview_answers SET grading_retry_count=grading_retry_count+1, grading_retry_at=? WHERE answer_id=?",
                           (now, row["answer_id"]))
    question = json.loads(row["question_json"])
    evaluation = await evaluate_answer(settings, question, row["answer_text"],
        **({"ensure_model": ensure_model} if ensure_model else {}),
        **({"inference_runner": inference_runner} if inference_runner else {}))
    voice = json.loads(row["metadata_json"] or "{}")
    if voice_requires_review(voice):
        evaluation.update(score_provisional=True, review_required=True)
    evaluation.update(assessment_feedback(evaluation, voice, interview_mode="practice"))
    with database(settings.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute("""UPDATE interview_answers SET score=?, ai_score=?, final_score=?, verdict=?,
            matched_points_json=?, missing_points_json=?, feedback=?, confidence=?, evaluator=?, assessment_json=?,
            review_required=?, score_provisional=? WHERE answer_id=? AND reviewed_at IS NULL
            AND question_json=? AND answer_text=? AND grading_retry_at=?""",
            (evaluation["score"], evaluation["score"], None if evaluation["score_provisional"] else evaluation["score"],
             evaluation["verdict"], json.dumps(evaluation["matched_points"], ensure_ascii=False),
             json.dumps(evaluation["missing_points"], ensure_ascii=False), evaluation["feedback"], evaluation["confidence"],
             evaluation["evaluator"], json.dumps(evaluation["point_assessments"], ensure_ascii=False),
             int(evaluation["review_required"]), int(evaluation["score_provisional"]), row["answer_id"],
             row["question_json"], row["answer_text"], now))
        if cursor.rowcount != 1:
            raise ValueError("Bài làm đã thay đổi trong lúc chấm; kết quả thử lại không được áp dụng")
        previous = {"score": row["score"], "evaluator": row["evaluator"], "feedback": row["feedback"],
                    "point_assessments": assessments, "score_provisional": bool(row["score_provisional"])}
        connection.execute("""INSERT INTO grading_retry_events
            (answer_id,attempt_number,previous_json,evaluation_json,created_at) VALUES (?,?,?,?,?)""",
            (row["answer_id"], row["grading_retry_count"] + 1, json.dumps(previous, ensure_ascii=False),
             json.dumps(evaluation, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
        receipt = connection.execute("SELECT response_json FROM submission_receipts WHERE session_id=? AND user_id=? AND request_key=?",
                                     (session_id, user_id, transcription_id)).fetchone()
        if receipt:
            response = json.loads(receipt[0])
            response["evaluation"] = evaluation
            connection.execute("UPDATE submission_receipts SET response_json=? WHERE session_id=? AND user_id=? AND request_key=?",
                               (json.dumps(response, ensure_ascii=False), session_id, user_id, transcription_id))
    return {"retried": True, "retryable": row["grading_retry_count"] + 1 < 2, "evaluation": evaluation}
