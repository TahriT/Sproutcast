# Unified Sproutcast - All-in-One Plant Vision System
# Combines C++ vision processing, Python web UI, and AI inference in a single container

FROM ubuntu:22.04 AS base

ARG DEBIAN_FRONTEND=noninteractive

# Install system dependencies for both C++ and Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      # C++ build tools
      build-essential cmake git pkg-config \
      # OpenCV and dependencies
      libopencv-dev libopencv-core4.5d libopencv-imgproc4.5d \
      libopencv-imgcodecs4.5d libopencv-videoio4.5d \
      # JSON library
      nlohmann-json3-dev \
      # Python
      python3.11 python3.11-dev python3-pip python3-venv \
      # System utilities
      curl wget ca-certificates \
      # AI dependencies
      libglib2.0-0 libglvnd0 libgl1 libsm6 libxext6 libxrender-dev libgomp1 \
      # Process management
      supervisor \
      # MQTT Broker
      mosquitto mosquitto-clients \
      && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# ==================== BUILD C++ APPLICATION ====================
FROM base AS cpp-builder

COPY cpp/CMakeLists.txt /app/cpp/
COPY cpp/include/ /app/cpp/include/
COPY cpp/src/ /app/cpp/src/

WORKDIR /app/cpp

RUN cmake -S . -B build \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_STANDARD=17 \
      -DCMAKE_CXX_FLAGS="-O3" && \
    cmake --build build --config Release --parallel $(nproc)

# ==================== SETUP PYTHON ENVIRONMENT ====================
FROM base AS python-deps

# Create virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install web UI dependencies
COPY web/requirements.txt /tmp/web-requirements.txt
RUN pip install --no-cache-dir -r /tmp/web-requirements.txt

# Install AI dependencies
COPY ai/requirements.txt /tmp/ai-requirements.txt
RUN pip install --no-cache-dir -r /tmp/ai-requirements.txt

# ==================== FINAL UNIFIED IMAGE ====================
FROM base AS production

# Copy Python virtual environment
COPY --from=python-deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy compiled C++ application
COPY --from=cpp-builder /app/cpp/build/plantvision_cpp /app/sproutcast-vision
RUN chmod +x /app/sproutcast-vision

# Copy Python applications
COPY web/ /app/web/
COPY ai/ /app/ai/

# Create necessary directories
RUN mkdir -p \
    /app/data/ai_requests \
    /app/data/ai_results \
    /app/data/debug \
    /app/data/sprouts \
    /app/data/plants \
    /app/models \
    /app/logs \
    /app/config \
    /mosquitto/data \
    /mosquitto/log

# Configure Mosquitto MQTT broker
RUN echo "listener 1883" > /mosquitto/config/mosquitto.conf && \
    echo "allow_anonymous true" >> /mosquitto/config/mosquitto.conf && \
    echo "persistence true" >> /mosquitto/config/mosquitto.conf && \
    echo "persistence_location /mosquitto/data/" >> /mosquitto/config/mosquitto.conf && \
    echo "log_dest file /mosquitto/log/mosquitto.log" >> /mosquitto/config/mosquitto.conf && \
    echo "log_dest stdout" >> /mosquitto/config/mosquitto.conf && \
    chown -R mosquitto:mosquitto /mosquitto

# Setup Supervisor for process management
RUN mkdir -p /etc/supervisor/conf.d /var/log/supervisor

# Create supervisor configuration
COPY <<EOF /etc/supervisor/conf.d/sproutcast.conf
[supervisord]
nodaemon=true
user=root
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[program:mqtt]
command=/usr/sbin/mosquitto -c /mosquitto/config/mosquitto.conf
user=mosquitto
autostart=true
autorestart=true
priority=100
stdout_logfile=/var/log/supervisor/mqtt-stdout.log
stderr_logfile=/var/log/supervisor/mqtt-stderr.log

[program:vision]
command=/app/sproutcast-vision
directory=/app
user=appuser
autostart=true
autorestart=true
priority=200
stdout_logfile=/var/log/supervisor/vision-stdout.log
stderr_logfile=/var/log/supervisor/vision-stderr.log
environment=HOME="/home/appuser",USER="appuser"

[program:web]
command=/opt/venv/bin/uvicorn main:app --host 0.0.0.0 --port 5323 --workers 2
directory=/app/web
user=appuser
autostart=true
autorestart=true
priority=200
stdout_logfile=/var/log/supervisor/web-stdout.log
stderr_logfile=/var/log/supervisor/web-stderr.log

[program:ai]
command=/opt/venv/bin/python main.py
directory=/app/ai
user=appuser
autostart=true
autorestart=true
priority=200
stdout_logfile=/var/log/supervisor/ai-stdout.log
stderr_logfile=/var/log/supervisor/ai-stderr.log
EOF

# Change ownership
RUN chown -R appuser:appuser /app /var/log/supervisor

# Environment variables with defaults
ENV CAMERA_ID=0 \
    MQTT_HOST=localhost \
    MQTT_PORT=1883 \
    MQTT_TOPIC=sproutcast/default \
    PUBLISH_INTERVAL_MS=30000 \
    THRESHOLD=100 \
    INPUT_MODE=IMAGE \
    INPUT_PATH=/app/samples/plant.jpg \
    CONFIG_PATH=/app/data/config.json \
    VISION_DEBUG_MODE=false \
    LOG_LEVEL=INFO \
    SCALE_PX_PER_CM=28.0 \
    WEB_PORT=5323 \
    DATA_DIR=/app/data \
    MODELS_DIR=/app/models

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5323/health || exit 1

# Expose ports
EXPOSE 5323 1883 9001

# Start all services with supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
