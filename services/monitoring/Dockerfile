# syntax=docker/dockerfile:1

# ============================================================================
# Stage 1: Build Frontend (Node.js)
# ============================================================================
FROM docker.io/library/node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY services/monitoring/frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY services/monitoring/frontend/ ./

# Build frontend
RUN npm run build

# ============================================================================
# Stage 2: Backend with gRPC (Python)
# ============================================================================
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY services/monitoring/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Generate gRPC code from proto files (clean industry-standard approach)
COPY specs/fleet/ray_executor/v1/ray_executor.proto /app/specs/fleet/ray_executor/v1/ray_executor.proto
COPY specs/fleet/orchestrator/v1/orchestrator.proto /app/specs/fleet/orchestrator/v1/orchestrator.proto
RUN mkdir -p /app/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/app/specs/fleet/ray_executor/v1 \
    --proto_path=/app/specs/fleet/orchestrator/v1 \
    --python_out=/app/gen \
    --grpc_python_out=/app/gen \
    --pyi_out=/app/gen \
    ray_executor.proto \
    orchestrator.proto && \
    # Fix known protoc bug: relative imports in _grpc.py files \
    sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' \
    /app/gen/ray_executor_pb2_grpc.py && \
    sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' \
    /app/gen/orchestrator_pb2_grpc.py && \
    # Create __init__.py \
    echo 'from . import ray_executor_pb2, ray_executor_pb2_grpc, orchestrator_pb2, orchestrator_pb2_grpc\n__all__ = ["ray_executor_pb2", "ray_executor_pb2_grpc", "orchestrator_pb2", "orchestrator_pb2_grpc"]' \
    > /app/gen/__init__.py

# Copy application
COPY services/monitoring/server.py .
COPY services/monitoring/sources/ ./sources/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
