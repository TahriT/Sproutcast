#!/bin/bash
# PlantVision Docker Quick Start Script
# This script helps you start the PlantVision container stack

set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

echo -e "${GREEN}🌱 PlantVision Docker Quick Start${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""

# Check if Docker is running
echo -e "${CYAN}Checking Docker status...${NC}"
if ! docker ps >/dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running${NC}"
    echo ""
    echo -e "${YELLOW}Please start Docker and run this script again.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

echo ""
echo -e "${CYAN}Select deployment mode:${NC}"
echo "1) Development (docker-compose.yml) - Build locally with debug mode"
echo "2) Production (docker-compose.prod.yml) - Use pre-built images"
echo ""
read -p "Enter your choice (1 or 2): " mode

COMPOSE_FILE=""
BUILD=false

case $mode in
    1)
        echo ""
        echo -e "${GREEN}Starting in DEVELOPMENT mode...${NC}"
        COMPOSE_FILE="docker-compose.yml"
        BUILD=true
        ;;
    2)
        echo ""
        echo -e "${GREEN}Starting in PRODUCTION mode...${NC}"
        COMPOSE_FILE="docker-compose.prod.yml"
        BUILD=false
        ;;
    *)
        echo -e "${RED}Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

# Create necessary directories
echo ""
echo -e "${CYAN}Creating data directories...${NC}"
directories=(
    "data"
    "data/ai_requests"
    "data/ai_results"
    "data/sprouts"
    "data/plants"
    "data/debug"
    "mqtt/data"
    "mqtt/log"
    "models"
    "samples"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${GRAY}  Created: $dir${NC}"
    fi
done

# Check if sample images exist
if [ ! -f "samples/plant.jpg" ]; then
    echo ""
    echo -e "${YELLOW}⚠ Warning: No sample images found in ./samples/${NC}"
    echo -e "${YELLOW}  The C++ service may fail to start without input images.${NC}"
    echo -e "${YELLOW}  Please add sample images to ./samples/ directory.${NC}"
fi

# Pull or build images
echo ""
if [ "$BUILD" = true ]; then
    echo -e "${CYAN}Building Docker images...${NC}"
    echo -e "${GRAY}(This may take 5-10 minutes on first run)${NC}"
    docker-compose -f "$COMPOSE_FILE" build
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${CYAN}Pulling Docker images...${NC}"
    if ! docker-compose -f "$COMPOSE_FILE" pull; then
        echo -e "${YELLOW}⚠ Pull failed - images may not exist on registry yet${NC}"
        echo -e "${YELLOW}  Falling back to local build...${NC}"
        docker-compose -f "$COMPOSE_FILE" build
    else
        echo -e "${GREEN}✓ Pull successful${NC}"
    fi
fi

# Start containers
echo ""
echo -e "${CYAN}Starting containers...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d

# Wait for services to be ready
echo ""
echo -e "${CYAN}Waiting for services to start...${NC}"
sleep 10

# Check service health
echo ""
echo -e "${CYAN}Checking service health...${NC}"

WEB_PORT=8001
if curl -sf "http://localhost:$WEB_PORT/health" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Web UI is healthy${NC}"
else
    echo -e "${YELLOW}⚠ Web UI may still be starting...${NC}"
fi

# Show container status
echo ""
echo -e "${CYAN}Container Status:${NC}"
docker-compose -f "$COMPOSE_FILE" ps

# Display access information
echo ""
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 PlantVision is running!${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo -e "Access the web dashboard:"
echo -e "  ${CYAN}http://localhost:$WEB_PORT${NC}"
echo ""
echo -e "API Documentation:"
echo -e "  ${CYAN}http://localhost:$WEB_PORT/docs${NC}"
echo ""
echo -e "MQTT Broker:"
echo -e "  ${CYAN}localhost:1883${NC}"
echo ""
echo -e "Useful Commands:"
echo -e "  ${GRAY}View logs:        docker-compose -f $COMPOSE_FILE logs -f${NC}"
echo -e "  ${GRAY}Stop services:    docker-compose -f $COMPOSE_FILE down${NC}"
echo -e "  ${GRAY}Restart service:  docker-compose -f $COMPOSE_FILE restart <service-name>${NC}"
echo -e "  ${GRAY}View data:        ls ./data${NC}"
echo ""
echo "Press Enter to view live logs (Ctrl+C to exit logs)..."
read -r

docker-compose -f "$COMPOSE_FILE" logs -f
