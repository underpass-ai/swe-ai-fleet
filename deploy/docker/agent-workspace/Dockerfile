# Agent Workspace Container
# Fully-tooled environment for executing atomic agent tasks
# Includes: git, build tools, test frameworks, linters, SonarQube CLI, e2e runners

FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install base tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    git \
    build-essential \
    pkg-config \
    libssl-dev \
    unzip \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Go 1.21
RUN wget -q https://go.dev/dl/go1.21.5.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz && \
    rm go1.21.5.linux-amd64.tar.gz
ENV PATH=/usr/local/go/bin:$PATH
ENV GOPATH=/workspace/go
ENV PATH=$GOPATH/bin:$PATH

# Install Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g npm@latest

# Install Python 3.11
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    python3.11-venv \
    && ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3

# Install Rust (optional, for high-performance paths)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH=/root/.cargo/bin:$PATH

# Install test frameworks
RUN pip3 install --no-cache-dir \
    pytest \
    pytest-cov \
    pytest-asyncio \
    coverage

RUN npm install -g \
    jest \
    vitest \
    playwright \
    @playwright/test

# Install linters
RUN go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest && \
    npm install -g eslint typescript && \
    pip3 install --no-cache-dir ruff black mypy pylint

# Install SonarQube Scanner CLI
RUN wget -q https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-5.0.1.3006-linux.zip && \
    unzip -q sonar-scanner-cli-5.0.1.3006-linux.zip && \
    mv sonar-scanner-5.0.1.3006-linux /opt/sonar-scanner && \
    rm sonar-scanner-cli-5.0.1.3006-linux.zip && \
    ln -s /opt/sonar-scanner/bin/sonar-scanner /usr/local/bin/sonar-scanner

# Install lsb-release and security scanners
RUN apt-get update && apt-get install -y lsb-release && \
    wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | apt-key add - && \
    echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | tee -a /etc/apt/sources.list.d/trivy.list && \
    apt-get update && apt-get install -y trivy

# Install GitHub CLI (for PR operations)
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt-get update && apt-get install -y gh

# Install Docker CLI (for building images within workspace if needed)
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - && \
    echo "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list && \
    apt-get update && apt-get install -y docker-ce-cli

# Create workspace directory
RUN mkdir -p /workspace && chmod 777 /workspace

WORKDIR /workspace

# Add helper scripts
COPY scripts/ /usr/local/bin/

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD echo "healthy"

# Default command (will be overridden by K8s Job)
CMD ["/bin/bash"]

