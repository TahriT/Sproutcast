# PlantVision

End-to-end example to estimate plant leaf area using OpenCV (C++) and publish via MQTT, with a FastAPI web UI for configuration and monitoring. Runs via Docker Compose and includes a Mosquitto broker.

## Stack
- C++ OpenCV app estimates leaf area and publishes JSON to `plant/area`
- Mosquitto MQTT broker
- FastAPI web UI subscribes to topic and shows latest payload

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

