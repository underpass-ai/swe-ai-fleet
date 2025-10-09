# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY services/orchestrator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source
COPY src/ /app/src/
COPY services/orchestrator/ /app/services/orchestrator/

# Create non-root user for security
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 appuser && \
    chown -R appuser:appuser /app

# Set PYTHONPATH
ENV PYTHONPATH=/app/src:/app

# Switch to non-root user
USER appuser

# Expose gRPC port
EXPOSE 50055

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50055'); channel.close()" || exit 1

# Run server
CMD ["python", "services/orchestrator/server.py"]

