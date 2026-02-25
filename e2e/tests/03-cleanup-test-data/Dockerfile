# ============================================================================
# Stage 1: Generate protobuf Python stubs
# ============================================================================
FROM docker.io/library/python:3.13-slim AS proto-builder

WORKDIR /build

# Install protoc and grpc_tools (with cache mount for apt)
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# Install Python protobuf tools (with cache mount for pip)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
    grpcio-tools==1.67.1 \
    protobuf==5.28.3

# Copy proto specs
COPY specs/fleet /build/specs/fleet

# Create output directory and generate Python stubs
RUN mkdir -p /build/gen && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --grpc_python_out=/build/gen \
    --pyi_out=/build/gen \
    /build/specs/fleet/planning/v2/planning.proto

# Fix imports in generated files
RUN find /build/gen -name "*_pb2*.py" -exec sed -i \
    -e 's/^from planning\.v2/from fleet.planning.v2/g' \
    -e 's/^import planning\.v2/import fleet.planning.v2/g' \
    {} \;

# ============================================================================
# Stage 2: Test Data Cleanup
# ============================================================================
FROM docker.io/library/python:3.13-slim

WORKDIR /app

# Install system dependencies (with cache mount for apt)
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (with cache mount for pip)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
    grpcio==1.67.1 \
    grpcio-tools==1.67.1 \
    protobuf==5.28.3 \
    neo4j==5.26.0 \
    valkey==6.0.2

# Copy generated protobuf stubs from builder stage
COPY --from=proto-builder /build/gen /app

# Copy test data cleanup script
COPY e2e/tests/03-cleanup-test-data/cleanup_test_data.py /app/cleanup_test_data.py

# Set PYTHONPATH to include /app for imports
ENV PYTHONPATH=/app

# Create non-root user for security
RUN groupadd -r cleanupuser && useradd -r -m -g cleanupuser -u 1000 cleanupuser && \
    chown -R cleanupuser:cleanupuser /app
USER cleanupuser

# Default command: run the cleanup script
CMD ["python", "/app/cleanup_test_data.py"]
