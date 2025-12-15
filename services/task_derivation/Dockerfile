# Task Derivation Service Dockerfile
# Multi-stage build for Python gRPC service

FROM python:3.13-slim AS builder

WORKDIR /build

# Install system deps for grpcio-tools compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install protobuf toolchain (pinned by repo constraints)
COPY constraints.txt /build/constraints.txt
RUN python -m pip install --no-cache-dir -c /build/constraints.txt grpcio-tools




# Copy API-first protobuf specs (requires build context at repo root)
# Build from project root: podman build -t task-derivation:latest -f services/task_derivation/Dockerfile .
COPY specs/fleet/task_derivation/v1/task_derivation.proto /build/specs/task_derivation.proto
COPY specs/fleet/ray_executor/v1/ray_executor.proto /build/specs/ray_executor.proto
COPY specs/fleet/context/v1/context.proto /build/specs/context.proto

# Generate Python stubs for Planning<->Task-Derivation contract
RUN mkdir -p /build/gen/task_derivation && \
    python -m grpc_tools.protoc \
        -I/build/specs \
        --python_out=/build/gen/task_derivation \
        --pyi_out=/build/gen/task_derivation \
        --grpc_python_out=/build/gen/task_derivation \
        /build/specs/task_derivation.proto && \
    sed -i 's/^import task_derivation_pb2/from . import task_derivation_pb2/' \
        /build/gen/task_derivation/task_derivation_pb2_grpc.py && \
    echo "" > /build/gen/task_derivation/__init__.py

# Generate Python stubs for Ray Executor client
# Note: Copy directly to task_derivation/gen/ (not subdirectory) to match import structure
RUN mkdir -p /build/gen/task_derivation && \
    python -m grpc_tools.protoc \
        -I/build/specs \
        --python_out=/build/gen/task_derivation \
        --pyi_out=/build/gen/task_derivation \
        --grpc_python_out=/build/gen/task_derivation \
        /build/specs/ray_executor.proto && \
    sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' \
        /build/gen/task_derivation/ray_executor_pb2_grpc.py && \
    sed -i 's/^from fleet.ray_executor.v1 import ray_executor_pb2/from . import ray_executor_pb2/' \
        /build/gen/task_derivation/ray_executor_pb2.py || true

# Generate Python stubs for Context Service client
# Note: Copy directly to task_derivation/gen/ (not subdirectory) to match import structure
RUN mkdir -p /build/gen/task_derivation && \
    python -m grpc_tools.protoc \
        -I/build/specs \
        --python_out=/build/gen/task_derivation \
        --pyi_out=/build/gen/task_derivation \
        --grpc_python_out=/build/gen/task_derivation \
        /build/specs/context.proto && \
    sed -i 's/^import context_pb2/from . import context_pb2/' \
        /build/gen/task_derivation/context_pb2_grpc.py && \
    sed -i 's/^from fleet.context.v1 import context_pb2/from . import context_pb2/' \
        /build/gen/task_derivation/context_pb2.py || true

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
COPY services/task_derivation/requirements.txt /app/
RUN pip install --no-cache-dir -c constraints.txt -r requirements.txt

COPY core/ /app/core/

# Copy generated gRPC code from builder stage
# Note: All stubs (context_pb2, task_derivation_pb2, ray_executor_pb2, etc.) must be directly in task_derivation/gen/
# to match imports like "from task_derivation.gen import context_pb2_grpc"
COPY --from=builder /build/gen/task_derivation/* /app/task_derivation/gen/

# Copy application code (similar to planning service structure)
COPY services/task_derivation/ /app/task_derivation/
COPY services/task_derivation/server.py /app/
COPY services/task_derivation/pyproject.toml /app/

# Copy task derivation configuration
COPY services/task_derivation/config/task_derivation.yaml /app/config/

# Create __init__.py files for proper Python module structure
RUN echo "" > /app/task_derivation/gen/__init__.py && \
    echo "" > /app/core/__init__.py

# Set Python path
ENV PYTHONPATH=/app

# Health check (optional - service runs as worker, no gRPC server yet)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run server (placeholder - will be replaced with full implementation)
CMD ["python", "server.py"]
