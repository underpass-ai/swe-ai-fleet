# ============================================================================
# Stage 1: Generate protobuf Python stubs
# ============================================================================
FROM docker.io/library/python:3.13-slim AS proto-builder

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
    /build/specs/fleet/planning_ceremony/v1/planning_ceremony.proto

RUN find /build/gen -name "*_pb2*.py" -exec sed -i \
    -e 's/^from planning_ceremony\.v1/from fleet.planning_ceremony.v1/g' \
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
    grpcio-tools==1.67.1 \
    protobuf==5.28.3 \
    nats-py==2.10.0 \
    neo4j==5.26.0 \
    valkey==6.0.2 \
    pyyaml==6.0.1

COPY --from=proto-builder /build/gen /app

COPY core/ceremony_engine /app/core/ceremony_engine
COPY core/shared /app/core/shared
COPY config/ceremonies /app/config/ceremonies
COPY e2e/tests/12-advance-ceremony-on-agent-completed/test_advance_ceremony_on_agent_completed.py /app/test_advance_ceremony_on_agent_completed.py

ENV PYTHONPATH=/app

RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

CMD ["python", "/app/test_advance_ceremony_on_agent_completed.py"]
