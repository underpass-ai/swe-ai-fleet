FROM python:3.13-slim

WORKDIR /app

# Build arguments for paths (relative to build context)
ARG SPECS_PATH=specs
ARG TEST_FILE=tests/e2e/test_system_e2e.py
ARG JOB_PATH=jobs/test-system-e2e

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps for gRPC + NATS + pytest
RUN pip install --no-cache-dir \
    grpcio==1.67.1 \
    grpcio-tools==1.67.1 \
    protobuf==5.28.3 \
    nats-py==2.10.0 \
    pytest==8.4.2 \
    pytest-asyncio==0.25.2

# Copy specs and the test file into image
COPY ${SPECS_PATH} /app/specs
COPY ${TEST_FILE} /app/tests/e2e/test_system_e2e.py

# Copy runner
COPY ${JOB_PATH}/run_test.py /app/run_test.py

# Ensure gen package location on PYTHONPATH
ENV PYTHONPATH=/app

# Non-root user
RUN groupadd -r jobuser && useradd -r -m -g jobuser -u 1000 jobuser && \
    mkdir -p /app/tests/e2e /app/gen && \
    chown -R jobuser:jobuser /app
USER jobuser

CMD ["python", "/app/run_test.py"]


