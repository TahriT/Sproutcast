# PlantVision Docker Quick Start Script
# This script helps you start the PlantVision container stack

Write-Host "🌱 PlantVision Docker Quick Start" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Cyan
$dockerRunning = $false
try {
    docker ps 2>&1 | Out-Null
    $dockerRunning = $true
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start Docker Desktop and run this script again." -ForegroundColor Yellow
    Write-Host "Docker Desktop can be started from the Start menu or taskbar." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Select deployment mode:" -ForegroundColor Cyan
Write-Host "1) Development (docker-compose.yml) - Build locally with debug mode"
Write-Host "2) Production (docker-compose.prod.yml) - Use pre-built images"
Write-Host ""
$mode = Read-Host "Enter your choice (1 or 2)"

$composeFile = ""
$build = $false

switch ($mode) {
    "1" {
        Write-Host ""
        Write-Host "Starting in DEVELOPMENT mode..." -ForegroundColor Green
        $composeFile = "docker-compose.yml"
        $build = $true
    }
    "2" {
        Write-Host ""
        Write-Host "Starting in PRODUCTION mode..." -ForegroundColor Green
        $composeFile = "docker-compose.prod.yml"
        $build = $false
    }
    default {
        Write-Host "Invalid choice. Exiting." -ForegroundColor Red
        exit 1
    }
}

# Create necessary directories
Write-Host ""
Write-Host "Creating data directories..." -ForegroundColor Cyan
$directories = @(
    "data",
    "data\ai_requests",
    "data\ai_results",
    "data\sprouts",
    "data\plants",
    "data\debug",
    "mqtt\data",
    "mqtt\log",
    "models",
    "samples"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Gray
    }
}

# Check if sample images exist
if (-not (Test-Path "samples\plant.jpg")) {
    Write-Host ""
    Write-Host "⚠ Warning: No sample images found in ./samples/" -ForegroundColor Yellow
    Write-Host "  The C++ service may fail to start without input images." -ForegroundColor Yellow
    Write-Host "  Please add sample images to ./samples/ directory." -ForegroundColor Yellow
}

# Pull or build images
Write-Host ""
if ($build) {
    Write-Host "Building Docker images..." -ForegroundColor Cyan
    Write-Host "(This may take 5-10 minutes on first run)" -ForegroundColor Gray
    docker-compose -f $composeFile build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Build successful" -ForegroundColor Green
} else {
    Write-Host "Pulling Docker images..." -ForegroundColor Cyan
    docker-compose -f $composeFile pull
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ Pull failed - images may not exist on registry yet" -ForegroundColor Yellow
        Write-Host "  Falling back to local build..." -ForegroundColor Yellow
        docker-compose -f $composeFile build
    } else {
        Write-Host "✓ Pull successful" -ForegroundColor Green
    }
}

# Start containers
Write-Host ""
Write-Host "Starting containers..." -ForegroundColor Cyan
docker-compose -f $composeFile up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to start containers" -ForegroundColor Red
    exit 1
}

# Wait for services to be ready
Write-Host ""
Write-Host "Waiting for services to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Check service health
Write-Host ""
Write-Host "Checking service health..." -ForegroundColor Cyan

$webPort = 8001
try {
    $response = Invoke-WebRequest -Uri "http://localhost:$webPort/health" -TimeoutSec 5 -UseBasicParsing
    Write-Host "✓ Web UI is healthy" -ForegroundColor Green
} catch {
    Write-Host "⚠ Web UI may still be starting..." -ForegroundColor Yellow
}

# Show container status
Write-Host ""
Write-Host "Container Status:" -ForegroundColor Cyan
docker-compose -f $composeFile ps

# Display access information
Write-Host ""
Write-Host "════════════════════════════════════════════" -ForegroundColor Green
Write-Host "🎉 PlantVision is running!" -ForegroundColor Green
Write-Host "════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "Access the web dashboard:" -ForegroundColor White
Write-Host "  http://localhost:$webPort" -ForegroundColor Cyan
Write-Host ""
Write-Host "API Documentation:" -ForegroundColor White
Write-Host "  http://localhost:$webPort/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "MQTT Broker:" -ForegroundColor White
Write-Host "  localhost:1883" -ForegroundColor Cyan
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor White
Write-Host "  View logs:        docker-compose -f $composeFile logs -f" -ForegroundColor Gray
Write-Host "  Stop services:    docker-compose -f $composeFile down" -ForegroundColor Gray
Write-Host "  Restart service:  docker-compose -f $composeFile restart <service-name>" -ForegroundColor Gray
Write-Host "  View data:        ls ./data" -ForegroundColor Gray
Write-Host ""
Write-Host "Press any key to view live logs (Ctrl+C to exit logs)..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

docker-compose -f $composeFile logs -f
