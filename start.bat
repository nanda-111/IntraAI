@echo off
chcp 65001 >nul
title IntraAI 启动器

echo ============================
echo   IntraAI 一键启动
echo ============================
echo.

echo [1/2] 启动后端服务 (FastAPI)...
start "IntraAI Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [2/2] 启动前端服务 (Vite)...
start "IntraAI Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo 后端: http://localhost:8000
echo 前端: http://localhost:5173
echo.
echo 关闭窗口即可停止对应服务
pause
