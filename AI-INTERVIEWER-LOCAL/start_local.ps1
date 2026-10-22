param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8001,
    [ValidateRange(1, 65535)]
    [int]$OllamaPort = 11434,
    [switch]$NoWarmup
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
Write-Host "[1/3] Kiem tra moi truong Python..."

$pythonCandidates = @(
    (Join-Path $Root ".test-venv\Scripts\python.exe"),
    (Join-Path $Root ".venv\Scripts\python.exe"),
    (Join-Path $Root ".train-venv\Scripts\python.exe")
)
$Python = $pythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Python) {
    throw "Không tìm thấy môi trường Python. Hãy tạo .venv và cài requirements.txt."
}

function Find-FreeLocalPort {
    param([int]$StartPort, [int[]]$Excluded = @())
    for ($candidate = $StartPort; $candidate -le [Math]::Min(65535, $StartPort + 20); $candidate++) {
        if ($Excluded -contains $candidate) { continue }
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $candidate)
        try {
            $listener.Start()
            return $candidate
        } catch [System.Net.Sockets.SocketException] {
            if ($_.Exception.SocketErrorCode -ne [System.Net.Sockets.SocketError]::AddressAlreadyInUse) { throw }
        } finally { $listener.Stop() }
    }
    throw "Khong tim thay cong trong gan $StartPort. Hay chon -Port khac."
}
$selectedPort = Find-FreeLocalPort -StartPort $Port
if ($selectedPort -ne $Port) { Write-Warning "Cong $Port dang ban; dung cong $selectedPort, khong dung ung dung khac." }
$Port = $selectedPort

$ollamaExe = Join-Path $Root "tools\ollama\ollama.exe"
$ollamaHome = Join-Path $Root ".ollama-home"
$ollamaModels = Join-Path $Root "models\ollama"
New-Item -ItemType Directory -Force -Path $ollamaHome, $ollamaModels | Out-Null
[Environment]::SetEnvironmentVariable("HOME", $ollamaHome, "Process")
[Environment]::SetEnvironmentVariable("USERPROFILE", $ollamaHome, "Process")
$env:OLLAMA_MODELS = $ollamaModels
$env:OLLAMA_NO_CLOUD = "1"
$env:PYTHONUTF8 = "1"
$cudaRuntime = Join-Path $Root "tools\ollama\lib\ollama\cuda_v12"
if (Test-Path (Join-Path $cudaRuntime "cublas64_12.dll")) {
    $env:PATH = "$cudaRuntime;$env:PATH"
}

function Test-Ollama {
    try {
        Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -TimeoutSec 1 | Out-Null
        return $true
    } catch {
        return $false
    }
}

$OllamaUrl = "http://127.0.0.1:$OllamaPort"
Write-Host "[2/3] Khoi dong Ollama local (khong chan mo web)..."
if (-not (Test-Ollama)) {
    $selectedOllamaPort = Find-FreeLocalPort -StartPort $OllamaPort -Excluded @($Port)
    if ($selectedOllamaPort -ne $OllamaPort) { Write-Warning "Ollama cong $OllamaPort khong truy cap duoc; dung cong $selectedOllamaPort." }
    $OllamaPort = $selectedOllamaPort
    $OllamaUrl = "http://127.0.0.1:$OllamaPort"
    $env:OLLAMA_HOST = "127.0.0.1:$OllamaPort"
    if (-not (Test-Path $ollamaExe)) {
        Write-Warning "Thieu tools\ollama\ollama.exe. Web van mo, nhung LLM chua san sang."
    } else {
        $logRoot = Join-Path $Root "data\runtime_logs"
        New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
        Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WorkingDirectory $Root -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $logRoot "ollama-$stamp.stdout.log") `
            -RedirectStandardError (Join-Path $logRoot "ollama-$stamp.stderr.log")
    }
}
$env:OLLAMA_BASE_URL = $OllamaUrl
$env:OLLAMA_HOST = "127.0.0.1:$OllamaPort"

$env:RUNTIME_WARMUP = if ($NoWarmup) { "0" } else { "1" }
Write-Host "STT/VAD chi nap khi bam Bat dau; LLM chi nap khi can sua transcript hoac cham bai."

Write-Host "[3/3] Dang mo backend: http://127.0.0.1:$Port"
Write-Host "STT: Faster-Whisper | Transcript correction: Qwen2.5 3B local"
Write-Host "Giu cua so nay mo. Doi dong 'Application startup complete' roi vao web."
& $Python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
if ($LASTEXITCODE -ne 0) { throw "Backend dung voi ma loi $LASTEXITCODE. Xem cac dong loi phia tren." }
