FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY tests/e2e/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy proto specs
COPY specs/fleet/orchestrator/v1/orchestrator.proto /app/specs/fleet/orchestrator/v1/orchestrator.proto
COPY specs/fleet/ray_executor/v1/ray_executor.proto /app/specs/fleet/ray_executor/v1/ray_executor.proto
COPY specs/fleet/context/v1/context.proto /app/specs/fleet/context/v1/context.proto

# Generate gRPC code
RUN mkdir -p /app/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/app/specs/fleet/orchestrator/v1 \
    --proto_path=/app/specs/fleet/ray_executor/v1 \
    --proto_path=/app/specs/fleet/context/v1 \
    --python_out=/app/gen \
    --grpc_python_out=/app/gen \
    --pyi_out=/app/gen \
    orchestrator.proto \
    ray_executor.proto \
    context.proto && \
    sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' \
    /app/gen/orchestrator_pb2_grpc.py && \
    sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' \
    /app/gen/ray_executor_pb2_grpc.py && \
    sed -i 's/^import context_pb2/from . import context_pb2/' \
    /app/gen/context_pb2_grpc.py && \
    echo 'from . import orchestrator_pb2, orchestrator_pb2_grpc, ray_executor_pb2, ray_executor_pb2_grpc, context_pb2, context_pb2_grpc\n__all__ = ["orchestrator_pb2", "orchestrator_pb2_grpc", "ray_executor_pb2", "ray_executor_pb2_grpc", "context_pb2", "context_pb2_grpc"]' \
    > /app/gen/__init__.py

# Copy test script
COPY tests/e2e/test_system_e2e.py .

# Run as non-root
USER 1000:1000

# Default command
CMD ["python", "test_system_e2e.py"]

