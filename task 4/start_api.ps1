param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [string]$Model = "auto"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Environment not found. Run setup.ps1 first."
}

$env:STT_MODEL = $Model
Set-Location $ProjectRoot
& $Python -m uvicorn api:app --host $HostAddress --port $Port

