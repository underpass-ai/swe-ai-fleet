# ============================================================================
# Stage 1: Generate protobuf Python stubs
# ============================================================================
FROM docker.io/library/python:3.13-slim AS proto-builder

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

# Create output directory and generate Python stubs for planning_ceremony
RUN mkdir -p /build/gen && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --grpc_python_out=/build/gen \
    --pyi_out=/build/gen \
    /build/specs/fleet/planning_ceremony/v1/planning_ceremony.proto

# Fix imports in generated files
RUN find /build/gen -name "*_pb2*.py" -exec sed -i \
    -e 's/^from planning_ceremony\.v1/from fleet.planning_ceremony.v1/g' \
    {} \;

# ============================================================================
# Stage 2: Test Runner
# ============================================================================
FROM docker.io/library/python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    grpcio==1.67.1 \
    grpcio-tools==1.67.1 \
    protobuf==5.28.3

# Copy generated protobuf stubs from builder stage
COPY --from=proto-builder /build/gen /app

# Copy test script
COPY e2e/tests/10-planning-ceremony-processor-grpc-start/test_grpc_start.py /app/test_grpc_start.py

# Set PYTHONPATH to include /app for imports
ENV PYTHONPATH=/app

# Create non-root user for security
RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

# Default command: run the E2E test
CMD ["python", "/app/test_grpc_start.py"]
