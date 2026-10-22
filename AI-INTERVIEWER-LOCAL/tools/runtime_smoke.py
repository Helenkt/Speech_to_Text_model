"""Non-destructive runtime checks. Authentication is cleaned up; no exam/grade writes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings


def request_check(report: dict, client: httpx.Client, method: str, path: str, expected: int = 200, **kwargs) -> httpx.Response:
    started = perf_counter()
    error = None
    try:
        response = client.request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        error = type(exc).__name__
        response = httpx.Response(599, json={"error": error})
    report["checks"].append({"method": method, "path": path, "expected": expected,
                             "actual": response.status_code, "passed": response.status_code == expected,
                             "seconds": round(perf_counter() - started, 3), "transport_error": error})
    return response


@contextmanager
def local_services(settings: Settings, base_url: str, output: Path, enabled: bool, report: dict):
    """Own child services inside one test process; never stop an existing user's server."""
    children, handles = [], []
    if not enabled:
        yield
        return
    parsed = urlsplit(base_url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port:
        raise ValueError("Managed checks require http://127.0.0.1:<port>")
    output.parent.mkdir(parents=True, exist_ok=True)
    ollama_port = 11587
    env = {**os.environ, "OLLAMA_MODELS": str(settings.root_dir / "models/ollama"),
           "HOME": str(settings.root_dir / ".ollama-home"), "USERPROFILE": str(settings.root_dir / ".ollama-home"),
           "OLLAMA_HOST": f"127.0.0.1:{ollama_port}", "OLLAMA_BASE_URL": f"http://127.0.0.1:{ollama_port}",
           "OLLAMA_NO_CLOUD": "1", "PYTHONUTF8": "1"}

    def spawn(name: str, command: list[str]):
        handle = output.with_name(f"{output.stem}.{name}.log").open("x", encoding="utf-8")
        handles.append(handle)
        process = subprocess.Popen(command, cwd=settings.root_dir, env=env, stdout=handle, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        children.append(process)
        return process

    def wait_ready(url: str, process: subprocess.Popen, timeout: int = 40):
        deadline = perf_counter() + timeout
        while perf_counter() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Service exited with code {process.returncode}; inspect managed service log")
            try:
                if httpx.get(url, timeout=1, trust_env=False).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        raise RuntimeError("Managed service readiness timed out")

    try:
        ollama = spawn("ollama", [str(settings.root_dir / "tools/ollama/ollama.exe"), "serve"])
        wait_ready(f"http://127.0.0.1:{ollama_port}/api/tags", ollama)
        started = perf_counter()
        api = spawn("launcher", ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                 str(settings.root_dir / "start_local.ps1"), "-Port", str(parsed.port), "-OllamaPort", str(ollama_port), "-NoWarmup"])
        report["model_warmup_enabled"] = False
        wait_ready(base_url + "/openapi.json", api)
        report["web_startup_seconds"] = round(perf_counter() - started, 3)
        yield
    finally:
        for process in reversed(children):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        for handle in handles:
            handle.close()


def inventory(path: Path, backup: Path | None = None) -> dict:
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as source:
        if backup:
            if backup.exists():
                raise ValueError("Refusing to overwrite a database backup")
            backup.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(backup) as destination:
                source.backup(destination)
        tables = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {table: source.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                  for table in ("questions", "users", "interview_sessions", "interview_answers",
                                "speech_transcriptions", "rubric_revisions", "grading_labels") if table in tables}
        answers = source.execute("SELECT answer_id, score, ai_score, final_score, teacher_score, answer_text FROM interview_answers ORDER BY answer_id").fetchall()
        checksum = hashlib.sha256(json.dumps(answers, ensure_ascii=False).encode()).hexdigest()
        first_question = source.execute("SELECT uid FROM questions WHERE active = 1 ORDER BY uid LIMIT 1").fetchone()
        first_answer = source.execute("SELECT answer_id FROM interview_answers ORDER BY answer_id LIMIT 1").fetchone()
        return {"integrity": source.execute("PRAGMA quick_check").fetchone()[0], "counts": counts,
                "answers_and_scores_sha256": checksum, "question_uid": first_question[0] if first_question else None,
                "answer_id": first_answer[0] if first_answer else None,
                "backup_created": str(backup.resolve()) if backup else None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--start-services", action="store_true", help="Test the real PowerShell launcher and services in one managed local test")
    args = parser.parse_args()
    parsed = urlsplit(args.base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        parser.error("Credentials may only be used against the local application")
    if args.output.exists():
        parser.error("Choose a new report path")
    settings = Settings.from_env()
    state = inventory(settings.database_path, args.backup)
    report = {"database": state, "checks": [], "writes_exam_or_grade_data": False}

    def check(client: httpx.Client, method: str, path: str, expected: int = 200, **kwargs) -> httpx.Response:
        return request_check(report, client, method, path, expected, **kwargs)

    if not args.inventory_only:
        with local_services(settings, args.base_url, args.output, args.start_services, report), \
             httpx.Client(base_url=args.base_url, timeout=httpx.Timeout(60, connect=3), trust_env=False) as teacher, \
             httpx.Client(base_url=args.base_url, timeout=httpx.Timeout(60, connect=3), trust_env=False) as candidate:
            try:
                check(teacher, "GET", "/")
                health = check(teacher, "GET", "/api/health")
                report["health"] = health.json() if health.status_code == 200 else {}
                spec = check(teacher, "GET", "/openapi.json").json()
                report["quality_api_loaded"] = "/api/teacher/quality/triage" in spec.get("paths", {})
                check(teacher, "GET", "/api/teacher/quality/corpus", expected=401)
                check(teacher, "GET", "/api/teacher/quality/triage", expected=401)
                check(teacher, "GET", "/api/speech/jobs/00000000-0000-0000-0000-000000000000", expected=401)
                teacher_login = check(teacher, "POST", "/api/auth/login", json={"username": "teacher", "password": "Teacher@123"})
                if teacher_login.status_code == 200:
                    check(teacher, "GET", "/api/speech/jobs/00000000-0000-0000-0000-000000000000", expected=403)
                    for path in ("/api/auth/me", "/api/questions/summary", "/api/teacher/reviews",
                                 "/api/teacher/quality/triage", "/api/teacher/quality/corpus"):
                        check(teacher, "GET", path)
                    if state["question_uid"]:
                        check(teacher, "GET", f"/api/teacher/rubrics/{state['question_uid']}")
                    if state["answer_id"]:
                        check(teacher, "GET", f"/api/teacher/answers/{state['answer_id']}/labeling-task")
                    check(teacher, "GET", "/api/teacher/quality/triage?limit=0", expected=422)
                candidate_login = check(candidate, "POST", "/api/auth/login", json={"username": "candidate01", "password": "Candidate@123"})
                if candidate_login.status_code == 200:
                    check(candidate, "GET", "/api/speech/jobs/00000000-0000-0000-0000-000000000000", expected=404)
                    check(candidate, "POST", "/api/speech/jobs/00000000-0000-0000-0000-000000000000/retry", expected=404)
                    check(candidate, "GET", "/api/interviews/unknown-test-session/resume", expected=409)
                    for path in ("/api/teacher/quality/triage", "/api/teacher/quality/corpus"):
                        check(candidate, "GET", path, expected=403)
                    if state["question_uid"]:
                        check(candidate, "GET", f"/api/teacher/rubrics/{state['question_uid']}", expected=403)
            finally:
                for client in (teacher, candidate):
                    try:
                        client.post("/api/auth/logout", timeout=3)
                    except httpx.HTTPError:
                        pass
        report["answers_and_scores_unchanged"] = inventory(settings.database_path)["answers_and_scores_sha256"] == state["answers_and_scores_sha256"]
    report["passed"] = (state["integrity"] == "ok" and all(item["passed"] for item in report["checks"])
                        and report.get("quality_api_loaded", True) and report.get("answers_and_scores_unchanged", True))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"passed": report["passed"], "checks": len(report["checks"]), "database": state,
                      "failures": [item for item in report["checks"] if not item["passed"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
