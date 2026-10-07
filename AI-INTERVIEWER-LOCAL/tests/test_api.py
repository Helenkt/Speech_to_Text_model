import json
from datetime import datetime, timedelta, timezone

import app.main as main_module
from app.database import database
from app.services.transcription_store import save_transcription


def sample_question(question_id: str, difficulty: str = "Easy", language: str = "vi"):
    return {
        "language": language,
        "subject": "Backend",
        "competency": "API Design",
        "topic": "HTTP",
        "concept": question_id,
        "difficulty": difficulty,
        "question": f"Câu hỏi {question_id}?",
        "reference_answer": "HTTP status code mô tả kết quả xử lý request.",
        "key_points": [
            "HTTP status code mô tả kết quả request",
            "Nêu được ví dụ cụ thể",
        ],
        "id": question_id,
    }


def login(client, username: str, password: str):
    return client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )


def upload(client, questions, mode="upsert"):
    return client.post(
        "/api/questions/import",
        data={"mode": mode, "default_language": ""},
        files={
            "file": (
                "test.json",
                json.dumps(questions, ensure_ascii=False).encode("utf-8"),
                "application/json",
            )
        },
    )


def submit_voice_answer(client, settings, session_id: str, answer: str):
    with database(settings.database_path) as connection:
        session = connection.execute(
            "SELECT user_id, current_question_uid FROM interview_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    transcription_id = save_transcription(
        settings.database_path,
        session_id=session_id,
        user_id=session["user_id"],
        question_uid=session["current_question_uid"],
        raw_text=answer,
        corrected_text=answer,
        model="test-model",
        runtime="cpu/int8",
        confidence=0.99,
        ambient_noise_dbfs=-50.0,
        metadata={"test": True},
    )
    return client.post(
        f"/api/interviews/{session_id}/answer",
        json={"answer": answer, "transcription_id": transcription_id},
    )


def test_login_identifies_role_and_protects_teacher_routes(client):
    assert client.get("/api/auth/me").status_code == 401

    candidate = login(client, "candidate01", "Candidate@123")
    assert candidate.status_code == 200
    assert candidate.json()["user"]["role"] == "candidate"
    assert client.get("/api/teacher/accounts").status_code == 403

    assert client.post("/api/auth/logout").status_code == 200
    teacher = login(client, "teacher", "Teacher@123")
    assert teacher.status_code == 200
    assert teacher.json()["user"]["role"] == "teacher"
    accounts = client.get("/api/teacher/accounts")
    assert accounts.status_code == 200
    assert len(accounts.json()["accounts"]) == 3


def test_practice_adapts_and_candidate_can_view_report(
    client, login_teacher, test_settings
):
    questions = [
        sample_question("Q1", "Easy"),
        sample_question("Q2", "Medium"),
        sample_question("Q3", "Hard"),
    ]
    imported = upload(client, questions)
    assert imported.status_code == 200
    assert imported.json()["imported"] == 3

    client.post("/api/auth/logout")
    assert login(client, "candidate01", "Candidate@123").status_code == 200
    started = client.post(
        "/api/interviews/start",
        json={
            "language": "vi",
            "subject": "Backend",
            "question_count": 2,
            "starting_difficulty": "Easy",
        },
    )
    assert started.status_code == 201
    session = started.json()
    assert session["candidate_name"] == "Nguyễn Văn An"
    assert session["answer_mode"] == "voice"
    assert "reference_answer" not in session["question"]
    assert session["question"]["difficulty"] == "Easy"

    first = submit_voice_answer(
        client,
        test_settings,
        session["session_id"],
        "HTTP status code mô tả kết quả request và nêu được ví dụ cụ thể.",
    )
    assert first.status_code == 200
    first_result = first.json()
    assert first_result["evaluation"]["score"] >= 80
    assert first_result["next_question"]["difficulty"] == "Medium"

    second = submit_voice_answer(
        client, test_settings, session["session_id"], "Tôi chưa biết."
    )
    assert second.status_code == 200
    assert second.json()["completed"] is True

    report = client.get(f"/api/interviews/{session['session_id']}/report")
    assert report.status_code == 200
    payload = report.json()
    assert payload["session"]["candidate_name"] == "Nguyễn Văn An"
    assert payload["session"]["interview_mode"] == "practice"
    assert len(payload["answers"]) == 2
    assert payload["answers"][0]["reference_answer"]
    assert payload["answers"][0]["evaluation"]["rubric_version"] == "key-points-v2"
    assert payload["answers"][0]["evaluation"]["point_assessments"]


def test_weak_answer_keeps_follow_up_on_same_concept(
    client, login_teacher, test_settings
):
    first = sample_question("CONCEPT_EASY", "Easy")
    first["concept"] = "HTTP status semantics"
    same_concept = sample_question("CONCEPT_MEDIUM", "Medium")
    same_concept["concept"] = "HTTP status semantics"
    different_concept = sample_question("OTHER_MEDIUM", "Medium")
    different_concept["concept"] = "Request routing"
    assert upload(client, [first, same_concept, different_concept]).status_code == 200

    client.post("/api/auth/logout")
    assert login(client, "candidate01", "Candidate@123").status_code == 200
    started = client.post(
        "/api/interviews/start",
        json={
            "language": "vi",
            "subject": "Backend",
            "question_count": 2,
            "starting_difficulty": "Easy",
        },
    ).json()
    assert started["question"]["concept"] == "HTTP status semantics"

    answered = submit_voice_answer(
        client, test_settings, started["session_id"], "Em không biết."
    )

    assert answered.status_code == 200
    assert answered.json()["next_question"]["concept"] == "HTTP status semantics"


def test_candidate_practice_history_is_saved_and_private(
    client, login_teacher, test_settings
):
    assert upload(client, [sample_question("HISTORY1", "Easy")]).status_code == 200

    client.post("/api/auth/logout")
    assert login(client, "candidate01", "Candidate@123").status_code == 200
    started = client.post(
        "/api/interviews/start",
        json={
            "language": "vi",
            "subject": "Backend",
            "question_count": 1,
            "starting_difficulty": "Easy",
        },
    )
    assert started.status_code == 201
    session_id = started.json()["session_id"]
    answered = submit_voice_answer(
        client,
        test_settings,
        session_id,
        "HTTP status code mô tả kết quả request và có ví dụ.",
    )
    assert answered.status_code == 200
    assert answered.json()["completed"] is True

    history = client.get("/api/candidate/practice-history")
    assert history.status_code == 200
    sessions = history.json()["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == session_id
    assert sessions[0]["answered_count"] == 1
    assert sessions[0]["average_score"] is not None
    assert sessions[0]["can_view_report"] is True

    client.post("/api/auth/logout")
    assert login(client, "candidate02", "Candidate@123").status_code == 200
    assert client.get("/api/candidate/practice-history").json()["sessions"] == []

    client.post("/api/auth/logout")
    assert login(client, "teacher", "Teacher@123").status_code == 200
    assert client.get("/api/candidate/practice-history").status_code == 403


def test_candidate_can_delete_only_their_own_practice_history(
    client, login_teacher, test_settings
):
    assert upload(client, [sample_question("DELETE_HISTORY", "Easy")]).status_code == 200

    client.post("/api/auth/logout")
    assert login(client, "candidate01", "Candidate@123").status_code == 200
    started = client.post(
        "/api/interviews/start",
        json={
            "language": "vi",
            "subject": "Backend",
            "question_count": 1,
            "starting_difficulty": "Easy",
        },
    )
    session_id = started.json()["session_id"]
    assert submit_voice_answer(
        client, test_settings, session_id, "HTTP status code mô tả kết quả request."
    ).status_code == 200

    client.post("/api/auth/logout")
    assert login(client, "candidate02", "Candidate@123").status_code == 200
    assert client.delete(
        f"/api/candidate/practice-history/{session_id}"
    ).status_code == 403

    client.post("/api/auth/logout")
    assert login(client, "candidate01", "Candidate@123").status_code == 200
    deleted = client.delete(f"/api/candidate/practice-history/{session_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True, "session_id": session_id}
    assert client.get("/api/candidate/practice-history").json()["sessions"] == []
    assert client.get(f"/api/interviews/{session_id}/report").status_code == 404


def test_real_interview_hides_feedback_and_teacher_sees_result(
    client, login_teacher, test_settings
):
    questions = [
        sample_question("REAL1", "Easy"),
        sample_question("REAL2", "Medium"),
        sample_question("REAL3", "Hard"),
    ]
    assert upload(client, questions).status_code == 200
    now = datetime.now(timezone.utc)
    created = client.post(
        "/api/teacher/exams",
        json={
            "title": "Backend đợt 1",
            "exam_code": "BE2026",
            "language": "vi",
            "subject": "Backend",
            "question_count": 2,
            "starting_difficulty": "Easy",
            "answer_mode": "text",
            "starts_at": (now - timedelta(minutes=2)).isoformat(),
            "ends_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert created.status_code == 201
    assert created.json()["exam"]["answer_mode"] == "voice"
    exam_id = created.json()["exam"]["exam_round_id"]

    client.post("/api/auth/logout")
    assert login(client, "candidate01", "Candidate@123").status_code == 200
    checked = client.get("/api/candidate/exams/BE2026")
    assert checked.status_code == 200
    assert checked.json()["exam"]["availability"] == "available"

    started = client.post("/api/candidate/exams/BE2026/start")
    assert started.status_code == 201
    session_id = started.json()["session_id"]
    assert started.json()["interview_mode"] == "real"
    assert started.json()["answer_mode"] == "voice"
    assert client.post(f"/api/interviews/{session_id}/finish").status_code == 409

    first = submit_voice_answer(
        client,
        test_settings,
        session_id,
        "HTTP status code mô tả kết quả request với ví dụ cụ thể.",
    )
    assert first.status_code == 200
    assert first.json()["evaluation"] is None
    assert first.json()["completed"] is False

    second = submit_voice_answer(
        client, test_settings, session_id, "Tôi chưa biết."
    )
    assert second.status_code == 200
    assert second.json()["evaluation"] is None
    assert second.json()["completed"] is True
    assert client.get(f"/api/interviews/{session_id}/report").status_code == 403
    assert client.post("/api/candidate/exams/BE2026/start").status_code == 409

    client.post("/api/auth/logout")
    assert login(client, "teacher", "Teacher@123").status_code == 200
    results = client.get(f"/api/teacher/results?exam_round_id={exam_id}")
    assert results.status_code == 200
    assert len(results.json()["results"]) == 1
    detail = client.get(f"/api/teacher/results/{session_id}")
    assert detail.status_code == 200
    assert len(detail.json()["answers"]) == 2


def test_voice_interview_uses_server_transcript_instead_of_submitted_text(
    client, login_teacher, monkeypatch
):
    assert upload(client, [sample_question("VOICE1")]).status_code == 200
    now = datetime.now(timezone.utc)
    created = client.post(
        "/api/teacher/exams",
        json={
            "title": "Kiểm tra Voice",
            "exam_code": "VOICE2026",
            "language": "vi",
            "subject": "Backend",
            "question_count": 1,
            "starting_difficulty": "Easy",
            "answer_mode": "voice",
            "starts_at": (now - timedelta(minutes=2)).isoformat(),
            "ends_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert created.status_code == 201

    client.post("/api/auth/logout")
    assert login(client, "candidate01", "Candidate@123").status_code == 200
    started = client.post("/api/candidate/exams/VOICE2026/start").json()

    def fake_transcription(_, content, *, filename, language, hotwords):
        assert content == b"voice-data"
        assert hotwords
        return {
            "text": "HTTP status code mô tả kết quả request.",
            "language": language,
            "language_probability": 0.99,
            "model": "large-v3",
            "runtime": "cuda/float16",
            "metrics": {"confidence": 0.42, "quality_score": 0.48},
            "needs_retry": False,
            "quality_reasons": [],
            "quality_warnings": ["Độ tin cậy nhận dạng thấp."],
        }

    async def no_correction(_, raw_text, **_kwargs):
        return {
            "raw_text": raw_text,
            "corrected_text": raw_text,
            "correction_applied": False,
            "correction_engine": "none",
            "correction_rejected_reason": None,
            "edit_ratio": 0.0,
        }

    monkeypatch.setattr(main_module, "transcribe_bytes", fake_transcription)
    monkeypatch.setattr(main_module, "correct_transcript", no_correction)
    transcript = client.post(
        "/api/speech/transcribe",
        data={"language": "vi", "session_id": started["session_id"]},
        files={"file": ("answer.webm", b"voice-data", "audio/webm")},
    )
    assert transcript.status_code == 200

    answered = client.post(
        f"/api/interviews/{started['session_id']}/answer",
        json={
            "answer": "Nội dung đã bị sửa ở trình duyệt.",
            "transcription_id": transcript.json()["transcription_id"],
        },
    )
    assert answered.status_code == 200

    client.post("/api/auth/logout")
    assert login(client, "teacher", "Teacher@123").status_code == 200
    report = client.get(f"/api/teacher/results/{started['session_id']}").json()
    assert report["answers"][0]["answer"] == "HTTP status code mô tả kết quả request."
    assert report["answers"][0]["evaluation"]["review_required"] is True
    assert "cảnh báo chất lượng" in report["answers"][0]["evaluation"]["feedback"]


def test_teacher_can_delete_real_result_and_candidate_cannot(
    client, login_teacher, test_settings
):
    assert upload(client, [sample_question("DELETE_REAL", "Easy")]).status_code == 200
    now = datetime.now(timezone.utc)
    created = client.post(
        "/api/teacher/exams",
        json={
            "title": "Đợt cần xóa kết quả",
            "exam_code": "DEL2026",
            "language": "vi",
            "subject": "Backend",
            "question_count": 1,
            "starting_difficulty": "Easy",
            "answer_mode": "text",
            "starts_at": (now - timedelta(minutes=2)).isoformat(),
            "ends_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert created.status_code == 201

    client.post("/api/auth/logout")
    assert login(client, "candidate01", "Candidate@123").status_code == 200
    started = client.post("/api/candidate/exams/DEL2026/start")
    session_id = started.json()["session_id"]
    assert submit_voice_answer(
        client, test_settings, session_id, "HTTP status code mô tả kết quả request."
    ).status_code == 200
    assert client.delete(f"/api/teacher/results/{session_id}").status_code == 403
    assert client.delete(
        f"/api/candidate/practice-history/{session_id}"
    ).status_code == 403

    client.post("/api/auth/logout")
    assert login(client, "teacher", "Teacher@123").status_code == 200
    deleted = client.delete(f"/api/teacher/results/{session_id}")
    assert deleted.status_code == 200
    assert client.get("/api/teacher/results").json()["results"] == []
    assert client.get(f"/api/teacher/results/{session_id}").status_code == 404

    client.post("/api/auth/logout")
    assert login(client, "candidate01", "Candidate@123").status_code == 200
    assert client.post("/api/candidate/exams/DEL2026/start").status_code == 201


def test_teacher_can_delete_exam_round_with_all_dependent_data(
    client, login_teacher, test_settings
):
    assert upload(client, [sample_question("DELETE_ROUND", "Easy")]).status_code == 200
    now = datetime.now(timezone.utc)
    created = client.post(
        "/api/teacher/exams",
        json={
            "title": "Đợt cần xóa",
            "exam_code": "ROUNDDEL",
            "language": "vi",
            "subject": "Backend",
            "question_count": 1,
            "starting_difficulty": "Easy",
            "answer_mode": "text",
            "starts_at": (now - timedelta(minutes=2)).isoformat(),
            "ends_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert created.status_code == 201
    exam_id = created.json()["exam"]["exam_round_id"]

    client.post("/api/auth/logout")
    assert login(client, "candidate01", "Candidate@123").status_code == 200
    started = client.post("/api/candidate/exams/ROUNDDEL/start")
    assert started.status_code == 201
    session_id = started.json()["session_id"]
    assert submit_voice_answer(
        client, test_settings, session_id, "HTTP status code mô tả kết quả request."
    ).status_code == 200
    assert client.delete(f"/api/teacher/exams/{exam_id}").status_code == 403

    client.post("/api/auth/logout")
    assert login(client, "teacher", "Teacher@123").status_code == 200
    assert len(client.get("/api/teacher/results").json()["results"]) == 1
    deleted = client.delete(f"/api/teacher/exams/{exam_id}")
    assert deleted.status_code == 200
    payload = deleted.json()
    assert payload["deleted"] is True
    assert payload["exam_round_id"] == exam_id
    assert payload["exam_code"] == "ROUNDDEL"
    assert payload["deleted_attempts"] == 1
    assert payload["deleted_answers"] == 1
    assert payload["deleted_question_snapshots"] == 1
    assert client.get("/api/teacher/exams").json()["exams"] == []
    assert client.get("/api/teacher/results").json()["results"] == []
    assert client.get(f"/api/teacher/results/{session_id}").status_code == 404
    assert client.delete(f"/api/teacher/exams/{exam_id}").status_code == 404

    client.post("/api/auth/logout")
    assert login(client, "candidate01", "Candidate@123").status_code == 200
    assert client.get("/api/candidate/exams/ROUNDDEL").status_code == 404


def test_invalid_question_file_is_rejected_atomically(client, login_teacher):
    questions = [sample_question("GOOD"), {"id": "BROKEN"}]
    response = upload(client, questions)
    assert response.status_code == 422
    summary = client.get("/api/questions/summary").json()
    assert summary["total"] == 0


def test_replace_only_affects_languages_present_in_file(client, login_teacher):
    assert upload(client, [sample_question("VI1", language="vi")]).status_code == 200
    assert upload(client, [sample_question("EN1", language="en")]).status_code == 200
    assert upload(
        client, [sample_question("VI2", language="vi")], mode="replace"
    ).status_code == 200

    summary = client.get("/api/questions/summary").json()
    totals = {item["language"]: item["total"] for item in summary["languages"]}
    assert totals == {"en": 1, "vi": 1}


def test_home_and_health_are_available_without_login(client):
    assert client.get("/").status_code == 200
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["database"]["users"] == 3
    assert {"installed", "ready", "model", "device", "compute_type"} <= set(
        health.json()["speech_to_text"]
    )
