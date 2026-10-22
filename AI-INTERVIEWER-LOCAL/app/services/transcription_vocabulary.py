"""Keep ASR hints separate from the much narrower correction vocabulary."""
import re


COMMON_WORDS = {"THE", "THIS", "THAT", "THEIR", "THERE", "THESE", "THOSE", "WITH", "WITHOUT",
                "NOT", "NEVER", "ALWAYS", "ONLY", "ALL", "ONE", "TWO", "FIRST", "LAST", "ORDER", "SORTED"}


def transcription_vocabulary(question: dict) -> dict:
    phrases = [str(question.get(field) or "").strip() for field in ("subject", "topic", "concept")]
    text = str(question.get("question") or "")
    tokens = re.findall(r"(?<!\w)[A-Za-z0-9][A-Za-z0-9+#._-]{1,}(?!\w)", text)
    hints = list(dict.fromkeys(value for value in phrases + tokens if value))[:60]
    identifiers = re.findall(r"(?<!\w)(?:[A-Z]{2,8}|\d+[A-Za-z]{1,5}|[A-Z]+\d+[A-Z]*)(?!\w)",
                             " ".join(phrases + [text]))
    return {"hotwords": hints, "approved_terms": list(dict.fromkeys(
        value for value in identifiers if value not in COMMON_WORDS))[:40]}
