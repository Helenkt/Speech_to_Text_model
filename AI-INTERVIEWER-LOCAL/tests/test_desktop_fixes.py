import asyncio
import json
import os
from types import SimpleNamespace

import httpx
import pytest

from app.database import database, init_database
from app.services import evaluator, grading_retry, runtime_readiness
from app.services.assessment_feedback import assessment_feedback
from app.services.interview_engine import _select_question, question_summary
from app.services.question_generator import _load_sources
from app.services.question_importer import import_question_bank
from app.services.speech_to_text import assess_microphone_quality
from app.services.teacher_review import review_answer, review_history
from app.services.transcript_corrector import _apply_audited_corrections, correct_transcript
from app.services.transcription_vocabulary import transcription_vocabulary
from test_teacher_strong_review import _settings, _seed_voice_answer, _save_result


@pytest.mark.parametrize("raw,terms", [
    ("A stack has push and pop operations. A stack is LIFO.", ["Stacks", "operational", "LIFO"]),
    ("Linear search costs less. Binary search needs sorting. There is no fixed cutoff.", ["Searching", "costs", "their"]),
    ("An array is not a stack. The capacity is 2TB, not 2GB.", ["Stacks", "2GB", "2TB"]),
])
def test_confident_correct_text_is_unchanged(tmp_path, raw, terms):
    result = asyncio.run(correct_transcript(_settings(tmp_path), raw, language="en", approved_terms=terms, uncertain_spans=[]))
    assert result["corrected_text"] == raw
    assert not result["correction_applied"]


def test_repeated_patches_never_rewrite_generated_words():
    suffix = " These are repeated words in a deliberately long transcript used to check stable substitutions."
    raw = "stack stack stack stack; searchable search searching." + suffix
    changes = [{"source": "stack", "target": "Stacks", "reason": "test"}] * 4
    changes += [{"source": "search", "target": "Searching", "reason": "test"}] * 3
    corrected, applied, _ = _apply_audited_corrections(raw, changes, ["Stacks", "Searching"])
    assert corrected == "Stacks Stacks Stacks Stacks; searchable Searching searching." + suffix
    assert len({(item["start"], item["end"]) for item in applied}) == len(applied) == 5
    assert _apply_audited_corrections(corrected, changes, ["Stacks", "Searching"])[0] == corrected


def test_explicit_span_changes_only_the_uncertain_occurrence():
    raw = "cục hẹn và cục hẹn là hai cụm."
    change = {"source": "cục hẹn", "target": "cuộc hẹn", "reason": "test", "start": 0, "end": 7}
    assert _apply_audited_corrections(raw, [change], ["cuộc hẹn"])[0] == "cuộc hẹn và cục hẹn là hai cụm."


@pytest.mark.parametrize("source,target", [("2TB", "2GB"), ("10", "100"), ("không", "có"), ("not", "now")])
def test_correction_cannot_change_numbers_units_or_negation(source, target):
    raw = f"A {source} system also has other technical details."
    result = _apply_audited_corrections(raw, [{"source": source, "target": target, "reason": "test"}], [target])
    assert result[0] == raw


def test_stt_hints_are_not_permission_to_rewrite_every_question_word():
    vocabulary = transcription_vocabulary({"topic": "Stacks", "question": "What operational principle governs a Stack with 2TB via HTTP?"})
    assert "operational" in vocabulary["hotwords"]
    assert set(vocabulary["approved_terms"]) == {"2TB", "HTTP"}


@pytest.mark.parametrize("peak", [0, -.1])
def test_near_full_scale_without_sustained_clipping_is_a_risk_not_a_fault(peak):
    result = assess_microphone_quality({"duration_seconds": 4, "input_level_dbfs": -16, "peak_dbfs": peak,
        "ambient_noise_dbfs": -60, "clipping_ratio": .0002, "silence_ratio": .2, "signal_to_noise_db": 40})
    assert result["ready"]
    assert result["metrics"]["peak_dbfs"] == peak
    assert not any("bị vỡ" in message for message in result["recommendations"])


def test_zero_db_noise_and_real_clipping_are_not_treated_as_missing():
    result = assess_microphone_quality({"duration_seconds": 4, "input_level_dbfs": -3, "peak_dbfs": 0,
        "ambient_noise_dbfs": 0, "clipping_ratio": .1, "silence_ratio": .1, "signal_to_noise_db": 2})
    assert result["metrics"]["ambient_noise_dbfs"] == 0
    assert not result["ready"]
    assert any("bị vỡ" in message for message in result["recommendations"])


def test_feedback_distinguishes_technical_failures_from_candidate_audio():
    evaluation = {"score_provisional": True, "point_assessments": [
        {"point": "A stack is LIFO", "status": "met", "needs_review": True, "review_reason": "model_timeout"}]}
    reasons = assessment_feedback(evaluation)["review_reasons"]
    assert reasons[0]["category"] == "system" and reasons[0]["action"] == "retry_grading"
    audio = assessment_feedback(evaluation, {"transcript_status": "needs_review"})
    assert {item["category"] for item in audio["review_reasons"]} == {"system", "audio"}


def test_unverified_evidence_cannot_become_a_final_score():
    question = {"key_points": ["A stack is LIFO"]}
    result = evaluator._coerce_llm_result({"confidence": .6, "point_assessments": [
        {"point": "A stack is LIFO", "status": "met", "evidence_quote": "Invented supporting text"}]},
        question, "test", "A stack is LIFO.")
    assert result["review_required"] and result["score_provisional"]
    assert result["point_assessments"][0]["needs_review"]


def test_test_bank_is_excluded_from_summary_selection_and_generation(client, test_settings):
    question = {"id": "CTX1", "language": "vi", "subject": "CTX01 - Phép cộng", "difficulty": "Easy",
                "question": "Một cộng một bằng mấy?", "reference_answer": "Hai", "key_points": ["Hai"]}
    import_question_bank(test_settings.database_path, json.dumps([question]).encode(), filename="cau_hoi_import.json")
    assert question_summary(test_settings.database_path)["total"] == 0
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT bank_scope,active FROM questions").fetchone()[:] == ("test", 1)
        assert _select_question(connection, language="vi", subject=None, target_rank=1, excluded_uids=[]) is None
    assert _load_sources(test_settings, language="vi", subject=question["subject"], difficulty="Easy", topic=None) == []
    init_database(test_settings.database_path)
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM questions").fetchone()[0] == 1


def test_migration_classifies_legacy_test_data_without_deleting_or_regrading(client, test_settings):
    bank = [{"id": "legacy", "language": "en", "subject": "DSA101", "question": "Stack?",
             "reference_answer": "LIFO", "key_points": ["LIFO"]}]
    import_question_bank(test_settings.database_path, json.dumps(bank).encode(), filename="course.json")
    with database(test_settings.database_path) as connection:
        connection.execute("UPDATE questions SET subject='CTX09 - So sánh điểm', source_name='cau_hoi_import.json'")
    init_database(test_settings.database_path)
    init_database(test_settings.database_path)
    assert question_summary(test_settings.database_path)["total"] == 0
    with database(test_settings.database_path) as connection:
        assert connection.execute("SELECT bank_scope FROM questions").fetchone()[0] == "test"


def test_wrong_llm_quote_is_recovered_from_the_actual_answer(test_settings, tmp_path, monkeypatch):
    test_settings.rubric_transformer_path = tmp_path
    (tmp_path / "tokenizer.json").write_text("{}")
    point = "Break-even thresholds depend on implementation"
    bad, good = "Linear search handles unsorted data", "The break-even threshold depends on implementation"
    def infer(_path, _question, text):
        probs = {"entailment": .94, "neutral": .04, "contradiction": .02} if good in text else {
            "entailment": .07, "neutral": .36, "contradiction": .57}
        return {"point_assessments": [{"probabilities": probs}]}
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", infer)
    question = {"key_points": [point]}
    result = evaluator._coerce_llm_result({"point_assessments": [{"point": point, "status": "met", "evidence_quote": bad}]},
                                         question, "test", f"{bad}. {good}.")
    checked = asyncio.run(evaluator._verify_llm_evidence(test_settings, question, result, f"{bad}. {good}."))
    assert checked["score"] == 100
    assert good in checked["point_assessments"][0]["evidence_quotes"]
    assert checked["point_assessments"][0]["evidence_verification"]["recovered_from_transcript"]


def test_teacher_manual_grade_survives_late_ai_result(tmp_path):
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    review_answer(settings, answer_id=1, teacher_id=1, action="manual", score=73, feedback="Manual while AI runs")
    _save_result(settings, 100)
    with database(settings.database_path) as connection:
        assert connection.execute("SELECT final_score,teacher_score,review_ai_score FROM interview_answers").fetchone()[:] == (73, 73, 100)
    assert len(review_history(settings, answer_id=1)) == 1


def prepare_retry(tmp_path):
    settings = _settings(tmp_path)
    question = _seed_voice_answer(settings)
    assessments = [{"point": point, "status": "met", "needs_review": True, "review_reason": "model_timeout"}
                   for point in question["key_points"]]
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_sessions SET interview_mode='practice'")
        connection.execute("UPDATE interview_answers SET assessment_json=?, score_provisional=1", (json.dumps(assessments),))
    return settings, question


def test_technical_regrade_updates_same_answer_not_question_progress(tmp_path, monkeypatch):
    settings, question = prepare_retry(tmp_path)
    async def grade(*_):
        return evaluator._compose_result(question, [{"point": point, "status": "met", "needs_review": False}
            for point in question["key_points"]], evaluator="test")
    monkeypatch.setattr(grading_retry, "evaluate_answer", grade)
    result = asyncio.run(grading_retry.retry_practice_grade(settings, "session-1", "stt-1", 2))
    assert result["evaluation"]["score"] == 100 and not result["evaluation"]["score_provisional"]
    with database(settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*),grading_retry_count,final_score FROM interview_answers").fetchone()[:] == (1, 1, 100)
        assert connection.execute("SELECT answered_count FROM interview_sessions").fetchone()[0] == 1
        event = connection.execute("SELECT previous_json,evaluation_json FROM grading_retry_events").fetchone()
        assert json.loads(event["previous_json"])["score_provisional"]
        assert json.loads(event["evaluation_json"])["score"] == 100
    with pytest.raises(ValueError):
        asyncio.run(grading_retry.retry_practice_grade(settings, "session-1", "stt-1", 2))


def test_regrade_is_owned_bounded_and_does_not_overwrite_a_teacher(tmp_path, monkeypatch):
    settings, question = prepare_retry(tmp_path)
    with pytest.raises(ValueError):
        asyncio.run(grading_retry.retry_practice_grade(settings, "session-1", "stt-1", 1))
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET grading_retry_count=2")
    assert not asyncio.run(grading_retry.retry_practice_grade(settings, "session-1", "stt-1", 2))["retryable"]
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_answers SET grading_retry_count=0")
    async def changed_while_running(*_):
        with database(settings.database_path) as connection:
            connection.execute("UPDATE interview_answers SET reviewed_at='now',teacher_score=80,final_score=80")
        return evaluator._compose_result(question, [{"point": point, "status": "met"} for point in question["key_points"]], evaluator="test")
    monkeypatch.setattr(grading_retry, "evaluate_answer", changed_while_running)
    with pytest.raises(ValueError, match="đã thay đổi"):
        asyncio.run(grading_retry.retry_practice_grade(settings, "session-1", "stt-1", 2))
    with database(settings.database_path) as connection:
        assert connection.execute("SELECT final_score FROM interview_answers").fetchone()[0] == 80


def test_warmup_is_single_owned_and_low_memory_defers_llm(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    settings.runtime_warmup = True
    settings.evaluator_mode = "auto"
    monkeypatch.setattr(runtime_readiness, "prepare_speech", lambda _: "ready")
    monkeypatch.setattr(runtime_readiness.speech, "_memory_stats_gb", lambda: (4, 2, 50))
    monkeypatch.setattr(runtime_readiness.speech, "_clear_loaded_model", lambda: None)
    async def local_inference(_self, operation, *args, **kwargs):
        return await asyncio.to_thread(operation, *args, **kwargs)
    monkeypatch.setattr(runtime_readiness.RuntimeReadiness, "run_inference", local_inference)
    requests = []
    def respond(request):
        requests.append((request.url.path, json.loads(request.content) if request.content else None))
        return httpx.Response(200, json={"models": [{"name": settings.ollama_model}]})
    actual = httpx.AsyncClient
    monkeypatch.setattr(runtime_readiness.httpx, "AsyncClient", lambda **kwargs: actual(transport=httpx.MockTransport(respond), **kwargs))
    async def exercise():
        readiness = runtime_readiness.RuntimeReadiness(settings)
        readiness.start()
        readiness.start()
        await readiness.speech_task
        assert readiness.llm_task is None
        assert readiness.snapshot()["llm"]["state"] == "released"
        assert all(path != "/api/generate" or payload.get("keep_alive") == 0 for path, payload in requests)
        await asyncio.gather(readiness.ensure_llm(), readiness.ensure_llm())
        assert readiness.snapshot()["llm"]["state"] == "ready"
        assert sum(path == "/api/generate" and "prompt" in payload for path, payload in requests) == 1
        await readiness.before_speech()
        assert readiness.snapshot()["llm"]["state"] == "released"
        assert requests[-1][1]["keep_alive"] == 0
        await readiness.stop()
    asyncio.run(exercise())


def test_desktop_controls_do_not_require_waiting_for_strong_ai(project_root):
    script = (project_root / "app/static/app.js").read_text(encoding="utf-8")
    assert "el.reviewSaveButton.disabled = state.reviewSaving;" in script
    assert "const waitingTimer = setInterval(updateWaiting, 1000)" in script
    assert "clearInterval(waitingTimer)" in script
    assert "async function retryTechnicalGrade(" in script


def test_one_isolated_worker_is_reused_and_owned(tmp_path):
    settings = _settings(tmp_path)
    settings.runtime_warmup = False
    settings.inference_worker = True
    async def exercise():
        readiness = runtime_readiness.RuntimeReadiness(settings)
        try:
            first = await readiness.run_inference(os.getpid)
            second = await readiness.run_inference(os.getpid)
            assert first == second and first != os.getpid()
        finally:
            await readiness.stop()
        assert readiness.pool is None
    asyncio.run(exercise())


def test_deterministic_grading_does_not_wait_for_a_model(tmp_path):
    settings = _settings(tmp_path)
    settings.evaluator_mode = "auto"
    question = {"language": "vi", "question": "A có 2 GB, B có 1 GB. So sánh.",
                "reference_answer": "A lớn hơn B", "key_points": ["A lớn hơn B"]}
    async def unnecessary_load():
        raise AssertionError("FactGuard must not load an LLM")
    result = asyncio.run(evaluator.evaluate_answer(settings, question, "A lớn hơn B.", ensure_model=unnecessary_load))
    assert result["score"] == 100 and not result["score_provisional"]


def test_speech_warmup_includes_vad_and_never_downloads(tmp_path, monkeypatch):
    import faster_whisper.vad
    settings = _settings(tmp_path)
    settings.whisper_download_root.mkdir()
    calls = []
    class Model:
        def transcribe(self, _audio, **kwargs):
            calls.append(kwargs["vad_filter"])
            return iter([]), None
    def load(_settings, *, local_only):
        assert local_only is True
        return Model()
    monkeypatch.setattr(runtime_readiness.speech, "_get_model", load)
    monkeypatch.setattr(runtime_readiness.speech, "_write_ready_marker", lambda _: None)
    monkeypatch.setattr(faster_whisper.vad, "get_vad_model", lambda: calls.append("vad_prepared"))
    result = runtime_readiness.prepare_speech(settings)
    assert result["state"] == "ready"
    assert calls == ["vad_prepared", True, False]


@pytest.mark.parametrize("accept_recheck", [True, False])
def test_pending_evidence_gets_one_llm_recheck_not_automatic_keyword_credit(tmp_path, monkeypatch, accept_recheck):
    settings = _settings(tmp_path)
    settings.rubric_transformer_path = tmp_path
    (tmp_path / "tokenizer.json").write_text("{}")
    point = "A base case returns directly and terminates recursion"
    answer = "A recursive function has two parts. The base case returns directly without further recursive calls."
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", lambda *_args, **_kwargs: {
        "point_assessments": [{"probabilities": {"entailment": .95, "neutral": .03, "contradiction": .02}}]})
    calls = []
    def respond(request):
        payload = json.loads(request.content)
        data = json.loads(payload["messages"][1]["content"])
        calls.append(data)
        recheck = len(calls) > 1
        item = {"point": point, "status": "met" if recheck and accept_recheck else "unresolved",
                "reason": "rechecked" if recheck else "no evidence", "evidence_ids": ["s2"] if recheck and accept_recheck else []}
        return httpx.Response(200, json={"message": {"content": json.dumps({"confidence": .9, "point_assessments": [item]})}})
    actual = httpx.AsyncClient
    monkeypatch.setattr(evaluator.httpx, "AsyncClient", lambda **kwargs: actual(transport=httpx.MockTransport(respond), **kwargs))
    result = asyncio.run(evaluator.evaluate_with_ollama(settings,
        {"question": "Explain recursion", "reference_answer": point, "key_points": [point]}, answer))
    assert len(calls) == 2 and calls[1]["evidence_recheck"]
    assert result["score"] == (100 if accept_recheck else 0)
    if accept_recheck:
        assert result["evidence_repair_passes"] == 1
        assert result["point_assessments"][0]["evidence_quote"] in answer
    else:
        assert result["score_provisional"]


def test_regrade_does_not_clear_audio_quality_warnings(tmp_path, monkeypatch):
    settings, question = prepare_retry(tmp_path)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE speech_transcriptions SET metadata_json=?", (json.dumps({"metrics": {"quality_score": .4}}),))
    async def grade(*_):
        return evaluator._compose_result(question, [{"point": point, "status": "met"} for point in question["key_points"]], evaluator="test")
    monkeypatch.setattr(grading_retry, "evaluate_answer", grade)
    result = asyncio.run(grading_retry.retry_practice_grade(settings, "session-1", "stt-1", 2))
    assert result["evaluation"]["score_provisional"]
    assert result["evaluation"]["review_reasons"][0]["category"] == "audio"
    with database(settings.database_path) as connection:
        assert connection.execute("SELECT final_score FROM interview_answers").fetchone()[0] is None
