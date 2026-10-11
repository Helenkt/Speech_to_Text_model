from app.config import Settings
from app.services.transcript_corrector import (
    _acronym_corrections,
    _apply_audited_corrections,
    _glossary_corrections,
    _uncertain_language_corrections,
    _source_is_uncertain,
    _validate_correction,
)


def _settings(tmp_path):
    return Settings(
        root_dir=tmp_path,
        database_path=tmp_path / "test.db",
        static_dir=tmp_path,
        demo_data_dir=tmp_path,
        whisper_download_root=tmp_path / "models",
    )


def _run_without_await(coroutine):
    """Resolve an async fast path and fail if it tries to perform network I/O."""
    try:
        coroutine.send(None)
    except StopIteration as completed:
        return completed.value
    finally:
        coroutine.close()
    raise AssertionError("Expected the deterministic correction path to avoid awaits")


def test_acronym_finds_vietnamese_and_spaced_english_pronunciations():
    vietnamese = _acronym_corrections(
        "Hát tê tê pê là một giao thức.", ["HTTP"]
    )
    english = _acronym_corrections("An A P I is useful.", ["API"])

    assert vietnamese[0]["source"] == "Hát tê tê pê"
    assert vietnamese[0]["target"] == "HTTP"
    assert english[0]["source"] == "A P I"
    assert english[0]["target"] == "API"


def test_safe_transcript_correction_accepts_punctuation_only():
    accepted, reason, edit_ratio = _validate_correction(
        "Cấu trúc dữ liệu là cách tổ chức dữ liệu",
        "Cấu trúc dữ liệu là cách tổ chức dữ liệu.",
    )

    assert accepted is True
    assert reason == ""
    assert edit_ratio == 0


def test_transcript_correction_rejects_changed_negation_and_numbers():
    negation = _validate_correction(
        "Thuật toán này không chạy trong 10 giây.",
        "Thuật toán này chạy trong 10 giây.",
    )
    number = _validate_correction(
        "Độ phức tạp là 10.",
        "Độ phức tạp là 100.",
    )

    assert negation[0] is False
    assert "phủ định" in negation[1]
    assert number[0] is False
    assert "số liệu" in number[1]


def test_transcript_correction_rejects_changed_uncertainty():
    result = _validate_correction(
        "Theo em thuật toán này có thể chạy nhanh hơn.",
        "Theo em thuật toán này chạy nhanh hơn.",
    )

    assert result[0] is False
    assert "chắc chắn" in result[1]


def test_transcript_correction_rejects_large_rewrite():
    result = _validate_correction(
        "Em chưa nhớ rõ khái niệm này.",
        "Khái niệm này mô tả đầy đủ nguyên lý hoạt động của hệ thống.",
    )

    assert result[0] is False


def test_only_safe_audited_replacements_are_applied():
    corrected, applied, rejected = _apply_audited_corrections(
        "Ý tưởng cục hẹn có nghệ sĩ yêu thú Chí Trung.",
        [
            {"source": "cục hẹn", "target": "cuộc hẹn", "reason": "ASR"},
            {"source": "yêu thú", "target": "hài", "reason": "Rewrite"},
        ],
        ["cuộc hẹn", "Chí Trung"],
    )

    assert corrected == "Ý tưởng cuộc hẹn có nghệ sĩ yêu thú Chí Trung."
    assert len(applied) == 1
    assert len(rejected) == 1


def test_glossary_finds_phonetically_close_approved_terms():
    changes = _glossary_corrections(
        "Ý tưởng cục hẹn có nghệ sĩ Cốc Khánh và Trung Rồi.",
        ["cuộc hẹn", "Quốc Khánh", "Trung Ruồi"],
    )

    pairs = {(item["source"], item["target"]) for item in changes}
    assert ("cục hẹn", "cuộc hẹn") in pairs
    assert ("Cốc Khánh", "Quốc Khánh") in pairs
    assert ("Trung Rồi", "Trung Ruồi") in pairs


def test_glossary_does_not_fuzzy_match_existing_term_or_cross_punctuation():
    changes = _glossary_corrections(
        "Ý tưởng có Tự Long. Táo quân, thân quen cùng Quang Thắng.",
        ["Tự Long", "Quang Thắng"],
    )

    assert changes == []


def test_uncertain_glossary_accepts_a_cautious_lower_similarity_match():
    assert _glossary_corrections("những mệnh nào", ["bệnh"], []) == []

    changes = _glossary_corrections(
        "những mệnh nào", ["bệnh"], ["mệnh"]
    )

    assert changes[0]["source"] == "mệnh"
    assert changes[0]["target"] == "bệnh"
    assert _source_is_uncertain("mệnh", ["mệnh"]) is True


def test_approved_english_term_accepts_vietnamese_pronunciation():
    changes = _glossary_corrections(
        "dùng ngôn ngữ hai le vờ",
        ["high level"],
        ["hai le vờ"],
    )

    assert any(
        item["source"] == "hai le vờ" and item["target"] == "high level"
        for item in changes
    )


def test_spoken_number_and_unit_can_be_normalized_only_as_approved_term():
    changes = _acronym_corrections("dung lượng hai tê bê", ["2TB"])
    corrected, applied, rejected = _apply_audited_corrections(
        "dung lượng hai tê bê", changes, ["2TB"]
    )

    assert corrected == "dung lượng 2TB"
    assert len(applied) == 1
    assert rejected == []
    assert _validate_correction("dung lượng 2", "dung lượng 20")[0] is False


def test_common_word_is_fixed_only_inside_uncertain_span():
    assert _uncertain_language_corrections("dới 2TB", None) == []
    changes = _uncertain_language_corrections("dới 2TB", ["dới hai tê bê"])
    assert changes[0]["target"] == "với"


def test_clean_transcript_skips_llm(tmp_path):
    from app.services.transcript_corrector import correct_transcript

    result = _run_without_await(
        correct_transcript(
            _settings(tmp_path),
            "Cấu trúc dữ liệu tổ chức dữ liệu trong bộ nhớ.",
            language="vi",
            approved_terms=["cấu trúc dữ liệu"],
            uncertain_spans=[],
        )
    )

    assert result["correction_engine"] == "skipped-high-confidence"
    assert result["corrected_text"] == result["raw_text"]


def test_deterministic_term_correction_does_not_wait_for_llm(tmp_path):
    from app.services.transcript_corrector import correct_transcript

    result = _run_without_await(
        correct_transcript(
            _settings(tmp_path),
            "Giao thức hát tê tê pê được sử dụng.",
            language="vi",
            approved_terms=["HTTP"],
            uncertain_spans=["hát tê tê pê"],
        )
    )

    assert result["correction_engine"] == "deterministic-glossary"
    assert "HTTP" in result["corrected_text"]
