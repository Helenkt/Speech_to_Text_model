"""Controlled contracts for imported safeguards; not a model accuracy benchmark."""
import asyncio
import json
import pickle
import sys
from types import SimpleNamespace

import httpx
import pytest

from app.services import evaluator, runtime_readiness, speech_to_text as speech
from app.services.grading_semantics import requires_semantic_audit
from app.services.llm_response import ModelResponseError, decode_model_json, validate_point_decisions
from app.services.resource_policy import canonical_ollama_name


QUESTION = {"question": "Explain stack and queue order.", "language": "en",
            "reference_answer": "A stack uses LIFO; a queue uses FIFO.",
            "key_points": ["A stack uses LIFO", "A queue uses FIFO"]}


@pytest.fixture(autouse=True)
def no_real_model_in_contract_tests(test_settings, tmp_path):
    test_settings.rubric_transformer_path = tmp_path / "not_installed"


@pytest.mark.parametrize("text", [
    '{"point_assessments": [], "point_assessments": []}',
    '{"confidence": NaN}', '{"confidence": Infinity}',
    'Explanation before {"point_assessments": []}',
    '```json\n{}\n``` and another {}',
])
def test_decoder_rejects_ambiguous_or_nonfinite_documents(text):
    with pytest.raises(ModelResponseError):
        decode_model_json(text)


def test_decoder_accepts_a_whole_fence_not_a_selected_fragment():
    assert decode_model_json('\ufeff```json\n{"value": 1}\n```') == {"value": 1}


@pytest.mark.parametrize("items", [
    [], [{"point": "P", "status": "missing", "evidence_ids": []}] * 2,
    [{"point": "P", "status": "met", "evidence_ids": ["invented"]}],
    [{"point": "P", "status": "met", "evidence_ids": [["s1"]]}],
    [{"point": "P", "status": "met", "evidence_ids": ["s1", "s1"]}],
    [{"point": "P", "status": "missing", "evidence_ids": ["s1"]}],
    [{"point": "P", "status": "wrong_label", "evidence_ids": []}],
])
def test_wire_decisions_require_complete_unique_points_and_real_evidence(items):
    with pytest.raises(ModelResponseError):
        validate_point_decisions({"point_assessments": items}, ["P"], {"s1": "Student assertion"})


def test_model_cannot_supply_its_own_quote_or_score():
    data = validate_point_decisions({"score": 100, "confidence": .99, "point_assessments": [
        {"point": "P", "status": "met", "evidence_ids": ["s1"], "evidence_quote": "Invented answer"}]},
        ["P"], {"s1": "Actual student words"})
    assert "score" not in data
    assert data["point_assessments"][0]["evidence_quote"] == "Actual student words"


@pytest.mark.parametrize("answer", [
    "Không phải stack không dùng LIFO.",
    "Stack dùng FIFO. Em xin sửa lại: stack dùng LIFO.",
    "It is not true that a stack does not use LIFO.",
    'The claim "a queue uses LIFO" is wrong. A queue uses FIFO.',
])
def test_only_complex_assertion_scope_requests_an_audit(answer):
    assert requires_semantic_audit(answer)


@pytest.mark.parametrize("answer", [
    "A stack uses LIFO. A queue uses FIFO.",
    "Khóa chính không được trùng lặp.", "A queue does not use LIFO.",
    "Gradient descent minimizes the loss function.",
])
def test_ordinary_answers_do_not_pay_for_a_second_llm_pass(answer):
    assert not requires_semantic_audit(answer)


def mock_grader(monkeypatch, labels, captured):
    def respond(request):
        payload = json.loads(request.content)
        data = json.loads(payload["messages"][1]["content"])
        captured.append(payload)
        selected = labels[min(len(captured) - 1, len(labels) - 1)]
        if selected == "invalid":
            return httpx.Response(200, json={"message": {"content": "invalid"}})
        statements = data["candidate_statements"]
        items = [{"point": point, "status": status, "reason": "Controlled decision",
                  "evidence_ids": [statements[-1]["id"]] if status != "missing" else []}
                 for point, status in zip(data["rubric_points"], selected, strict=True)]
        return httpx.Response(200, json={"done": True, "message": {
            "content": json.dumps({"confidence": .95, "point_assessments": items})}})

    actual = httpx.AsyncClient
    monkeypatch.setattr(evaluator.httpx, "AsyncClient", lambda **kwargs:
                        actual(transport=httpx.MockTransport(respond), **kwargs))


def test_ordinary_answer_needs_one_request_and_backend_applies_weights(test_settings, monkeypatch):
    captured = []
    mock_grader(monkeypatch, [["met", "missing"]], captured)
    question = {**QUESTION, "key_point_weights": dict(zip(QUESTION["key_points"], [3, 1]))}
    result = asyncio.run(evaluator.evaluate_with_ollama(test_settings, question, "A stack uses LIFO."))
    assert len(captured) == 1 and result["score"] == 75


@pytest.mark.parametrize("second,expected,pending", [
    (["met", "contradicted"], 50, False),
    (["met", "met"], 50, True),
    ("invalid", 0, True),
])
def test_difficult_answers_use_independent_audit_and_never_hide_disagreement(
        test_settings, monkeypatch, second, expected, pending):
    captured = []
    mock_grader(monkeypatch, [["met", "contradicted"], second], captured)
    answer = "Correction: a stack uses LIFO. A queue also uses LIFO."
    result = asyncio.run(evaluator.evaluate_with_ollama(test_settings, QUESTION, answer))
    assert len(captured) == 2
    assert result["score"] == expected and result["score_provisional"] is pending
    user = json.loads(captured[1]["messages"][1]["content"])
    assert user["student_answer"] == answer
    assert "point_assessments" not in user
    assert result["point_assessments"][0]["semantic_audit_status"] == (
        "unavailable" if second == "invalid" else "agreed")


def test_explicit_correction_bypasses_premature_fact_and_transformer_credit(test_settings, monkeypatch):
    test_settings.evaluator_mode = "auto"
    point = "Lớp là khuôn mẫu"
    question = {"question": "Lớp là gì?", "reference_answer": point, "key_points": [point]}
    calls = []
    mock_grader(monkeypatch, [["met"], ["met"]], calls)
    monkeypatch.setattr(evaluator, "check_rubric_point", lambda *_:
                        pytest.fail("A correction needs whole-answer semantic evaluation"))
    monkeypatch.setattr(evaluator, "evaluate_with_transformer", lambda *_, **__:
                        pytest.fail("Do not finalize this from the fast classifier alone"))
    result = asyncio.run(evaluator.evaluate_answer(test_settings, question,
        "Lớp không phải là khuôn mẫu. Em xin sửa lại: lớp là khuôn mẫu."))
    assert result["score"] == 100 and not result["score_provisional"] and len(calls) == 2


def test_audit_shares_the_existing_time_budget(test_settings, monkeypatch):
    captured = []
    mock_grader(monkeypatch, [["met", "met"]], captured)
    ticks = iter([0., 0., 21.])
    monkeypatch.setattr(evaluator, "perf_counter", lambda: next(ticks))
    result = asyncio.run(evaluator.evaluate_with_ollama(test_settings, QUESTION,
        "Correction: a stack uses LIFO. A queue uses FIFO."))
    assert len(captured) == 1
    assert result["score_provisional"]
    assert all(p["semantic_audit_status"] == "unavailable" for p in result["point_assessments"])


def test_model_failure_never_generates_keyword_credit(test_settings, monkeypatch):
    test_settings.evaluator_mode = "ollama"
    monkeypatch.setattr(evaluator, "check_rubric_point", lambda *_: SimpleNamespace(status="unknown"))
    async def unavailable(*_, **__):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr(evaluator, "evaluate_with_ollama", unavailable)
    result = asyncio.run(evaluator.evaluate_answer(test_settings, QUESTION,
        "A stack uses LIFO. A queue uses FIFO."))
    assert result["score_provisional"] and not result["matched_points"]
    assert all(p["status"] == "unresolved" for p in result["point_assessments"])


@pytest.mark.parametrize("exc", [MemoryError(), RuntimeError("mkl_malloc: failed to allocate memory"),
    RuntimeError("The paging file is too small"), RuntimeError("DefaultCPUAllocator: can't allocate"),
    RuntimeError("bad allocation"), RuntimeError("out of memory")])
def test_host_memory_errors_stop_without_loading_more_profiles(exc):
    assert speech._host_memory_error(exc)


def test_cuda_vram_failure_can_still_fall_back_but_other_errors_are_not_oom():
    assert not speech._host_memory_error(RuntimeError("CUDA out of memory"))
    assert not speech._host_memory_error(RuntimeError("invalid audio file"))


def test_decode_oom_releases_weights_and_stops_retrying(test_settings, monkeypatch):
    calls = []
    monkeypatch.setattr(speech, "_get_model", lambda _: object())
    monkeypatch.setattr(speech, "_clear_loaded_model", lambda: calls.append("release"))
    monkeypatch.setattr(speech, "_memory_stats_gb", lambda: (8, .3, 96))
    def decode(_):
        calls.append("decode")
        raise MemoryError("mkl_malloc")
    with pytest.raises(speech.SpeechToTextMemoryError):
        speech._decode_with_fallback(test_settings, decode)
    assert calls == ["decode", "release"]
    error = speech.SpeechToTextMemoryError("retry saved audio")
    assert isinstance(pickle.loads(pickle.dumps(error)), speech.SpeechToTextMemoryError)


def test_constructor_oom_never_loads_a_second_model(test_settings, monkeypatch):
    calls = []
    monkeypatch.setattr(speech, "_MODEL", None)
    monkeypatch.setattr(speech, "_FAILED_PROFILE_KEYS", set())
    monkeypatch.setattr(speech, "is_installed", lambda: True)
    monkeypatch.setattr(speech, "_configure_local_cuda_runtime", lambda: None)
    monkeypatch.setattr(speech, "_memory_stats_gb", lambda: (8, .2, 97))
    def model(*_, **__):
        calls.append("load")
        raise MemoryError("failed to allocate memory")
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=model))
    with pytest.raises(speech.SpeechToTextMemoryError):
        speech._get_model(test_settings)
    assert calls == ["load"]


def test_next_recording_can_retry_a_failed_profile_and_keeps_stt_loaded(test_settings, monkeypatch):
    monkeypatch.setattr(speech, "_FAILED_PROFILE_KEYS", {("small", "cpu", "int8")})
    releases = []
    def transcribe(*_, **__):
        assert speech._FAILED_PROFILE_KEYS == set()
        return {"text": "answer"}
    monkeypatch.setattr(speech, "_transcribe_bytes_locked", transcribe)
    monkeypatch.setattr(speech, "_clear_loaded_model", lambda: releases.append(True))
    assert speech.transcribe_bytes(test_settings, b"voice", filename="voice.wav")["text"] == "answer"
    assert not releases


def test_unload_normalizes_latest_without_unloading_other_models(test_settings, monkeypatch):
    test_settings.ollama_model = "qwen2.5"
    requests = []
    def respond(request):
        if request.method == "GET":
            return httpx.Response(200, json={"models": [
                {"name": "qwen2.5:latest"}, {"name": "unrelated:latest"}]})
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={})
    actual = httpx.AsyncClient
    monkeypatch.setattr(runtime_readiness.httpx, "AsyncClient", lambda **kwargs:
                        actual(transport=httpx.MockTransport(respond), **kwargs))
    readiness = runtime_readiness.RuntimeReadiness(test_settings)
    asyncio.run(readiness._unload_owned_llms())
    assert [p["model"] for p in requests] == ["qwen2.5:latest"]
    assert requests[0]["keep_alive"] == 0
    assert canonical_ollama_name("localhost:11434/team/model") == "localhost:11434/team/model:latest"
