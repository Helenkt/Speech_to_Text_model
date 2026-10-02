param(
    [int]$Port = 8001
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$pythonCandidates = @(
    (Join-Path $Root ".test-venv\Scripts\python.exe"),
    (Join-Path $Root ".venv\Scripts\python.exe")
)
$Python = $pythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Python) {
    throw "Không tìm thấy môi trường Python. Hãy tạo .venv và cài requirements.txt."
}

$ollamaExe = Join-Path $Root "tools\ollama\ollama.exe"
$ollamaHome = Join-Path $Root ".ollama-home"
$ollamaModels = Join-Path $Root "models\ollama"
New-Item -ItemType Directory -Force -Path $ollamaHome, $ollamaModels | Out-Null
[Environment]::SetEnvironmentVariable("HOME", $ollamaHome, "Process")
[Environment]::SetEnvironmentVariable("USERPROFILE", $ollamaHome, "Process")
$env:OLLAMA_MODELS = $ollamaModels
$cudaRuntime = Join-Path $Root "tools\ollama\lib\ollama\cuda_v12"
if (Test-Path (Join-Path $cudaRuntime "cublas64_12.dll")) {
    $env:PATH = "$cudaRuntime;$env:PATH"
}

function Test-Ollama {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-Ollama)) {
    if (-not (Test-Path $ollamaExe)) {
        throw "Thiếu Ollama portable tại tools\ollama\ollama.exe."
    }
    Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WorkingDirectory $Root -WindowStyle Hidden
    for ($attempt = 0; $attempt -lt 30 -and -not (Test-Ollama); $attempt++) {
        Start-Sleep -Seconds 1
    }
}

if (-not (Test-Ollama)) {
    throw "Ollama không khởi động được tại http://127.0.0.1:11434."
}

$tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
if (-not ($tags.models.name -contains "qwen2.5:3b")) {
    & $ollamaExe pull "qwen2.5:3b"
    if ($LASTEXITCODE -ne 0) {
        throw "Không tải được model qwen2.5:3b."
    }
}

$warmupBody = @{
    model = "qwen2.5:3b"
    prompt = ""
    stream = $false
    keep_alive = "30m"
} | ConvertTo-Json
Invoke-RestMethod `
    -Uri "http://127.0.0.1:11434/api/generate" `
    -Method Post `
    -ContentType "application/json" `
    -Body $warmupBody `
    -TimeoutSec 180 | Out-Null

Write-Host "AI Interviewer: http://127.0.0.1:$Port"
Write-Host "STT: Faster-Whisper | Transcript correction: Qwen2.5 3B local"
& $Python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
