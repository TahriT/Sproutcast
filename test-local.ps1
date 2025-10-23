#!/usr/bin/env pwsh
# Local Testing Script for Sproutcast
# Quick test and health check

$ErrorActionPreference = "Stop"

Write-Host "🌿 Sproutcast Local Test" -ForegroundColor Green
Write-Host "========================" -ForegroundColor Green
Write-Host ""

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Start the container
Write-Host "Starting Sproutcast container..." -ForegroundColor Cyan
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start container" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Container started" -ForegroundColor Green
Write-Host ""

# Wait for healthcheck
Write-Host "Waiting for service to be ready..." -ForegroundColor Cyan
$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 2
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5323/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Service is healthy!" -ForegroundColor Green
            break
        }
    } catch {
        $attempt++
        Write-Host "." -NoNewline -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host ""

if ($attempt -ge $maxAttempts) {
    Write-Host "⚠️  Health check timeout - checking logs..." -ForegroundColor Yellow
    docker-compose logs --tail=50 sproutcast
} else {
    Write-Host "🎉 Sproutcast is running!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Access points:" -ForegroundColor Cyan
    Write-Host "  Web UI:  http://localhost:5323" -ForegroundColor White
    Write-Host "  MQTT:    localhost:1883" -ForegroundColor White
    Write-Host "  Health:  http://localhost:5323/health" -ForegroundColor White
    Write-Host ""
    Write-Host "View logs:       docker-compose logs -f" -ForegroundColor Yellow
    Write-Host "Stop service:    docker-compose down" -ForegroundColor Yellow
    Write-Host ""
    
    # Open browser
    $openBrowser = Read-Host "Open Web UI in browser? (y/n)"
    if ($openBrowser -eq "y") {
        Start-Process "http://localhost:5323"
    }
}
