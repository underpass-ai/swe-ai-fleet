# ============================================================================
# Stage 1: Generate protobuf Python stubs
# ============================================================================
FROM python:3.13-slim AS proto-builder

WORKDIR /build

# Install protoc and grpc_tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# Install Python protobuf tools
RUN pip install --no-cache-dir \
    grpcio-tools==1.67.1 \
    protobuf==5.28.3

# Copy proto specs
COPY specs/fleet /build/specs/fleet

# Create output directory and generate Python stubs for all services
RUN mkdir -p /build/gen && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --grpc_python_out=/build/gen \
    --pyi_out=/build/gen \
    /build/specs/fleet/context/v1/context.proto \
    /build/specs/fleet/orchestrator/v1/orchestrator.proto

# Fix imports in generated files
# Change: from context.v1 -> from fleet.context.v1
# Change: from orchestrator.v1 -> from fleet.orchestrator.v1
RUN find /build/gen -name "*_pb2*.py" -exec sed -i \
    -e 's/^from context\.v1/from fleet.context.v1/g' \
    -e 's/^from orchestrator\.v1/from fleet.orchestrator.v1/g' \
    {} \;

# ============================================================================
# Stage 2: Test Runner
# ============================================================================
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    grpcio==1.67.1 \
    grpcio-tools==1.67.1 \
    protobuf==5.28.3 \
    pytest==8.4.2 \
    pytest-asyncio==0.25.2 \
    neo4j==5.25.0 \
    redis==5.2.1

# Copy generated protobuf stubs from builder stage
COPY --from=proto-builder /build/gen /app

# Copy test code
COPY tests/e2e/refactored /app/tests/e2e/refactored

# Copy runner script
COPY jobs/e2e-tests/run_tests.py /app/run_tests.py

# Set PYTHONPATH to include /app for imports
ENV PYTHONPATH=/app

# Create non-root user for security
RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

# Default command: run all e2e tests
CMD ["python", "/app/run_tests.py"]

