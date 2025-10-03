# PlantVision

A high-performance, real-time plant monitoring system with advanced morphological analysis, intelligent plant/sprout classification, and AI-powered insights. Features comprehensive phenotyping including branch/tip analysis, disease detection, and multi-stage growth tracking.

## 🛠️ Technology Stack

- **C++17+**: High-performance vision processing with OpenCV
- **Python 3.11**: AI inference (MiDaS, DPT) and web interface
- **FastAPI**: REST API and real-time web UI
- **OpenCV**: Computer vision and image processing
- **Eclipse Paho MQTT**: Message broker and telemetry streaming
- **Docker**: Containerized deployment with multi-stage builds

## 🌟 Key Features

### Advanced Plant Analysis
- **Intelligent Classification**: Automatic differentiation between sprouts (<5000px²) and mature plants (≥5000px²)
- **Morphological Analysis**: Branch/tip counting, skeleton analysis, shape descriptors (solidity, eccentricity, circularity)
- **Disease Detection**: Brown spot and yellowing identification with health scoring
- **Growth Stage Tracking**: From cotyledon to fruiting stages

### Enhanced Metrics & AI Integration
- **Vegetation Indices**: NDVI, EXG color analysis for plant health assessment
- **Multi-colorspace Analysis**: BGR, HSV, LAB color spaces
- **Change Detection**: Smart AI request generation (70% reduction in processing)
- **Depth Estimation**: Optional MiDaS/DPT Swin2 models for 3D analysis

### Real-time Streaming
- **MQTT Telemetry**: Hierarchical topic structure with UNS (Unified Namespace)
- **Web Dashboard**: Live monitoring with plant/sprout specific views
- **Casting Support**: Stream dashboard to any local cast device

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (Windows/macOS/Linux)
- Optional: Camera device for live capture (Linux/WSL2)

### Basic Deployment

```bash
# Clone the repository
git clone https://github.com/TahriT/sproutcast.git
cd PlantVision

# Start all services
docker compose up --build

# Access the web interface at http://localhost:8000
```

### MQTT Monitoring

Subscribe to plant telemetry:
```bash
# All sprout data
mosquitto_sub -h localhost -t "plantvision/+/+/+/sprouts/#"

# All plant data
mosquitto_sub -h localhost -t "plantvision/+/+/+/plants/#"

# System status
mosquitto_sub -h localhost -t "plantvision/+/+/+/system/status"
```

## ⚙️ Configuration

Edit `docker-compose.yml` or create a `.env` file:

```bash
# Camera Configuration
CAMERA_ID=0                    # Camera device index
INPUT_MODE=IMAGE              # IMAGE or CAMERA
INPUT_PATH=/samples/plant.jpg # Sample image path

# Processing Parameters
THRESHOLD=100                 # Green mask threshold
SCALE_PX_PER_CM=28.0         # Pixel to cm conversion (0 = auto-detect)
PUBLISH_INTERVAL_MS=1000     # MQTT publish frequency

# MQTT Configuration
MQTT_HOST=mqtt-broker
MQTT_PORT=1883

# Network Ports
WEB_PORT=8000
MQTT_PORT=1883
```

## 📊 Data Organization

```
/app/data/
├── config.json              # System configuration
├── frame_raw.jpg           # Latest camera capture
├── frame_annotated.jpg     # Analysis visualization
├── sprouts/                # Early growth stage data
│   ├── sprout_000/
│   │   ├── data.json      # Sprout telemetry
│   │   ├── crop.jpg       # Cropped image
│   │   └── highlight.jpg  # Analysis overlay
│   └── summary.json       # Aggregate statistics
├── plants/                 # Mature plant data
│   ├── plant_000/
│   │   ├── data.json      # Plant telemetry
│   │   ├── crop.jpg       # Cropped image
│   │   └── highlight.jpg  # Analysis overlay
│   └── summary.json       # Aggregate statistics
└── ai_requests/           # AI processing queue
    └── ai_results/        # AI inference results
```

## 🌱 Plant Classification

### Sprout Detection (Early Growth)
- **Threshold**: Area < 5000 pixels, Height < 8 cm
- **Metrics**: Leaf count, cotyledon tracking, basic color analysis
- **Update Rate**: 500ms (high-frequency for rapid growth)
- **Focus**: Germination tracking, early health assessment

### Mature Plant Detection (Advanced Growth)
- **Threshold**: Area ≥ 5000 pixels, Height ≥ 8 cm
- **Metrics**: Petal/bud/fruit counting, disease detection, stress analysis
- **Update Rate**: 1000ms (standard monitoring)
- **Focus**: Phenological stages, comprehensive health scoring

## 📡 MQTT Topic Structure

```
plantvision/{room}/{area}/{camera}/
├── system/
│   ├── status           # System health
│   ├── config          # Configuration updates
│   └── alerts          # Error notifications
├── sprouts/
│   ├── {id}/telemetry  # Individual sprout data
│   └── summary         # All sprouts aggregate
└── plants/
    ├── {id}/telemetry  # Individual plant data
    └── summary         # All plants aggregate
```

## 📖 Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)**: Detailed system architecture and VisionProcessor design
- **[Deployment Guide](docs/DEPLOYMENT.md)**: CI/CD setup and production deployment
- **[Data Organization](docs/DATA_ORGANIZATION.md)**: File structure and MQTT topic hierarchy
- **[Enhancement Roadmap](docs/ENHANCEMENT_ROADMAP.md)**: Planned features and improvements

## 🐛 Troubleshooting

### Camera not detected
```bash
# Linux: Check camera permissions
ls -la /dev/video*
sudo usermod -a -G video $USER

# Windows: Use INPUT_MODE=IMAGE for testing
```

### MQTT connection failed
```bash
# Test MQTT broker connectivity
docker logs sc-mqtt
mosquitto_pub -h localhost -p 1883 -t test -m "hello"
```

### AI processing not working
```bash
# Check AI service logs
docker logs sc-ai

# Verify model files exist
docker exec sc-ai ls -la /app/models/
```

## 🏗️ Project Structure

```
PlantVision/
├── cpp/                   # C++ vision processing
│   ├── src/
│   │   ├── main.cpp
│   │   ├── vision_processor.cpp
│   │   ├── morphology_analysis.cpp
│   │   ├── leaf_area.cpp
│   │   └── mqtt_client.cpp
│   ├── include/
│   └── CMakeLists.txt
├── web/                   # FastAPI web interface
│   ├── main.py
│   ├── static/
│   └── templates/
├── ai/                    # Python AI inference
│   ├── main.py
│   └── requirements.txt
├── models/                # AI model storage
├── data/                  # Runtime data
├── docs/                  # Additional documentation
└── docker-compose.yml
```

## 🤝 Contributing

Contributions are welcome! Please ensure:
- C++ code follows modern C++17 standards
- All shared resources use proper mutex protection
- Changes include relevant documentation updates
- Docker builds complete successfully

## 📄 License

This project uses components inspired by PlantCV (Mozilla Public License 2.0).
See individual component licenses for details.

---

**Built with 🌱 for plant science and monitoring**

