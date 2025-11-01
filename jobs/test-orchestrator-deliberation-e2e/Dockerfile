FROM python:3.13-slim

WORKDIR /app

# System tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps: gRPC + NATS
RUN pip install --no-cache-dir \
    grpcio==1.67.1 \
    grpcio-tools==1.67.1 \
    protobuf==5.28.3 \
    nats-py==2.10.0 \
    pytest==8.4.2

# Generate gRPC stubs from specs
COPY specs/fleet/orchestrator/v1/orchestrator.proto /app/specs/fleet/orchestrator/v1/orchestrator.proto
RUN mkdir -p /app/gen && \
    python -m grpc_tools.protoc \
      --proto_path=/app/specs/fleet/orchestrator/v1 \
      --python_out=/app/gen \
      --grpc_python_out=/app/gen \
      --pyi_out=/app/gen \
      orchestrator.proto && \
    sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' /app/gen/orchestrator_pb2_grpc.py && \
    echo 'from . import orchestrator_pb2, orchestrator_pb2_grpc\n__all__ = ["orchestrator_pb2", "orchestrator_pb2_grpc"]' > /app/gen/__init__.py

# Copy test runner
COPY jobs/test-orchestrator-deliberation-e2e/run_e2e.py /app/run_e2e.py

ENV PYTHONPATH=/app

# Non-root user
RUN groupadd -r jobuser && useradd -r -m -g jobuser -u 1000 jobuser && \
    chown -R jobuser:jobuser /app
USER jobuser

CMD ["python", "/app/run_e2e.py"]
