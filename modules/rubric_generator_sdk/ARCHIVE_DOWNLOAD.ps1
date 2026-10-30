[CmdletBinding()]
param(
    [string]$ZipPath = (Join-Path $env:USERPROFILE 'Downloads\RUBRIC_ENGINE_V15_PACKAGE.zip'),
    [string]$Kho = 'D:\UP\Rubric_Builder_7_Thiet_ke_va_ma_tham_chieu\kho'
)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Install and check this package before archiving the ZIP.' }
& $python -m rubric_generator_sdk doctor --offline
if ($LASTEXITCODE -ne 0) { throw 'SDK check failed; original ZIP was kept.' }
if (-not (Test-Path -LiteralPath $ZipPath -PathType Leaf)) {
    Write-Host 'ZIP not found; no files moved.'
    exit 0
}
$item = Get-Item -LiteralPath $ZipPath
if ($item.Extension -ne '.zip' -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Expected a regular ZIP file.' }
$destinationFolder = Join-Path $Kho ('sdk_v15_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + [guid]::NewGuid().ToString('N').Substring(0,8))
$null = New-Item -ItemType Directory -Path $destinationFolder -Force
$destination = Join-Path $destinationFolder $item.Name
$hash = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash
Copy-Item -LiteralPath $ZipPath -Destination $destination
if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $hash) { throw 'ZIP copy differs; original was kept.' }
Remove-Item -LiteralPath $ZipPath
Write-Host "Archived ZIP: $destination"
Write-Host 'SDK, old generator, tests, model and all outputs were kept.'
