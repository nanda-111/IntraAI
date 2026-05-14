@echo off
chcp 65001 >nul
echo ========================================
echo   IntraAI Dev Startup
echo ========================================

echo [1/2] Starting backend (uvicorn) ...
start "IntraAI Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting frontend (vite) ...
start "IntraAI Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo.
echo Close the two opened windows to stop services.
pause
