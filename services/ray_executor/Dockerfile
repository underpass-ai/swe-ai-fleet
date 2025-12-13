# Ray Executor Service Dockerfile
# Multi-stage build for Python gRPC service with Ray
# Note: Using Python 3.11 to match Ray cluster (2.52.1-py311)
# Python 3.12 not available in official Ray images for version 2.52.1

FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install grpcio-tools for proto generation
RUN python -m pip install --no-cache-dir grpcio-tools==1.68.1

# Copy protobuf specs
# Build from project root: podman build -t ray-executor:latest -f services/ray_executor/Dockerfile .
COPY specs/fleet/ray_executor/v1/ray_executor.proto /build/specs/fleet/ray_executor/v1/ray_executor.proto

# Generate gRPC code from proto
RUN mkdir -p /build/services/ray_executor/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/build/specs/fleet/ray_executor/v1 \
    --python_out=/build/services/ray_executor/gen \
    --grpc_python_out=/build/services/ray_executor/gen \
    --pyi_out=/build/services/ray_executor/gen \
    ray_executor.proto && \
    # Fix known protoc bug: relative imports in _grpc.py files \
    sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' \
    /build/services/ray_executor/gen/ray_executor_pb2_grpc.py && \
    # Create __init__.py \
    echo 'from . import ray_executor_pb2, ray_executor_pb2_grpc' > \
    /build/services/ray_executor/gen/__init__.py && \
    echo '__all__ = ["ray_executor_pb2", "ray_executor_pb2_grpc"]' >> \
    /build/services/ray_executor/gen/__init__.py

#########################################
# Final stage
#########################################
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (including Ray)
COPY services/ray_executor/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy core module (ray_jobs)
COPY core/ray_jobs/ /app/core/ray_jobs/

# Copy application code
COPY services/ray_executor/application/ /app/services/ray_executor/application/
COPY services/ray_executor/domain/ /app/services/ray_executor/domain/
COPY services/ray_executor/infrastructure/ /app/services/ray_executor/infrastructure/
COPY services/ray_executor/__init__.py /app/services/ray_executor/
COPY services/ray_executor/server.py /app/

# Copy generated gRPC code from builder stage
COPY --from=builder /build/services/ray_executor/gen /app/services/ray_executor/gen

# Create __init__.py for core module and non-root user
RUN mkdir -p /app/core && \
    echo "" > /app/core/__init__.py && \
    groupadd -r appuser && \
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
