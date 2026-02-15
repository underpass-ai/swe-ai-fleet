FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY e2e/tests/29-workspace-k8s-read-minimal/test_workspace_k8s_read_minimal.py /app/test_workspace_k8s_read_minimal.py

RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app

USER testuser

CMD ["python", "/app/test_workspace_k8s_read_minimal.py"]
