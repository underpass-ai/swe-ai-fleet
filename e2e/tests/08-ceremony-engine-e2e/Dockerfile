# ============================================================================
# E2E Test Runner: Ceremony Engine (E0)
# ============================================================================
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (with cache mount for apt)
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (with cache mount for pip)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
    pyyaml==6.0.1

# Copy ceremony engine and configs
COPY core/ceremony_engine /app/core/ceremony_engine
COPY config/ceremonies /app/config/ceremonies

# Copy test script
COPY e2e/tests/08-ceremony-engine-e2e/run_ceremony_engine_e2e.py /app/run_ceremony_engine_e2e.py

# Set PYTHONPATH to include /app for imports
ENV PYTHONPATH=/app

# Create non-root user for security
RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

# Default command: run the test script
CMD ["python", "/app/run_ceremony_engine_e2e.py"]
