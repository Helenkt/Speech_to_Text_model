import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from test_learning_feedback import report_fixtures


def test_speech_recovery_ownership(tmp_path):
    node = os.environ.get('NODE_BINARY') or shutil.which('node')
    if not node:
        pytest.skip('Node.js is required for speech recovery checks')
    root = Path(__file__).parents[1]
    fixture = tmp_path / 'recovery-fixtures.json'
    fixture.write_text(json.dumps(report_fixtures(tmp_path), ensure_ascii=False), encoding='utf-8')
    result = subprocess.run([node, str(root / 'tests/speech_recovery.cjs'),
        str(root / 'app/static/app.js'), str(fixture)], capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
