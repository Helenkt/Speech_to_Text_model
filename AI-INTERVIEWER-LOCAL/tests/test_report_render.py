"""Exercise the actual report JS with real backend reports in a DOM double."""
import asyncio
import json
import os
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.auth import COOKIE_NAME, create_session
from app.services import evaluator, runtime_readiness, session_grading
from app.services.interview_engine import interview_report, list_practice_history, start_interview
from app.services.transcription_store import save_microphone_check
from test_grading_reliability import due, pending_result
from test_low_memory_sessions import prepare, answer_current
from test_teacher_strong_review import _settings
from app.services.practice_grading import question_breakdown
from test_practice_grading import QUESTION, evaluation


class Ids(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, _tag, attrs):
        self.ids.extend(value for name, value in attrs if name == "id")


def test_real_report_rendering_and_polling(tmp_path, monkeypatch):
    node = os.environ.get("NODE_BINARY") or shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for frontend DOM-double regression tests")
    settings = _settings(tmp_path)
    sid = prepare(settings, count=2)["session_id"]
    jobs = session_grading.SessionGrading(settings, runtime_readiness.RuntimeReadiness(settings))

    def grade(current, reason, count=2):
        for _ in range(count):
            answer_current(settings, current)
        first = []

        async def evaluate(_settings, question, *_args, **_kwargs):
            if not first:
                first.append(question["uid"])
            if question["uid"] == first[0]:
                return evaluator._compose_result(question, [
                    {"point": p, "status": "met"} for p in question["key_points"]], evaluator="test")
            return pending_result(question, reason)

        monkeypatch.setattr(session_grading, "evaluate_answer", evaluate)
        for _ in range(3 if reason == "model_timeout" else 1):
            due(settings)
            asyncio.run(jobs.run_once())
        report = interview_report(settings, current)
        report["grading"] = jobs.status(current)
        return report

    mixed = grade(sid, "neutral_evidence")
    history = next(item for item in list_practice_history(settings.database_path, user_id=2)
                   if item["session_id"] == sid)
    assert history["average_score"] == 100 and history["final_score"] is None
    assert history["scored_answer_count"] == history["unscored_answer_count"] == 1
    second = start_interview(settings, user_id=2, candidate_name="Test Student", language="en",
        subject="DSA101", question_count=2, starting_difficulty="Easy")["session_id"]
    save_microphone_check(settings.database_path, session_id=second, user_id=2, result={"ready": True})
    failed = grade(second, "model_timeout")
    third = start_interview(settings, user_id=2, candidate_name="Test Student", language="en",
        subject="DSA101", question_count=1, starting_difficulty="Easy")["session_id"]
    save_microphone_check(settings.database_path, session_id=third, user_id=2, result={"ready": True})
    full = grade(third, None, count=1)
    parser = Ids()
    app = Path(__file__).resolve().parents[1]
    settings.static_dir = app / "app/static"
    token, _ = create_session(settings.database_path, user_id=2)
    with TestClient(create_app(settings)) as client:
        client.cookies.set(COOKIE_NAME, token)
        def get_report(session_id):
            response = client.get(f"/api/interviews/{session_id}/report")
            assert response.status_code == 200, response.text
            return response.json()
        mixed, failed, full = (get_report(key) for key in (sid, second, third))
        response = client.get("/api/candidate/practice-history")
        assert response.status_code == 200, response.text
        history = next(item for item in response.json()["sessions"] if item["session_id"] == sid)
        assert client.get("/").status_code == 200
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/static/styles.css").status_code == 200
    parser.feed((app / "app/static/index.html").read_text(encoding="utf-8"))
    fixture = tmp_path / "report-fixtures.json"
    weighted = evaluation(["met", "met", "unresolved"], score_provisional=True)
    weighted["score_breakdown"] = question_breakdown(QUESTION, weighted, completed=True)
    fixture.write_text(json.dumps({"ids": parser.ids, "mixed": mixed, "failed": failed,
        "full": full, "history": history, "weighted": weighted}, ensure_ascii=False), encoding="utf-8")
    for script in ("report_render.cjs", "report_lifecycle.cjs", "auth_lifecycle.cjs"):
        result = subprocess.run([node, str(Path(__file__).with_name(script)),
            str(app / "app/static/app.js"), str(fixture)], capture_output=True, text=True,
            encoding="utf-8", timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
