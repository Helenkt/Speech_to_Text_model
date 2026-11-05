import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess

from fastapi import UploadFile
import pytest

from app.database import database
from app.main import create_app
from app.services.grading_queue import queue_session_grading
from app.services.session_grading import SessionGrading
from app.services.transcription_store import expire_stale_sessions
from app.services.transcript_corrector import correct_transcript, _acronym_corrections, _validate_correction
from test_learning_feedback import report_fixtures, seed_stack
from test_transcript_corrector import _run_without_await, _settings


def pending_session(tmp_path):
    settings = seed_stack(tmp_path)
    with database(settings.database_path) as connection:
        connection.execute("""UPDATE interview_sessions SET status='active', grading_strategy='end_of_session',
            created_at='2000-01-01T00:00:00+00:00'""")
        connection.execute("UPDATE interview_answers SET grading_pending=1,score_provisional=1,final_score=NULL")
    return settings


@pytest.mark.parametrize('mode', ['practice', 'real'])
def test_expiry_creates_a_durable_job_before_status_is_read(tmp_path, mode):
    settings = pending_session(tmp_path)
    if mode == 'real':
        with database(settings.database_path) as connection:
            connection.execute("""INSERT INTO exam_rounds (exam_round_id,exam_code,title,language,subject,
                question_count,starting_difficulty,answer_mode,starts_at,ends_at,status,created_by,created_at,updated_at)
                VALUES ('old-exam','OLD','Exam','vi','DSA101',1,'Easy','voice',
                '2000-01-01T00:00:00+00:00','2000-01-02T00:00:00+00:00','open',1,'now','now')""")
            connection.execute("UPDATE interview_sessions SET interview_mode='real',exam_round_id='old-exam'")
    assert expire_stale_sessions(settings.database_path) == 1
    with database(settings.database_path) as connection:
        job = dict(connection.execute('SELECT * FROM session_grading_jobs').fetchone())
        answer = dict(connection.execute('SELECT * FROM interview_answers').fetchone())
    assert job['session_id'] == 'session-1' and job['state'] == 'queued' and job['attempts'] == 0
    assert answer['grading_pending'] and answer['final_score'] is None
    assert expire_stale_sessions(settings.database_path) == 0
    with database(settings.database_path) as connection:
        assert dict(connection.execute('SELECT * FROM session_grading_jobs').fetchone()) == job
    assert SessionGrading(settings, None).claim() == 'session-1'


def test_queue_insertion_failure_rolls_back_expiry(tmp_path):
    settings = pending_session(tmp_path)
    with database(settings.database_path) as connection:
        connection.execute("""CREATE TRIGGER fail_fixture_job BEFORE INSERT ON session_grading_jobs
            BEGIN SELECT RAISE(ABORT, 'fixture queue failure'); END""")
    with pytest.raises(sqlite3.IntegrityError, match='fixture queue failure'):
        expire_stale_sessions(settings.database_path)
    with database(settings.database_path) as connection:
        assert connection.execute('SELECT status FROM interview_sessions').fetchone()[0] == 'active'
        assert connection.execute('SELECT COUNT(*) FROM session_grading_jobs').fetchone()[0] == 0


def test_status_repairs_an_old_orphan_without_regrading_or_resetting_history(tmp_path):
    settings = pending_session(tmp_path)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_sessions SET status='completed'")
        before = dict(connection.execute('SELECT * FROM interview_answers').fetchone())
    worker = SessionGrading(settings, None)
    first, second = worker.status('session-1'), worker.status('session-1')
    assert first['state'] == second['state'] == 'queued'
    assert first['pending_count'] == 1 and not first['report_ready']
    with database(settings.database_path) as connection:
        assert connection.execute('SELECT COUNT(*) FROM session_grading_jobs').fetchone()[0] == 1
        assert dict(connection.execute('SELECT * FROM interview_answers').fetchone()) == before


@pytest.mark.parametrize('state,strategy,pending', [
    ('active', 'end_of_session', 1), ('completed', 'per_answer', 1), ('completed', 'end_of_session', 0),
])
def test_queue_ignores_sessions_without_eligible_confirmed_work(tmp_path, state, strategy, pending):
    settings = pending_session(tmp_path)
    with database(settings.database_path) as connection:
        connection.execute('UPDATE interview_sessions SET status=?,grading_strategy=?', (state, strategy))
        connection.execute('UPDATE interview_answers SET grading_pending=?', (pending,))
        queue_session_grading(connection)
    SessionGrading(settings, None).status('session-1')
    with database(settings.database_path) as connection:
        assert connection.execute('SELECT COUNT(*) FROM session_grading_jobs').fetchone()[0] == 0


def test_expiry_does_not_reset_a_failed_job_or_its_attempt_budget(tmp_path):
    settings = pending_session(tmp_path)
    with database(settings.database_path) as connection:
        connection.execute("UPDATE interview_sessions SET status='completed'")
        queue_session_grading(connection, 'session-1')
        connection.execute("UPDATE session_grading_jobs SET state='failed',attempts=3,error='original error'")
        original = dict(connection.execute('SELECT * FROM session_grading_jobs').fetchone())
        connection.execute("UPDATE interview_sessions SET status='active'")
    expire_stale_sessions(settings.database_path)
    SessionGrading(settings, None).status('session-1')
    with database(settings.database_path) as connection:
        assert dict(connection.execute('SELECT * FROM session_grading_jobs').fetchone()) == original


def test_microphone_route_enqueues_sessions_that_expire_during_runtime(tmp_path):
    settings = pending_session(tmp_path)
    with database(settings.database_path) as connection:
        connection.execute("""INSERT INTO interview_sessions (session_id,user_id,candidate_name,language,
            requested_count,current_difficulty_rank,evaluator_requested,status,created_at,mic_check_result_json)
            VALUES ('new-mic',2,'Candidate','vi',1,1,'rule','active',CURRENT_TIMESTAMP,'{"ready":true}')""")
    app = create_app(settings)
    route = next(route for route in app.routes if getattr(route, 'path', '') == '/api/speech/microphone-check')
    result = _run_without_await(route.endpoint(file=UploadFile(filename='unused.webm', file=io.BytesIO(b'not-read')),
        session_id='new-mic', ambient_noise_dbfs=None, user={'user_id': 2}))
    assert result['already_checked']
    with database(settings.database_path) as connection:
        assert connection.execute('SELECT COUNT(*) FROM session_grading_jobs').fetchone()[0] == 1
    assert app.state.session_grading.claim() == 'session-1'


@pytest.mark.parametrize('raw,terms,expected', [
    ('hai tê bê', ['2TB'], '2TB'), ('hai tê bê.', ['2TB'], '2TB.'),
    ('(hai tê bê)', ['2TB'], '(2TB)'), ('hát tê tê pê', ['HTTP'], 'HTTP'),
    ('a p i', ['API'], 'API'),
    ('hai tê bê và hát tê tê pê', ['2TB', 'HTTP'], '2TB và HTTP'),
])
def test_short_approved_pronunciations_use_exact_spans_without_llm(tmp_path, raw, terms, expected):
    result = _run_without_await(correct_transcript(_settings(tmp_path), raw, language='vi',
        approved_terms=terms, uncertain_spans=[]))
    assert result['corrected_text'] == expected
    assert result['correction_engine'] == 'deterministic-glossary'
    assert all('start' in change and 'end' in change for change in result['corrections'])


@pytest.mark.parametrize('raw,changed,terms', [
    ('hai tê bê và 10 GB', '2TB và 20 GB', ['2TB']),
    ('không dùng hát tê tê pê', 'dùng HTTP', ['HTTP']),
    ('không tê bê', '0TB', ['0TB']),
])
def test_exact_contraction_does_not_hide_changed_numbers_or_negation(raw, changed, terms):
    proof = _acronym_corrections(raw, terms)
    assert proof
    assert not _validate_correction(raw, changed, audited_corrections=proof, approved_terms=terms)[0]


@pytest.mark.parametrize('proof,terms', [
    ([], ['2TB']),
    ([{'source': 'hai tê bê', 'target': '2TB', 'start': 1, 'end': 9}], ['2TB']),
    ([{'source': 'hai tê bê', 'target': '2TB', 'start': 0, 'end': 9}], []),
    ([{'source': 'hai tê bê', 'target': '3TB', 'start': 0, 'end': 9}], ['3TB']),
])
def test_short_contraction_requires_valid_positions_and_an_approved_exact_reading(proof, terms):
    assert not _validate_correction('hai tê bê', '2TB', audited_corrections=proof, approved_terms=terms)[0]


def test_recording_lifecycle_guards(tmp_path):
    node = os.environ.get('NODE_BINARY') or shutil.which('node')
    if not node:
        pytest.skip('Node.js is required for capture lifecycle checks')
    root = Path(__file__).parents[1]
    fixture = tmp_path / 'capture-fixtures.json'
    fixture.write_text(json.dumps(report_fixtures(tmp_path), ensure_ascii=False), encoding='utf-8')
    result = subprocess.run([node, str(root / 'tests/recording_lifecycle.cjs'),
        str(root / 'app/static/app.js'), str(fixture)], capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
