# Getting Started with SWE AI Fleet

This guide will help you deploy the SWE AI Fleet on your own infrastructure.

## 📚 Table of Contents

1.  [Prerequisites](prerequisites.md) - Check hardware and software requirements.
2.  [Deployment Guide](../../deploy/k8s/README.md) - Detailed Kubernetes deployment instructions.
3.  [Development Setup](../../CONTRIBUTING.md) - Setting up your local environment for contributing.

---

## 🚀 Quick Start (Production)

If you have a Kubernetes cluster ready (see Prerequisites):

```bash
# 1. Clone the repository
git clone https://github.com/underpass-ai/swe-ai-fleet
cd swe-ai-fleet

# 2. Run the deployment script
# This script installs NATS, Neo4j, Valkey, and all microservices.
./scripts/infra/fresh-redeploy-v2.sh
```

## 💻 Quick Start (Local Development)

If you want to run the services locally without Kubernetes for development:

```bash
# 1. Install dependencies
make install-deps

# 2. Start infrastructure (NATS/DBs) using Podman/Docker Compose
make infra-up

# 3. Run a service (e.g., Planning)
cd services/planning
python server.py
```
