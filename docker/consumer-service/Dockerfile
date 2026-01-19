# Multi-stage Dockerfile for Kafka Consumer Service

# Build stage
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

LABEL maintainer="devops@hyperscale.com"
LABEL description="HyperScale Kafka Consumer Service"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    librdkafka1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r consumer && \
    useradd -r -g consumer -u 1001 consumer && \
    chown -R consumer:consumer /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/consumer/.local

# Copy application code
COPY --chown=consumer:consumer . .

# Switch to non-root user
USER consumer

# Add local bin to PATH
ENV PATH=/home/consumer/.local/bin:$PATH

# Environment variables for Kafka
ENV KAFKA_BOOTSTRAP_SERVERS="" \
    KAFKA_GROUP_ID="hyperscale-consumer-group" \
    KAFKA_AUTO_OFFSET_RESET="earliest"

# Run consumer
CMD ["python", "consumer.py"]
