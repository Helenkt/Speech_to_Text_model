[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PythonPath)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$manifest = Get-Content -LiteralPath (Join-Path $root 'RELEASE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($entry in $manifest.files.PSObject.Properties) {
    $file = Join-Path $root $entry.Name
    if (-not (Test-Path -LiteralPath $file -PathType Leaf) -or
        (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $entry.Value) {
        throw "Release file missing or changed: $file"
    }
}
& $PythonPath -c 'import sys,struct; assert sys.version_info[:2] == (3,11) and struct.calcsize(chr(80)) == 8'
if ($LASTEXITCODE -ne 0) { throw 'Use Windows 64-bit Python 3.11 for the bundled offline wheels.' }
$venv = Join-Path $root '.venv'
$python = Join-Path $venv 'Scripts\python.exe'
$owner = Join-Path $root '.sdk_venv_owner'
if ((Test-Path -LiteralPath $venv) -and -not (Test-Path -LiteralPath $owner)) {
    throw 'An unrelated .venv exists here. Extract the release into a new folder.'
}
if ((Test-Path -LiteralPath $owner) -and (Get-Content -LiteralPath $owner -Raw).Trim() -ne 'rubric-generator-sdk-1.0.0') {
    throw 'Unknown SDK environment owner; use a new folder.'
}
if (-not (Test-Path -LiteralPath $venv)) {
    'rubric-generator-sdk-1.0.0' | Set-Content -LiteralPath $owner -Encoding ASCII
    & $PythonPath -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the dedicated SDK environment.' }
}
if (-not (Test-Path -LiteralPath $python)) { throw 'Incomplete .venv; preserve it and extract the release into a new folder.' }
$wheelhouse = Join-Path $root 'wheelhouse'
$wheel = Join-Path $wheelhouse 'rubric_generator_sdk-1.0.0-py3-none-any.whl'
& $python -m pip install --no-index --find-links $wheelhouse --no-deps --force-reinstall $wheel
if ($LASTEXITCODE -ne 0) { throw 'SDK wheel installation failed.' }
& $python -m pip install --no-index --find-links $wheelhouse -r (Join-Path $root 'requirements-win311.lock')
if ($LASTEXITCODE -ne 0) { throw 'Offline dependency installation failed.' }
& $python -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed.' }
& $python -m rubric_generator_sdk doctor --offline
if ($LASTEXITCODE -ne 0) { throw 'SDK offline check failed.' }
Write-Host "SDK_READY: $python"
Write-Host 'Existing project environments, V15 and Ollama were kept.'
