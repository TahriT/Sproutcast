# PlantVision Quick Start Guide

## Initial Setup

### 1. Prerequisites

- **Docker Desktop**: Installed and running
- **Git**: For cloning the repository
- **4GB RAM minimum** for all containers
- **10GB disk space** for images and models

### 2. Clone and Start

```bash
# Clone the repository
git clone https://github.com/TahriT/PlantViz.git
cd PlantVision

# Start all services
docker compose up --build
```

### 3. First Run

On first run, the system will:
1. Download AI models (~200MB) - this may take 5-10 minutes
2. Initialize MQTT broker
3. Start processing sample images
4. Launch web interface

### 4. Access the System

- **Web Dashboard**: http://localhost:8001
- **MQTT Broker**: localhost:1883
- **Sample Data**: Automatically processed from `samples/plant.jpg`

## Common Issues & Solutions

### Issue: "Connection Refused" Error

**Symptom**: AI service fails with `ConnectionRefusedError: [Errno 111] Connection refused`

**Cause**: Old Docker images with outdated code

**Solution**:
```bash
# Stop all containers
docker compose down

# Rebuild with no cache
docker compose build --no-cache

# Start again
docker compose up
```

### Issue: Docker Build Fails on AI Service

**Symptom**: `Package 'libgl1-mesa-glx' has no installation candidate`

**Cause**: Dockerfile using outdated package names

**Solution**: Already fixed in latest version. Pull latest code:
```bash
git pull origin main
docker compose build ai
```

### Issue: MQTT Broker Permission Warning

**Symptom**: `chown: /mosquitto/config/mosquitto.conf: Read-only file system`

**Cause**: Config file mounted as read-only (this is intentional and safe)

**Impact**: None - this warning can be ignored

### Issue: Web Interface Not Loading

**Checks**:
```bash
# Check if web service is running
docker ps | grep sc-web

# Check web logs
docker logs sc-web

# Test API endpoint
curl http://localhost:8001/api/latest
```

**Solution**:
```bash
# Restart web service
docker compose restart web-ui
```

### Issue: No Plant Data Showing

**Checks**:
```bash
# Check if C++ processor is running
docker ps | grep sc-cpp

# Check C++ logs
docker logs sc-cpp

# Check data directory
ls -la data/plants/
```

**Solution**:
```bash
# Restart C++ processor
docker compose restart cpp-app

# Check for errors
docker logs cpp-app | grep -i error
```

## Configuration

### Switch from Sample Image to Camera

Edit `docker-compose.yml`:

```yaml
cpp-app:
  environment:
    - INPUT_MODE=CAMERA      # Change from IMAGE to CAMERA
    - CAMERA_ID=0            # Use camera device 0
  devices:
    - /dev/video0:/dev/video0  # Add device mapping (Linux)
```

**Note**: Camera passthrough doesn't work on Windows Docker Desktop. Use WSL2 or keep `INPUT_MODE=IMAGE`.

### Adjust Processing Parameters

Edit `docker-compose.yml`:

```yaml
cpp-app:
  environment:
    - THRESHOLD=100                # Green mask threshold (50-150)
    - SCALE_PX_PER_CM=28.0        # Pixel to cm calibration
    - PUBLISH_INTERVAL_MS=1000    # MQTT publish rate
    - VISION_DEBUG_MODE=false     # Disable debug images
```

### Change MQTT Topics

Edit `data/config.json`:

```json
{
  "uns": {
    "room": "greenhouse-a",    # Change location
    "area": "shelf-1",
    "camera_id": "cam-0"
  }
}
```

Topics will be: `plantvision/greenhouse-a/shelf-1/cam-0/...`

## Monitoring

### Check Service Status

```bash
# View all services
docker compose ps

# View logs (all services)
docker compose logs -f

# View specific service logs
docker logs sc-cpp -f
docker logs sc-web -f
docker logs sc-ai -f
docker logs sc-mqtt -f
```

### Monitor MQTT Topics

```bash
# Subscribe to all PlantVision topics
mosquitto_sub -h localhost -t "plantvision/#" -v

# Subscribe to specific plant data
mosquitto_sub -h localhost -t "plantvision/+/+/+/plants/+/telemetry"

# Subscribe to system status
mosquitto_sub -h localhost -t "plantvision/+/+/+/system/status"
```

### Check Resource Usage

```bash
# Docker stats
docker stats

# Disk usage
docker system df

# Clean up old images
docker system prune -a
```

## Data Management

### View Processed Data

```bash
# Navigate to data directory
cd data

# View plant instances
ls -la plants/

# View sprout instances
ls -la sprouts/

# Check latest frame
ls -la frame_*.jpg

# Read plant data
cat plants/plant_000/data.json | jq .
```

### Backup Data

```bash
# Backup all data
tar -czf plantvision-backup-$(date +%Y%m%d).tar.gz data/

# Backup specific instances
tar -czf plants-backup.tar.gz data/plants/
tar -czf sprouts-backup.tar.gz data/sprouts/
```

### Clean Up Old Data

```bash
# Remove debug images
rm -rf data/debug/*

# Remove old AI requests
find data/ai_requests -type f -mtime +1 -delete

# Remove old AI results
find data/ai_results -type f -mtime +7 -delete
```

## Testing

### Verify System is Working

```bash
# 1. Check all services are running
docker compose ps
# All should show "running" status

# 2. Check web interface
curl http://localhost:8001/health
# Should return: {"status":"ok"}

# 3. Check MQTT is receiving data
mosquitto_sub -h localhost -t "plantvision/#" -C 1
# Should show a message within a few seconds

# 4. Check plant data is being created
ls -la data/plants/
# Should see plant_000/ directory

# 5. Check web dashboard
# Open http://localhost:8001 in browser
# Should see plant visualization
```

### Test with Different Images

```bash
# Add your own image
cp /path/to/your/plant.jpg samples/my-plant.jpg

# Update docker-compose.yml
# Change INPUT_PATH=/samples/my-plant.jpg

# Restart
docker compose restart cpp-app
```

## Performance Tuning

### Reduce CPU Usage

```yaml
cpp-app:
  environment:
    - PUBLISH_INTERVAL_MS=5000    # Slower processing (5 seconds)
    - VISION_DEBUG_MODE=false     # Disable debug images
```

### Reduce Memory Usage

```yaml
services:
  cpp-app:
    deploy:
      resources:
        limits:
          memory: 512M
  
  ai:
    deploy:
      resources:
        limits:
          memory: 1G
```

### Speed Up Processing

```yaml
cpp-app:
  environment:
    - PUBLISH_INTERVAL_MS=500     # Faster processing (0.5 seconds)
    - THRESHOLD=120               # Less aggressive masking
```

## Updating PlantVision

```bash
# Stop services
docker compose down

# Pull latest code
git pull origin main

# Rebuild images
docker compose build

# Start with new version
docker compose up
```

## Getting Help

1. **Check Documentation**:
   - [Architecture Guide](docs/ARCHITECTURE.md)
   - [Data Organization](docs/DATA_ORGANIZATION.md)
   - [Deployment Guide](docs/DEPLOYMENT.md)

2. **Check Logs**:
   ```bash
   docker compose logs | grep -i error
   ```

3. **GitHub Issues**:
   - Search existing issues: https://github.com/TahriT/PlantViz/issues
   - Create new issue with logs and configuration

4. **Community**:
   - GitHub Discussions for questions
   - Include Docker version, OS, and error logs

## Next Steps

Once the system is running:

1. **Explore the Dashboard**: http://localhost:8001
2. **Monitor MQTT Data**: Use mosquitto_sub to see real-time telemetry
3. **Review Plant Data**: Check `data/plants/` directory
4. **Configure for Your Setup**: Adjust thresholds and camera settings
5. **Read the Docs**: Deep dive into [ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

**Need more help?** Check the main [README.md](README.md) or open an issue!
