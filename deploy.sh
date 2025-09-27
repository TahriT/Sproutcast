#!/bin/bash

# PlantVision Deployment Script
# This script automates the deployment process for PlantVision

set -e

# Configuration
REPO_URL="https://github.com/TahriT/PlantVision.git"
DEPLOY_DIR="/opt/plantvision"
SERVICE_NAME="plantvision"
BACKUP_DIR="/opt/plantvision/backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
        exit 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check Git
    if ! command -v git &> /dev/null; then
        error "Git is not installed. Please install Git first."
        exit 1
    fi
    
    log "Prerequisites check passed"
}

# Function to create directories
setup_directories() {
    log "Setting up directories..."
    
    sudo mkdir -p "$DEPLOY_DIR"
    sudo mkdir -p "$BACKUP_DIR"
    sudo mkdir -p "$DEPLOY_DIR/data"
    sudo mkdir -p "$DEPLOY_DIR/models"
    sudo mkdir -p "$DEPLOY_DIR/logs"
    
    # Set ownership
    sudo chown -R $USER:$USER "$DEPLOY_DIR"
    
    log "Directories created successfully"
}

# Function to backup existing deployment
backup_deployment() {
    if [ -d "$DEPLOY_DIR" ]; then
        log "Creating backup of existing deployment..."
        
        BACKUP_NAME="plantvision-backup-$(date +%Y%m%d-%H%M%S)"
        BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
        
        mkdir -p "$BACKUP_PATH"
        
        # Backup configuration and data
        if [ -f "$DEPLOY_DIR/.env" ]; then
            cp "$DEPLOY_DIR/.env" "$BACKUP_PATH/"
        fi
        
        if [ -d "$DEPLOY_DIR/data" ]; then
            cp -r "$DEPLOY_DIR/data" "$BACKUP_PATH/"
        fi
        
        log "Backup created at $BACKUP_PATH"
    fi
}

# Function to clone or update repository
update_code() {
    log "Updating application code..."
    
    if [ -d "$DEPLOY_DIR/.git" ]; then
        cd "$DEPLOY_DIR"
        git fetch origin
        git reset --hard origin/main
    else
        git clone "$REPO_URL" "$DEPLOY_DIR"
        cd "$DEPLOY_DIR"
    fi
    
    log "Code updated successfully"
}

# Function to setup environment
setup_environment() {
    log "Setting up environment configuration..."
    
    if [ ! -f "$DEPLOY_DIR/.env" ]; then
        cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env"
        
        warn "Environment file created from template."
        warn "Please edit $DEPLOY_DIR/.env and configure your settings before continuing."
        warn "Press Enter when ready to continue..."
        read
    fi
    
    # Load environment variables
    source "$DEPLOY_DIR/.env"
    
    log "Environment configuration loaded"
}

# Function to pull Docker images
pull_images() {
    log "Pulling Docker images..."
    
    cd "$DEPLOY_DIR"
    docker-compose -f docker-compose.prod.yml pull
    
    log "Docker images pulled successfully"
}

# Function to start services
start_services() {
    log "Starting PlantVision services..."
    
    cd "$DEPLOY_DIR"
    
    # Stop existing services
    docker-compose -f docker-compose.prod.yml down || true
    
    # Start new services
    docker-compose -f docker-compose.prod.yml up -d
    
    log "Services started successfully"
}

# Function to verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    sleep 30  # Wait for services to start
    
    # Check if all containers are running
    CONTAINERS=$(docker-compose -f "$DEPLOY_DIR/docker-compose.prod.yml" ps -q)
    RUNNING_CONTAINERS=$(docker inspect $CONTAINERS | grep '"Status": "running"' | wc -l)
    TOTAL_CONTAINERS=$(echo $CONTAINERS | wc -w)
    
    if [ "$RUNNING_CONTAINERS" -eq "$TOTAL_CONTAINERS" ]; then
        log "All containers are running"
    else
        warn "Some containers may not be running properly"
    fi
    
    # Check web interface
    if curl -f http://localhost:${WEB_PORT:-8001}/health > /dev/null 2>&1; then
        log "Web interface is responding"
    else
        warn "Web interface health check failed"
    fi
    
    log "Deployment verification completed"
}

# Function to show status
show_status() {
    log "PlantVision Status:"
    echo
    
    cd "$DEPLOY_DIR"
    docker-compose -f docker-compose.prod.yml ps
    
    echo
    log "Logs can be viewed with: docker-compose -f $DEPLOY_DIR/docker-compose.prod.yml logs -f"
    log "Web interface: http://localhost:${WEB_PORT:-8001}"
}

# Main deployment function
main() {
    log "Starting PlantVision deployment..."
    
    check_root
    check_prerequisites
    setup_directories
    backup_deployment
    update_code
    setup_environment
    pull_images
    start_services
    verify_deployment
    show_status
    
    log "PlantVision deployment completed successfully!"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "start")
        cd "$DEPLOY_DIR"
        docker-compose -f docker-compose.prod.yml up -d
        ;;
    "stop")
        cd "$DEPLOY_DIR"
        docker-compose -f docker-compose.prod.yml down
        ;;
    "restart")
        cd "$DEPLOY_DIR"
        docker-compose -f docker-compose.prod.yml restart
        ;;
    "status")
        show_status
        ;;
    "logs")
        cd "$DEPLOY_DIR"
        docker-compose -f docker-compose.prod.yml logs -f
        ;;
    "update")
        update_code
        pull_images
        start_services
        verify_deployment
        ;;
    *)
        echo "Usage: $0 {deploy|start|stop|restart|status|logs|update}"
        echo
        echo "Commands:"
        echo "  deploy  - Full deployment (default)"
        echo "  start   - Start services"
        echo "  stop    - Stop services"
        echo "  restart - Restart services"
        echo "  status  - Show service status"
        echo "  logs    - Show service logs"
        echo "  update  - Update and restart services"
        exit 1
        ;;
esac