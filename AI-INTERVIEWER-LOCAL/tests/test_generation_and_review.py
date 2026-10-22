import hashlib
import json
from datetime import datetime, timedelta, timezone

import app.main as main_module
from app.services.transcription_store import save_transcription


def _login(client, username: str, password: str):
    return client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )


def _source_question(question_id: str = "AI_SOURCE_001"):
    return {
        "id": question_id,
        "language": "vi",
        "subject": "AI101",
        "competency": "Hiểu học máy",
        "topic": "Machine Learning",
        "concept": "Mô hình học máy",
        "difficulty": "Easy",
        "question": "Mô hình học máy là gì?",
        "reference_answer": "Mô hình học máy học quy luật từ dữ liệu để đưa ra dự đoán.",
        "key_points": ["Học quy luật từ dữ liệu", "Đưa ra dự đoán"],
    }


def _generated_candidate():
    return {
        "id": "IGNORED_BY_SERVER",
        "language": "vi",
        "subject": "AI101",
        "competency": "Hiểu học máy",
        "topic": "Machine Learning",
        "concept": "Mô hình học máy",
        "difficulty": "Easy",
        "bloom_level": "understand",
        "learning_objective": "Giải thích vai trò của mô hình học máy",
        "question": "Hãy mô tả vai trò cơ bản của mô hình trong một hệ thống học máy?",
        "reference_answer": "Mô hình học quy luật từ dữ liệu và dùng quy luật đó để dự đoán.",
        "key_points": ["Học quy luật từ dữ liệu", "Dùng quy luật để dự đoán"],
        "source_question_ids": ["AI_SOURCE_001"],
        "source_evidence": [
            {
                "source_question_id": "AI_SOURCE_001",
                "evidence_quote": "Mô hình học máy học quy luật từ dữ liệu",
                "supported_claim": "Vai trò của mô hình được nêu trong đáp án nguồn",
            }
        ],
        "difficulty_evidence": {
            "concept_count": 1,
            "reasoning_steps": 1,
            "constraint_count": 0,
            "expected_answer_seconds": 30,
            "justification": "Câu hỏi yêu cầu giải thích một khái niệm cơ bản.",
        },
    }


def test_teacher_can_generate_review_and_approve_question(
    client, login_teacher, monkeypatch
):
    source = json.dumps([_source_question()], ensure_ascii=False).encode("utf-8")
    imported = client.post(
        "/api/questions/import",
        files={"file": ("source.json", source, "application/json")},
        data={"mode": "upsert"},
    )
    assert imported.status_code == 200

    async def fake_generate(*_args, **_kwargs):
        return _generated_candidate()

    monkeypatch.setattr(
        "app.services.question_generator._generate_with_ollama", fake_generate
    )
    response = client.post(
        "/api/teacher/questions/generate",
        json={
            "language": "vi",
            "subject": "AI101",
            "easy_count": 1,
            "medium_count": 0,
            "hard_count": 0,
        },
    )
    assert response.status_code == 201
    generated = response.json()["questions"][0]
    assert generated["status"] == "draft"
    assert generated["rubric"]["score"] == 100
    assert generated["question"]["generation_provenance"]["prompt_sha256"]
    assert generated["question"]["source_provenance"][0]["source_name"] == "source.json"
    assert len(generated["question"]["source_provenance"][0]["source_sha256"]) == 64

    approved = client.patch(
        f"/api/teacher/questions/generated/{generated['generated_id']}",
        json={"action": "approve"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert client.get("/api/questions/summary").json()["total"] == 2


def test_voice_evidence_and_teacher_score_become_final(
    client, login_teacher, test_settings, monkeypatch
):
    source = json.dumps([_source_question()], ensure_ascii=False).encode("utf-8")
    assert client.post(
        "/api/questions/import",
        files={"file": ("source.json", source, "application/json")},
        data={"mode": "upsert"},
    ).status_code == 200

    now = datetime.now(timezone.utc)
    exam = client.post(
        "/api/teacher/exams",
        json={
            "title": "Kiểm tra AI",
            "exam_code": "AIVOICE1",
            "language": "vi",
            "subject": "AI101",
            "question_count": 1,
            "starting_difficulty": "Easy",
            "answer_mode": "voice",
            "starts_at": (now - timedelta(minutes=1)).isoformat(),
            "ends_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert exam.status_code == 201

    client.post("/api/auth/logout")
    assert _login(client, "candidate01", "Candidate@123").status_code == 200
    started = client.post("/api/candidate/exams/AIVOICE1/start").json()
    voice = b"fake-webm-audio-evidence"
    transcription_id = save_transcription(
        test_settings.database_path,
        session_id=started["session_id"],
        user_id=2,
        question_uid=f"vi:{started['question']['id']}",
        raw_text="Tôi không biết",
        corrected_text="Tôi không biết",
        model="test-stt",
        runtime="cpu",
        confidence=0.95,
        ambient_noise_dbfs=-45,
        metadata={"metrics": {"quality_score": 0.95}, "quality_warnings": []},
        audio_storage_dir=test_settings.audio_storage_dir,
        audio_content=voice,
        audio_filename="answer.webm",
        audio_mime_type="audio/webm",
    )
    submitted = client.post(
        f"/api/interviews/{started['session_id']}/answer",
        json={"answer": "Tôi không biết", "transcription_id": transcription_id},
    )
    assert submitted.status_code == 200
    assert client.get(
        f"/api/teacher/transcriptions/{transcription_id}/audio"
    ).status_code == 403

    client.post("/api/auth/logout")
    assert _login(client, "teacher", "Teacher@123").status_code == 200
    queue = client.get("/api/teacher/reviews").json()["answers"]
    assert len(queue) == 1
    assert queue[0]["review_policy"] == "ai_reanalysis_required"
    assert queue[0]["can_accept_ai"] is False
    answer_id = queue[0]["answer_id"]
    provisional_report = client.get(
        f"/api/teacher/results/{started['session_id']}"
    ).json()
    assert provisional_report["answers"][0]["evaluation"]["final_score"] is None
    assert provisional_report["answers"][0]["evaluation"]["score_status"] == "proposed"

    monkeypatch.setattr(
        main_module,
        "transcribe_review_audio",
        lambda *_args, **_kwargs: {
            "text": "Tôi không biết",
            "model": "large-v3",
            "runtime": "cpu/int8",
            "metrics": {"confidence": 0.96},
            "uncertain_spans": [],
        },
    )

    async def no_review_correction(_settings, raw_text, **_kwargs):
        return {
            "raw_text": raw_text,
            "corrected_text": raw_text,
            "correction_applied": False,
            "correction_engine": "none",
            "correction_rejected_reason": None,
            "edit_ratio": 0.0,
            "corrections": [],
            "rejected_corrections": [],
        }

    async def low_review_score(_settings, question, _answer):
        return {
            "score": 0,
            "feedback": "Câu trả lời chưa thể hiện kiến thức.",
            "point_assessments": [{"point": point, "status": "missing"} for point in question["key_points"]],
        }

    monkeypatch.setattr(main_module, "correct_transcript", no_review_correction)
    monkeypatch.setattr(main_module, "evaluate_answer", low_review_score)
    strong_review = client.post(
        f"/api/teacher/answers/{answer_id}/ai-review"
    )
    assert strong_review.status_code == 200
    assert strong_review.json()["review_model"] == "large-v3"
    assert strong_review.json()["review_ai_score"] == 0
    cached_review = client.post(f"/api/teacher/answers/{answer_id}/ai-review")
    assert cached_review.status_code == 200
    assert cached_review.json()["cached"] is True
    assert cached_review.json()["can_accept_ai"] is False
    assert cached_review.json()["manual_review_required"] is True

    queue = client.get("/api/teacher/reviews").json()["answers"]
    assert queue[0]["review_policy"] == "teacher_manual_required"
    assert queue[0]["audio_required"] is False
    assert queue[0]["can_accept_ai"] is False
    rejected = client.patch(f"/api/teacher/answers/{answer_id}/review",
                            json={"action": "accept_ai"})
    assert rejected.status_code == 422
    assert "dưới trung bình" in rejected.json()["detail"]
    assert client.get(f"/api/teacher/answers/{answer_id}/reviews").json()["reviews"] == []

    audio = client.get(f"/api/teacher/transcriptions/{transcription_id}/audio")
    assert audio.status_code == 200
    assert audio.content == voice
    assert audio.headers["x-audio-sha256"] == hashlib.sha256(voice).hexdigest()
    for _ in range(3):
        assert client.get(f"/api/teacher/transcriptions/{transcription_id}/audio").content == voice

    reviewed = client.patch(
        f"/api/teacher/answers/{answer_id}/review",
        json={
            "action": "manual",
            "score": 72,
            "feedback": "Giảng viên tự chấm theo transcript và rubric.",
        },
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["final_score"] == 72
    reviewed_queue = client.get("/api/teacher/reviews").json()["answers"]
    assert len(reviewed_queue) == 1
    assert reviewed_queue[0]["final_score"] == 72
    assert reviewed_queue[0]["reviewed_at"] is not None

    reviewed_again = client.patch(
        f"/api/teacher/answers/{answer_id}/review",
        json={
            "action": "manual",
            "score": 68,
            "feedback": "Giảng viên nghe lại voice lần hai và điều chỉnh điểm.",
        },
    )
    assert reviewed_again.status_code == 200
    assert reviewed_again.json()["previous_final_score"] == 72
    assert reviewed_again.json()["final_score"] == 68

    report = client.get(f"/api/teacher/results/{started['session_id']}").json()
    assert report["summary"]["average_score"] == 68
    assert report["answers"][0]["evaluation"]["final_score"] == 68
    assert report["answers"][0]["evaluation"]["teacher_score"] == 68
    assert report["answers"][0]["voice"]["audio_available"] is True
    history = client.get(f"/api/teacher/answers/{answer_id}/reviews").json()
    assert len(history["reviews"]) == 2
    assert history["reviews"][0]["teacher_score"] == 72
    assert history["reviews"][1]["teacher_score"] == 68

    deleted = client.delete(f"/api/teacher/results/{started['session_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
