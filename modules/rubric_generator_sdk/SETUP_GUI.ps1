$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = & py -3.11 -c 'import sys; print(sys.executable)'
if ($LASTEXITCODE -ne 0) { throw 'Install Windows Python 3.11 x64 with Tk.' }
& $python -c 'import struct,tkinter; assert struct.calcsize(chr(80)) == 8'
if ($LASTEXITCODE -ne 0) { throw 'Python x64 with Tk is required.' }
$deps = Get-Content -Raw DEPENDENCIES.json | ConvertFrom-Json
foreach ($entry in $deps) {
    if ((Get-FileHash -LiteralPath (Join-Path wheelhouse $entry.file)).Hash -ne $entry.sha256) { throw "Damaged wheel: $($entry.file)" }
}
$marker = '.sdk_venv_owner'
if ((Test-Path .venv) -and (!(Test-Path $marker) -or (Get-Content -Raw $marker).Trim() -ne 'rubric-generator-sdk-1.0.0')) { throw 'Existing environment is not owned by this SDK.' }
if (!(Test-Path .venv)) {
    'rubric-generator-sdk-1.0.0' | Set-Content $marker -Encoding ASCII
    & $python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv' }
}
& .\.venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse -r requirements-win311.lock rubric-generator-sdk==1.0.0
if ($LASTEXITCODE -ne 0) { throw 'Offline setup failed.' }
& .\.venv\Scripts\python.exe -m rubric_generator_sdk doctor --offline
exit $LASTEXITCODE
