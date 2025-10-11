# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base

WORKDIR /app

# Install system dependencies with cache mounts
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++

# Copy requirements and install dependencies with cache mount
COPY services/context/requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Copy protobuf spec and configuration
COPY specs/context.proto /app/specs/context.proto
COPY config/prompt_scopes.yaml /app/config/prompt_scopes.yaml

# Generate gRPC code from protobuf during build
RUN mkdir -p /app/services/context/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/app/specs \
    --python_out=/app/services/context/gen \
    --grpc_python_out=/app/services/context/gen \
    --pyi_out=/app/services/context/gen \
    context.proto && \
    # Fix imports in generated files \
    sed -i 's/^import context_pb2/from . import context_pb2/' \
    /app/services/context/gen/context_pb2_grpc.py && \
    # Create __init__.py \
    echo 'from . import context_pb2, context_pb2_grpc\n__all__ = ["context_pb2", "context_pb2_grpc"]' \
    > /app/services/context/gen/__init__.py

# Copy project source
COPY src/ /app/src/
COPY services/context/ /app/services/context/

# Create non-root user for security
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 appuser && \
    chown -R appuser:appuser /app

# Set PYTHONPATH
ENV PYTHONPATH=/app/src:/app

# Switch to non-root user
USER appuser

# Expose gRPC port
EXPOSE 50054

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50054'); channel.close()" || exit 1

# Run server
CMD ["python", "services/context/server.py"]

