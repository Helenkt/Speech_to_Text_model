"""Closed proofs for source-derived traversal criteria; unknown language goes to NLI."""
from __future__ import annotations

import re

from app.services.fact_guard import FactCheck, plain_text, split_clauses


def _requirement(point: str) -> str | None:
    text = plain_text(point).strip(' .')
    prefix = r'level-order traversal tham cac nut '
    for suffix, kind in [('theo tung muc', 'levels'), ('tu tren xuong duoi', 'top_down'),
                         ('trai sang phai trong moi muc', 'left_right')]:
        if text == prefix + suffix:
            return kind
    if re.fullmatch(r'day chinh la viec ap dung thuat toan bfs cho cau truc cay', text):
        return 'bfs_tree'
    if re.fullmatch(r'ca hai deu dung queue de dam bao thu tu xu ly theo khoang cach tu goc/nguon', text):
        return 'queue_distance'
    return None


def _clause_facts(text: str) -> dict | None:
    value = plain_text(text).strip(' .')
    value = re.sub(r'^(?:em|toi|minh)\s+(?:se\s+)?', '', value)
    if re.fullmatch(r'(?:duyet|xu ly|tham) (?:het |toan bo |tat ca )?(?:cac )?(?:nut|dinh) '
        r'(?:o |trong |cung )?(?:mot |moi |cung )?(?:tang|muc)(?: hien tai)? '
        r'(?:roi moi|xong moi|sau do moi) (?:xuong|sang|chuyen sang) (?:tang|muc) (?:ke tiep|tiep theo)', value):
        facts = {'levels': True}
        if re.search(r'\bxuong\b', value):
            facts['top_down'] = True
        return facts
    if re.fullmatch(r'(?:day|do) la bfs ap dung cho (?:cau truc )?cay', value):
        return {'bfs_tree': True}
    if re.fullmatch(r'(?:duyet|di) sau het mot nhanh truoc roi moi quay lai nhanh khac', value):
        return {'levels': False}
    if re.fullmatch(r'(?:dung|su dung) (?:stack|ngan xep)', value):
        # Mentioning an auxiliary stack does not prove that no queue is used.
        return {'auxiliary_stack': True}
    return None


def check_traversal_point(question: dict, answer: str, point: str) -> FactCheck:
    if (question.get('rubric_snapshot') or {}).get('origin') != 'practice_source_decomposition':
        return FactCheck('unknown', 0)
    kind = _requirement(point)
    if kind is None or re.search(r"[?\"'\u2018\u2019\u201c\u201d]", answer):
        return FactCheck('unknown', 0)
    clauses = split_clauses(answer)
    parsed = [(original, _clause_facts(original)) for original in clauses]
    # An unfamiliar trailing assertion could qualify or reject an earlier claim.
    if not parsed or any(facts is None for _, facts in parsed):
        return FactCheck('unknown', 0)
    values = [(original, facts[kind]) for original, facts in parsed if kind in facts]
    if len({value for _, value in values}) > 1:
        return FactCheck('conflicted', 0, 'Có các phát biểu ngược nhau về cùng một yêu cầu.',
                         values[0][0], verification_rule='traversal-source-v1')
    if values:
        quote, supported = values[0]
        return FactCheck('supported' if supported else 'contradicted', .99,
            'Đối chiếu thứ tự duyệt được phát biểu với tiêu chí từ nguồn học.', quote,
            verification_rule='traversal-source-v1')
    return FactCheck('missing', .99, 'Đã đối chiếu toàn bộ các mệnh đề; yêu cầu này chưa được nêu.',
                     '', verification_rule='traversal-source-v1:closed_absence')
