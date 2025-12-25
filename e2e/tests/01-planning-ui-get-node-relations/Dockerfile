# ============================================================================
# Stage 1: Generate protobuf Python stubs
# ============================================================================
FROM python:3.13-slim AS proto-builder

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

# Create output directory and generate Python stubs for all required services
# Services used in this test:
# - Planning Service: CreateProject, CreateEpic, CreateStory, CreateBacklogReviewCeremony, StartBacklogReviewCeremony, CancelBacklogReviewCeremony
# - Context Service: GetGraphRelationships, UpdateContext
RUN mkdir -p /build/gen && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --grpc_python_out=/build/gen \
    --pyi_out=/build/gen \
    /build/specs/fleet/context/v1/context.proto \
    /build/specs/fleet/planning/v2/planning.proto

# Fix imports in generated files
# Change: from context.v1 -> from fleet.context.v1
# Change: from planning.v2 -> from fleet.planning.v2
# Also fix any cross-references between protos
RUN find /build/gen -name "*_pb2*.py" -exec sed -i \
    -e 's/^from context\.v1/from fleet.context.v1/g' \
    -e 's/^from planning\.v2/from fleet.planning.v2/g' \
    -e 's/^import context\.v1/import fleet.context.v1/g' \
    -e 's/^import planning\.v2/import fleet.planning.v2/g' \
    {} \;

# ============================================================================
# Stage 2: Test Runner
# ============================================================================
FROM python:3.13-slim

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
    protobuf==5.28.3

# Copy generated protobuf stubs from builder stage
COPY --from=proto-builder /build/gen /app

# Copy test script
COPY e2e/tests/01-planning-ui-get-node-relations/test_get_node_relations.py /app/test_get_node_relations.py

# Set PYTHONPATH to include /app for imports
ENV PYTHONPATH=/app

# Create non-root user for security
RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

# Default command: run the E2E test
CMD ["python", "/app/test_get_node_relations.py"]

