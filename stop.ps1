# IntraAI Stop Script
# Usage: Run in PowerShell: .\stop.ps1

Write-Host "Stopping IntraAI services..." -ForegroundColor Yellow

Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "  [Stopped] Backend" -ForegroundColor Green

Get-Process -Name "node" -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "  [Stopped] Frontend" -ForegroundColor Green

Write-Host ""
Write-Host "IntraAI stopped." -ForegroundColor Cyan
