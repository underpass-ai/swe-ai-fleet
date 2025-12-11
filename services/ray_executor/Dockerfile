# syntax=docker/dockerfile:1
# Note: Using Python 3.11 to match Ray cluster (2.52.1-py311)
# Python 3.12 not available in official Ray images for version 2.52.1
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies with cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends gcc g++

# Install Python dependencies with cache mount
COPY services/ray_executor/requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir datamodel-code-generator pyyaml

# Generate gRPC code from proto (clean industry-standard approach)
COPY specs/fleet/ray_executor/v1/ray_executor.proto /app/specs/fleet/ray_executor/v1/ray_executor.proto
RUN mkdir -p /app/services/ray_executor/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/app/specs/fleet/ray_executor/v1 \
    --python_out=/app/services/ray_executor/gen \
    --grpc_python_out=/app/services/ray_executor/gen \
    --pyi_out=/app/services/ray_executor/gen \
    ray_executor.proto && \
    # Fix known protoc bug: relative imports in _grpc.py files \
    sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' \
    /app/services/ray_executor/gen/ray_executor_pb2_grpc.py && \
    # Create __init__.py \
    echo 'from . import ray_executor_pb2, ray_executor_pb2_grpc\n__all__ = ["ray_executor_pb2", "ray_executor_pb2_grpc"]' \
    > /app/services/ray_executor/gen/__init__.py

# Generate AsyncAPI models (NATS message payloads) inside Docker
# Copy AsyncAPI spec and generation script
COPY specs/asyncapi.yaml /app/specs/asyncapi.yaml
COPY scripts/specs/generate-asyncapi-models.sh /app/scripts/specs/generate-asyncapi-models.sh
RUN chmod +x /app/scripts/specs/generate-asyncapi-models.sh && \
    pip install --no-cache-dir datamodel-code-generator pyyaml && \
    cd /app && \
    bash scripts/specs/generate-asyncapi-models.sh

# Copy application code
# Note: core/nats/gen will be generated above, but we need to copy the infrastructure mappers
COPY core/nats/infrastructure/ /app/core/nats/infrastructure/
COPY core/ray_jobs/ /app/core/ray_jobs/
COPY services/ray_executor/ /app/services/ray_executor/

# Create non-root user
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 appuser && \
    chown -R appuser:appuser /app

# Set environment
ENV PYTHONPATH=/app/core:/app
ENV RAY_DEDUP_LOGS=0
# Disable log truncation - show full logs
ENV RAY_LOGGING_TO_STDERR=1
ENV RAY_LOGGING_ROTATE_BYTES=0
ENV RAY_LOGGING_ROTATE_BACKUP_COUNT=0

# Switch to non-root user
USER appuser

# Expose gRPC port
EXPOSE 50056

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50056'); channel.close()" || exit 1

# Run server
CMD ["python", "/app/services/ray_executor/server.py"]
