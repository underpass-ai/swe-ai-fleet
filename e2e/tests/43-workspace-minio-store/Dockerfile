FROM docker.io/library/python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir minio==7.2.16

COPY e2e/tests/43-workspace-minio-store/test_workspace_minio_store.py /app/test_workspace_minio_store.py

RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app

USER testuser

CMD ["python", "/app/test_workspace_minio_store.py"]
