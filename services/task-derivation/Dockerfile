# Task Derivation Service Dockerfile (builder stage only)
# ------------------------------------------------------
# API-first: we only materialize protobuf stubs during the build stage.
# Runtime/serving stage will be added once the service entrypoint is finalized.

FROM python:3.11-slim AS builder

WORKDIR /build

# Install system deps for grpcio-tools compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install grpcio-tools to compile protobuf/gRPC stubs
RUN python -m pip install --no-cache-dir grpcio-tools==1.60.0

# Copy API-first protobuf specs (requires build context at repo root)
# Usage example:
#   podman build -t task-derivation:stubs -f services/task-derivation/Dockerfile .
COPY specs/fleet/task_derivation/v1/task_derivation.proto /build/specs/task_derivation.proto
COPY specs/fleet/ray_executor/v1/ray_executor.proto /build/specs/ray_executor.proto

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
RUN mkdir -p /build/gen/ray_executor && \
    python -m grpc_tools.protoc \
        -I/build/specs \
        --python_out=/build/gen/ray_executor \
        --pyi_out=/build/gen/ray_executor \
        --grpc_python_out=/build/gen/ray_executor \
        /build/specs/ray_executor.proto && \
    sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' \
        /build/gen/ray_executor/ray_executor_pb2_grpc.py && \
    echo "" > /build/gen/ray_executor/__init__.py

# NOTE: Future runtime stage will COPY the generated stubs from /build/gen/*
# into the application image once the service server entrypoint is ready.

