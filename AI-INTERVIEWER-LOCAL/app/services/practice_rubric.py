"""Conservative, source-bound decomposition before a practice answer is recorded."""
from __future__ import annotations

from copy import deepcopy
import re

from app.services.rubric_contract import digest, question_fingerprint

VERSION = 'practice-extractive-v1'
SCOPE = re.compile(r'\b(không|chưa|chỉ|duy nhất|hoặc|trừ|nếu|khi|not|never|only|unless|either|except|if)\b', re.I)
ACTION = r'(?:tăng|chạy|đánh dấu|duyệt|increment|run|mark|visit)\b'


def _parts(point: str) -> list[str]:
    # Distributing negation/disjunction/"only" across a conjunction changes meaning.
    if SCOPE.search(point) or re.search(r'```|[{}]|\b(?:SELECT|INSERT|UPDATE|DELETE)\b', point):
        return [point]
    comparison = re.fullmatch(
        r'(.+?)\s+so sánh và hoán đổi\s+(.+?liền kề)(\s+sai thứ tự)?(\s+qua nhiều lượt duyệt)?[.]?',
        point, re.I)
    if comparison:
        subject, pair, condition, repeated = comparison.groups()
        parts = [f'{subject} so sánh {pair}', f'{subject} hoán đổi {pair}{condition or ""}']
        if repeated:
            parts.append(f'{subject} duyệt nhiều lượt')
        return parts
    traversal = re.fullmatch(
        r'(.+?\b(?:thăm|duyệt)\s+(?:các\s+)?(?:nút|đỉnh|phần tử))\s+'
        r'(theo từng mức|theo từng tầng),\s*(từ trên xuống dưới)\s+và\s+(.+)', point, re.I)
    if traversal:
        prefix, *modifiers = traversal.groups()
        return [f'{prefix} {part.strip()}' for part in modifiers]
    # Two complete propositions with an explicit subject in the second clause.
    clauses = re.split(r';\s*|,\s*(?=(?:cả hai|both|mỗi lần|each time)\b)', point, flags=re.I)
    if len(clauses) > 1 and all(len(clause.split()) >= 4 for clause in clauses):
        return [clause.strip() for clause in clauses]
    # A repeated condition must remain attached to both actions.
    conditional = re.fullmatch(r'(.+?\bthì\s+)(.+?)\s+và\s+(' + ACTION + r'.+)', point, re.I)
    if conditional and re.match(ACTION, conditional[2], re.I):
        return [conditional[1] + conditional[2], conditional[1] + conditional[3]]
    return [point]


def prepare_practice_rubric(question: dict) -> dict:
    """No model call, bank write, teacher attestation or answer-dependent weighting."""
    if question.get('rubric_snapshot'):
        return question
    original = question.get('key_points') or []
    weights = question.get('key_point_weights') or {}
    groups = [(point, _parts(point)) for point in original]
    if all(parts == [point] for point, parts in groups):
        return question
    if sum(len(parts) for _, parts in groups) > max(6, len(original)):
        return question
    claims = [claim for _, parts in groups for claim in parts]
    if len({claim.casefold().strip() for claim in claims}) != len(claims):
        return question
    criteria, parents = [], []
    for index, (point, parts) in enumerate(groups, 1):
        parent_weight = float(weights.get(point, 1.0))
        for subindex, claim in enumerate(parts, 1):
            identifier = f'c{index}_{subindex}'
            criteria.append({'id': identifier, 'claim': claim, 'weight': parent_weight / len(parts),
                'credit_policy': 'binary', 'source_field': 'key_points', 'source_quote': point})
            parents.append({'criterion_id': identifier, 'source_point': point,
                            'source_weight': parent_weight, 'subcriterion_count': len(parts)})
    contract = {'schema_version': VERSION, 'question_fingerprint': question_fingerprint(question),
                'criteria': criteria}
    result = deepcopy(question)
    result.update(key_points=[item['claim'] for item in criteria],
        key_point_weights={item['claim']: item['weight'] for item in criteria},
        rubric_version=f'{VERSION}:{digest(contract)}',
        rubric_snapshot={'contract': contract, 'sha256': digest(contract),
            'origin': 'practice_source_decomposition', 'parent_criteria': parents,
            'teacher_approved': False})
    return result
