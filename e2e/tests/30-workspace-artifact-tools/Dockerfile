FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY e2e/tests/30-workspace-artifact-tools/test_workspace_artifact_tools.py /app/test_workspace_artifact_tools.py

RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app

USER testuser

CMD ["python", "/app/test_workspace_artifact_tools.py"]
