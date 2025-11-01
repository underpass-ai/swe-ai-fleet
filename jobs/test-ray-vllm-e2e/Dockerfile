FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for git, build tools, and pytest
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for E2E testing and protobuf generation
RUN pip install --no-cache-dir \
    pytest==8.4.2 \
    pytest-asyncio==0.25.2 \
    pytest-mock==3.14.0 \
    pytest-cov==5.0.0 \
    aiohttp>=3.9.0 \
    pyyaml>=6.0 \
    pydantic>=2.0.0 \
    requests \
    grpcio==1.67.1 \
    grpcio-tools==1.67.1 \
    protobuf==5.28.3

# Set PYTHONPATH to include workspace
ENV PYTHONPATH=/workspace

# Copy test runner script
COPY jobs/test-ray-vllm-e2e/run_test.py /app/run_test.py

# Create non-root user with home directory
RUN groupadd -r jobuser && \
    useradd -r -m -g jobuser -u 1000 jobuser && \
    mkdir -p /workspace && \
    chown -R jobuser:jobuser /app /workspace

# Set working directory to workspace (where repo will be cloned)
WORKDIR /workspace

# Switch to non-root user
USER jobuser

# Configure git for the test user
RUN git config --global user.name "E2E Test Agent" && \
    git config --global user.email "e2e@swe-ai-fleet.local" && \
    git config --global init.defaultBranch main

# Default: run the test runner script
CMD ["python", "/app/run_test.py"]

