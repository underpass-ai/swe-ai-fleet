# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies with cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++

# Install Python dependencies with cache mount
COPY services/ray-executor/requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Generate gRPC code from proto (new versioned structure)
COPY specs/fleet/ray_executor/v1/ray_executor.proto /app/specs/fleet/ray_executor/v1/ray_executor.proto
RUN mkdir -p /app/ray-executor/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/app/specs/fleet \
    --python_out=/app/ray-executor/gen \
    --grpc_python_out=/app/ray-executor/gen \
    --pyi_out=/app/ray-executor/gen \
    ray_executor/v1/ray_executor.proto && \
    # Move generated files from subdirectory to gen/ root \
    mv /app/ray-executor/gen/ray_executor/v1/* /app/ray-executor/gen/ && \
    rm -rf /app/ray-executor/gen/ray_executor && \
    # Fix imports \
    sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' \
    /app/ray-executor/gen/ray_executor_pb2_grpc.py && \
    sed -i 's/from fleet\.ray_executor\.v1 import/from . import/g' \
    /app/ray-executor/gen/*.py && \
    echo 'from . import ray_executor_pb2, ray_executor_pb2_grpc\n__all__ = ["ray_executor_pb2", "ray_executor_pb2_grpc"]' \
    > /app/ray-executor/gen/__init__.py

# Copy application code
COPY src/ /app/src/
COPY services/ray-executor/ /app/ray-executor/

# Create non-root user
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 appuser && \
    chown -R appuser:appuser /app

# Set PYTHONPATH to include src directory
ENV PYTHONPATH=/app/src:/app

# Switch to non-root user
USER appuser

# Set working directory to ray-executor
WORKDIR /app/ray-executor

# Expose gRPC port
EXPOSE 50056

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50056'); channel.close()" || exit 1

# Run server
CMD ["python", "server.py"]
