# SWE AI Fleet

> **The Autonomous Multi-Agent Software Engineering Platform.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Beta-yellow)](ROADMAP.md)

SWE AI Fleet is a **self-hostable, production-grade** platform for autonomous software development. It replaces the "single AI assistant" model with a **Council of Agents** (Developer, Architect, QA) that deliberate, critique, and refine code before you ever see it.

It is built on a **Decision-Centric Architecture**, prioritizing "Why" (context) over just "What" (code), enabling small open-source models (7B-13B) to perform at the level of massive proprietary models.

---

## 📚 Documentation

We maintain a comprehensive **[Documentation Index](docs/README.md)** that maps out all available guides.

**Quick Links:**

- **[System Overview](docs/architecture/OVERVIEW.md)**: High-level architecture and core concepts.
- **[Microservices](docs/architecture/MICROSERVICES.md)**: Reference for the 7 deployable services.
- **[Core Contexts](docs/architecture/CORE_CONTEXTS.md)**: Deep dive into Agents, Knowledge Graph, and Orchestration logic.
- **[Deployment Guide](deploy/k8s/README.md)**: How to run the fleet on Kubernetes.

---

## 🏗️ Architecture at a Glance

The system follows **Hexagonal Architecture** and is composed of the following microservices:

| Service | Description | Tech Stack |
|---------|-------------|------------|
| **[Planning](services/planning/)** | Manages Projects, Epics, and User Stories. | Python, Neo4j |
| **[Workflow](services/workflow/)** | Tracks task lifecycle (FSM) and enforces RBAC. | Python, Neo4j |
| **[Orchestrator](services/orchestrator/)** | Runs the Multi-Agent Councils (Deliberation). | Python, NATS |
| **[Context](services/context/)** | Assembles surgical context from the Knowledge Graph. | Python, Neo4j |
| **[Ray Executor](services/ray_executor/)** | Gateway to the GPU cluster for agent execution. | Python, Ray |
| **[Task Derivation](services/task_derivation/)** | Auto-breaks plans into executable tasks. | Python, NATS |
| **[Monitoring](services/monitoring/)** | Real-time dashboard and observability. | Python, React |

---

## 🚀 Quick Start

### Prerequisites

- Kubernetes Cluster (1.28+)
- NVIDIA GPUs (recommended for local inference)
- [Podman](https://podman.io/) (for local development)

### Deployment

See the **[Kubernetes Deployment Guide](deploy/k8s/README.md)** for full instructions.

```bash
# Quick deploy script (if configured)
./scripts/infra/fresh-redeploy.sh
```

---

## 🤝 Contributing

We welcome contributions! Please read **[CONTRIBUTING.md](CONTRIBUTING.md)** for details on our development workflow, coding standards, and testing requirements.

## 📄 License

Apache License 2.0 - See [LICENSE](LICENSE) for details.
