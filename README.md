# SproutCast

End-to-end real-time plant monitoring system with advanced morphological analysis using OpenCV (C++), AI-powered insights, and casting capability for dashboard viewing. Features comprehensive plant phenotyping including branch/tip analysis, disease detection, and enhanced color analysis with vegetation indices.

## Stack
- C++ OpenCV app with advanced morphological analysis (skeleton analysis, branch/tip detection, disease monitoring)
- AI component with change detection optimization for efficient processing
- Mosquitto MQTT broker with SproutCast topic structure
- FastAPI web UI with real-time dashboard and Google Cast support
- Advanced plant phenotyping with NDVI, EXG color analysis, and health scoring

## Key Features
- 🌱 **Advanced Plant Analysis**: Branch/tip counting, skeleton analysis, morphological descriptors
- 🔬 **Disease Detection**: Brown spot and yellowing identification with health scoring
- 📊 **Enhanced Metrics**: NDVI, EXG vegetation indices, solidity, eccentricity, circularity
- 🎯 **AI Optimization**: Change detection system to minimize AI processing overhead
- 📺 **Casting Support**: Cast dashboard to any local cast device for real-time monitoring
- 🚀 **Real-time Processing**: Optimized pipeline with configurable frame analysis intervals

## Prerequisites
- Docker Desktop (Windows/macOS/Linux)
- Optional camera on `/dev/video0` for Linux. On Windows, remove the camera device mapping in `docker-compose.yml` or use WSL2 with camera passthrough.

## Quick start
```bash
# From repo root
docker compose up --build
```

Open the web UI at http://localhost:8000

You can also subscribe to MQTT with a client:
```bash
# Using mosquitto_sub if installed locally
mosquitto_sub -h localhost -t plant/area -v
```

## Configuration
The C++ app accepts environment variables (set in `docker-compose.yml`):
- `CAMERA_ID` (default: 0)
- `THRESHOLD` (default: 100)
- `PUBLISH_INTERVAL_MS` (default: 1000)
- `SCALE_PX_PER_CM` (default: 0)
- `MQTT_HOST` (default: mqtt-broker)
- `MQTT_PORT` (default: 1883)
- `MQTT_TOPIC` (default: plant/area)
- `INPUT_MODE` (default: IMAGE; options: IMAGE, CAMERA)
- `INPUT_PATH` (default: /samples/plant.jpg when IMAGE)

Web UI environment:
- `MQTT_HOST` (default: mqtt-broker)
- `MQTT_PORT` (default: 1883)

## Notes
- Default mode uses a sample image mounted at `./samples/plant.jpg`.
- On Windows, camera passthrough to Linux containers is not trivial. Keep `INPUT_MODE=IMAGE` for now. If you move to camera, set `INPUT_MODE=CAMERA` and configure device mapping appropriately for your environment.
- The leaf area is computed via simple thresholding; adapt `THRESHOLD` and pipeline as needed.

## Structure
```
cpp/
  Dockerfile
  CMakeLists.txt
  include/
    leaf_area.hpp
    mqtt_client.hpp
  src/
    leaf_area.cpp
    mqtt_client.cpp
    main.cpp
web/
  Dockerfile
  requirements.txt
  main.py
mqtt/
  mosquitto.conf
docker-compose.yml
```

