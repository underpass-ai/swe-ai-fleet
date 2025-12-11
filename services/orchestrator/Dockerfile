# Orchestrator Service Dockerfile
# Multi-stage build for Python gRPC service

FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install grpcio-tools for proto generation
# Using 1.68.1 for Python 3.13 compatibility (has wheels, no compilation needed)
RUN python -m pip install --no-cache-dir grpcio-tools==1.68.1

# Copy protobuf specs (new versioned structure)
# Build from project root: podman build -t orchestrator:latest -f services/orchestrator/Dockerfile .
COPY specs/fleet/orchestrator/v1/orchestrator.proto /build/specs/fleet/orchestrator/v1/orchestrator.proto
COPY specs/fleet/ray_executor/v1/ray_executor.proto /build/specs/fleet/ray_executor/v1/ray_executor.proto

# Generate gRPC code with source_relative paths (industry standard)
RUN mkdir -p /build/services/orchestrator/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/build/specs/fleet/orchestrator/v1 \
    --proto_path=/build/specs/fleet/ray_executor/v1 \
    --python_out=/build/services/orchestrator/gen \
    --grpc_python_out=/build/services/orchestrator/gen \
    --pyi_out=/build/services/orchestrator/gen \
    /build/specs/fleet/orchestrator/v1/orchestrator.proto \
    /build/specs/fleet/ray_executor/v1/ray_executor.proto && \
    sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' \
    /build/services/orchestrator/gen/orchestrator_pb2_grpc.py && \
    sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' \
    /build/services/orchestrator/gen/ray_executor_pb2_grpc.py && \
    echo 'from . import orchestrator_pb2, orchestrator_pb2_grpc, ray_executor_pb2, ray_executor_pb2_grpc' > \
    /build/services/orchestrator/gen/__init__.py && \
    echo '__all__ = ["orchestrator_pb2", "orchestrator_pb2_grpc", "ray_executor_pb2", "ray_executor_pb2_grpc"]' >> \
    /build/services/orchestrator/gen/__init__.py

#########################################
# Final stage
#########################################
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/orchestrator/requirements.txt /app/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Verify nats-py installation (test both nats.js and nats.aio)
RUN python -c "from nats.js import JetStreamContext; from nats.aio.client import Client; print('nats-py installed successfully')" || \
    (echo "ERROR: nats-py installation failed" && exit 1)

# Copy core orchestrator module (bounded context)
COPY core/orchestrator/ /app/core/orchestrator/

# Copy orchestrator service
COPY services/orchestrator/ /app/services/orchestrator/

# Copy generated gRPC code from builder stage
COPY --from=builder /build/services/orchestrator/gen /app/services/orchestrator/gen

# Create __init__.py files for proper Python module structure
RUN echo "" > /app/core/__init__.py && \
    echo "" > /app/services/__init__.py

# Create non-root user for security
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 appuser && \
    chown -R appuser:appuser /app

# Set PYTHONPATH
ENV PYTHONPATH=/app/core:/app

# Switch to non-root user
USER appuser

# Expose gRPC port
EXPOSE 50055

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50055'); channel.close()" || exit 1

# Run server
CMD ["python", "services/orchestrator/server.py"]
