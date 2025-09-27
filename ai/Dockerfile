# Multi-stage build for AI module
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1-mesa-glx libglib2.0-0 \
    libsm6 libxext6 libxrender-dev libgomp1 \
    libgcc-s1 \
    curl wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Dependencies stage
FROM base as deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --user -r /app/requirements.txt

# Development stage
FROM base as development
COPY --from=deps /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . /app
ENV MQTT_HOST=localhost MQTT_PORT=1883
CMD ["python", "main.py"]

# Production stage
FROM base as production
COPY --from=deps /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy source code
COPY . /app

# Create models directory and set permissions
RUN mkdir -p /app/models /app/cache /app/logs \
    && chown -R appuser:appuser /app

ENV MQTT_HOST=mqtt-broker \
    MQTT_PORT=1883 \
    MODEL_CACHE_DIR=/app/models \
    LOG_LEVEL=INFO

# Add health check
HEALTHCHECK --interval=60s --timeout=15s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

USER appuser

CMD ["python", "main.py"]

