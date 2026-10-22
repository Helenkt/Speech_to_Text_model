from __future__ import annotations

import re
import math
import unicodedata
from collections import Counter
from typing import Any, Iterable


NEGATIONS = {
    "vi": {"không", "chưa", "chẳng", "đừng", "không thể"},
    "en": {"no", "not", "never", "without", "cannot", "can't", "don't"},
}

# These are pronunciation-equivalent spellings, not semantic corrections. Keeping
# them canonical prevents WER from penalizing accepted Vietnamese loanword forms.
ORTHOGRAPHIC_EQUIVALENTS = {
    "card": "cạc",
}


def normalize_text(value: str) -> str:
    tokens = re.findall(
        r"\d+(?:[.,]\d+)?(?:[a-zA-Z]+)?|[^\W\d_]+(?:['’][^\W\d_]+)?",
        unicodedata.normalize("NFC", str(value or "")).casefold(),
        flags=re.UNICODE,
    )
    normalized = [token.replace("’", "'") for token in tokens]
    return " ".join(ORTHOGRAPHIC_EQUIVALENTS.get(token, token) for token in normalized)


def _phrase_count(tokens: list[str], phrase: str) -> int:
    phrase_tokens = normalize_text(phrase).split()
    width = len(phrase_tokens)
    if not width:
        return 0
    return sum(
        tokens[index : index + width] == phrase_tokens
        for index in range(len(tokens) - width + 1)
    )


def _distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, ref_item in enumerate(reference, start=1):
        current = [row]
        for column, hyp_item in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (ref_item != hyp_item),
                )
            )
        previous = current
    return previous[-1]


def _critical_errors(
    reference: str,
    hypothesis: str,
    *,
    language: str,
    critical_terms: Iterable[str],
) -> list[dict[str, Any]]:
    normalized_reference = normalize_text(reference)
    normalized_hypothesis = normalize_text(hypothesis)
    reference_tokens = normalized_reference.split()
    hypothesis_tokens = normalized_hypothesis.split()
    errors: list[dict[str, Any]] = []

    required = [normalize_text(term) for term in critical_terms if normalize_text(term)]
    required.extend(token for token in reference_tokens if any(char.isdigit() for char in token))
    for term in dict.fromkeys(required):
        if _phrase_count(reference_tokens, term) > _phrase_count(hypothesis_tokens, term):
            errors.append({"type": "critical_term", "value": term})

    reference_numbers = [token for token in reference_tokens if any(char.isdigit() for char in token)]
    hypothesis_numbers = [token for token in hypothesis_tokens if any(char.isdigit() for char in token)]
    for term, count in (Counter(hypothesis_numbers) - Counter(reference_numbers)).items():
        errors.append({"type": "critical_term", "value": term, "change": "inserted_number", "count": count})
    if reference_numbers != hypothesis_numbers and Counter(reference_numbers) == Counter(hypothesis_numbers):
        errors.append({"type": "number_order", "expected": reference_numbers, "actual": hypothesis_numbers})

    negations = NEGATIONS.get(language, NEGATIONS["en"])
    reference_negations = Counter(
        {term: _phrase_count(reference_tokens, term) for term in negations}
    )
    hypothesis_negations = Counter(
        {term: _phrase_count(hypothesis_tokens, term) for term in negations}
    )
    for term in negations:
        expected = reference_negations[term]
        actual = hypothesis_negations[term]
        if actual != expected:
            errors.append(
                {
                    "type": "negation",
                    "value": term,
                    "expected_count": expected,
                    "actual_count": actual,
                }
            )
    for term in dict.fromkeys(required):
        expected, actual = _phrase_count(reference_tokens, term), _phrase_count(hypothesis_tokens, term)
        if actual > expected:
            errors.append({"type": "critical_term", "value": term, "change": "duplicated_term",
                           "expected_count": expected, "actual_count": actual})
    return errors


def evaluate_sample(sample: dict[str, Any]) -> dict[str, Any]:
    reference = str(sample.get("reference") or "")
    hypothesis = str(sample.get("hypothesis") or "")
    reference_words = normalize_text(reference).split()
    if not reference_words:
        raise ValueError("A human reference transcript must not be empty")
    critical_terms = sample.get("critical_terms") or []
    if not isinstance(critical_terms, list) or any(not isinstance(term, str) or not normalize_text(term) for term in critical_terms):
        raise ValueError("critical_terms must be a list of non-empty reference terms")
    if any(not _phrase_count(reference_words, term) for term in critical_terms):
        raise ValueError("Critical term is absent from the reference")
    hypothesis_words = normalize_text(hypothesis).split()
    reference_chars = list(normalize_text(reference).replace(" ", ""))
    hypothesis_chars = list(normalize_text(hypothesis).replace(" ", ""))
    word_errors = _distance(reference_words, hypothesis_words)
    character_errors = _distance(reference_chars, hypothesis_chars)
    critical_errors = _critical_errors(
        reference,
        hypothesis,
        language=str(sample.get("language") or "vi").lower(),
        critical_terms=critical_terms,
    )
    spans = sample.get("critical_spans") or []
    if not isinstance(spans, list) or any(not isinstance(span, str) or not normalize_text(span) for span in spans):
        raise ValueError("critical_spans must be non-empty reference phrases")
    for span in spans:
        expected = _phrase_count(reference_words, span)
        if not expected:
            raise ValueError("Critical span is absent from the reference")
        actual = _phrase_count(hypothesis_words, span)
        if actual != expected:
            critical_errors.append({"type": "critical_span", "value": span,
                                    "expected_count": expected, "actual_count": actual})
    return {
        **sample,
        "word_errors": word_errors,
        "reference_word_count": len(reference_words),
        "wer": round(word_errors / max(1, len(reference_words)), 4),
        "character_errors": character_errors,
        "reference_character_count": len(reference_chars),
        "cer": round(character_errors / max(1, len(reference_chars)), 4),
        "critical_errors": critical_errors,
        "critical_pass": not critical_errors,
    }


def build_benchmark_report(
    samples: Iterable[dict[str, Any]],
    *,
    clean_wer_target: float = 0.08,
    noisy_wer_target: float = 0.15,
    required_languages: Iterable[str] = (),
) -> dict[str, Any]:
    if any(not math.isfinite(target) or not 0 <= target <= 1 for target in (clean_wer_target, noisy_wer_target)):
        raise ValueError("WER targets must be finite values in [0, 1]")
    evaluated = [evaluate_sample(sample) for sample in samples]
    if any(item.get("condition") not in {"clean", "noisy"} for item in evaluated):
        raise ValueError("Each sample must specify clean or noisy condition")
    conditions: dict[str, Any] = {}
    for condition, target in (("clean", clean_wer_target), ("noisy", noisy_wer_target)):
        group = [item for item in evaluated if item.get("condition") == condition]
        words = sum(item["reference_word_count"] for item in group)
        errors = sum(item["word_errors"] for item in group)
        wer = errors / max(1, words)
        conditions[condition] = {
            "sample_count": len(group),
            "reference_word_count": words,
            "word_errors": errors,
            "wer": round(wer, 4),
            "target": target,
            "passed": bool(group) and wer <= target,
        }
    critical_errors = [
        {"sample_id": item.get("id"), **error}
        for item in evaluated
        for error in item["critical_errors"]
    ]
    languages = {str(item.get("language") or "vi").lower() for item in evaluated} | set(required_languages)
    language_conditions = []
    for language in sorted(languages):
        for condition, target in (("clean", clean_wer_target), ("noisy", noisy_wer_target)):
            group = [item for item in evaluated if str(item.get("language") or "vi").lower() == language
                     and item["condition"] == condition]
            words = sum(item["reference_word_count"] for item in group)
            errors = sum(item["word_errors"] for item in group)
            language_conditions.append({"language": language, "condition": condition, "sample_count": len(group),
                                        "wer": round(errors / max(1, words), 4), "target": target,
                                        "passed": bool(group) and errors / max(1, words) <= target})
    passed = (all(item["passed"] for item in conditions.values()) and not critical_errors
              and all(item["passed"] for item in language_conditions))
    return {
        "benchmark_version": "stt-wer-v2",
        "targets": {
            "clean_wer_max": clean_wer_target,
            "noisy_wer_max": noisy_wer_target,
            "critical_error_max": 0,
        },
        "conditions": conditions,
        "by_language_condition": language_conditions,
        "critical_errors": critical_errors,
        "limitations": "Counts/order/spans are regression guards, not full semantic verification or speaker separation.",
        "passed": passed,
        "samples": evaluated,
    }
