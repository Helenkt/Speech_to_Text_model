from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from app.services.stt_benchmark import build_benchmark_report


ROOT = Path(__file__).resolve().parents[1]


def test_documentation_local_markdown_links_exist():
    documents = list(ROOT.rglob("*.md"))
    parent_readme = ROOT.parent / "README.md"
    if parent_readme.is_file():
        documents.append(parent_readme)
    documents = [path for path in documents if not any(
        part.startswith(".") or part in {"models", "node_modules", "reports"}
        for part in path.relative_to(ROOT.parent).parts
    )]
    for document in documents:
        for target in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", document.read_text(encoding="utf-8")):
            target = target.strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resolved = document.parent / unquote(parsed.path)
            assert resolved.exists(), f"Broken local link in {document}: {target}"


def test_benchmark_example_is_schema_only_and_covers_both_languages():
    payload = json.loads((ROOT / "data/stt_benchmark_manifest.example.json").read_text(encoding="utf-8"))
    samples = payload["samples"]
    assert {(item["language"], item["condition"]) for item in samples} == {
        (language, condition) for language in ("vi", "en") for condition in ("clean", "noisy")
    }
    assert len({item["id"] for item in samples}) == len(samples)
    assert all(item["audio"] and "hypothesis" not in item for item in samples)
    # A synthetic identity check validates schema/critical spans, not ASR quality.
    report = build_benchmark_report([{**item, "hypothesis": item["reference"]} for item in samples])
    assert report["passed"]


def test_current_guide_references_shipped_benchmark_and_current_cache_version():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    recovery = (ROOT / "BACKEND_RECOVERY.md").read_text(encoding="utf-8")
    teacher_review = (ROOT / "app/services/teacher_review.py").read_text(encoding="utf-8")
    cache_version = re.search(r'"(teacher-review-v[^"\n]+)"', teacher_review)
    assert cache_version and cache_version.group(1) in recovery
    assert "data/stt_benchmark_manifest.example.json" in readme
    assert "test_audio/" not in readme
    assert "http://127.0.0.1:8001/docs" in readme
