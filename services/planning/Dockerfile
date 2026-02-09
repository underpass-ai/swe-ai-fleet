# Planning Service Dockerfile
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
RUN python -m pip install --no-cache-dir --upgrade pip setuptools && \
    python -m pip install --no-cache-dir -c /build/constraints.txt grpcio-tools

# Copy proto specs from project (expects build context at project root)
# Build from project root: podman build -t planning:latest -f services/planning/Dockerfile .
COPY specs/fleet/planning/v2/planning.proto /build/specs/planning.proto
COPY specs/fleet/task_derivation/v1/task_derivation.proto /build/specs/task_derivation.proto
COPY specs/fleet/context/v1/context.proto /build/specs/context.proto
COPY specs/fleet/orchestrator/v1/orchestrator.proto /build/specs/orchestrator.proto
COPY specs/fleet/ray_executor/v1/ray_executor.proto /build/specs/ray_executor.proto
COPY specs/fleet/planning_ceremony/v1/planning_ceremony.proto /build/specs/planning_ceremony.proto

# Generate Python gRPC stubs for Planning Service
RUN mkdir -p /build/gen && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --pyi_out=/build/gen \
    --grpc_python_out=/build/gen \
    /build/specs/planning.proto && \
    sed -i 's/^import planning_pb2/from . import planning_pb2/' \
    /build/gen/planning_pb2_grpc.py

# Generate Python gRPC stubs for Task Derivation <-> Planning contract
RUN python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --pyi_out=/build/gen \
    --grpc_python_out=/build/gen \
    /build/specs/task_derivation.proto && \
    sed -i 's/^import task_derivation_pb2/from . import task_derivation_pb2/' \
    /build/gen/task_derivation_pb2_grpc.py

# Generate Python gRPC stubs for Context Service (client)
RUN python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --pyi_out=/build/gen \
    --grpc_python_out=/build/gen \
    /build/specs/context.proto && \
    sed -i 's/^import context_pb2/from . import context_pb2/' \
    /build/gen/context_pb2_grpc.py

# Generate Python gRPC stubs for Orchestrator Service (client)
RUN python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --pyi_out=/build/gen \
    --grpc_python_out=/build/gen \
    /build/specs/orchestrator.proto && \
    sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' \
    /build/gen/orchestrator_pb2_grpc.py

# Generate Python gRPC stubs for Ray Executor Service (client)
RUN python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --pyi_out=/build/gen \
    --grpc_python_out=/build/gen \
    /build/specs/ray_executor.proto && \
    sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' \
    /build/gen/ray_executor_pb2_grpc.py

# Generate Python gRPC stubs for Planning Ceremony Processor (client)
RUN python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --pyi_out=/build/gen \
    --grpc_python_out=/build/gen \
    /build/specs/planning_ceremony.proto && \
    sed -i 's/^import planning_ceremony_pb2/from . import planning_ceremony_pb2/' \
    /build/gen/planning_ceremony_pb2_grpc.py && \
    echo "" > /build/gen/__init__.py

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
COPY services/planning/requirements.txt /app/
RUN pip install --no-cache-dir -c constraints.txt -r requirements.txt

# Copy core module (shared value objects - TODO: refactor to remove this dependency)
COPY core/ /app/core/

# Copy application code (package is now at root level after restructuring)
# Copy package directories and files
COPY services/planning/application/ /app/planning/application/
COPY services/planning/domain/ /app/planning/domain/
COPY services/planning/infrastructure/ /app/planning/infrastructure/
COPY services/planning/__init__.py /app/planning/
COPY services/planning/server.py /app/

# Copy generated gRPC code from builder stage to planning.gen
COPY --from=builder /build/gen /app/planning/gen

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50054'); channel.channel_ready()" || exit 1

# Expose gRPC port
EXPOSE 50054

# Run server
CMD ["python", "server.py"]
