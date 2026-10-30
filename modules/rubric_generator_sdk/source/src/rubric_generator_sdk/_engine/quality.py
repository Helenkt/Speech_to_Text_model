"""Review aids, never a semantic approval or a student-answer grader."""
from collections import defaultdict
from pathlib import Path
import json

from .._core.core import InputSpec, Rubric, digest, validate_rubric
from .generator import now, read_json, render_markdown, sha, write_json


def inspect_rubric(rubric):
    """Report observable review signals. Shared sources alone do not prove duplication."""
    validate_rubric(rubric)
    owners = defaultdict(list)
    flags = []
    for c in rubric.criteria:
        for source in c.sources:
            if source.source == 'reference_answer':
                owners[source.quote].append(c.id)
        if c.verification.method == 'RELATION' and len(c.verification.relations) > 1 and len(c.levels) == 2:
            flags.append(dict(code='MULTI_COMPONENT_BINARY_LEVELS', criterion_ids=[c.id],
                note='Tiêu chí đối chiếu nhiều phía hiện chỉ có mức 0 và tối đa; cần xem có nên cho điểm một phần.'))
    for quote, ids in owners.items():
        ids = list(dict.fromkeys(ids))
        if len(ids) > 1:
            flags.append(dict(code='SHARED_SOURCE_REVIEW', criterion_ids=ids, source_quote=quote,
                note='Cùng nguồn có thể chứa nhiều ý khác nhau. Chỉ gắn cờ rà soát, không tự xóa hay gộp tiêu chí.'))
    return dict(status='SEMANTIC_REVIEW_PENDING', structural_valid=True, flags=flags,
        semantic_accuracy=None, production_ready=False,
        unchecked=['Đủ phạm vi yêu cầu', 'Nguồn hỗ trợ đúng nghĩa', 'Trùng ý diễn đạt khác',
                   'Vai thực thể, phủ định và điều kiện', 'Trọng số và ranh giới điểm'])


def validate_credit_ledger(rubric, ledger, context_links):
    """Validate an explicitly reviewed allocation; do not infer semantic equivalence."""
    criteria = {c.id: c for c in rubric.criteria}
    seen = set()
    totals = {cid: 0 for cid in criteria}
    for unit in ledger:
        uid, cid, points = unit['id'], unit['criterion_id'], unit['points_units']
        if uid in seen:
            raise ValueError('Repeated credit unit: ' + uid)
        if cid not in criteria or type(points) is not int or points <= 0:
            raise ValueError('Invalid credit owner or points')
        if not unit['claim'].strip() or not unit['source_quote'] or unit['source_quote'] not in rubric.reference_answer:
            raise ValueError('Invalid credit source')
        if not any(s.source == 'reference_answer' and unit['source_quote'] in s.quote for s in criteria[cid].sources):
            raise ValueError('Credit source absent from its owning criterion')
        seen.add(uid); totals[cid] += points
    if totals != {cid: c.max_points_units for cid, c in criteria.items()}:
        raise ValueError('Credit units must account for each criterion exactly')
    graph = {cid: [] for cid in criteria}
    pairs = set()
    for link in context_links:
        pair = (link['criterion_id'], link['credit_owner_id'])
        if pair[0] not in criteria or pair[1] not in criteria or pair[0] == pair[1] or pair in pairs:
            raise ValueError('Invalid context link')
        if type(link['additional_points_units']) is not int or link['additional_points_units'] != 0:
            raise ValueError('Reused context cannot receive additional points')
        pairs.add(pair); graph[pair[0]].append(pair[1])
    active, done = set(), set()
    def visit(cid):
        if cid in active: raise ValueError('Cyclic context links')
        if cid in done: return
        active.add(cid)
        for other in graph[cid]: visit(other)
        active.remove(cid); done.add(cid)
    for cid in graph: visit(cid)


def reviewed_current(source_state, proposal):
    """Materialize one AI-authored review bound to the exact observed input/rubric."""
    spec = InputSpec.model_validate(source_state['input'])
    original = Rubric.model_validate_json(json.dumps(source_state['rubric'], ensure_ascii=False))
    validate_rubric(original)
    if sha(spec.model_dump(mode='json')) != proposal['original_input_sha256'] or digest(original) != proposal['original_rubric_sha256']:
        raise ValueError('Review belongs to a different input/rubric. No model call or original file change.')
    if spec.task_budgets_units is not None:
        raise ValueError('This AI proposal changes auto weights; explicit teacher budgets require a separate review.')
    revised = Rubric.model_validate_json(json.dumps(proposal['rubric'], ensure_ascii=False))
    validate_rubric(revised)
    for field in ['question', 'reference_answer', 'question_id', 'total_units', 'units_per_point']:
        if getattr(original, field) != getattr(revised, field):
            raise ValueError('Review changed an immutable input field: ' + field)
    if [(t.id,t.question_quote,t.primary_type,t.secondary_types) for t in original.tasks] != [
            (t.id,t.question_quote,t.primary_type,t.secondary_types) for t in revised.tasks]:
        raise ValueError('Review changed question decomposition')
    validate_credit_ledger(revised, proposal['credit_ledger'], proposal['context_links'])
    return dict(status='AI_REVIEWED_DRAFT', reviewer_type='AI', human_approved=False,
        production_ready=False, model_calls=0, rubric=revised.model_dump(mode='json'),
        rubric_sha256=digest(revised), original_rubric_sha256=digest(original),
        original_input_sha256=proposal['original_input_sha256'],
        credit_ledger=proposal['credit_ledger'], context_links=proposal['context_links'],
        changes=proposal['changes'], limitations=proposal['limitations'])


def review_markdown(review):
    rubric = Rubric.model_validate_json(json.dumps(review['rubric'], ensure_ascii=False))
    text = render_markdown(rubric).replace('# Rubric nháp', '# Rubric mẫu đã được AI rà soát', 1)
    text = text.replace('**Chưa xác nhận chất lượng ngữ nghĩa.**',
        '**Bản đề xuất sau rà soát của AI; chưa có phê duyệt của người dùng, chưa nghiệm thu triển khai.**', 1)
    text += '\n## Những thay đổi khi rà soát\n\n' + '\n'.join('- '+x for x in review['changes'])
    text += '\n\n## Phân bổ mỗi ý kiến thức một lần\n\n| Ý | Tiêu chí nhận điểm | Điểm | Nội dung |\n|---|---|---:|---|\n'
    for u in review['credit_ledger']:
        text += f"| {u['id']} | {u['criterion_id']} | {u['points_units']/100:g} | {u['claim']} |\n"
    text += '\n## Nội dung dùng làm bối cảnh\n\n'
    text += '\n'.join('- '+x['note'] for x in review['context_links']) + '\n'
    return text


def write_review(folder, review):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder/'review_result.json'
    if path.exists() and read_json(path) != review:
        raise ValueError('Existing review differs. Preserve it and use another output folder.')
    write_json(path, review)
    write_json(folder/'rubric_ai_reviewed.json', review['rubric'])
    (folder/'rubric_ai_reviewed.md').write_text(review_markdown(review), encoding='utf-8')


def summarize_cases(items, total):
    ready = [x for x in items if x['state'].get('status') == 'DRAFT_READY']
    labels = sorted({kind for x in ready for kind in x['state']['rubric']['question_types']})
    return dict(total_cases=total, attempted_cases=len(items), structurally_ready=len(ready),
        blocked_cases=len(items)-len(ready), remaining_cases=total-len(items),
        model_calls_total=sum(len(x['state'].get('calls', [])) for x in items),
        historical_model_calls=sum(str(c.get('origin_version','')).endswith('_IMPORTED') for x in items for c in x['state'].get('calls',[])),
        new_model_calls=sum(not str(c.get('origin_version','')).endswith('_IMPORTED') for x in items for c in x['state'].get('calls',[])),
        generated_labels=labels, semantic_review_complete=False, semantic_accuracy=None,
        human_gold_cases=0, production_ready=False)
