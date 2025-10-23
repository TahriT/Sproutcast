#!/usr/bin/env pwsh
# Local Build Script for Sproutcast
# Builds and optionally pushes the Docker image

param(
    [switch]$NoBuild,
    [switch]$Push,
    [switch]$Test,
    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"
$ImageName = "tahrit/sproutcast"

Write-Host "🌿 Sproutcast Local Build Script" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Cyan
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker is running" -ForegroundColor Green
Write-Host ""

# Build the image
if (-not $NoBuild) {
    Write-Host "Building Docker image: ${ImageName}:${Tag}" -ForegroundColor Cyan
    docker-compose build
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Build failed!" -ForegroundColor Red
        exit 1
    }
    
    # Tag the image
    docker tag "${ImageName}:latest" "${ImageName}:${Tag}"
    Write-Host "✅ Build successful!" -ForegroundColor Green
    Write-Host ""
}

# Test the image
if ($Test) {
    Write-Host "Starting container for testing..." -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host ""
    
    # Run in foreground for testing
    docker-compose up
    
    exit 0
}

# Push to Docker Hub
if ($Push) {
    Write-Host "Pushing to Docker Hub..." -ForegroundColor Cyan
    
    # Login check
    Write-Host "Please ensure you're logged in to Docker Hub" -ForegroundColor Yellow
    Write-Host "Run: docker login" -ForegroundColor Yellow
    Read-Host "Press Enter to continue or Ctrl+C to cancel"
    
    docker push "${ImageName}:${Tag}"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Push failed!" -ForegroundColor Red
        exit 1
    }
    
    if ($Tag -ne "latest") {
        docker push "${ImageName}:latest"
    }
    
    Write-Host "✅ Push successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Image available at: https://hub.docker.com/r/${ImageName}" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Available commands:" -ForegroundColor Yellow
Write-Host "  docker-compose up -d    # Start in background" -ForegroundColor Gray
Write-Host "  docker-compose logs -f  # View logs" -ForegroundColor Gray
Write-Host "  docker-compose down     # Stop and remove" -ForegroundColor Gray
Write-Host ""
Write-Host "Web UI: http://localhost:5323" -ForegroundColor Cyan
Write-Host "MQTT: localhost:1883" -ForegroundColor Cyan
