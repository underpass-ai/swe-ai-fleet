# ============================================================================
# Stage 1: Generate protobuf Python stubs from fleet_proxy.proto
# ============================================================================
FROM docker.io/library/python:3.13-slim AS proto-builder

WORKDIR /build

# Install protoc and grpc_tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    grpcio-tools==1.67.1 \
    protobuf==5.28.3

# Copy proto specs
COPY specs/fleet /build/specs/fleet

# Create output directory structure and generate Python stubs
RUN mkdir -p /build/gen/fleet/proxy/v1 && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --grpc_python_out=/build/gen \
    --pyi_out=/build/gen \
    /build/specs/fleet/proxy/v1/fleet_proxy.proto

# Create __init__.py files for the package hierarchy
RUN touch /build/gen/fleet/__init__.py && \
    touch /build/gen/fleet/proxy/__init__.py && \
    touch /build/gen/fleet/proxy/v1/__init__.py

# Fix imports in generated files (make them absolute)
RUN find /build/gen -name "*_pb2*.py" -exec sed -i \
    -e 's/^from fleet\.proxy\.v1 import/from fleet.proxy.v1 import/g' \
    {} \;

# ============================================================================
# Stage 2: Test Runner
# ============================================================================
FROM docker.io/library/python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    grpcio==1.67.1 \
    protobuf==5.28.3 \
    cryptography>=43.0.0

# Copy generated protobuf stubs from builder stage
COPY --from=proto-builder /build/gen /app

# Copy test script
COPY e2e/tests/44-fleet-proxy-enrollment-and-proxy/test_fleet_proxy_enrollment.py /app/test_fleet_proxy_enrollment.py

ENV PYTHONPATH=/app

# Non-root user
RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

CMD ["python", "/app/test_fleet_proxy_enrollment.py"]
