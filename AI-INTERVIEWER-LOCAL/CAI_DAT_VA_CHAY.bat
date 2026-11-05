@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_and_run.ps1"
if errorlevel 1 (
  echo.
  echo Cai dat hoac khoi dong chua hoan tat. Xem loi phia tren.
  pause
  exit /b 1
)
