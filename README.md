# EdgeCrew — Multi-Agent Agile Engineering

**The industry reference for agile software engineering with autonomous agents.**

A virtual agile team of specialized AI agents — auditable, role-based, and designed for enterprise and homelab clusters.

## Why EdgeCrew?

- **Agile Squad Simulation**: Agents (developers, DevOps, QA, architect, data) collaborate like a real agile team, guided by a human Product Owner.
- **Human Product Owner**: A human PO (no PM bot) participates in ceremonies with agents (planning, daily as needed, reviews, retros).
- **Role-Based Context**: Automated pipelines distribute exactly the right information per role → avoids confusion and improves efficiency.
- **State-of-the-Art Memory**:
  - **Short-term** → in-memory key-value store for recent events/summaries.
  - **Long-term** → graph knowledge store for decisions, tasks, user stories.
- **Auditability**: Every decision and artifact is stored in the knowledge graph for traceability.
- **Local-First**: Runs on your workstation or enterprise cluster. No dependency on external APIs.

Target hardware: 4–8× NVIDIA GPUs (≥24 GB each) for enterprise tier. Practical minimum: 1 node with 2×24 GB; scalable to multi‑node (≥1×24 GB per node) with Ray/KubeRay.

## Deployment Scenarios

- 🖥️ **Workstation** → 1 node with **4×24 GB GPUs** (e.g. RTX 3090/4090).
- ⚡ **Native Ray (no Kubernetes)** → distributed execution on a local/lightweight cluster with `ray start`.
- ☁️ **Enterprise cluster** → Kubernetes + Ray/KubeRay for horizontal scale.
- 🏠 **Homelab/Edge** → installable on a single machine with a container runtime.

For a detailed CRI-O GPU setup (Arch Linux), see:

- `docs/INSTALL_CRIO.md` — install, initialization, and demo runbook
- `docs/TROUBLESHOOTING_CRIO.md` — common errors and fixes
- `deploy/crio/README.md` — CRI-O manifests (crictl) for Redis/Neo4j/vLLM

## Developer Quickstart

Start here:

- Golden Path (10 min): [docs/GOLDEN_PATH.md](docs/GOLDEN_PATH.md)
- Use Cases: [docs/USE_CASES.md](docs/USE_CASES.md)

Prerequisites:

- Python 3.13+
- Container runtime: CRI‑O
- Optional for Kubernetes workflows: kind, kubectl, helm

Setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .

# Run unit tests
python -m pytest tests/unit -v

# Explore the legacy PoC CLI (cluster-from-yaml)
swe_ai_fleet-e2e --help  # PoC only; see docs for full agile flow

# Optional: start native Ray (local)
ray start --head  # start a local head node for distributed tasks
ray status
```

### Quickstart (CRI‑O)

Use CRI‑O directly with `crictl` (GPU via CDI). Full commands are in:
- `deploy/crio/README.md` (runbook with `crictl`)
- `docs/INSTALL_CRIO.md` (step-by-step and seeding)

Minimal summary (see guides for details and cleanup):

1) Services (Redis / RedisInsight / vLLM GPU / Neo4j):
- Follow `deploy/crio/README.md` for `crictl runp|create|start` of each service.

2) Demo seed (CTX‑001):
```bash
source .venv/bin/activate
export REDIS_URL=redis://:swefleet-dev@localhost:6379/0
export NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=swefleet-dev
python scripts/seed_context_example.py
```

3) Frontend (local, without container):
```bash
pip install -e .[web]
HOST=0.0.0.0 PORT=8080 \
REDIS_URL=redis://:swefleet-dev@localhost:6379/0 \
NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=swefleet-dev \
swe_ai_fleet-web
```

4) Test:
- UI: http://localhost:8080/ui/report?case_id=CTX-001
- API: http://localhost:8080/api/report?case_id=CTX-001&persist=false

### Demo Frontend (local)

Renders the "Decision‑Enriched" report from Redis + Neo4j running under CRI‑O.

```bash
pip install -e .[web]
HOST=0.0.0.0 PORT=8080 \
REDIS_URL=redis://:swefleet-dev@localhost:6379/0 \
NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=swefleet-dev \
swe_ai_fleet-web
```

URLs:

- Home: `http://localhost:8080/`
- UI: `http://localhost:8080/ui/report?case_id=CASE-123`
- API: `http://localhost:8080/api/report?case_id=CASE-123&persist=false`

## Local runtime (CRI‑O) — Advanced/Experimental

- Standalone CRI‑O path for power users and diagnostics.
- Prefer Kubernetes + CRI‑O for cluster setups (see `docs/INSTALL_K8S_CRIO_GPU.md`).
- Use CRI‑O with `crictl` (see `deploy/crio/README.md`).
- For containerized task execution, see `docs/RUNNER_SYSTEM.md`.

Optional vLLM (multi‑GPU, 4 GPUs):

```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
  --model /models/llama-3-8b-instruct \
  --tensor-parallel-size 4 \
  --gpu-memory-utilization 0.90 \
  --port 8000

export LLM_BACKEND=vllm
export VLLM_ENDPOINT=http://localhost:8000/v1
export VLLM_MODEL=llama-3-8b-instruct

# 2‑GPU variant (2×48 GB or 2×24 GB with conservative limits)
python -m vllm.entrypoints.openai.api_server \
  --model /models/llama-3-8b-instruct \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.85 \
  --max-model-len 8192 \
  --port 8000
```

## Documentation

- [Documentation Index](docs/INDEX.md)
- [Golden Path (10 min)](docs/GOLDEN_PATH.md)
- [Use Cases](docs/USE_CASES.md)
- [Vision](docs/VISION.md)
- [Installation](docs/INSTALLATION.md)
- [Agile Team Simulation](docs/AGILE_TEAM.md)
- [Context Management](docs/CONTEXT_MANAGEMENT.md)
- [User Story Flow](docs/USER_STORY_FLOW.md)
- [Memory Architecture](docs/MEMORY_ARCH.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Kubernetes + CRI-O + GPU Operator Install](docs/INSTALL_K8S_CRIO_GPU.md)
- [Context Demo (Redis + Neo4j)](docs/CONTEXT_DEMO.md)
- [Security & Privacy](docs/SECURITY_PRIVACY.md)
- [FAQ](docs/FAQ.md)
- [Glossary](docs/GLOSSARY.md)
- [Investors & Partners](docs/INVESTORS.md)
- [Roadmap + Progress](ROADMAP.md)

## Kubernetes (next phase)

- Goal: package the demo for Kubernetes using charts in `deploy/helm/`.
- Requirements (when enabled): `kubectl`, `helm`, a K8s cluster (e.g., kind or real).
- Planned steps (draft):
  - `helm dependency update deploy/helm`
  - `helm install swe-fleet deploy/helm -n swe --create-namespace`
  - Configure `values.yaml` for Redis/Neo4j/vLLM endpoints and GPU resources.
  - Validate pod/service health, then point the frontend to internal services.
