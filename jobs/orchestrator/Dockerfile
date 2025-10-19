FROM python:3.13-slim

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    grpcio>=1.60.0 \
    grpcio-tools>=1.60.0

# Copy protobuf specs (clean industry-standard approach)
COPY specs/fleet/orchestrator/v1/orchestrator.proto /app/specs/fleet/orchestrator/v1/orchestrator.proto

# Generate gRPC code from protobuf
RUN mkdir -p /app/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/app/specs/fleet/orchestrator/v1 \
    --python_out=/app/gen \
    --grpc_python_out=/app/gen \
    --pyi_out=/app/gen \
    orchestrator.proto && \
    # Fix known protoc bug: relative imports in _grpc.py files \
    sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' \
    /app/gen/orchestrator_pb2_grpc.py && \
    # Create __init__.py \
    echo 'from . import orchestrator_pb2, orchestrator_pb2_grpc\n__all__ = ["orchestrator_pb2", "orchestrator_pb2_grpc"]' \
    > /app/gen/__init__.py

# Copy job scripts
COPY jobs/orchestrator/init_councils.py /app/init_councils.py
COPY jobs/orchestrator/delete_councils.py /app/delete_councils.py

# Create non-root user
RUN groupadd -r jobuser && \
    useradd -r -g jobuser -u 1000 jobuser && \
    chown -R jobuser:jobuser /app

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Switch to non-root user
USER jobuser

# Default: init councils (can be overridden)
CMD ["python", "/app/init_councils.py"]
