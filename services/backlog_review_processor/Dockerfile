# Backlog Review Processor Service Dockerfile
# Multi-stage build for Python service

FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install build tools for proto generation and AsyncAPI code generation
RUN python -m pip install --no-cache-dir \
    grpcio-tools==1.68.1 \
    pyyaml \
    datamodel-code-generator

# Copy proto specs and AsyncAPI spec from project (expects build context at project root)
# Build from project root: podman build -t backlog-review-processor:latest -f services/backlog_review_processor/Dockerfile .
COPY specs/fleet/planning/v2/planning.proto /build/specs/planning.proto
COPY specs/fleet/ray_executor/v1/ray_executor.proto /build/specs/ray_executor.proto
COPY specs/asyncapi.yaml /build/specs/asyncapi.yaml

# Generate Python gRPC stubs for Planning Service (client)
RUN mkdir -p /build/backlog_review_processor/gen && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/backlog_review_processor/gen \
    --pyi_out=/build/backlog_review_processor/gen \
    --grpc_python_out=/build/backlog_review_processor/gen \
    /build/specs/planning.proto && \
    sed -i 's/^import planning_pb2/from backlog_review_processor.gen import planning_pb2/' \
    /build/backlog_review_processor/gen/planning_pb2_grpc.py

# Generate Python gRPC stubs for Ray Executor Service (client)
RUN python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/backlog_review_processor/gen \
    --pyi_out=/build/backlog_review_processor/gen \
    --grpc_python_out=/build/backlog_review_processor/gen \
    /build/specs/ray_executor.proto && \
    sed -i 's/^import ray_executor_pb2/from backlog_review_processor.gen import ray_executor_pb2/' \
    /build/backlog_review_processor/gen/ray_executor_pb2_grpc.py && \
    echo "" > /build/backlog_review_processor/gen/__init__.py

# Generate AsyncAPI models (NATS message payloads) inside Docker
COPY services/backlog_review_processor/scripts/generate_asyncapi_models.py /build/scripts/generate_asyncapi_models.py
RUN python /build/scripts/generate_asyncapi_models.py

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

# Copy generated gRPC code and AsyncAPI models from builder stage
COPY --from=builder /build/backlog_review_processor/gen /app/backlog_review_processor/gen

# Create non-root user for security (matches Kubernetes securityContext)
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 appuser && \
    chown -R appuser:appuser /app


# Switch to non-root user
USER appuser

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run server
CMD ["python", "server.py"]

