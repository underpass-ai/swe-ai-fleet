# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies with cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++

# Copy requirements and install dependencies with pip cache mount
COPY services/orchestrator/requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Install grpcio-tools for generating protobuf code
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir grpcio-tools>=1.60.0

# Copy protobuf spec
COPY specs/orchestrator.proto /app/specs/orchestrator.proto

# Generate gRPC code from protobuf during build
RUN mkdir -p /app/services/orchestrator/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/app/specs \
    --python_out=/app/services/orchestrator/gen \
    --grpc_python_out=/app/services/orchestrator/gen \
    --pyi_out=/app/services/orchestrator/gen \
    orchestrator.proto && \
    # Fix imports in generated files \
    sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' \
    /app/services/orchestrator/gen/orchestrator_pb2_grpc.py && \
    # Create __init__.py \
    echo 'from . import orchestrator_pb2, orchestrator_pb2_grpc\n__all__ = ["orchestrator_pb2", "orchestrator_pb2_grpc"]' \
    > /app/services/orchestrator/gen/__init__.py

# Copy project source (after generating proto files)
COPY src/ /app/src/
COPY services/orchestrator/server.py /app/services/orchestrator/server.py

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

