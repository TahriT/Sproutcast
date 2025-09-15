FROM ubuntu:22.04 AS build

# Install build dependencies including filesystem support
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential cmake git \
      libopencv-dev \
      nlohmann-json3-dev \
      libssl-dev ca-certificates \
      && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Build with C++17 filesystem support
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 && \
    cmake --build build --config Release

FROM ubuntu:22.04 AS runtime
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libopencv-dev \
      nlohmann-json3-dev \
      libssl3 ca-certificates \
      && rm -rf /var/lib/apt/lists/*

# Create necessary directories for new architecture
WORKDIR /app
RUN mkdir -p /app/data/ai_requests /app/data/ai_results /app/data/debug \
             /app/data/sprouts /app/data/plants

COPY --from=build /app/build/plantvision_cpp /app/plantvision_cpp

# Updated environment variables for consolidated architecture
ENV CAMERA_ID=0 MQTT_HOST=localhost MQTT_PORT=1883 MQTT_TOPIC=sprout/area \
    PUBLISH_INTERVAL_MS=30000 THRESHOLD=100 \
    CONFIG_PATH=/app/data/config.json \
    VISION_DEBUG_MODE=false

CMD ["/app/plantvision_cpp"]

