# ============================================================================
# Stage 1: Generate protobuf Python stubs
# ============================================================================
FROM python:3.13-slim AS proto-builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    grpcio-tools==1.67.1 \
    protobuf==5.28.3

COPY specs/fleet /build/specs/fleet

RUN mkdir -p /build/gen && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --grpc_python_out=/build/gen \
    --pyi_out=/build/gen \
    /build/specs/fleet/planning/v2/planning.proto && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --grpc_python_out=/build/gen \
    --pyi_out=/build/gen \
    /build/specs/fleet/task_derivation/v1/task_derivation.proto

RUN find /build/gen -name "*_pb2*.py" -exec sed -i \
    -e 's/^from planning\.v2/from fleet.planning.v2/g' \
    -e 's/^import planning\.v2/import fleet.planning.v2/g' \
    -e 's/^from task_derivation\.v1/from fleet.task_derivation.v1/g' \
    -e 's/^import task_derivation\.v1/import fleet.task_derivation.v1/g' \
    {} \;

# ============================================================================
# Stage 2: Test Runner
# ============================================================================
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    grpcio==1.67.1 \
    grpcio-tools==1.67.1 \
    protobuf==5.28.3 \
    nats-py==2.9.0 \
    valkey==6.0.2 \
    neo4j==5.26.0

COPY --from=proto-builder /build/gen /app
COPY e2e/tests/13-task-derivation-planning-service-grpc/test_task_derivation_planning_service_grpc.py /app/test_task_derivation_planning_service_grpc.py

ENV PYTHONPATH=/app

RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

CMD ["python", "/app/test_task_derivation_planning_service_grpc.py"]
