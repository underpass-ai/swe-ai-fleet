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
- ☁️ **Enterprise cluster** → Kubernetes + Ray/KubeRay para escalar horizontalmente.
- 🏠 **Homelab/Edge** → installable on a single machine with a container runtime.

For a detailed CRI-O GPU setup (Arch Linux), see:

- `docs/INSTALL_CRIO.md` — install, initialization, and demo runbook
- `docs/TROUBLESHOOTING_CRIO.md` — common errors and fixes

## Developer Quickstart

Prerequisites:

- Python 3.13+
- Container runtime (Podman/CRI-O preferred; Docker compatible)
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

## Local runtime (Podman/CRI-O)

- Recommended on Linux: rootless Podman with CRI-O backend [[preferred runtime]].
- On macOS: `podman machine init && podman machine start`.
- Optional: `alias docker=podman` for CLI compatibility.
- For containerized task execution details, see `docs/RUNNER_SYSTEM.md`.

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

- [Vision](docs/VISION.md)
- [Installation](docs/INSTALLATION.md)
- [Agile Team Simulation](docs/AGILE_TEAM.md)
- [Context Management](docs/CONTEXT_MANAGEMENT.md)
- [User Story Flow](docs/USER_STORY_FLOW.md)
- [Memory Architecture](docs/MEMORY_ARCH.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Context Demo (Redis + Neo4j)](docs/CONTEXT_DEMO.md)
- [Security & Privacy](docs/SECURITY_PRIVACY.md)
- [FAQ](docs/FAQ.md)
- [Glossary](docs/GLOSSARY.md)
- [Investors & Partners](docs/INVESTORS.md)
- [Roadmap + Progress](ROADMAP.md)
