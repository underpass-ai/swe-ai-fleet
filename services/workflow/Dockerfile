# Workflow Orchestration Service Dockerfile
# Multi-stage build for Python gRPC service

FROM docker.io/library/python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install protobuf toolchain (pinned by repo constraints)
COPY constraints.txt /build/constraints.txt
RUN python -m pip install --no-cache-dir -c /build/constraints.txt grpcio-tools

# Copy proto spec from project (expects build context at project root)
# Build from project root: podman build -t workflow:latest -f services/workflow/Dockerfile .
COPY specs/workflow.proto /build/specs/

# Generate Python gRPC stubs
RUN mkdir -p /build/workflow/gen && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/workflow/gen \
    --pyi_out=/build/workflow/gen \
    --grpc_python_out=/build/workflow/gen \
    /build/specs/workflow.proto && \
    sed -i 's/^import workflow_pb2/from . import workflow_pb2/' \
    /build/workflow/gen/workflow_pb2_grpc.py && \
    echo "" > /build/workflow/gen/__init__.py

#########################################
# Final stage
#########################################
FROM docker.io/library/python:3.13-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY constraints.txt /app/constraints.txt
COPY services/workflow/requirements.txt /app/
RUN pip install --no-cache-dir -c constraints.txt -r requirements.txt

# Copy generated gRPC code from builder stage
COPY --from=builder /build/workflow/gen /app/services/workflow/gen

# Copy application code
COPY services/workflow/ /app/services/workflow/

# Copy shared kernel (Action/ActionEnum)
COPY core/shared/ /app/core/shared/

# Copy FSM configuration
COPY config/workflow.fsm.yaml /app/config/

# Create __init__.py files for proper Python module structure
RUN echo "" > /app/services/__init__.py && \
    echo "" > /app/services/workflow/gen/__init__.py && \
    echo "" > /app/core/__init__.py

# Set Python path
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50056'); channel.channel_ready()" || exit 1

# Expose gRPC port
EXPOSE 50056

# Run server
CMD ["python", "-m", "services.workflow.server"]

