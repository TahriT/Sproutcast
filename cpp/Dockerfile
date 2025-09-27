# Multi-stage C++ build optimized for CI/CD
FROM ubuntu:22.04 AS dependencies

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential cmake git \
      libopencv-dev \
      nlohmann-json3-dev \
      libssl-dev ca-certificates \
      wget pkg-config \
      && rm -rf /var/lib/apt/lists/*

# Build stage
FROM dependencies AS build

WORKDIR /app
COPY CMakeLists.txt /app/
COPY include/ /app/include/
COPY src/ /app/src/

# Build with optimizations and caching
RUN cmake -S . -B build \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_STANDARD=17 \
      -DCMAKE_CXX_FLAGS="-O3 -march=native" && \
    cmake --build build --config Release --parallel $(nproc)

# Test stage (optional)
FROM build AS test
RUN if [ -f build/plantvision_cpp_test ]; then \
      ./build/plantvision_cpp_test; \
    fi

# Production runtime
FROM ubuntu:22.04 AS production

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libopencv-core4.5d libopencv-imgproc4.5d libopencv-imgcodecs4.5d \
      libopencv-videoio4.5d libopencv-features2d4.5d \
      libssl3 ca-certificates \
      curl \
      && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Create necessary directories for new architecture
RUN mkdir -p /app/data/ai_requests /app/data/ai_results /app/data/debug \
             /app/data/sprouts /app/data/plants \
             /app/models \
             /app/logs

# Copy binary from build stage
COPY --from=build /app/build/plantvision_cpp /app/plantvision_cpp
RUN chmod +x /app/plantvision_cpp

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Updated environment variables for consolidated architecture
ENV CAMERA_ID=0 \
    MQTT_HOST=mqtt-broker \
    MQTT_PORT=1883 \
    MQTT_TOPIC=sprout/area \
    PUBLISH_INTERVAL_MS=30000 \
    THRESHOLD=100 \
    CONFIG_PATH=/app/data/config.json \
    VISION_DEBUG_MODE=false \
    LOG_LEVEL=INFO

# Add health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD test -f /app/data/frame_raw.jpg || exit 1

USER appuser

CMD ["/app/plantvision_cpp"]

