import copy
import json

import pytest

from app.services.evaluator import _compose_result
from app.services.grade_state import effective_grade
from app.services.interview_engine import apply_voice_assurance
from app.services.learning_feedback import question_feedback
from app.services.practice_rubric import prepare_practice_rubric
from app.services.rubric_contract import rubric_hash
from app.services.voice_evidence import project_voice_assessments, voice_risk
from app.services.speech_to_text import _critical_decode_tokens


def question(points=None):
    points = points or ['A stack uses LIFO', 'A queue uses FIFO']
    return {'uid': 'q1', 'id': 'q1', 'question': 'Explain these structures.',
        'reference_answer': '. '.join(points), 'language': 'vi', 'subject': 'DSA101',
        'key_points': points, 'key_point_weights': dict(zip(points, [4, 6]))}


def voice(text, spans):
    return {'raw_text': text, 'corrected_text': text, 'text': text,
        'metrics': {'quality_score': .9, 'uncertain_word_ratio': .05},
        'uncertain_spans': spans, 'transcript_status': 'needs_review', 'quality_warnings': []}


def graded(settings, metadata, statuses=('met', 'met')):
    q = question()
    evidence = ['A stack uses LIFO', 'A queue uses FIFO']
    evaluation = _compose_result(q, [{'point': p, 'status': s, 'evidence_quote': e, 'evidence_quotes': [e]}
        for p, s, e in zip(q['key_points'], statuses, evidence)], evaluator='fixture')
    apply_voice_assurance(settings, evaluation, q, metadata, 'practice')
    row = {'question_json': json.dumps(q), 'score': evaluation['score'], 'ai_score': evaluation['score'],
        'final_score': None if evaluation['score_provisional'] else evaluation['score'],
        'score_provisional': evaluation['score_provisional'],
        'assessment_json': json.dumps(evaluation['point_assessments']),
        'voice_metadata_json': json.dumps(metadata), 'grading_pending': 0, 'answer_text': metadata['text']}
    return q, effective_grade(row, interview_mode='practice')


def test_uncertain_filler_does_not_erase_two_clear_criterion_evidences(test_settings):
    text = 'A stack uses LIFO. ờ. A queue uses FIFO.'
    q, grade = graded(test_settings, voice(text, ['ờ']))
    assert grade['final_score'] == 100
    assert grade['score_breakdown']['score'] == 10
    assert grade['recognition_status'] == 'processed'


def test_local_uncertainty_preserves_the_other_criterion_points_and_feedback(test_settings):
    text = 'A stack uses LIFO. A queue uses FIFO.'
    q, grade = graded(test_settings, voice(text, ['queue']))
    assert grade['final_score'] is None
    assert grade['recognition_scope'] == 'criteria'
    breakdown = grade['score_breakdown']
    assert breakdown['confirmed_points'] == 4
    assert breakdown['possible_score_interval'] == [4, 10]
    assert [item['status'] for item in breakdown['criteria']] == ['met', 'unresolved']
    feedback = question_feedback(q, text, grade)
    assert [item['status'] for item in feedback['items']] == ['met', 'unresolved']


@pytest.mark.parametrize('span', ['FIFO', 'không', 'not', '2', 'trước'])
def test_critical_uncertainty_still_blocks_the_whole_grade(test_settings, span):
    text = f'A stack uses LIFO. A queue uses FIFO. {span}'
    q, grade = graded(test_settings, voice(text, [span]))
    assert grade['final_score'] is None
    assert grade['recognition_scope'] == 'all'
    assert grade['score_breakdown']['resolved_criterion_count'] == 0


@pytest.mark.parametrize('change', [
    {'quality_warnings': ['bad capture']}, {'metrics': {'quality_score': .54}},
    {'correction_rejected_reason': 'meaning changed'}, {'uncertain_spans': ['absent word']},
    {'metrics': {'quality_score': float('nan')}}, {'metrics': []},
])
def test_severe_or_unlocatable_voice_errors_cannot_be_bypassed(change):
    metadata = {**voice('A stack uses LIFO. ờ. A queue uses FIFO.', ['ờ']), **change}
    assert voice_risk(metadata)[0] == 'all'


def test_missing_knowledge_is_not_certified_through_a_low_confidence_span():
    metadata = voice('A stack uses LIFO. ờ.', ['ờ'])
    assessments = [{'point': 'A stack uses LIFO', 'status': 'met', 'evidence_quote': 'A stack uses LIFO'},
                   {'point': 'A queue uses FIFO', 'status': 'missing', 'evidence_quote': ''}]
    projected = project_voice_assessments(metadata, assessments)
    assert projected[0]['status'] == 'met'
    assert projected[1]['status'] == 'unresolved'
    assert assessments[1]['status'] == 'missing'


@pytest.mark.parametrize('point,parts', [
    ('Level-order Traversal thăm các nút theo từng mức, từ trên xuống dưới và trái sang phải trong mỗi mức', 3),
    ('Đây là BFS cho cây, cả hai đều dùng Queue để đảm bảo thứ tự xử lý', 2),
    ('Bubble Sort so sánh và hoán đổi từng cặp phần tử liền kề sai thứ tự qua nhiều lượt duyệt', 3),
    ('Biến đếm là số thành phần; mỗi lần khởi động mới phát hiện một thành phần', 2),
])
def test_practice_rubric_decomposition_preserves_source_and_parent_weight(point, parts):
    q = question([point, 'An independent unchanged criterion'])
    before = copy.deepcopy(q)
    derived = prepare_practice_rubric(q)
    assert len(derived['key_points']) == parts + 1
    assert sum(list(derived['key_point_weights'].values())[:parts]) == pytest.approx(4)
    assert derived['key_point_weights']['An independent unchanged criterion'] == 6
    assert rubric_hash(derived) == derived['rubric_snapshot']['sha256']
    assert derived['rubric_snapshot']['teacher_approved'] is False
    assert all(item['source_quote'] in q['key_points'] for item in derived['rubric_snapshot']['contract']['criteria'])
    assert q == before
    assert prepare_practice_rubric(derived) == derived


@pytest.mark.parametrize('point', [
    'Không so sánh và hoán đổi từng cặp phần tử liền kề sai thứ tự',
    'Only visit nodes and mark their parents',
    'Either A and B or C and D',
])
def test_conjunction_scope_is_not_silently_rewritten(point):
    q = question([point, 'An independent unchanged criterion'])
    assert prepare_practice_rubric(q) is q


def test_retry_disagreement_covers_algorithm_identifiers_in_addition_to_digits():
    assert _critical_decode_tokens('BFS visits nodes') != _critical_decode_tokens('DFS visits nodes')
    assert _critical_decode_tokens('Use HTTP', ['HTTP']) != _critical_decode_tokens('Use SMTP', ['HTTP'])
    assert _critical_decode_tokens('RAM 2GB') != _critical_decode_tokens('RAM 3GB')
    assert _critical_decode_tokens('not FIFO') != _critical_decode_tokens('FIFO')


def test_decomposition_is_fixed_before_answer_and_does_not_change_official_rubrics(tmp_path):
    from app.database import database
    from app.services.question_importer import import_question_bank
    from app.services.interview_engine import start_interview
    from test_teacher_strong_review import _settings, _seed_voice_answer
    settings = _settings(tmp_path)
    _seed_voice_answer(settings)
    settings.defer_grading_until_finish = True
    point = 'Level-order Traversal thăm các nút theo từng mức, từ trên xuống dưới và trái sang phải trong mỗi mức'
    q = {**question([point, 'Một tiêu chí khác không đổi']), 'id': 'DSA1', 'difficulty': 'Easy',
         'competency': 'Cây', 'topic': 'Cây', 'concept': 'Level-order'}
    q.pop('key_point_weights')
    import_question_bank(settings.database_path, json.dumps([q], ensure_ascii=False).encode(), filename='source.json')
    kwargs = dict(user_id=2, candidate_name='Fixture', language='vi', subject='DSA101',
                  question_count=1, starting_difficulty='Easy')
    practice = start_interview(settings, **kwargs)
    official = start_interview(settings, **kwargs, interview_mode='real')
    with database(settings.database_path) as connection:
        practice_row = connection.execute('SELECT current_question_json,question_plan_json FROM interview_sessions WHERE session_id=?',
                                          (practice['session_id'],)).fetchone()
        practice_q = json.loads(practice_row['current_question_json'])
        official_q = json.loads(connection.execute('SELECT current_question_json FROM interview_sessions WHERE session_id=?',
                                                  (official['session_id'],)).fetchone()[0])
        raw = json.loads(connection.execute('SELECT key_points_json FROM questions WHERE question_id=?', ('DSA1',)).fetchone()[0])
    assert len(practice_q['key_points']) == 4
    assert json.loads(practice_row['question_plan_json'])[0] == practice_q
    assert official_q['key_points'] == raw == q['key_points']


def traversal_question():
    q = question([
        'Level-order Traversal thăm các nút theo từng mức, từ trên xuống dưới và trái sang phải trong mỗi mức',
        'Đây chính là việc áp dụng thuật toán BFS cho cấu trúc cây, cả hai đều dùng Queue để đảm bảo thứ tự xử lý theo khoảng cách từ gốc/nguồn',
    ])
    q['key_point_weights'] = {p: 1 for p in q['key_points']}
    return prepare_practice_rubric(q)


def test_clear_partial_traversal_answer_gets_weighted_credit_without_llm(test_settings):
    from app.services.evaluator import evaluate_answer
    q = traversal_question()
    answer = 'Em duyệt hết các nút ở một tầng rồi mới xuống tầng kế tiếp. Đây là BFS áp dụng cho cây.'
    coroutine = evaluate_answer(test_settings, q, answer)
    with pytest.raises(StopIteration) as completed:
        coroutine.send(None)
    result = completed.value.value
    assert result['evaluator'] == 'factguard-v2'
    assert result['score_provisional'] is False
    assert result['score'] == pytest.approx(58.3)
    assert [item['status'] for item in result['point_assessments']] == ['met', 'met', 'missing', 'met', 'missing']
    assert 'Queue' not in ' '.join(result['matched_points'])


@pytest.mark.parametrize('tail', [
    'Không phải như vậy.', 'Nhưng thực ra em đi sâu trước.', 'Nếu đồ thị có chu trình thì chưa chắc.',
    'Đó là DFS áp dụng cho cây.', 'Em không dùng Queue.',
])
def test_closed_traversal_proof_cannot_ignore_unparsed_or_contrary_tail(tail):
    from app.services.traversal_facts import check_traversal_point
    q = traversal_question()
    answer = 'Em duyệt hết các nút ở một tầng rồi mới xuống tầng kế tiếp. ' + tail
    assert check_traversal_point(q, answer, q['key_points'][0]).status == 'unknown'


def test_wrong_depth_first_explanation_is_not_rewarded_as_level_order():
    from app.services.traversal_facts import check_traversal_point
    q = traversal_question()
    answer = 'Em đi sâu hết một nhánh trước rồi mới quay lại nhánh khác. Em dùng Stack.'
    assert check_traversal_point(q, answer, q['key_points'][0]).status == 'contradicted'
    assert check_traversal_point(q, answer, q['key_points'][-1]).status == 'missing'
