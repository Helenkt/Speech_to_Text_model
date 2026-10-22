import asyncio
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from app.database import database
from app.services.evaluator import _compose_result, evaluate_answer
from app.services.exam_service import create_exam_round
from app.services.fact_guard import asserted_text, check_rubric_point, split_clauses
from app.services.grading_quality import digest, evaluate_predictions, export_corpus, labeling_task, rubric_hash, save_point_labels
from app.services.teacher_review import review_cache_key
from app.services.interview_engine import _row_to_question, _select_question, public_question
from app.services.question_importer import import_question_bank
from app.services.rubric_contract import attach_published_contract, publish_contract, rubric_draft, validate_contract
from app.services.stt_benchmark import build_benchmark_report, evaluate_sample
from app.services import speech_to_text


def seed_question(path):
    bank = [{"id": "DSA_TEST", "language": "en", "subject": "DSA101", "question": "What is a stack?",
             "reference_answer": "A stack is LIFO. It supports push and pop.",
             "key_points": ["A stack is LIFO", "It supports push and pop"], "difficulty": "Easy"}]
    import_question_bank(path, json.dumps(bank).encode(), filename="supplied_test.json")
    with database(path) as connection:
        return _row_to_question(connection.execute("SELECT * FROM questions LIMIT 1").fetchone())


def seed_answer(path, question):
    with database(path) as connection:
        candidate = connection.execute("SELECT user_id FROM users WHERE role = 'candidate' LIMIT 1").fetchone()[0]
        connection.execute("""INSERT INTO interview_sessions
            (session_id, user_id, candidate_name, language, subject, requested_count,
             current_difficulty_rank, evaluator_requested, created_at)
            VALUES ('quality-test', ?, 'Test', 'en', 'DSA101', 1, 1, 'rule', '2026-10-17')""", (candidate,))
        cursor = connection.execute("""INSERT INTO interview_answers
            (session_id, sequence_number, question_uid, question_json, answer_text, score,
             verdict, matched_points_json, missing_points_json, feedback, confidence, evaluator, created_at)
            VALUES ('quality-test', 1, ?, ?, 'A stack is LIFO.', 50, 'Partial', '[]', '[]', 'Test', .8, 'test', '2026-10-17')""",
            (question["uid"], json.dumps(question)))
        return cursor.lastrowid


def test_rubric_draft_is_not_teacher_approval(client, login_teacher, test_settings):
    question = seed_question(test_settings.database_path)
    response = client.get(f"/api/teacher/rubrics/{question['uid']}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["draft_status"] == "needs_teacher_review" and payload["revisions"] == []
    assert payload["warnings"]
    assert client.post(f"/api/teacher/rubrics/{question['uid']}/publish", json={
        "contract": payload["draft"], "attestation": "I checked the source, meaning and weights."}).status_code == 201
    with database(test_settings.database_path) as connection:
        selected = _select_question(connection, language="en", subject="DSA101", target_rank=1)
    assert selected["rubric_snapshot"]["approved_by"] == login_teacher["user_id"]
    assert "rubric_snapshot" not in public_question(selected)
    assert "key_points" not in public_question(selected)
    # Subsequent publishing cannot rewrite an already selected session/exam snapshot.
    old_snapshot = deepcopy(selected)
    new_contract = deepcopy(payload["draft"])
    new_contract["criteria"][0]["weight"] = 2
    with database(test_settings.database_path) as connection:
        publish_contract(connection, question, new_contract, login_teacher["user_id"], "Checked revised importance of the first point.")
        assert attach_published_contract(connection, selected) == old_snapshot
        fresh = attach_published_contract(connection, question)
    assert fresh["rubric_snapshot"]["sha256"] != old_snapshot["rubric_snapshot"]["sha256"]


def test_candidate_cannot_read_or_publish_rubrics(client, login_candidate, test_settings):
    question = seed_question(test_settings.database_path)
    assert client.get(f"/api/teacher/rubrics/{question['uid']}").status_code == 403
    assert client.get("/api/teacher/quality/corpus").status_code == 403
    assert client.get("/api/teacher/quality/triage").status_code == 403


@pytest.mark.parametrize("invalid_score", [True, False, "75"])
def test_review_api_does_not_coerce_non_numeric_values_into_grades(client, login_teacher, invalid_score):
    response = client.patch("/api/teacher/answers/999999/review",
                            json={"action": "manual", "score": invalid_score, "feedback": "Test validation"})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert response.json()["detail"][0]["loc"][-1] == "score"


def test_exam_snapshot_retains_approved_rubric_when_a_later_revision_is_published(client, login_teacher, test_settings):
    question = seed_question(test_settings.database_path)
    contract = rubric_draft(question)
    with database(test_settings.database_path) as connection:
        publish_contract(connection, question, contract, login_teacher["user_id"], "Checked atomic claims against the supplied source.")
    now = datetime.now(timezone.utc)
    exam = create_exam_round(test_settings.database_path, created_by=login_teacher["user_id"],
        title="Snapshot", exam_code="SNAP01", language="en", subject="DSA101", question_count=1,
        starting_difficulty="Easy", answer_mode="voice", starts_at=now - timedelta(minutes=1), ends_at=now + timedelta(hours=1))
    contract["criteria"][0]["weight"] = 5
    with database(test_settings.database_path) as connection:
        publish_contract(connection, question, contract, login_teacher["user_id"], "Confirmed revised weight for future sessions only.")
        selected = _select_question(connection, language="en", subject="DSA101", target_rank=1,
                                    exam_round_id=exam["exam_round_id"])
        assert selected["key_point_weights"][question["key_points"][0]] == 1
        assert attach_published_contract(connection, question)["key_point_weights"][question["key_points"][0]] == 5


def test_changed_bank_does_not_silently_reuse_an_old_rubric(client, login_teacher, test_settings):
    question = seed_question(test_settings.database_path)
    with database(test_settings.database_path) as connection:
        publish_contract(connection, question, rubric_draft(question), login_teacher["user_id"], "Checked source and all atomic claims.")
        changed = {**question, "reference_answer": "New source version"}
        assert "rubric_snapshot" not in attach_published_contract(connection, changed)


@pytest.mark.parametrize("mutation", ["stale", "source", "duplicate", "nan", "partial"])
def test_rubric_rejects_untraceable_or_invalid_criteria(client, test_settings, mutation):
    question = seed_question(test_settings.database_path)
    draft = rubric_draft(question)
    if mutation == "stale":
        draft["question_fingerprint"] = "0" * 64
    elif mutation == "source":
        draft["criteria"][0]["source_quote"] = "Knowledge from outside the supplied source"
    elif mutation == "duplicate":
        draft["criteria"][1]["id"] = "c1"
    elif mutation == "nan":
        draft["criteria"][0]["weight"] = float("nan")
    else:
        draft["criteria"][0]["credit_policy"] = "half"
    with pytest.raises(ValueError):
        validate_contract(question, draft)


def test_weighted_atomic_grading_has_no_invented_half_credit(client, test_settings):
    question = seed_question(test_settings.database_path)
    draft = rubric_draft(question)
    draft["criteria"][0]["weight"] = 3
    question.update(rubric_snapshot={"contract": draft}, key_point_weights={question["key_points"][0]: 3},
                    rubric_version="atomic-test")
    result = _compose_result(question, [
        {"point": question["key_points"][0], "status": "met"},
        {"point": question["key_points"][1], "status": "partial"}], evaluator="test")
    assert result["score"] == 75 and result["score_provisional"] is True
    assert result["point_assessments"][1]["criterion_id"] == "c2"


def test_teacher_point_labels_are_append_only_and_do_not_set_final_grade(client, login_teacher, test_settings):
    question = seed_question(test_settings.database_path)
    answer_id = seed_answer(test_settings.database_path, question)
    task = client.get(f"/api/teacher/answers/{answer_id}/labeling-task").json()
    assert "score" not in task
    body = {"transcript_source": "original", "expected_transcript_sha256": task["transcript_sha256"],
            "expected_rubric_sha256": task["rubric_sha256"], "annotation_mode": "independent",
            "labels": [{"point": question["key_points"][0], "status": "met", "evidence_quote": "A stack is LIFO"},
                       {"point": question["key_points"][1], "status": "missing", "evidence_quote": ""}]}
    for _ in range(2):
        response = client.post(f"/api/teacher/answers/{answer_id}/point-labels", json=body)
        assert response.status_code == 201 and response.json()["changes_final_grade"] is False
    corpus = client.get("/api/teacher/quality/corpus").json()
    assert len(corpus["samples"][0]["labels"]) == 1  # Latest label per human rater, history retained.
    assert corpus["samples"][0]["data_origin"] == "unverified"
    assert "candidate_name" not in json.dumps(corpus)
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM grading_labels").fetchone()[0] == 2
        assert connection.execute("SELECT final_score FROM interview_answers").fetchone()[0] is None
        connection.execute("DELETE FROM interview_answers WHERE answer_id = ?", (answer_id,))
        assert connection.execute("SELECT COUNT(*) FROM grading_labels").fetchone()[0] == 0


def test_stale_or_fabricated_evidence_labels_are_rejected(client, login_teacher, test_settings):
    question = seed_question(test_settings.database_path)
    answer_id = seed_answer(test_settings.database_path, question)
    task = labeling_task(test_settings.database_path, answer_id)
    kwargs = dict(answer_id=answer_id, teacher_id=login_teacher["user_id"], transcript_source="original",
                  expected_transcript_sha256=task["transcript_sha256"], expected_rubric_sha256=task["rubric_sha256"],
                  annotation_mode="independent", labels=[
                      {"point": question["key_points"][0], "status": "met", "evidence_quote": "invented quote"},
                      {"point": question["key_points"][1], "status": "missing", "evidence_quote": ""}])
    with pytest.raises(ValueError, match="exact transcript"):
        save_point_labels(test_settings.database_path, **kwargs)
    kwargs["expected_transcript_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="changed"):
        save_point_labels(test_settings.database_path, **kwargs)
    assert export_corpus(test_settings.database_path)["samples"] == []


def quality_case():
    question = {"key_points": ["P1", "P2"], "key_point_weights": {"P1": 3, "P2": 1}}
    answer_hash, rubric_sha = digest("Synthetic behavioral test"), rubric_hash(question)
    sample = {"sample_id": "s1", "question_id": "DSA1", "student_group": "student1", "answer_hash": answer_hash,
              "answer": "Synthetic behavioral test", "rubric_sha256": rubric_sha, "subject": "DSA101", "language": "vi", "split": "blind_test",
              "data_origin": "synthetic", "question": question,
              "labels": [{"mode": "independent", "reviewer": "teacher1", "points": [
                  {"point": "P1", "status": "contradicted", "credit": 0},
                  {"point": "P2", "status": "met", "credit": 1}]}]}
    prediction = {"sample_id": "s1", "answer_hash": answer_hash, "rubric_sha256": rubric_sha, "score": 75,
                  "point_assessments": [{"point": "P1", "status": "met"}, {"point": "P2", "status": "missing"}]}
    return sample, prediction


def test_quality_metrics_measure_false_credit_and_unfair_loss_not_only_keywords():
    sample, prediction = quality_case()
    report = evaluate_predictions([sample], [prediction])
    assert report["overall"]["mae"] == 50
    assert report["overall"]["automatic_false_credit_points"] == 1
    assert report["overall"]["automatic_unfair_loss_points"] == 1
    assert report["production_certified"] is False
    assert "insufficient_real_blind_samples" in report["validation_issues"]


def test_quality_report_detects_leakage_and_human_disagreement():
    sample, prediction = quality_case()
    second = deepcopy(sample)
    second.update(sample_id="s2", split="train")
    report = evaluate_predictions([sample, second], [prediction])
    assert "cross_split_leakage" in report["validation_issues"]
    sample["labels"].append({**deepcopy(sample["labels"][0]), "reviewer": "teacher2"})
    sample["labels"][1]["points"][0].update(status="met", credit=1)
    report = evaluate_predictions([sample], [prediction])
    assert report["overall"]["sample_count"] == 0
    assert report["exclusions"][0]["reason"] == "human_rater_disagreement"


def test_quality_report_does_not_treat_ai_acceptance_as_independent_gold():
    sample, prediction = quality_case()
    sample["labels"][0]["mode"] = "assisted"
    assert evaluate_predictions([sample], [prediction])["overall"]["sample_count"] == 0


@pytest.mark.parametrize("mutation", ["score", "hash", "point"])
def test_quality_report_fails_on_mismatched_predictions(mutation):
    sample, prediction = quality_case()
    if mutation == "score":
        prediction["score"] = 99
    elif mutation == "hash":
        prediction["answer_hash"] = "wrong"
    else:
        prediction["point_assessments"].pop()
    with pytest.raises(ValueError):
        evaluate_predictions([sample], [prediction])


def test_decimal_and_rejected_quoted_sentences_are_not_split_into_false_facts():
    assert split_clauses("A has 2.5 TB. B has 1.5 TB.") == ["A has 2.5 TB", "B has 1.5 TB"]
    assert "FIFO" not in asserted_text('"A stack is FIFO. A stack is not LIFO" is wrong. A stack is LIFO.')
    point = "Điểm là 2"
    assert check_rubric_point({"key_points": [point]}, "Điểm là 2.5.", point).status != "supported"


@pytest.mark.parametrize("prefix,point", [
    ("Em xin sửa lại: ", "Lớp là khuôn mẫu"),
    ("Tôi đính chính: ", "Hàng đợi là FIFO"),
    ("Xin sửa lại: ", "Khóa chính là duy nhất"),
    ("Correction: ", "A stack is LIFO"),
])
def test_explicit_correction_prefix_does_not_hide_a_complete_claim(prefix, point):
    assert check_rubric_point({"key_points": [point]}, prefix + point + ".", point).status == "supported"


def test_correction_prefix_never_removes_a_negation_quote_or_hypothesis():
    point = "Lớp là khuôn mẫu"
    for answer in ("Em xin sửa lại: Lớp không phải là khuôn mẫu.",
                   '"Em xin sửa lại: Lớp là khuôn mẫu" là sai.',
                   "Nếu em xin sửa lại: Lớp là khuôn mẫu."):
        assert check_rubric_point({"key_points": [point]}, answer, point).status != "supported"


def test_evaluator_records_latency_and_original_evidence_offsets(test_settings):
    question = {"language": "en", "question": "What is a stack?", "reference_answer": "A stack is LIFO",
                "key_points": ["A stack is LIFO"]}
    result = asyncio.run(evaluate_answer(test_settings, question, "A stack is LIFO."))
    assert result["grading_elapsed_seconds"] >= 0 and result["confidence_is_accuracy"] is False


def test_fact_guard_evidence_is_recovered_as_an_original_vietnamese_span(test_settings):
    point = "Lớp là khuôn mẫu"
    question = {"language": "vi", "question": "Lớp là gì?", "reference_answer": point, "key_points": [point]}
    answer = "Lớp là khuôn mẫu."
    result = asyncio.run(evaluate_answer(test_settings, question, answer))
    item = result["point_assessments"][0]
    assert item["evidence_quote"] == point and item["evidence_spans"]
    for span in item["evidence_spans"]:
        assert answer[span["start"]:span["end"]] == span["text"]


def test_stt_timings_include_failed_fallback_and_model_ready_time(test_settings, monkeypatch):
    monkeypatch.setattr(speech_to_text, "_get_model", lambda _: object())
    monkeypatch.setattr(speech_to_text, "_invalidate_active_model", lambda _: True)
    trace, calls = [], []

    def decode(_model):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("simulated fallback")
        return iter(["segment"]), "info"

    segments, info = speech_to_text._decode_with_fallback(test_settings, decode, trace)
    assert segments == ["segment"] and info == "info"
    assert [item["succeeded"] for item in trace] == [False, True]
    assert all(item["model_ready_seconds"] >= 0 and item["decode_seconds"] >= 0 for item in trace)


def test_triage_groups_unresolved_evidence_without_changing_grades(client, login_teacher, test_settings):
    question = seed_question(test_settings.database_path)
    answer_id = seed_answer(test_settings.database_path, question)
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET review_required = 1, assessment_json = ? WHERE answer_id = ?",
            (json.dumps([{"point": question["key_points"][0], "status": "unresolved", "needs_review": True}]), answer_id))
    response = client.get("/api/teacher/quality/triage?limit=1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["groups"][0]["reason"] == "unresolved_meaning"
    assert payload["groups"][0]["answer_ids"] == [answer_id]
    assert payload["changes_grades"] is False


def test_atomic_hash_does_not_trust_a_stored_digest_when_weights_changed():
    question = {"key_points": ["A stack is LIFO"], "reference_answer": "A stack is LIFO"}
    contract = {"criteria": [{"id": "c1", "claim": "A stack is LIFO", "weight": 1.0}]}
    question.update(key_point_weights={"A stack is LIFO": 1.0},
                    rubric_snapshot={"sha256": digest(contract), "contract": contract})
    original = rubric_hash(question)
    question["key_point_weights"]["A stack is LIFO"] = 3
    try:
        changed = rubric_hash(question)
    except ValueError:
        return
    assert changed != original


def test_atomic_hash_rejects_contract_tampering_and_retains_valid_published_hash(client, login_teacher, test_settings):
    question = seed_question(test_settings.database_path)
    with database(test_settings.database_path) as connection:
        published = publish_contract(connection, question, rubric_draft(question), login_teacher["user_id"],
                                     "Checked every atomic claim and its source.")
        question = attach_published_contract(connection, question)
    assert rubric_hash(question) == published["contract_sha256"]
    question["rubric_snapshot"]["contract"]["criteria"][0]["source_quote"] = "Altered source"
    with pytest.raises(ValueError, match="integrity"):
        rubric_hash(question)


def test_triage_ignores_old_strong_review_and_keeps_original_unresolved_points(client, login_teacher, test_settings):
    question = seed_question(test_settings.database_path)
    answer_id = seed_answer(test_settings.database_path, question)
    original = [{"point": question["key_points"][0], "status": "unresolved", "needs_review": True}]
    old_strong = {"score": 100, "point_assessments": [{"point": question["key_points"][0], "status": "met"}]}
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET review_required = 1, assessment_json = ?, review_ai_evaluation_json = ? WHERE answer_id = ?",
                           (json.dumps(original), json.dumps(old_strong), answer_id))
    payload = client.get("/api/teacher/quality/triage").json()
    assert any(group["reason"] == "unresolved_meaning" and group["point"] == question["key_points"][0]
               for group in payload["groups"])


def test_triage_uses_a_complete_current_strong_review(client, login_teacher, test_settings):
    question = seed_question(test_settings.database_path)
    answer_id = seed_answer(test_settings.database_path, question)
    original = [{"point": question["key_points"][0], "status": "unresolved", "needs_review": True}]
    strong = {"score": 100, "point_assessments": [{"point": point, "status": "met"} for point in question["key_points"]]}
    with database(test_settings.database_path) as connection:
        user_id = connection.execute("SELECT user_id FROM users LIMIT 1").fetchone()[0]
        connection.execute("""INSERT INTO speech_transcriptions
            (transcription_id, session_id, question_uid, user_id, raw_text, corrected_text, model, runtime, confidence,
             metadata_json, review_metadata_json, review_processed_at, created_at)
            VALUES ('triage-stt', 'quality-test', ?, ?, 'test', 'test', 'medium', 'cpu', .9, '{}', ?, 'now', 'now')""",
            (question["uid"], user_id, json.dumps({"review_cache_key": review_cache_key(test_settings)})))
        connection.execute("""UPDATE interview_answers SET review_required = 1, assessment_json = ?,
            review_ai_evaluation_json = ?, review_ai_score = 100, review_ai_at = 'now',
            transcription_id = 'triage-stt' WHERE answer_id = ?""", (json.dumps(original), json.dumps(strong), answer_id))
    payload = client.get("/api/teacher/quality/triage").json()
    assert [item["reason"] for item in payload["groups"]] == ["teacher_decision"]


@pytest.mark.parametrize("bad_json", ["{", "null", "[null, 5]"])
def test_triage_reports_malformed_assessment_without_crashing(client, login_teacher, test_settings, bad_json):
    question = seed_question(test_settings.database_path)
    answer_id = seed_answer(test_settings.database_path, question)
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET assessment_json = ? WHERE answer_id = ?", (bad_json, answer_id))
    response = client.get("/api/teacher/quality/triage")
    assert response.status_code == 200
    assert any(item["reason"] == "invalid_review_data" for item in response.json()["groups"])


def test_stt_detects_extra_numbers_reversed_numbers_and_moved_negation():
    for reference, hypothesis in [("A 2TB B 1TB", "A 1TB B 2TB"), ("A has memory", "A has 2TB memory")]:
        assert evaluate_sample({"reference": reference, "hypothesis": hypothesis})["critical_pass"] is False
    sample = {"reference": "A không dùng SQL, B dùng SQL", "hypothesis": "A dùng SQL, B không dùng SQL",
              "critical_spans": ["A không dùng SQL", "B dùng SQL"]}
    assert evaluate_sample(sample)["critical_pass"] is False
    with pytest.raises(ValueError, match="empty"):
        evaluate_sample({"reference": "", "hypothesis": ""})


def test_stt_language_average_cannot_hide_bad_english():
    samples = [{"condition": condition, "language": "vi", "reference": "từ " * 100, "hypothesis": "từ " * 100}
               for condition in ("clean", "noisy")]
    samples += [{"condition": condition, "language": "en", "reference": "stack", "hypothesis": "queue"}
                for condition in ("clean", "noisy")]
    report = build_benchmark_report(samples, required_languages=["vi", "en"])
    assert all(item["passed"] for item in report["conditions"].values())
    assert report["passed"] is False
