# Planning Ceremony Processor Service Dockerfile
# Multi-stage build for Python gRPC service
# Build from project root: podman build -t planning-ceremony-processor:latest -f services/planning_ceremony_processor/Dockerfile .

FROM docker.io/library/python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY constraints.txt /build/constraints.txt
RUN python -m pip install --no-cache-dir -c /build/constraints.txt grpcio-tools

COPY specs/fleet/planning_ceremony/v1/planning_ceremony.proto /build/specs/planning_ceremony.proto
COPY specs/fleet/ray_executor/v1/ray_executor.proto /build/specs/ray_executor.proto

RUN mkdir -p /build/gen && \
    python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --pyi_out=/build/gen \
    --grpc_python_out=/build/gen \
    /build/specs/planning_ceremony.proto && \
    sed -i 's/^import planning_ceremony_pb2/from . import planning_ceremony_pb2/' \
    /build/gen/planning_ceremony_pb2_grpc.py

RUN python -m grpc_tools.protoc \
    -I/build/specs \
    --python_out=/build/gen \
    --pyi_out=/build/gen \
    --grpc_python_out=/build/gen \
    /build/specs/ray_executor.proto && \
    sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' \
    /build/gen/ray_executor_pb2_grpc.py && \
    echo "" > /build/gen/__init__.py

#########################################
# Final stage
#########################################
FROM docker.io/library/python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY constraints.txt /app/constraints.txt
COPY services/planning_ceremony_processor/requirements.txt /app/
RUN pip install --no-cache-dir -c constraints.txt -r requirements.txt

COPY core/ /app/core/
COPY services/planning_ceremony_processor/application/ /app/services/planning_ceremony_processor/application/
COPY services/planning_ceremony_processor/infrastructure/ /app/services/planning_ceremony_processor/infrastructure/
COPY services/planning_ceremony_processor/__init__.py /app/services/planning_ceremony_processor/
COPY services/planning_ceremony_processor/server.py /app/services/planning_ceremony_processor/
COPY --from=builder /build/gen /app/services/planning_ceremony_processor/gen
COPY config/ceremonies/ /app/config/ceremonies/

RUN echo "" > /app/services/__init__.py

ENV PYTHONPATH=/app
ENV CEREMONIES_DIR=/app/config/ceremonies

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; c=grpc.insecure_channel('localhost:50057'); c.channel_ready()" || exit 1

EXPOSE 50057

CMD ["python", "-m", "services.planning_ceremony_processor.server"]
