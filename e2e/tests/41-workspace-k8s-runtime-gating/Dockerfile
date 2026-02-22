FROM --platform=linux/amd64 docker.io/library/golang:1.23-bookworm AS workspace_builder

WORKDIR /src
COPY services/workspace/ /src/
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/workspace-service ./cmd/workspace

FROM --platform=linux/amd64 docker.io/library/python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=workspace_builder /out/workspace-service /usr/local/bin/workspace-service
COPY e2e/tests/41-workspace-k8s-runtime-gating/test_workspace_k8s_runtime_gating.py /app/test_workspace_k8s_runtime_gating.py

RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

CMD ["python", "/app/test_workspace_k8s_runtime_gating.py"]
