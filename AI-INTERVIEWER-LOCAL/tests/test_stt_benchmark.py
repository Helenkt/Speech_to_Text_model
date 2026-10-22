from app.services.stt_benchmark import build_benchmark_report, evaluate_sample


def test_benchmark_passes_targets_and_critical_terms():
    report = build_benchmark_report(
        [
            {
                "id": "clean",
                "condition": "clean",
                "language": "vi",
                "reference": "Hệ thống có bộ nhớ 2TB và không dùng MP4",
                "hypothesis": "Hệ thống có bộ nhớ 2TB và không dùng MP4",
                "critical_terms": ["2TB", "MP4"],
            },
            {
                "id": "noisy",
                "condition": "noisy",
                "language": "vi",
                "reference": "Mô hình không sử dụng dữ liệu ngoài",
                "hypothesis": "Mô hình không sử dụng dữ liệu ngoài",
                "critical_terms": ["dữ liệu ngoài"],
            },
        ]
    )

    assert report["passed"] is True
    assert report["conditions"]["clean"]["wer"] == 0
    assert report["conditions"]["noisy"]["wer"] == 0


def test_benchmark_fails_when_number_or_negation_changes():
    result = evaluate_sample(
        {
            "id": "critical",
            "condition": "clean",
            "language": "vi",
            "reference": "Hệ thống không có bộ nhớ 2TB",
            "hypothesis": "Hệ thống có bộ nhớ 2GB",
            "critical_terms": ["2TB"],
        }
    )

    assert result["critical_pass"] is False
    assert {item["type"] for item in result["critical_errors"]} == {
        "critical_term",
        "negation",
    }


def test_benchmark_rejects_added_negation_and_partial_number_match():
    result = evaluate_sample(
        {
            "id": "added-negation",
            "condition": "clean",
            "language": "vi",
            "reference": "Máy có 2TB bộ nhớ",
            "hypothesis": "Máy không có 20TB bộ nhớ",
            "critical_terms": ["2TB"],
        }
    )

    assert result["critical_pass"] is False
    assert {item["type"] for item in result["critical_errors"]} == {
        "critical_term",
        "negation",
    }


def test_benchmark_accepts_equivalent_vietnamese_loanword_spelling():
    result = evaluate_sample(
        {
            "id": "orthography",
            "condition": "clean",
            "language": "vi",
            "reference": "card đồ họa RTX 4060",
            "hypothesis": "cạc đồ họa RTX 4060",
            "critical_terms": ["RTX 4060"],
        }
    )

    assert result["wer"] == 0
    assert result["critical_pass"] is True
