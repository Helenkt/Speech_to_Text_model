@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0SETUP_GUI.ps1"
  if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" "%~dp0gui\app.py"
if errorlevel 1 goto fail
exit /b 0
:fail
echo Xem loi o tren. Kiem tra Python 3.11 x64 va Ollama.
pause
exit /b 1
