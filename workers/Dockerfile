# Workspace Runner - Python service that creates K8s Jobs
FROM docker.io/library/python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY workers/requirements-worker.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker code
COPY workers/natsx.py workers/workspace_runner.py ./

# Note: pyclients not needed for now

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1
ENV NATS_URL=nats://nats:4222
ENV K8S_NAMESPACE=swe

ENTRYPOINT ["python", "workspace_runner.py"]

