#!/usr/bin/env pwsh
# Deployment Script for Sproutcast
# Full build, test, and push workflow

param(
    [string]$Version = "latest",
    [switch]$SkipTests,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ImageName = "tahrit/sproutcast"

Write-Host "🚀 Sproutcast Deployment Pipeline" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "Image: ${ImageName}:${Version}" -ForegroundColor Cyan
Write-Host ""

# Confirm deployment
if (-not $Force) {
    $confirm = Read-Host "Deploy to Docker Hub? This will build, test, and push. (yes/no)"
    if ($confirm -ne "yes") {
        Write-Host "Deployment cancelled." -ForegroundColor Yellow
        exit 0
    }
}

# Step 1: Build
Write-Host ""
Write-Host "📦 Step 1/4: Building image..." -ForegroundColor Cyan
Write-Host "------------------------------" -ForegroundColor Gray
docker-compose build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

# Tag with version
if ($Version -ne "latest") {
    docker tag "${ImageName}:latest" "${ImageName}:${Version}"
}

Write-Host "✅ Build complete" -ForegroundColor Green

# Step 2: Test
if (-not $SkipTests) {
    Write-Host ""
    Write-Host "🧪 Step 2/4: Testing image..." -ForegroundColor Cyan
    Write-Host "-----------------------------" -ForegroundColor Gray
    
    # Start container
    docker-compose up -d
    
    # Wait and health check
    Write-Host "Waiting for service to start..."
    Start-Sleep -Seconds 10
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5323/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Health check passed" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️  Health check failed - check logs manually" -ForegroundColor Yellow
        docker-compose logs --tail=20 sproutcast
        
        $continue = Read-Host "Continue with deployment anyway? (yes/no)"
        if ($continue -ne "yes") {
            docker-compose down
            exit 1
        }
    }
    
    # Stop test container
    docker-compose down
} else {
    Write-Host ""
    Write-Host "⏭️  Step 2/4: Tests skipped" -ForegroundColor Yellow
}

# Step 3: Login
Write-Host ""
Write-Host "🔐 Step 3/4: Docker Hub login..." -ForegroundColor Cyan
Write-Host "--------------------------------" -ForegroundColor Gray

docker login

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Login failed!" -ForegroundColor Red
    exit 1
}

# Step 4: Push
Write-Host ""
Write-Host "⬆️  Step 4/4: Pushing to Docker Hub..." -ForegroundColor Cyan
Write-Host "-------------------------------------" -ForegroundColor Gray

docker push "${ImageName}:${Version}"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Push failed!" -ForegroundColor Red
    exit 1
}

if ($Version -ne "latest") {
    docker push "${ImageName}:latest"
}

Write-Host ""
Write-Host "🎉 Deployment successful!" -ForegroundColor Green
Write-Host ""
Write-Host "Image: ${ImageName}:${Version}" -ForegroundColor Cyan
Write-Host "URL: https://hub.docker.com/r/${ImageName}" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pull and run with:" -ForegroundColor Yellow
Write-Host "  docker pull ${ImageName}:${Version}" -ForegroundColor Gray
Write-Host "  docker-compose pull && docker-compose up -d" -ForegroundColor Gray
