"""Localize ASR uncertainty without treating it as a knowledge error."""
from __future__ import annotations

import math
import re

VERSION = 'criterion-voice-evidence-v1'
CRITICAL = re.compile(r'\d|\b(?:không|chưa|chẳng|hơn|kém|trước|sau|not|never|before|after|than)\b', re.I)


def voice_risk(voice: dict) -> tuple[str, list[tuple[int, int]]]:
    if not isinstance(voice, dict):
        return 'all', []
    try:
        metrics = voice.get('metrics') or {}
        quality = metrics.get('quality_score')
        if quality is not None and (isinstance(quality, bool) or not math.isfinite(float(quality)) or float(quality) < .55):
            return 'all', []
        if (voice.get('quality_warnings') or voice.get('quality_reasons') or voice.get('needs_retry')
                or voice.get('correction_rejected_reason') or voice.get('rejected_corrections')):
            return 'all', []
        spans = voice.get('uncertain_spans') or []
        flagged = voice.get('transcript_status') == 'needs_review'
        if not spans:
            return ('all' if flagged else 'none'), []
        # A legacy warning without measurable/locatable evidence stays globally blocked.
        text = voice.get('corrected_text', voice.get('text'))
        if quality is None or not isinstance(text, str) or not text.strip() or not isinstance(spans, list):
            return 'all', []
        ranges = []
        for span in spans:
            if not isinstance(span, str) or not span.strip():
                return 'all', []
            if CRITICAL.search(span) or re.search(r'\b[A-Z][A-Z0-9]{1,}\b', span):
                return 'all', []
            found = list(re.finditer(re.escape(span.strip()), text, re.I))
            if not found:
                return 'all', []
            ranges.extend((match.start(), match.end()) for match in found)
        return 'criteria', ranges
    except (ValueError, TypeError, AttributeError):
        return 'all', []


def project_voice_assessments(voice: dict, assessments: list[dict]) -> list[dict]:
    scope, ranges = voice_risk(voice)
    items = [dict(item) if isinstance(item, dict) else
             {'point': '', 'status': 'unresolved', 'needs_review': True, 'review_reason': 'invalid_assessment'}
             for item in assessments]
    if scope == 'none':
        return items
    text = voice.get('corrected_text', voice.get('text', '')) if isinstance(voice, dict) else ''
    for item in items:
        blocked = scope == 'all'
        if scope == 'criteria':
            quotes = item.get('evidence_quotes') or [item.get('evidence_quote', '')]
            if not isinstance(quotes, list):
                quotes = []
            valid = [quote for quote in quotes if isinstance(quote, str) and quote.strip() and quote in text]
            # Missing claims cannot be certified from an incompletely recognized answer.
            blocked = item.get('status') in {'missing', 'partial'} or not valid
            if not blocked:
                blocked = any(start < end_quote and end > start_quote
                    for quote in valid for match in re.finditer(re.escape(quote), text)
                    for start_quote, end_quote in [(match.start(), match.end())] for start, end in ranges)
        if blocked:
            item['voice_original_status'] = item.get('voice_original_status', item.get('status'))
            item.update(status='unresolved', needs_review=True, voice_evidence_status='unverified',
                        voice_evidence_policy=VERSION)
            if not item.get('review_reason'):
                item['review_reason'] = 'audio_unverified'
            if not item.get('reason'):
                item['reason'] = 'Bằng chứng của tiêu chí này còn vướng vùng nhận dạng chưa chắc chắn.'
        else:
            item.update(voice_evidence_status='clear_span', voice_evidence_policy=VERSION)
    return items


def voice_requires_review(voice: dict, assessments: list[dict] | None = None) -> bool:
    scope, _ = voice_risk(voice)
    if scope != 'criteria' or assessments is None:
        return scope != 'none'
    return any(item.get('voice_evidence_status') == 'unverified'
               for item in project_voice_assessments(voice, assessments))
