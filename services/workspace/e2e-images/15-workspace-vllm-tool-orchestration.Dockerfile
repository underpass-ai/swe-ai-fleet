FROM docker.io/library/python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    build-essential \
    ca-certificates \
    coreutils \
    curl \
    findutils \
    gawk \
    git \
    grep \
    jq \
    less \
    openssh-client \
    patch \
    procps \
    ripgrep \
    sed \
    unzip \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

COPY e2e/tests/15-workspace-vllm-tool-orchestration/test_workspace_vllm_tool_orchestration.py /app/test_workspace_vllm_tool_orchestration.py

RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

CMD ["python", "/app/test_workspace_vllm_tool_orchestration.py"]
