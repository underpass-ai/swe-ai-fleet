# Context Service Dockerfile
# Multi-stage build for Python gRPC service

FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install protobuf toolchain (pinned by repo constraints)
COPY constraints.txt /build/constraints.txt
RUN python -m pip install --no-cache-dir -c /build/constraints.txt grpcio-tools

# Copy protobuf spec and configuration
# Build from project root: podman build -t context:latest -f services/context/Dockerfile .
COPY specs/fleet/context/v1/context.proto /build/specs/fleet/context/v1/context.proto
COPY config/prompt_scopes.yaml /build/config/prompt_scopes.yaml

# Generate gRPC code from protobuf
RUN mkdir -p /build/services/context/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/build/specs/fleet/context/v1 \
    --python_out=/build/services/context/gen \
    --grpc_python_out=/build/services/context/gen \
    --pyi_out=/build/services/context/gen \
    /build/specs/fleet/context/v1/context.proto && \
    sed -i 's/^import context_pb2/from . import context_pb2/' \
    /build/services/context/gen/context_pb2_grpc.py && \
    echo 'from . import context_pb2, context_pb2_grpc' > \
    /build/services/context/gen/__init__.py && \
    echo '__all__ = ["context_pb2", "context_pb2_grpc"]' >> \
    /build/services/context/gen/__init__.py

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
COPY constraints.txt /app/constraints.txt
COPY services/context/requirements.txt /app/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -c constraints.txt -r requirements.txt

# Verify nats-py installation (test both nats.js and nats.aio)
RUN python -c "from nats.js import JetStreamContext; from nats.aio.client import Client; print('nats-py installed successfully')" || \
    (echo "ERROR: nats-py installation failed" && exit 1)

# Copy shared kernel (event envelope) and core modules (bounded contexts)
COPY core/shared/ /app/core/shared/
COPY core/context/ /app/core/context/
COPY core/memory/ /app/core/memory/
COPY core/reports/ /app/core/reports/

# Copy context service
COPY services/context/ /app/services/context/

# Copy configuration
COPY config/prompt_scopes.yaml /app/config/prompt_scopes.yaml

# Copy generated gRPC code from builder stage
COPY --from=builder /build/services/context/gen /app/services/context/gen

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
EXPOSE 50054

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50054'); channel.close()" || exit 1

# Run server
CMD ["python", "services/context/server.py"]
