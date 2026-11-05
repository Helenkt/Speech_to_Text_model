"""Connect real teacher-result payloads to the production desktop renderer."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.database import database
from app.main import create_app
from app.services.auth import COOKIE_NAME, create_session
from app.services.exam_service import list_exam_attempts
from app.services.teacher_review import review_answer
from test_teacher_strong_review import _settings, _seed_voice_answer


def attempt(tmp_path, *, scores=(), pending=False, state="completed", empty=False):
    settings = _settings(tmp_path)
    question = _seed_voice_answer(settings)
    with database(settings.database_path) as connection:
        connection.execute("""INSERT INTO exam_rounds (exam_round_id,exam_code,title,language,subject,
            question_count,starting_difficulty,answer_mode,starts_at,ends_at,status,created_by,created_at,updated_at)
            VALUES ('exam','DEMO','Exam','vi','AI101',2,'Easy','voice',
            '2026-10-01T00:00:00+00:00','2030-01-01T00:00:00+00:00','closed',1,
            '2026-10-01T00:00:00+00:00','2026-10-01T00:00:00+00:00')""")
        connection.execute("""UPDATE interview_sessions SET exam_round_id='exam',requested_count=2,
            answered_count=2,grading_strategy='end_of_session',created_at='2026-10-29T12:00:00+00:00',
            finished_at='2026-10-29T12:05:00+00:00',status=?""", (state,))
        original = dict(connection.execute('SELECT * FROM interview_answers').fetchone())
        second = {**original, 'answer_id': 2, 'sequence_number': 2,
                  'question_uid': 'vi:AI101:q2', 'transcription_id': None,
                  'question_json': json.dumps({**question, 'uid': 'vi:AI101:q2', 'id': 'AI101:q2'})}
        connection.execute(f"INSERT INTO interview_answers ({','.join(second)}) VALUES ({','.join('?' for _ in second)})",
                           list(second.values()))
    for index, score in enumerate(scores, 1):
        review_answer(settings, answer_id=index, teacher_id=1, action='manual', score=score, feedback='Fixture review')
    with database(settings.database_path) as connection:
        if pending:
            connection.execute('UPDATE interview_answers SET grading_pending=1 WHERE answer_id=2')
            connection.execute("""INSERT INTO session_grading_jobs (session_id,state)
                VALUES ('session-1','processing')""")
        if empty:
            connection.execute('DELETE FROM interview_answers')
            connection.execute('UPDATE interview_sessions SET answered_count=0')
    return settings


def result(settings):
    app = create_app(settings)
    endpoint = next(route.endpoint for route in app.routes if getattr(route, 'path', None) == '/api/teacher/results')
    coroutine = endpoint(exam_round_id=None, _={'role': 'teacher', 'user_id': 1})
    try:
        coroutine.send(None)
    except StopIteration as completed:
        return completed.value['results'][0]
    finally:
        coroutine.close()
    raise AssertionError('This read-only endpoint must not wait on inference')


@pytest.mark.parametrize('scores,expected', [((), None), ((80,), None), ((80, 60), 70), ((0, 0), 0)])
def test_teacher_results_distinguish_partial_and_final_grade(tmp_path, scores, expected):
    item = result(attempt(tmp_path, scores=scores))
    assert item['answer_count'] == 2
    assert item['scored_answer_count'] == len(scores)
    assert item['unscored_answer_count'] == 2 - len(scores)
    assert item['final_score'] == expected
    assert item['score_status'] == ('final' if expected is not None else 'pending')
    assert item['average_score'] == item['scored_only_average']


@pytest.mark.parametrize('variant', ['empty', 'active', 'pending', 'count_mismatch'])
def test_teacher_results_do_not_finalize_incomplete_attempts(tmp_path, variant):
    settings = attempt(tmp_path, scores=() if variant == 'empty' else (80, 60), pending=variant == 'pending',
                       state='active' if variant == 'active' else 'completed', empty=variant == 'empty')
    if variant == 'count_mismatch':
        with database(settings.database_path) as connection:
            connection.execute('UPDATE interview_sessions SET answered_count=3')
    item = result(settings)
    assert item['final_score'] is None
    assert item['score_status'] == 'pending'
    if variant == 'pending':
        assert item['grading_state'] == 'processing'
        assert item['grading_processed_count'] == item['grading_pending_count'] == 1
    assert list_exam_attempts(settings.database_path, exam_round_id='other') == []


def test_real_teacher_payloads_render_and_refresh_without_inference(tmp_path):
    node = os.environ.get('NODE_BINARY') or shutil.which('node')
    if not node:
        pytest.skip('Node.js is required for production renderer tests')
    fixtures = {name: result(attempt(tmp_path / name, **args)) for name, args in {
        'partial': {'scores': (80,)}, 'complete': {'scores': (80, 60)},
        'zero': {'scores': (0, 0)}, 'processing': {'pending': True}, 'empty': {'empty': True},
    }.items()}
    project = Path(__file__).resolve().parents[1]
    fixture_path = tmp_path / 'teacher-results.json'
    fixture_path.write_text(json.dumps(fixtures), encoding='utf-8')
    run = subprocess.run([node, str(project / 'tests/frontend_connection.cjs'),
                          str(project / 'app/static/app.js'), str(project / 'app/static/index.html'),
                          str(fixture_path)], capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr


def test_http_review_updates_the_list_and_report_consistently(tmp_path):
    settings = attempt(tmp_path, scores=(80,))
    settings.static_dir = Path(__file__).resolve().parents[1] / 'app/static'
    teacher_token, _ = create_session(settings.database_path, user_id=1)
    student_token, _ = create_session(settings.database_path, user_id=2)
    with TestClient(create_app(settings)) as client:
        assert client.get('/api/teacher/results').status_code == 401
        client.cookies.set(COOKIE_NAME, student_token)
        assert client.get('/api/teacher/results').status_code == 403
        assert client.get('/api/interviews/session-1/report').status_code == 403
        client.cookies.set(COOKIE_NAME, teacher_token)
        partial = client.get('/api/teacher/results')
        assert partial.status_code == 200
        assert partial.json()['results'][0]['final_score'] is None
        assert partial.json()['results'][0]['scored_answer_count'] == 1
        review = client.patch('/api/teacher/answers/2/review', json={
            'action': 'manual', 'score': 60, 'feedback': 'Fixture manual review',
        })
        assert review.status_code == 200, review.text
        completed = client.get('/api/teacher/results').json()['results'][0]
        report = client.get('/api/teacher/results/session-1').json()
        assert completed['final_score'] == report['summary']['average_score'] == 70
        assert completed['scored_answer_count'] == report['summary']['scored_answer_count'] == 2
        assert completed['score_status'] == 'final'
        assert '/static/app.js?v=1.18.11' in client.get('/').text
        assert client.get('/static/app.js?v=1.18.11').status_code == 200
