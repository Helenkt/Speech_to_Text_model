"""Regression coverage for the seven defects reproduced during the specialist audit."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unicodedata

import pytest

from app.services import rubric_transformer as runtime
from app.services import specialist_grader as specialist
from app.services.grading_quality import evaluate_predictions, rubric_hash
from app.services.grading_semantics import requires_semantic_audit
from tools import specialist_grading as cli
from test_specialist_grader import model_dir


QUESTION = {"question": "Explain learning.", "key_points": ["The system learns patterns from data."]}


@pytest.mark.parametrize("config", [None, [], 0, "config", {"id2label": None},
    {"id2label": []}, {"id2label": 1}, {"rubric_input_format": []}, {"rubric_input_format": {}}])
def test_malformed_config_is_validation_error(model_dir, config):
    (model_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError):
        specialist.freeze_candidate(model_dir)


@pytest.mark.parametrize("payload", [None, [], 0, "data", *[
    {"schema_version": "specialist-shadow-dataset-v1", "samples": [item]} for item in (None, 1, "sample")]])
def test_bad_dataset_shape_is_validation_error(payload):
    with pytest.raises(ValueError):
        cli.validate_samples(payload)


@pytest.mark.parametrize("variant", ["leading", "trailing", "case", "nfd", "whitespace"])
def test_canonical_duplicate_claim_rejected_before_inference(variant):
    point = "Machine learning học quy luật từ dữ liệu."
    duplicate = {"leading": " " + point, "trailing": point + " ", "case": point.upper(),
                 "nfd": unicodedata.normalize("NFD", point), "whitespace": point.replace(" ", "\t  ")}[variant]
    with pytest.raises(ValueError, match="unique"):
        specialist.validate_grading_input({**QUESTION, "key_points": [point, duplicate]}, "An answer")


def test_duplicate_policy_does_not_strip_accents_or_change_original_claims():
    points = ["The variable is ma.", "The variable is má."]
    question = {**QUESTION, "key_points": points}
    assert specialist.validate_grading_input(question, "An answer")[0] is points


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), object()])
def test_serialization_failure_has_no_partial_report(tmp_path, value):
    path = tmp_path / "report.json"
    with pytest.raises((TypeError, ValueError)):
        cli.write_new(path, {"prefix": "valid", "invalid": value})
    assert not path.exists()
    assert list(tmp_path.iterdir()) == []
    cli.write_new(path, {"retry": True})
    assert json.loads(path.read_text()) == {"retry": True}


def test_publish_failure_cleans_temporary_file(tmp_path, monkeypatch):
    def fail(*_):
        raise OSError("Simulated unavailable filesystem")
    monkeypatch.setattr(cli.os, "rename" if cli.os.name == "nt" else "link", fail)
    with pytest.raises(OSError):
        cli.write_new(tmp_path / "report.json", {"valid": True})
    assert list(tmp_path.iterdir()) == []


def test_concurrent_report_writers_do_not_overwrite_history(tmp_path):
    path = tmp_path / "report.json"
    barrier = threading.Barrier(2)
    def write(number):
        barrier.wait(timeout=5)
        try:
            cli.write_new(path, {"winner": number})
            return number
        except FileExistsError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, (1, 2)))
    winners = [number for number in results if number is not None]
    assert len(winners) == 1
    assert json.loads(path.read_text()) == {"winner": winners[0]}
    assert [p.name for p in tmp_path.iterdir()] == ["report.json"]


@pytest.mark.parametrize("field", ["answer_hash", "rubric_sha256"])
@pytest.mark.parametrize("missing", [True, False])
def test_all_corpus_hashes_are_required_before_inference(field, missing):
    sample = {"sample_id": "s1", "answer": "student answer", "question": QUESTION,
              "answer_hash": specialist.digest("student answer"), "rubric_sha256": rubric_hash(QUESTION)}
    if missing:
        sample.pop(field)
    else:
        sample[field] = "stale"
    with pytest.raises(ValueError, match="hash mismatch"):
        cli.validate_samples({"schema_version": "grading-corpus-v1", "samples": [sample]})


def test_unlabeled_corpus_cannot_skip_integrity_validation():
    sample = {"sample_id": "s1", "answer": "student answer", "question": QUESTION,
              "question_id": "q1", "student_group": "g1", "labels": [],
              "answer_hash": specialist.digest("student answer"), "rubric_sha256": "stale"}
    with pytest.raises(ValueError, match="hash mismatch"):
        evaluate_predictions([sample], [])


def test_entire_dataset_validated_before_model_construction(tmp_path, monkeypatch):
    good = {"sample_id": "good", "question": QUESTION, "answer": "An answer"}
    bad = {"sample_id": "bad", "question": QUESTION, "answer": ""}
    path = tmp_path / "data.json"
    cli.write_new(path, {"schema_version": "specialist-shadow-dataset-v1", "samples": [good, bad]})
    monkeypatch.setattr(cli, "SpecialistGrader", lambda *_: pytest.fail("Invalid data must not load a model"))
    with pytest.raises(ValueError, match=r"Sample 2 \(bad\)"):
        cli.run(SimpleNamespace(dataset=path))


def test_checkpoint_tuple_captured_before_unlock(tmp_path, monkeypatch):
    directories = [tmp_path / name for name in ("a", "b")]
    for directory in directories:
        directory.mkdir()
        (directory / "model.int8.onnx").write_bytes(b"fixture")
        (directory / "tokenizer.json").write_text("{}")
        (directory / "config.json").write_text(json.dumps({"id2label": {
            "0": "entailment", "1": "neutral", "2": "contradiction"}}))
    class Tokenizer:
        @staticmethod
        def from_file(filename):
            return SimpleNamespace(filename=filename, enable_truncation=lambda **_: None,
                                   enable_padding=lambda **_: None)
    ort = SimpleNamespace(SessionOptions=lambda: SimpleNamespace(),
        GraphOptimizationLevel=SimpleNamespace(ORT_ENABLE_ALL=99),
        InferenceSession=lambda filename, *_args, **_kwargs: SimpleNamespace(filename=filename))
    monkeypatch.setitem(sys.modules, "onnxruntime", ort)
    monkeypatch.setitem(sys.modules, "tokenizers", SimpleNamespace(Tokenizer=Tokenizer))
    import app.services.resource_policy as policy
    monkeypatch.setattr(policy, "detect_resource_policy", lambda: SimpleNamespace(cpu_threads=1))
    for name in ("_SESSION", "_TOKENIZER", "_MODEL_PATH", "_MODEL_STAMP"):
        monkeypatch.setattr(runtime, name, None)
    paused, finished = threading.Event(), threading.Event()
    class InterleavingLock:
        def __init__(self):
            self.lock = threading.Lock()
        def __enter__(self):
            self.lock.acquire()
        def __exit__(self, *_):
            self.lock.release()
            if threading.current_thread().name.endswith("_0"):
                paused.set()
                assert finished.wait(5)
    monkeypatch.setattr(runtime, "_LOCK", InterleavingLock())
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="checkpoint") as pool:
        a = pool.submit(runtime._load, directories[0])
        try:
            assert paused.wait(5)
            b = pool.submit(runtime._load, directories[1])
            b.result(timeout=5)
        finally:
            finished.set()
        session, tokenizer, _ = a.result(timeout=5)
    assert Path(session.filename).parent == directories[0]
    assert Path(tokenizer.filename).parent == directories[0]


def retractions():
    root = Path(__file__).resolve().parents[1] / "data/student_answer_dataset_v1"
    for subject in ("AI101", "DB101", "DSA101", "OOP101"):
        payload = json.loads((root / (subject + ".json")).read_text(encoding="utf-8"))
        for question in payload["questions"]:
            for answer in question["answers"]:
                if answer["style"] == "retract_correct_to_wrong":
                    yield pytest.param(answer["student_answer"], id=answer["id"])


@pytest.mark.parametrize("answer", list(retractions()))
def test_course_answer_retractions_require_scope_audit(answer):
    assert requires_semantic_audit(answer)


@pytest.mark.parametrize("answer", ["I retract that answer.", "I take that back.", "Scratch that, the opposite.",
    "Em rút lại lời giải trước."])
def test_other_explicit_retractions_require_scope_audit(answer):
    assert requires_semantic_audit(answer)


@pytest.mark.parametrize("answer", ["Thuật toán rút gọn dữ liệu.", "A queue is FIFO and a stack is LIFO."])
def test_simple_answers_do_not_create_an_extra_audit(answer):
    assert not requires_semantic_audit(answer)
