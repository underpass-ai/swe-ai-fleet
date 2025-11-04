# Planning Service Dockerfile
# Multi-stage build for Python gRPC service

FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install grpcio-tools for proto generation
RUN python -m pip install --no-cache-dir grpcio-tools==1.60.0

# Copy proto spec from project (expects build context at project root)
# Build from project root: podman build -t planning:latest -f services/planning/Dockerfile .
COPY specs/fleet/planning/v2/planning.proto /build/specs/

# Generate Python gRPC stubs
RUN mkdir -p /build/planning/gen && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/planning/gen \
    --pyi_out=/build/planning/gen \
    --grpc_python_out=/build/planning/gen \
    /build/specs/planning.proto && \
    sed -i 's/^import planning_pb2/from . import planning_pb2/' \
    /build/planning/gen/planning_pb2_grpc.py && \
    echo "" > /build/planning/gen/__init__.py

#########################################
# Final stage
#########################################
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy generated gRPC code from builder stage
COPY --from=builder /build/planning/gen /app/planning/gen

# Copy application code
COPY planning/ /app/planning/
COPY server.py /app/

# Create __init__.py for gen module
RUN echo "" > /app/planning/gen/__init__.py

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50054'); channel.channel_ready()" || exit 1

# Expose gRPC port
EXPOSE 50054

# Run server
CMD ["python", "server.py"]

