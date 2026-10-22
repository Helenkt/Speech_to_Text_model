import json

import pytest

from tools import check_saved_audio


def test_saved_audio_check_preserves_source_files_and_does_not_use_correction(tmp_path, test_settings, monkeypatch):
    (tmp_path / "clip.wav").write_bytes(b"saved-audio")
    samples = [{"audio": "clip.wav", "reference": "A stack is LIFO", "language": "en", "condition": condition}
               for condition in ("clean", "noisy")]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"samples": samples}))
    original = manifest.read_bytes()
    monkeypatch.setattr(check_saved_audio, "transcribe_bytes", lambda *_args, **_kwargs:
        {"text": "A stack is LIFO", "model": "stub", "runtime": "test", "needs_retry": False})
    report = check_saved_audio.check_audio(test_settings, manifest, ["en"])
    assert report["passed"] is True
    assert report["llm_correction_used"] is report["writes_student_data"] is report["production_certified"] is False
    assert manifest.read_bytes() == original and (tmp_path / "clip.wav").read_bytes() == b"saved-audio"


def test_saved_audio_check_rejects_a_file_outside_its_manifest_directory(tmp_path, test_settings):
    (tmp_path / "outer.wav").write_bytes(b"outside")
    inner = tmp_path / "inner"
    inner.mkdir()
    manifest = inner / "manifest.json"
    manifest.write_text(json.dumps([{"audio": "../outer.wav"}]))
    with pytest.raises(ValueError, match="inside"):
        check_saved_audio.check_audio(test_settings, manifest, ["en"])
