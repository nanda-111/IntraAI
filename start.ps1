# IntraAI Startup Script
# Usage: Run in PowerShell: .\start.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "        IntraAI Startup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start backend
Write-Host "[1/2] Starting backend (FastAPI)..." -ForegroundColor Green
Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location 'F:\a\backend'; .\venv\Scripts\Activate.ps1; Write-Host 'Backend starting...'; Write-Host 'API Docs: http://localhost:8000/docs'; Write-Host ''; uvicorn app.main:app --reload"

# Wait for backend
Write-Host "      Waiting 3s..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# Start frontend
Write-Host "[2/2] Starting frontend (Vue)..." -ForegroundColor Green
Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location 'F:\a\frontend'; Write-Host 'Frontend starting...'; Write-Host 'URL: http://localhost:5173'; Write-Host ''; npm run dev"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Started!" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Backend API Docs: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "  Frontend:         http://localhost:5173" -ForegroundColor Yellow
Write-Host ""
Write-Host "  To stop: press Ctrl+C in each window" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
