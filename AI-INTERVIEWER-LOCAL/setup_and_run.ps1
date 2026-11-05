param([switch]$SetupOnly, [switch]$Repair, [switch]$VerifyStartup, [ValidateRange(1,65535)][int]$Port = 8001)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Find-Python311 {
    $ErrorActionPreference = 'Continue'
    $candidates = @((Join-Path $PSScriptRoot '.venv\Scripts\python.exe'))
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        $resolved = & $py.Source -3.11 -c 'import sys; print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $resolved) { $candidates += $resolved }
    }
    $candidates += (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe')
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python -and $python.Source -notmatch 'WindowsApps') { $candidates += $python.Source }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            & $candidate -c 'import sys,struct; sys.exit(0 if sys.version_info[:2] == (3,11) and struct.calcsize(chr(80)) == 8 else 1)' 2>$null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        }
    }
    return $null
}

try {
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'Can Windows 64-bit.' }
    $pythonPath = Find-Python311
    if (-not $pythonPath) {
        $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if (-not $winget) { throw 'Thieu Python 3.11 va WinGet. Cai Python 3.11 x64 tu python.org, roi bam lai. Xem ONE_CLICK_SETUP.md.' }
        Write-Host '[Python] Dang cai Python 3.11 x64 cho tai khoan hien tai...'
        & $winget.Source install --id Python.Python.3.11 --exact --source winget --scope user --architecture x64 --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
        if ($LASTEXITCODE -ne 0) { throw 'WinGet khong cai duoc Python. Xem loi phia tren va ONE_CLICK_SETUP.md.' }
        $pythonPath = Find-Python311
        if (-not $pythonPath) { throw 'Chua tim thay Python 3.11 x64 sau khi cai. Mo lai launcher.' }
    }
    $launcherArgs = @((Join-Path $PSScriptRoot 'tools\desktop_launcher.py'), '--port', "$Port")
    if ($SetupOnly) { $launcherArgs += '--setup-only' }
    if ($Repair) { $launcherArgs += '--repair' }
    if ($VerifyStartup) { $launcherArgs += '--verify-startup' }
    & $pythonPath @launcherArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} catch {
    Write-Host ("LOI: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
