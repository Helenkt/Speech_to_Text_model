[CmdletBinding()]
param([switch]$Generate)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run INSTALL.ps1 first.' }
& $python -m rubric_generator_sdk doctor
if ($LASTEXITCODE -ne 0) { throw 'SDK or Ollama check failed.' }
if ($Generate) {
    & $python -m rubric_generator_sdk generate `
      --input (Join-Path $PSScriptRoot 'examples\input.json') `
      --work-dir (Join-Path $PSScriptRoot 'runtime')
    $code = $LASTEXITCODE
    if ($code -ne 0) { Write-Host "Generator returned exit code $code. Read its JSON status." }
    exit $code
}
