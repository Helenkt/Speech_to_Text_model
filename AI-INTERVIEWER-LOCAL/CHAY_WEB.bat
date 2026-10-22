@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [LOI] Khong tim thay moi truong Python: .venv\Scripts\python.exe
  echo Hay cai thu vien truoc khi chay lai.
  pause
  exit /b 1
)

echo Dang khoi dong AI Interview tai http://127.0.0.1:8000
echo Giu cua so nay mo trong khi su dung ung dung.
echo.

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info

echo.
echo Server da dung hoac gap loi. Xem thong bao phia tren.
pause
