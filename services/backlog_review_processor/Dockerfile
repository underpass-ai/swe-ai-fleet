# Backlog Review Processor Service Dockerfile
# Multi-stage build for Python service

FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install grpcio-tools for proto generation (Python 3.13 wheels available)
RUN python -m pip install --no-cache-dir grpcio-tools==1.68.1

# Copy proto specs and AsyncAPI spec from project (expects build context at project root)
# Build from project root: podman build -t backlog-review-processor:latest -f services/backlog_review_processor/Dockerfile .
COPY specs/fleet/planning/v2/planning.proto /build/specs/planning.proto
COPY specs/fleet/ray_executor/v1/ray_executor.proto /build/specs/ray_executor.proto
COPY specs/asyncapi.yaml /build/specs/asyncapi.yaml
COPY scripts/specs/generate-asyncapi-models.sh /build/scripts/specs/generate-asyncapi-models.sh

# Generate Python gRPC stubs for Planning Service (client)
RUN mkdir -p /build/gen && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --pyi_out=/build/gen \
    --grpc_python_out=/build/gen \
    /build/specs/planning.proto && \
    sed -i 's/^import planning_pb2/from backlog_review_processor.gen import planning_pb2/' \
    /build/gen/planning_pb2_grpc.py

# Generate Python gRPC stubs for Ray Executor Service (client)
RUN python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --pyi_out=/build/gen \
    --grpc_python_out=/build/gen \
    /build/specs/ray_executor.proto && \
    sed -i 's/^import ray_executor_pb2/from backlog_review_processor.gen import ray_executor_pb2/' \
    /build/gen/ray_executor_pb2_grpc.py && \
    echo "" > /build/gen/__init__.py

# Generate AsyncAPI models (NATS message payloads) inside Docker
RUN chmod +x /build/scripts/specs/generate-asyncapi-models.sh && \
    cd /build && \
    bash scripts/specs/generate-asyncapi-models.sh

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
COPY services/backlog_review_processor/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/backlog_review_processor/application/ /app/backlog_review_processor/application/
COPY services/backlog_review_processor/domain/ /app/backlog_review_processor/domain/
COPY services/backlog_review_processor/infrastructure/ /app/backlog_review_processor/infrastructure/
COPY services/backlog_review_processor/__init__.py /app/backlog_review_processor/
COPY services/backlog_review_processor/server.py /app/

# Copy core/nats infrastructure (mappers, etc.) - NOT the gen/ folder (generated in builder)
# Create core/nats structure
RUN mkdir -p /app/core/nats/infrastructure/mappers && \
    touch /app/core/nats/__init__.py && \
    touch /app/core/nats/infrastructure/__init__.py && \
    touch /app/core/nats/infrastructure/mappers/__init__.py

# Copy mappers
COPY core/nats/infrastructure/mappers/agent_response_mapper.py /app/core/nats/infrastructure/mappers/agent_response_mapper.py
COPY core/nats/infrastructure/mappers/__init__.py /app/core/nats/infrastructure/mappers/__init__.py

# Copy generated gRPC code from builder stage to backlog_review_processor.gen
COPY --from=builder /build/gen /app/backlog_review_processor/gen

# Copy generated AsyncAPI models from builder stage
COPY --from=builder /build/core/nats/gen /app/core/nats/gen

# Set PYTHONPATH to include core
ENV PYTHONPATH=/app/core:/app

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run server
CMD ["python", "server.py"]

