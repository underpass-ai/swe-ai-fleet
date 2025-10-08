# SWE AI Fleet

**AI-powered software engineering fleet** with multi-agent deliberation, event-driven workflows, and GPU-accelerated execution.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.28+-326CE5?logo=kubernetes)](https://kubernetes.io/)
[![Ray](https://img.shields.io/badge/Ray-2.49-blue?logo=ray)](https://ray.io/)

## 🎯 What is SWE AI Fleet?

SWE AI Fleet is an **open-source platform** for orchestrating teams of AI agents to collaboratively solve complex software engineering tasks. It features:

- **🤖 Multi-Agent Deliberation**: Agents collaborate with peer review and consensus
- **📊 FSM-Driven Workflows**: Statechart-based user story lifecycle management
- **⚡ GPU-Accelerated**: Distributed execution with Ray and time-sliced GPUs
- **🧠 Context-Aware**: Knowledge graph-powered context hydration
- **🏗️ Microservices Architecture**: Event-driven with NATS and gRPC

## 🚀 Quick Start

### Prerequisites

- Kubernetes cluster (1.28+)
- kubectl configured
- cert-manager & ingress-nginx installed

See [full prerequisites](docs/getting-started/prerequisites.md) for details.

### Deploy

```bash
# 1. Clone repository
git clone https://github.com/yourusername/swe-ai-fleet
cd swe-ai-fleet

# 2. Verify prerequisites
./scripts/infra/00-verify-prerequisites.sh

# 3. Deploy everything
./scripts/infra/deploy-all.sh

# 4. Verify health
./scripts/infra/verify-health.sh
```

### Access

```bash
# Expose UI publicly (optional)
./scripts/infra/06-expose-ui.sh

# Access at https://swe-fleet.yourdomain.com
```

📚 **Full Guide**: [Getting Started](docs/getting-started/README.md)

## 🏗️ Architecture

### Microservices

| Service | Language | Purpose |
|---------|----------|---------|
| **Planning** | Go | FSM-based workflow & story lifecycle |
| **StoryCoach** | Go | User story quality scoring (DoR/INVEST) |
| **Workspace** | Go | Agent work validation & rigor scoring |
| **PO UI** | React | Product Owner interface |
| **Agent Orchestrator** | Python | Multi-agent deliberation (planned) |

### Technology Stack

- **Frontend**: React + Tailwind + Vite
- **Async Messaging**: NATS JetStream
- **Sync RPC**: gRPC + Protocol Buffers
- **Agent Execution**: Ray (GPU-accelerated)
- **Context Store**: Neo4j (planned)
- **Container Runtime**: CRI-O / containerd

📚 **Details**: [Architecture Documentation](docs/architecture/README.md)

## 📊 System Overview

```
┌─────────────┐
│   PO UI     │ ← Product Owner manages stories
└──────┬──────┘
       │ (gRPC)
┌──────▼──────┐     ┌──────────────┐
│  Planning   │────→│ StoryCoach   │ ← Score stories
└──────┬──────┘     └──────────────┘
       │ (NATS events)
       ▼
┌──────────────┐
│     NATS     │ ← Event backbone
│  JetStream   │
└──────┬───────┘
       │ (agent.requests)
       ▼
┌──────────────┐     ┌──────────────┐
│ Orchestrator │────→│  RayCluster  │ ← GPU workers
└──────┬───────┘     └──────────────┘
       │ (agent.responses)
       ▼
┌──────────────┐
│  Workspace   │ ← Validate agent work
│   Scorer     │
└──────────────┘
```

## 📚 Documentation

### 🚀 Getting Started
- [Prerequisites](docs/getting-started/prerequisites.md)
- [Installation](docs/getting-started/README.md)

### 🏗️ Architecture
- [Microservices](docs/architecture/microservices.md)
- [API Specifications](specs/)
- [FSM Workflow](docs/architecture/fsm-workflow.md)

### 🔧 Infrastructure
- [Kubernetes Deployment](docs/infrastructure/kubernetes.md)
- [GPU Setup & Time-Slicing](docs/infrastructure/GPU_TIME_SLICING.md)
- [Ray Cluster](docs/infrastructure/RAYCLUSTER_INTEGRATION.md)

### 🛠️ Development
- [Contributing Guide](docs/development/CONTRIBUTING.md)
- [Development Setup](docs/development/DEVELOPMENT_GUIDE.md)
- [Git Workflow](docs/development/GIT_WORKFLOW.md)

### 🚀 Operations
- [Troubleshooting](docs/operations/K8S_TROUBLESHOOTING.md)
- [Monitoring](docs/operations/monitoring.md)

### 📖 Reference
- [Glossary](docs/reference/GLOSSARY.md)
- [FAQ](docs/reference/FAQ.md)
- [RFCs](docs/reference/rfcs/)

## 🌟 Features

### ✅ Implemented

- [x] Microservices architecture (Planning, StoryCoach, Workspace, UI)
- [x] NATS JetStream messaging
- [x] FSM-based workflow engine
- [x] User story quality scoring (DoR/INVEST/Gherkin)
- [x] Agent work validation with adjustable rigor
- [x] React UI with Tailwind
- [x] Kubernetes deployment
- [x] GPU time-slicing support
- [x] Local container registry
- [x] TLS with cert-manager

### 🚧 In Progress

- [ ] Agent Orchestrator service
- [ ] Multi-agent deliberation
- [ ] Context Service (Neo4j)
- [ ] Workspace Runner (Python)
- [ ] LLM integrations

### 🔮 Planned

- [ ] Gateway service (REST API)
- [ ] OpenTelemetry observability
- [ ] Multi-tenant support
- [ ] Agent marketplace

See [Roadmap](docs/vision/ROADMAP.md) for details.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/development/CONTRIBUTING.md).

### Development Setup

```bash
# Install dependencies
make install-deps

# Run tests
pytest -m 'not e2e and not integration'

# Build services
cd services && make build

# Run locally
./scripts/dev/dev.sh
```

## 📄 License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built with:
- [NATS](https://nats.io/) - Cloud-native messaging
- [Ray](https://ray.io/) - Distributed compute
- [gRPC](https://grpc.io/) - RPC framework
- [React](https://react.dev/) - UI framework
- [Kubernetes](https://kubernetes.io/) - Container orchestration

## 📧 Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/swe-ai-fleet/issues)
- **Discord**: [Join our community](https://discord.gg/yourserver)
- **Email**: contact@yourdomain.com

---

⭐ **Star us on GitHub** if you find this project useful!