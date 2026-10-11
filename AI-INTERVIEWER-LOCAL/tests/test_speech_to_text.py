import json
import io
import math
import struct
import wave

import app.main as main_module
import app.services.speech_to_text as speech_module


def test_stt_setup_marks_matching_model_ready(test_settings, monkeypatch):
    class FakeModel:
        def transcribe(self, path, **_):
            with wave.open(path, "rb") as audio:
                assert audio.getframerate() == 16_000
                assert audio.getnchannels() == 1
            return iter(()), object()

    monkeypatch.setattr(speech_module, "_get_model", lambda _: FakeModel())
    monkeypatch.setattr(speech_module, "is_installed", lambda: True)

    result = speech_module.verify_stt_setup(test_settings)

    assert result["ready"] is True
    marker = test_settings.whisper_download_root / ".stt_ready.json"
    assert json.loads(marker.read_text(encoding="utf-8"))["model"] == "small"


def test_stt_marker_for_different_config_is_not_ready(test_settings, monkeypatch):
    monkeypatch.setattr(speech_module, "is_installed", lambda: True)
    marker = test_settings.whisper_download_root / ".stt_ready.json"
    marker.parent.mkdir(parents=True)
    marker.write_text(
        json.dumps({"model": "tiny", "device": "cpu", "compute_type": "int8"}),
        encoding="utf-8",
    )

    assert speech_module.stt_status(test_settings)["ready"] is False


def test_stt_status_reports_verified_fallback_profile(test_settings, monkeypatch):
    monkeypatch.setattr(speech_module, "is_installed", lambda: True)
    marker = test_settings.whisper_download_root / ".stt_ready.json"
    marker.parent.mkdir(parents=True)
    marker.write_text(
        json.dumps(
            {
                "requested": ["auto", "small", "cpu", "int8"],
                "model": "medium",
                "device": "cpu",
                "compute_type": "int8",
                "tier": "fallback_cpu",
                "reason": "GPU không khởi tạo được.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    status = speech_module.stt_status(test_settings)

    assert status["ready"] is True
    assert status["model"] == "medium"
    assert status["tier"] == "fallback_cpu"


def test_first_transcription_marks_stt_ready_without_manual_setup(
    test_settings, monkeypatch
):
    class Segment:
        text = " Câu trả lời bằng giọng nói. "

    class Info:
        language = "vi"
        language_probability = 0.98

    class FakeModel:
        def transcribe(self, path, **kwargs):
            assert path.endswith(".webm")
            assert kwargs["language"] == "vi"
            return iter([Segment()]), Info()

    monkeypatch.setattr(speech_module, "_get_model", lambda _: FakeModel())
    monkeypatch.setattr(speech_module, "is_installed", lambda: True)

    result = speech_module.transcribe_bytes(
        test_settings,
        b"fake-webm-audio",
        filename="answer.webm",
        language="vi",
    )

    assert result["text"] == "Câu trả lời bằng giọng nói."
    assert speech_module.stt_status(test_settings)["ready"] is True


def test_teacher_review_uses_large_v3_with_single_accurate_pass(
    test_settings, monkeypatch
):
    calls = []

    class Segment:
        text = " HTTP là giao thức truyền tải siêu văn bản. "
        start = 0.0
        end = 3.0
        avg_logprob = -0.05
        no_speech_prob = 0.01
        compression_ratio = 1.0
        words = []

    class Info:
        language = "vi"
        language_probability = 0.99

    class FakeModel:
        def transcribe(self, _path, **kwargs):
            calls.append(kwargs)
            return iter([Segment()]), Info()

    def fake_get_model(settings):
        assert settings.whisper_model == "large-v3"
        return FakeModel()

    monkeypatch.setattr(speech_module, "_get_model", fake_get_model)
    result = speech_module.transcribe_review_audio(
        test_settings,
        b"voice",
        filename="answer.webm",
        language="vi",
        hotwords=["HTTP"],
    )

    assert len(calls) == 1
    assert calls[0]["beam_size"] == 5
    assert result["model"] == "large-v3"
    assert result["decode_strategy"] == "forced_accurate"
    assert result["purpose"] == "teacher_review"


def test_transcription_endpoint_returns_text(client, login_candidate, monkeypatch):
    def fake_transcription(
        _, content, *, filename, language, ambient_noise_dbfs=None
    ):
        assert content == b"fake-audio"
        assert filename == "answer.webm"
        assert language == "vi"
        assert ambient_noise_dbfs is None
        return {
            "text": "Đây là câu trả lời bằng giọng nói.",
            "language": "vi",
            "language_probability": 0.99,
            "model": "small",
        }

    monkeypatch.setattr(main_module, "transcribe_bytes", fake_transcription)
    response = client.post(
        "/api/speech/transcribe",
        data={"language": "vi"},
        files={"file": ("answer.webm", b"fake-audio", "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json()["text"].startswith("Đây là")


def test_auto_runtime_prefers_validated_medium_when_cuda_is_available(
    test_settings, monkeypatch
):
    test_settings.whisper_model = "auto"
    test_settings.whisper_device = "auto"
    test_settings.whisper_compute_type = "auto"
    monkeypatch.setattr(speech_module, "_cuda_available", lambda: True)

    profile = speech_module.resolve_runtime_profile(test_settings)

    assert (profile.model, profile.device, profile.compute_type) == (
        "medium", "cuda", "float16"
    )


def test_auto_runtime_uses_low_profile_for_resource_limited_cpu(
    test_settings, monkeypatch
):
    test_settings.whisper_model = "auto"
    test_settings.whisper_device = "auto"
    test_settings.whisper_compute_type = "auto"
    hardware = speech_module.HardwareCapabilities(
        cpu_threads=4,
        total_memory_gb=8.0,
        available_memory_gb=2.0,
        memory_load_percent=75.0,
        cuda_available=False,
        cuda_device_count=0,
        cuda_vram_gb=None,
    )
    monkeypatch.setattr(speech_module, "detect_hardware", lambda: hardware)

    profile = speech_module.resolve_runtime_profile(test_settings)

    assert (profile.model, profile.device, profile.compute_type) == (
        "small", "cpu", "int8"
    )
    assert profile.tier == "low"
    assert profile.max_parallel_models == 1


def test_auto_runtime_uses_balanced_profile_for_capable_cpu(
    test_settings, monkeypatch
):
    test_settings.whisper_model = "auto"
    test_settings.whisper_device = "auto"
    test_settings.whisper_compute_type = "auto"
    hardware = speech_module.HardwareCapabilities(
        cpu_threads=12,
        total_memory_gb=16.0,
        available_memory_gb=7.0,
        memory_load_percent=56.0,
        cuda_available=False,
        cuda_device_count=0,
        cuda_vram_gb=None,
    )
    monkeypatch.setattr(speech_module, "detect_hardware", lambda: hardware)

    profile = speech_module.resolve_runtime_profile(test_settings)

    assert profile.tier == "balanced"
    assert profile.model == "medium"
    assert profile.denoise_policy == "deepfilter_on_demand"


def test_auto_runtime_keeps_medium_on_high_accuracy_gpu(
    test_settings, monkeypatch
):
    test_settings.whisper_model = "auto"
    test_settings.whisper_device = "auto"
    test_settings.whisper_compute_type = "auto"
    hardware = speech_module.HardwareCapabilities(
        cpu_threads=16,
        total_memory_gb=32.0,
        available_memory_gb=20.0,
        memory_load_percent=37.0,
        cuda_available=True,
        cuda_device_count=1,
        cuda_vram_gb=12.0,
    )
    monkeypatch.setattr(speech_module, "detect_hardware", lambda: hardware)

    profile = speech_module.resolve_runtime_profile(test_settings)

    assert profile.tier == "high_accuracy"
    assert profile.model == "medium"
    assert profile.device == "cuda"
    assert profile.compute_type == "float16"
    assert profile.max_parallel_models == 1


def test_forced_gpu_profile_is_downgraded_when_cuda_is_missing(
    test_settings, monkeypatch
):
    test_settings.runtime_profile = "performance"
    test_settings.whisper_model = "auto"
    test_settings.whisper_device = "auto"
    test_settings.whisper_compute_type = "auto"
    hardware = speech_module.HardwareCapabilities(
        cpu_threads=8,
        total_memory_gb=16.0,
        available_memory_gb=6.0,
        memory_load_percent=62.0,
        cuda_available=False,
        cuda_device_count=0,
        cuda_vram_gb=None,
    )
    monkeypatch.setattr(speech_module, "detect_hardware", lambda: hardware)

    profile = speech_module.resolve_runtime_profile(test_settings)

    assert profile.tier == "balanced"
    assert profile.device == "cpu"


def test_stt_status_exposes_hardware_and_memory_policy(test_settings, monkeypatch):
    hardware = speech_module.HardwareCapabilities(
        cpu_threads=4,
        total_memory_gb=8.0,
        available_memory_gb=2.0,
        memory_load_percent=75.0,
        cuda_available=False,
        cuda_device_count=0,
        cuda_vram_gb=None,
    )
    monkeypatch.setattr(speech_module, "detect_hardware", lambda: hardware)
    monkeypatch.setattr(speech_module, "is_installed", lambda: True)

    status = speech_module.stt_status(test_settings)

    assert status["cpu_threads"] == 4
    assert status["available_memory_gb"] == 2.0
    assert status["cuda_available"] is False
    assert status["features"]["memory"]["max_parallel_models"] == 1


def test_low_confidence_transcript_with_content_is_sent_to_correction(test_settings, monkeypatch):
    class Segment:
        text = " câu trả lời không rõ "
        start = 0.0
        end = 1.0
        avg_logprob = -2.0
        no_speech_prob = 0.1
        compression_ratio = 1.0

    class Info:
        language = "vi"
        language_probability = 0.9

    class FakeModel:
        def transcribe(self, *_args, **_kwargs):
            return iter([Segment()]), Info()

    monkeypatch.setattr(speech_module, "_get_model", lambda _: FakeModel())
    result = speech_module.transcribe_bytes(
        test_settings, b"audio", filename="answer.webm", language="vi"
    )

    assert result["needs_retry"] is False
    assert result["metrics"]["confidence"] < test_settings.stt_min_confidence
    assert result["quality_warnings"]


def test_short_uncertain_segment_does_not_reject_long_clear_recording(
    test_settings, monkeypatch
):
    class Segment:
        compression_ratio = 1.0

        def __init__(self, text, start, end, no_speech_prob):
            self.text = text
            self.start = start
            self.end = end
            self.avg_logprob = -0.1
            self.no_speech_prob = no_speech_prob

    class Info:
        language = "vi"
        language_probability = 0.99

    class FakeModel:
        def transcribe(self, *_args, **_kwargs):
            return iter(
                [
                    Segment(" Nội dung chính rõ ràng. ", 0.0, 20.0, 0.05),
                    Segment(" Đoạn kết. ", 20.0, 20.5, 0.95),
                ]
            ), Info()

    monkeypatch.setattr(speech_module, "_get_model", lambda _: FakeModel())
    result = speech_module.transcribe_bytes(
        test_settings, b"audio", filename="answer.webm", language="vi"
    )

    assert result["metrics"]["maximum_no_speech_probability"] > 0.75
    assert result["metrics"]["average_no_speech_probability"] < 0.1
    assert result["needs_retry"] is False


def test_word_confidence_exposes_only_uncertain_spans(test_settings, monkeypatch):
    class Word:
        def __init__(self, text, probability, start, end):
            self.word = text
            self.probability = probability
            self.start = start
            self.end = end

    class Segment:
        text = " bệnh nào thường gặp "
        start = 0.0
        end = 2.0
        avg_logprob = -0.2
        no_speech_prob = 0.05
        compression_ratio = 1.0
        words = [
            Word("bệnh", 0.42, 0.0, 0.5),
            Word("nào", 0.95, 0.5, 0.9),
            Word("thường", 0.51, 0.9, 1.4),
            Word("gặp", 0.93, 1.4, 2.0),
        ]

    class Info:
        language = "vi"
        language_probability = 0.99

    class FakeModel:
        def transcribe(self, *_args, **kwargs):
            assert kwargs["word_timestamps"] is True
            return iter([Segment()]), Info()

    monkeypatch.setattr(speech_module, "_get_model", lambda _: FakeModel())
    result = speech_module.transcribe_bytes(
        test_settings, b"audio", filename="answer.webm", language="vi"
    )

    assert result["uncertain_spans"] == ["bệnh"]
    assert result["metrics"]["uncertain_word_count"] == 1
    assert result["metrics"]["word_confidence_threshold"] == 0.45
    assert result["segments"][0]["words"][0]["confidence"] == 0.42


def test_low_segment_score_is_accepted_when_most_words_are_confident(
    test_settings, monkeypatch
):
    class Word:
        word = "nội"
        probability = 0.92
        start = 0.0
        end = 1.0

    class Segment:
        text = " nội dung trả lời rõ ràng "
        start = 0.0
        end = 4.0
        avg_logprob = -1.0
        no_speech_prob = 0.05
        compression_ratio = 1.0
        words = [Word(), Word(), Word(), Word()]

    class Info:
        language = "vi"
        language_probability = 0.99

    class FakeModel:
        def transcribe(self, *_args, **_kwargs):
            return iter([Segment()]), Info()

    monkeypatch.setattr(speech_module, "_get_model", lambda _: FakeModel())
    result = speech_module.transcribe_bytes(
        test_settings, b"audio", filename="answer.webm", language="vi"
    )

    assert result["metrics"]["confidence"] < test_settings.stt_min_confidence
    assert result["metrics"]["uncertain_word_ratio"] == 0
    assert result["needs_retry"] is False


def test_noisy_environment_passes_when_words_are_confident():
    result = speech_module.assess_transcription_quality(
        {
            "text": "Câu trả lời có vẻ rõ theo mô hình.",
            "metrics": {
                "confidence": 0.91,
                "speech_duration_seconds": 4.0,
                "average_no_speech_probability": 0.02,
                "maximum_compression_ratio": 1.0,
                "word_count": 7,
                "uncertain_word_ratio": 0.0,
            },
        },
        minimum_confidence=0.48,
        ambient_noise_dbfs=-24.0,
        maximum_ambient_noise_dbfs=-32.0,
    )

    assert result["needs_retry"] is False
    assert result["metrics"]["noisy_environment"] is True
    assert result["metrics"]["quality_gate_version"] == "stt-quality-v3"


def test_noisy_environment_warns_when_recognition_is_uncertain():
    result = speech_module.assess_transcription_quality(
        {
            "text": "Câu trả lời nhận dạng chưa rõ.",
            "metrics": {
                "confidence": 0.54,
                "speech_duration_seconds": 4.0,
                "average_no_speech_probability": 0.12,
                "maximum_compression_ratio": 1.0,
                "word_count": 6,
                "uncertain_word_ratio": 0.34,
            },
        },
        minimum_confidence=0.48,
        ambient_noise_dbfs=-24.0,
        maximum_ambient_noise_dbfs=-28.0,
    )

    assert result["needs_retry"] is False
    assert "Tiếng nền" in result["quality_warnings"][-1]


def test_adaptive_vad_becomes_stricter_as_noise_increases():
    quiet = speech_module.adaptive_vad_profile(-50.0)
    noisy = speech_module.adaptive_vad_profile(-18.0)

    assert quiet["name"] == "quiet"
    assert noisy["name"] == "very_noisy"
    assert noisy["threshold"] > quiet["threshold"]
    assert noisy["speech_pad_ms"] > quiet["speech_pad_ms"]
    assert noisy["min_silence_duration_ms"] < quiet["min_silence_duration_ms"]


def test_transcription_passes_adaptive_vad_to_faster_whisper(test_settings, monkeypatch):
    captured = {}

    class Segment:
        text = " câu trả lời rõ ràng "
        start = 0.0
        end = 2.0
        avg_logprob = -0.1
        no_speech_prob = 0.02
        compression_ratio = 1.0
        words = []

    class Info:
        language = "vi"
        language_probability = 0.99

    class FakeModel:
        def transcribe(self, *_args, **kwargs):
            captured.update(kwargs)
            return iter([Segment()]), Info()

    monkeypatch.setattr(speech_module, "_get_model", lambda _: FakeModel())
    result = speech_module.transcribe_bytes(
        test_settings,
        b"audio",
        filename="answer.webm",
        language="vi",
        ambient_noise_dbfs=-18.0,
    )

    assert captured["vad_parameters"]["threshold"] == 0.72
    assert captured["condition_on_previous_text"] is False
    assert result["metrics"]["vad_profile"]["name"] == "very_noisy"


def test_quiet_environment_passes_quality_gate():
    result = speech_module.assess_transcription_quality(
        {
            "text": "Câu trả lời rõ ràng và đủ dài.",
            "metrics": {
                "confidence": 0.72,
                "speech_duration_seconds": 3.0,
                "average_no_speech_probability": 0.05,
                "maximum_compression_ratio": 1.0,
                "word_count": 7,
                "uncertain_word_ratio": 0.1,
            },
        },
        minimum_confidence=0.48,
        ambient_noise_dbfs=-48.0,
        maximum_ambient_noise_dbfs=-32.0,
    )

    assert result["needs_retry"] is False
    assert result["metrics"]["quality_score"] >= 0.7


def test_microphone_quality_reports_noise_and_recommendations():
    result = speech_module.assess_microphone_quality(
        {
            "duration_seconds": 3.0,
            "input_level_dbfs": -24.0,
            "peak_dbfs": -5.0,
            "ambient_noise_dbfs": -18.0,
            "clipping_ratio": 0.0,
            "silence_ratio": 0.12,
            "signal_to_noise_db": 6.0,
        },
        maximum_ambient_noise_dbfs=-28.0,
    )

    assert result["ready"] is False
    assert result["status"] == "poor"
    assert result["noise"]["level"] == "very_noisy"
    assert result["recommendations"]


def test_analyze_microphone_sample_reads_real_wav():
    output = io.BytesIO()
    sample_rate = 16_000
    samples = [0] * sample_rate
    samples.extend(
        int(0.2 * 32767 * math.sin(2 * math.pi * 440 * index / sample_rate))
        for index in range(sample_rate * 2)
    )
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    result = speech_module.analyze_microphone_sample(
        output.getvalue(),
        filename="microphone-check.wav",
        maximum_ambient_noise_dbfs=-28.0,
    )

    assert result["ready"] is True
    assert result["metrics"]["duration_seconds"] == 3.0
    assert result["noise"]["level"] == "quiet"
    assert result["microphone_score_percent"] >= 80


def test_microphone_analysis_does_not_trust_client_noise_value():
    output = io.BytesIO()
    sample_rate = 16_000
    samples = [int(0.15 * 32767)] * (sample_rate * 3)
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    result = speech_module.analyze_microphone_sample(
        output.getvalue(),
        filename="microphone-check.wav",
        ambient_noise_dbfs=-80.0,
        maximum_ambient_noise_dbfs=-28.0,
    )

    assert result["metrics"]["ambient_noise_dbfs"] > -20
    assert result["metrics"]["client_ambient_noise_dbfs"] == -80.0
    assert result["metrics"]["noise_measurement_source"] == "backend_audio"


def test_recording_report_exposes_ui_ready_percentages():
    report = speech_module.build_recording_report(
        {
            "confidence": 0.82,
            "quality_score": 0.76,
            "uncertain_word_ratio": 0.1,
            "ambient_noise_dbfs": -36.0,
        }
    )

    assert report["recognition_confidence_percent"] == 82
    assert report["recording_quality_percent"] == 76
    assert report["estimated_recognition_accuracy_percent"] == 83
    assert report["noise"]["level"] == "moderate"


def test_microphone_check_endpoint_returns_backend_assessment(
    client, login_candidate, monkeypatch
):
    def fake_analysis(content, **kwargs):
        assert content == b"microphone-audio"
        assert kwargs["filename"] == "mic.webm"
        assert kwargs["ambient_noise_dbfs"] == -42.0
        return {
            "status": "good",
            "status_label": "Mic hoạt động tốt",
            "ready": True,
            "microphone_score_percent": 92,
            "noise": {"dbfs": -42.0, "level": "moderate", "label": "Trung bình"},
            "metrics": {"duration_seconds": 3.0},
            "recommendations": [],
        }

    monkeypatch.setattr(main_module, "analyze_microphone_sample", fake_analysis)
    monkeypatch.setattr(
        main_module,
        "microphone_check_session",
        lambda *_args, **_kwargs: {"session_id": "session-1", "result": {}},
    )
    monkeypatch.setattr(
        main_module,
        "save_microphone_check",
        lambda *_args, result, **_kwargs: {
            **result,
            "session_id": "session-1",
            "already_checked": False,
        },
    )
    response = client.post(
        "/api/speech/microphone-check",
        data={"session_id": "session-1", "ambient_noise_dbfs": "-42"},
        files={"file": ("mic.webm", b"microphone-audio", "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json()["microphone_score_percent"] == 92
    assert response.json()["ready"] is True
