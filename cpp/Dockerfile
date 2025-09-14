FROM ubuntu:22.04 AS build

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

RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && \
    cmake --build build --config Release

FROM ubuntu:22.04 AS runtime
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libopencv-dev \
      nlohmann-json3-dev \
      libssl3 ca-certificates \
      && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /app/build/plantvision_cpp /app/plantvision_cpp

ENV CAMERA_ID=0 MQTT_HOST=localhost MQTT_PORT=1883 MQTT_TOPIC=sprout/area \
    PUBLISH_INTERVAL_MS=1000 THRESHOLD=100

CMD ["/app/plantvision_cpp"]

