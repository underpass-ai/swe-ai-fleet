# Multi-stage build for cleanup storage job
FROM python:3.13-slim

WORKDIR /app

# Install dependencies (with cache mount for pip)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
    neo4j==5.20.0 \
    redis==5.0.1

# Copy cleanup script
COPY e2e/tests/00-cleanup-storage/cleanup_storage.py /app/cleanup_storage.py

# Set permissions
RUN chmod +x /app/cleanup_storage.py

# Run as non-root user
RUN groupadd -r cleanupuser && useradd -r -m -g cleanupuser -u 1000 cleanupuser && \
    chown -R cleanupuser:cleanupuser /app

USER cleanupuser

CMD ["python", "/app/cleanup_storage.py"]

