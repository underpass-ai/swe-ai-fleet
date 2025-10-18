# Stage 1: Build frontend
FROM docker.io/library/node:20-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY services/monitoring/frontend/package*.json ./

# Install dependencies (using npm install since package-lock may be out of sync)
RUN npm install --production=false

# Copy frontend source
COPY services/monitoring/frontend/ ./

# Build frontend (lint is done in CI/locally)
RUN npm run build:no-lint

# Stage 2: Python backend
FROM docker.io/library/python:3.13-slim

WORKDIR /app

# Install dependencies
COPY services/monitoring/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Generate gRPC code from proto files
COPY specs/ray_executor.proto /app/specs/ray_executor.proto
COPY specs/orchestrator.proto /app/specs/orchestrator.proto
RUN mkdir -p /app/gen && \
    python -m grpc_tools.protoc \
    --proto_path=/app/specs \
    --python_out=/app/gen \
    --grpc_python_out=/app/gen \
    --pyi_out=/app/gen \
    ray_executor.proto && \
    python -m grpc_tools.protoc \
    --proto_path=/app/specs \
    --python_out=/app/gen \
    --grpc_python_out=/app/gen \
    --pyi_out=/app/gen \
    orchestrator.proto && \
    sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' \
    /app/gen/ray_executor_pb2_grpc.py && \
    sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' \
    /app/gen/orchestrator_pb2_grpc.py && \
    echo 'from . import ray_executor_pb2, ray_executor_pb2_grpc, orchestrator_pb2, orchestrator_pb2_grpc\n__all__ = ["ray_executor_pb2", "ray_executor_pb2_grpc", "orchestrator_pb2", "orchestrator_pb2_grpc"]' \
    > /app/gen/__init__.py

# Copy application
COPY services/monitoring/server.py .
COPY services/monitoring/sources/ ./sources/

# Copy built frontend from stage 1
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Create non-root user
RUN useradd -m -u 1000 monitoring && \
    chown -R monitoring:monitoring /app
USER monitoring

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')"

# Run server
CMD ["python", "server.py"]

