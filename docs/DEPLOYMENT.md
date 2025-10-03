# PlantVision CI/CD & Deployment Guide

This document provides comprehensive instructions for setting up continuous integration/continuous deployment (CI/CD) for PlantVision and deploying the application to production.

## 🚀 CI/CD Pipeline Overview

The PlantVision CI/CD pipeline automatically:

- **Tests** code quality and runs unit tests
- **Builds** multi-stage Docker images for all services
- **Scans** containers for security vulnerabilities
- **Publishes** images to GitHub Container Registry (GHCR)
- **Deploys** to production on successful builds
- **Monitors** application health and performance

## 📋 Prerequisites

### For CI/CD Setup
- GitHub repository with admin access
- GitHub Container Registry enabled
- Docker Hub account (optional, for additional registry)

### For Deployment
- Linux server with Docker and Docker Compose
- Minimum 4GB RAM, 2 CPU cores
- Camera device (for vision processing)
- Network access for MQTT and web interface

## 🔧 Setting Up CI/CD

### 1. Enable GitHub Container Registry

1. Go to your repository settings
2. Navigate to `Actions > General`
3. Ensure "Read and write permissions" are enabled for `GITHUB_TOKEN`
4. Go to `Security > Secrets and variables > Actions`

### 2. Configure Repository Secrets

Add these secrets to your GitHub repository:

```bash
# Optional: Additional registry credentials
DOCKER_USERNAME=your-docker-hub-username
DOCKER_PASSWORD=your-docker-hub-token

# Optional: Production server SSH access
DEPLOY_HOST=your-production-server.com
DEPLOY_USER=deployment-user
DEPLOY_SSH_KEY=your-private-ssh-key
```

### 3. Customize Environment Variables

Edit `.env.example` to match your deployment needs:

```bash
# Docker Registry Configuration
IMAGE_REGISTRY=ghcr.io
GITHUB_REPOSITORY=yourusername/plantvision
IMAGE_TAG=latest

# Network Configuration
WEB_PORT=8001
MQTT_PORT=1883

# Camera and Processing
CAMERA_ID=0
SCALE_PX_PER_CM=28.0
```

### 4. Trigger First Build

Push to `main` branch or create a pull request to trigger the CI/CD pipeline:

```bash
git add .
git commit -m "Setup CI/CD pipeline"
git push origin main
```

## 🏗️ Multi-Stage Docker Builds

Our optimized Dockerfiles use multi-stage builds for better performance and security:

### Web Service (FastAPI)
- **Base**: Python 3.11 slim with system dependencies
- **Dependencies**: Install Python packages with user isolation
- **Development**: Development server with hot reload
- **Production**: Production server with security hardening

### C++ Service (Vision Processing)
- **Dependencies**: Build tools and libraries
- **Build**: Compile optimized C++ application
- **Test**: Run unit tests (if available)
- **Production**: Minimal runtime with non-root user

### AI Service (Python ML)
- **Base**: Python 3.11 with ML libraries
- **Dependencies**: Install ML frameworks and models
- **Production**: Optimized runtime for inference

## 📦 Container Registry

Images are published to GitHub Container Registry with semantic versioning:

```bash
# Latest images
ghcr.io/yourusername/plantvision-web:latest
ghcr.io/yourusername/plantvision-cpp:latest
ghcr.io/yourusername/plantvision-ai:latest

# Tagged versions
ghcr.io/yourusername/plantvision-web:v1.0.0
ghcr.io/yourusername/plantvision-web:main-abc123def
```

## 🚀 Deployment Options

### Option 1: Automated Deployment Script

Use the provided deployment script for easy setup:

```bash
# Download and run deployment script
curl -sSL https://raw.githubusercontent.com/yourusername/plantvision/main/deploy.sh | bash

# Or download and customize
wget https://raw.githubusercontent.com/yourusername/plantvision/main/deploy.sh
chmod +x deploy.sh
./deploy.sh
```

### Option 2: Manual Deployment

1. **Clone Repository**
   ```bash
   git clone https://github.com/yourusername/plantvision.git
   cd plantvision
   ```

2. **Setup Environment**
   ```bash
   cp .env.example .env
   nano .env  # Edit configuration
   ```

3. **Create Data Directories**
   ```bash
   mkdir -p /opt/plantvision/{data,models,logs}
   ```

4. **Deploy with Docker Compose**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Option 3: Kubernetes Deployment

For production Kubernetes deployment:

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Or use Helm chart
helm install plantvision ./charts/plantvision
```

## 🔍 Monitoring & Health Checks

### Health Endpoints

- **Web Service**: `http://localhost:8001/health`
- **Container Health**: Built-in Docker health checks
- **Service Discovery**: Automatic service registration

### Logging

Centralized logging with structured output:

```bash
# View all service logs
docker-compose -f docker-compose.prod.yml logs -f

# View specific service
docker-compose -f docker-compose.prod.yml logs -f web-ui

# Monitor health
curl http://localhost:8001/health | jq .
```

### Monitoring Stack (Optional)

Deploy monitoring with Prometheus and Grafana:

```bash
# Enable monitoring stack
docker-compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml up -d
```

## 🔒 Security Features

### Container Security
- Non-root users in all containers
- Minimal base images with security updates
- Security vulnerability scanning with Trivy
- Read-only root filesystems where possible

### Network Security
- Isolated Docker networks
- Service-to-service communication only
- Configurable firewall rules
- TLS/SSL termination support

### Data Protection
- Encrypted data volumes
- Configuration secrets management
- Backup and recovery procedures
- Access control and authentication

## 🔄 Update Procedures

### Automated Updates (Watchtower)

Watchtower automatically updates containers:

```yaml
watchtower:
  image: containrrr/watchtower
  environment:
    - WATCHTOWER_POLL_INTERVAL=3600  # Check hourly
    - WATCHTOWER_CLEANUP=true
```

### Manual Updates

```bash
# Update specific service
./deploy.sh update

# Or update all services
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### Rolling Updates (Zero Downtime)

```bash
# Rolling update with health checks
docker-compose -f docker-compose.prod.yml up -d --scale web-ui=2
# Wait for health check
docker-compose -f docker-compose.prod.yml up -d --scale web-ui=1
```

## 🐛 Troubleshooting

### Common Issues

1. **Container Won't Start**
   ```bash
   # Check logs
   docker-compose -f docker-compose.prod.yml logs service-name
   
   # Check resource usage
   docker stats
   ```

2. **Camera Access Issues**
   ```bash
   # Check device permissions
   ls -la /dev/video*
   sudo usermod -a -G video $USER
   ```

3. **MQTT Connection Problems**
   ```bash
   # Test MQTT connectivity
   mosquitto_pub -h localhost -t test/topic -m "test"
   mosquitto_sub -h localhost -t test/topic
   ```

### Performance Optimization

1. **Resource Limits**
   ```yaml
   deploy:
     resources:
       limits:
         memory: 1G
         cpus: '0.5'
   ```

2. **Volume Optimization**
   ```bash
   # Use SSD for data volumes
   # Regular cleanup of old data
   ```

### Backup & Recovery

```bash
# Backup data and configuration
tar -czf plantvision-backup-$(date +%Y%m%d).tar.gz /opt/plantvision/data /opt/plantvision/.env

# Restore from backup
tar -xzf plantvision-backup-20240101.tar.gz -C /
```

## 📊 Performance Metrics

Monitor key performance indicators:

- **Processing Latency**: Time from capture to analysis
- **Throughput**: Plants processed per minute
- **Resource Usage**: CPU, memory, storage utilization
- **Error Rates**: Failed processing attempts
- **Availability**: Service uptime percentage

## 🔗 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Container Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [MQTT Protocol Guide](https://mqtt.org/getting-started/)

## 📞 Support

For deployment issues:
1. Check the [troubleshooting section](#-troubleshooting)
2. Review service logs
3. Submit an issue with deployment details
4. Contact the development team

---

**Happy Deploying! 🌱**