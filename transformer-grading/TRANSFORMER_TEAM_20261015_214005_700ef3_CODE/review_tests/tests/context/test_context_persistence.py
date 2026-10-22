import json

from app.database import database
from app.services.question_importer import import_question_bank
from app.services.interview_engine import interview_report, start_interview, submit_answer
from app.services.transcription_store import save_transcription
import asyncio


def test_context_metadata_survives_database_and_report(test_settings, client, monkeypatch):
    q = {"id": "CONTEXT_PERSIST", "language": "vi", "subject": "Context",
         "difficulty": "Easy", "question": "Lớp là gì?", "reference_answer": "Lớp là khuôn mẫu.",
         "key_points": ["Lớp là khuôn mẫu"]}
    import_question_bank(test_settings.database_path, json.dumps([q]).encode(), filename="context.json", mode="upsert")
    with database(test_settings.database_path) as connection:
        user_id = connection.execute("SELECT user_id FROM users WHERE username='candidate01'").fetchone()["user_id"]
    session = start_interview(test_settings, user_id=user_id, candidate_name="Demo", language="vi",
                              subject="Context", question_count=1, starting_difficulty="Easy")
    with database(test_settings.database_path) as connection:
        stored = connection.execute("SELECT current_question_uid FROM interview_sessions WHERE session_id=?",
                                    (session["session_id"],)).fetchone()
    answer = "Lớp là khuôn mẫu để tạo các đối tượng."
    transcription_id = save_transcription(
        test_settings.database_path, session_id=session["session_id"], user_id=user_id,
        question_uid=stored["current_question_uid"], raw_text=answer, corrected_text=answer,
        model="test", runtime="cpu", confidence=.99, ambient_noise_dbfs=-50, metadata={})
    test_settings.context_mode = "shadow"
    monkeypatch.setattr("app.context.model.predict_context", lambda *a: [
        {"point": q["key_points"][0], "status": "contradicted", "abstained": False,
         "demo_only": True, "model_version": "test-persist", "confidence": .9}])
    asyncio.run(submit_answer(test_settings, session["session_id"], user_id=user_id,
                             answer_text=answer, transcription_id=transcription_id))
    report = interview_report(test_settings, session["session_id"])
    detail = report["answers"][0]
    assert detail["evaluation"]["review_required"]
    assert detail["evaluation"]["point_assessments"][0]["context"]["model_version"] == "test-persist"
