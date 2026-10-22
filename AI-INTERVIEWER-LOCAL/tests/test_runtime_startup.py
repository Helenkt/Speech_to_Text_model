import io
import json
import os
import subprocess
import wave

import httpx
import pytest
from packaging.requirements import Requirement

from tools.runtime_smoke import request_check


def test_connection_failure_is_reported_without_masking_the_original_error():
    report = {"checks": []}

    def unavailable(request):
        raise httpx.ConnectError("test unavailable", request=request)

    with httpx.Client(base_url="http://127.0.0.1:9999", transport=httpx.MockTransport(unavailable)) as client:
        response = request_check(report, client, "GET", "/api/health")
    assert response.status_code == 599
    assert report["checks"][0]["passed"] is False
    assert report["checks"][0]["transport_error"] == "ConnectError"


def test_faster_whisper_really_decodes_wav_with_installed_pyav():
    from faster_whisper.audio import decode_audio

    audio = io.BytesIO()
    with wave.open(audio, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        stream.writeframes(b"\x00\x00" * 1600)
    audio.seek(0)
    samples = decode_audio(audio)
    assert samples.shape == (1600,)
    assert str(samples.dtype) == "float32"


def test_requirements_prevent_the_reproduced_pyav_19_incompatibility(project_root):
    requirements = [Requirement(line) for line in (project_root / "requirements.txt").read_text().splitlines()
                    if line.strip() and not line.startswith("#")]
    av_requirement = next(item for item in requirements if item.name == "av")
    assert "18.1.0" in av_requirement.specifier
    assert "19.0.1" not in av_requirement.specifier


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell launcher")
def test_launcher_parses_and_selects_free_ports_without_stopping_another_service(project_root):
    script = str(project_root / "start_local.ps1").replace("'", "''")
    command = r"""$ErrorActionPreference = 'Stop'
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile('__SCRIPT_PATH__', [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) { throw ($errors | Out-String) }
$function = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Find-FreeLocalPort' }, $true)
. ([scriptblock]::Create($function.Extent.Text))
$occupied = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 0)
try {
    $occupied.Start()
    $busy = $occupied.LocalEndpoint.Port
    $selected = Find-FreeLocalPort -StartPort $busy
    $excluded = Find-FreeLocalPort -StartPort $selected -Excluded @($selected)
    if ($selected -le $busy -or $excluded -le $selected) { throw 'Port selection failed' }
    @{ syntax_valid = $true; busy_port = $busy; selected = $selected; excluded = $excluded } | ConvertTo-Json -Compress
} finally { $occupied.Stop() }
""".replace("__SCRIPT_PATH__", script)
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["syntax_valid"] is True
