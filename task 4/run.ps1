param(
    [Parameter(Mandatory = $true)]
    [string]$Audio,
    [string]$Language = "vi",
    [string]$Model = "auto"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Environment not found. Run setup.ps1 first."
}

& $Python (Join-Path $ProjectRoot "transcribe.py") $Audio `
    --language $Language `
    --model $Model
