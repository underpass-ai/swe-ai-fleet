FROM docker.io/library/python:3.13-slim

WORKDIR /app

# Install build dependencies and NATS client
RUN pip install --no-cache-dir \
    nats-py==2.9.0 \
    grpcio-tools>=1.60.0

# Copy proto specs for API generation
COPY specs/fleet/orchestrator/v1/orchestrator.proto /app/specs/fleet/orchestrator/v1/orchestrator.proto

# Generate gRPC Python stubs
RUN mkdir -p /app/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/app/specs/fleet/orchestrator/v1 \
    --python_out=/app/gen \
    --grpc_python_out=/app/gen \
    --pyi_out=/app/gen \
    /app/specs/fleet/orchestrator/v1/orchestrator.proto && \
    sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' /app/gen/orchestrator_pb2_grpc.py && \
    echo 'from . import orchestrator_pb2, orchestrator_pb2_grpc\n__all__ = ["orchestrator_pb2", "orchestrator_pb2_grpc"]' \
    > /app/gen/__init__.py

# Copy script
COPY jobs/show-deliberations/show_deliberations.py .

# Make executable
RUN chmod +x show_deliberations.py

# Set Python path to include generated stubs
ENV PYTHONPATH=/app

# Run script
CMD ["python", "show_deliberations.py"]

