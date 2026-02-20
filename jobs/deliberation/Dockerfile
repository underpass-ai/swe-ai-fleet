FROM docker.io/library/python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir grpcio==1.67.1 grpcio-tools==1.67.1 protobuf==5.28.3

# Copy proto specs
COPY specs/fleet/orchestrator/v1/orchestrator.proto /app/specs/fleet/orchestrator/v1/orchestrator.proto

# Generate gRPC code
RUN mkdir -p /app/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/app/specs/fleet/orchestrator/v1 \
    --python_out=/app/gen \
    --grpc_python_out=/app/gen \
    --pyi_out=/app/gen \
    orchestrator.proto && \
    sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' \
    /app/gen/orchestrator_pb2_grpc.py && \
    echo 'from . import orchestrator_pb2, orchestrator_pb2_grpc\n__all__ = ["orchestrator_pb2", "orchestrator_pb2_grpc"]' \
    > /app/gen/__init__.py

# Copy job script
COPY jobs/deliberation/trigger_deliberation.py /app/trigger_deliberation.py

# Run as non-root
USER 1000:1000

# Default command
CMD ["python", "trigger_deliberation.py"]

