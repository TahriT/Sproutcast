# Multi-stage build for Web UI
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user for security
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
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production
COPY --from=deps /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy source code
COPY . /app

# Change ownership to non-root user
RUN chown -R appuser:appuser /app
USER appuser

ENV MQTT_HOST=mqtt-broker MQTT_PORT=1883

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production server with better performance
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

