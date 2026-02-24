FROM docker.io/library/golang:1.23-bookworm

WORKDIR /app

ENV RUSTUP_HOME=/usr/local/rustup
ENV CARGO_HOME=/usr/local/cargo
ENV PATH=/usr/local/cargo/bin:${PATH}

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    ca-certificates \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal --default-toolchain stable && \
    rustup component add rustfmt clippy

COPY services/workspace /tmp/workspace-src
RUN cd /tmp/workspace-src && \
    CGO_ENABLED=0 go build -o /usr/local/bin/workspace-service ./cmd/workspace && \
    rm -rf /tmp/workspace-src

COPY e2e/tests/auxiliary/workspace_vllm_todo_evolution_generic.py /app/e2e/tests/auxiliary/workspace_vllm_todo_evolution_generic.py
COPY e2e/tests/18-workspace-vllm-rust-todo-evolution /app/e2e/tests/18-workspace-vllm-rust-todo-evolution

RUN groupadd -r testuser && useradd -r -m -g testuser -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

CMD ["python3", "/app/e2e/tests/auxiliary/workspace_vllm_todo_evolution_generic.py"]
