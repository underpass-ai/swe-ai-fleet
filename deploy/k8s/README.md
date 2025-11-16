# Kubernetes Deployment - Organized Structure

## Overview

This directory contains Kubernetes manifests organized into logical layers for easy maintenance and deployment.

**Last Reorganization**: 2025-11-08
**Structure Version**: 2.0

---

## 📁 Directory Structure

```
deploy/k8s/
├── 00-foundation/      # Namespace, ConfigMaps, Secrets (FIRST)
├── 10-infrastructure/  # NATS, Neo4j, Valkey, Registry (SECOND)
├── 20-streams/         # NATS JetStream streams init (THIRD)
├── 30-microservices/   # Core application services (FOURTH)
├── 40-monitoring/      # Grafana, Loki, Monitoring dashboard
├── 50-ingress/         # Ingress resources (public exposure)
├── 90-debug/           # Debug tools (grpcui, proto-docs)
└── 99-jobs/            # Utility jobs (cleanup, init)
```

**Numbering System**:
- `00-09`: Foundation
- `10-19`: Infrastructure
- `20-29`: Messaging setup
- `30-39`: Application services
- `40-49`: Monitoring & Observability
- `50-59`: Ingress & Exposure
- `90-99`: Debug & Utilities

---

## 🚀 Quick Deploy

### Option 1: Automated (Recommended)

```bash
cd scripts/infra
./fresh-redeploy.sh
```

## 📊 Service Inventory

### Core Microservices (30-microservices/)

Note: Refer to each manifest for authoritative ports and replica counts.

| Service           | Manifest                     | Purpose                      |
|-------------------|------------------------------|------------------------------|
| Context           | 30-microservices/context.yaml        | Knowledge graph context      |
| Orchestrator      | 30-microservices/orchestrator.yaml   | Multi-agent orchestration    |
| Planning          | 30-microservices/planning.yaml       | Story FSM                    |
| Workflow          | 30-microservices/workflow.yaml       | Task FSM + RBAC              |
| Ray Executor      | 30-microservices/ray-executor.yaml   | GPU task execution           |
| vLLM Server       | 30-microservices/vllm-server.yaml    | LLM model serving            |

### Infrastructure (10-infrastructure/)

| Service  | Manifest                         | Purpose                     |
|----------|----------------------------------|-----------------------------|
| NATS     | 10-infrastructure/nats.yaml      | Event-driven messaging      |
| Neo4j    | 10-infrastructure/neo4j.yaml     | Knowledge graph storage     |
| Valkey   | 10-infrastructure/valkey.yaml    | Redis-compatible cache      |
| Registry | 10-infrastructure/container-registry.yaml | Internal container registry |

---

## 🔐 Secrets Management

**File**: `01-secrets.yaml` (lives in `deploy/k8s/` root)

⚠️ **EXCLUDED FROM GIT** - See `SECRETS_README.md` for management.

Required secrets:
- `neo4j-auth` (NEO4J_USER, NEO4J_PASSWORD)
- `huggingface-token` (HF_TOKEN)
- `grafana-admin` (GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD)

---

## 📖 Documentation

- **Deploy Guide**: `docs/operations/DEPLOYMENT.md`
- **Troubleshooting**: `docs/operations/K8S_TROUBLESHOOTING.md`
- **Secrets Management**: `deploy/k8s/SECRETS_README.md`

---

## ✅ Health Check

```bash
# Check all namespaces resources
kubectl get all -n swe-ai-fleet

# Watch rollouts
kubectl get deploy,sts,po -n swe-ai-fleet -w

# Tail logs for a service (example)
kubectl logs -n swe-ai-fleet -l app=orchestrator -f --tail=100
```

---

## 🎯 Migration from Old Structure

If you're migrating from old flat structure:

1. **New deployments** use subdirectories (00-foundation/, 30-microservices/, etc.)
2. **Old numbered files** (01-, 02-, etc.) at the root are phased out
3. **Scripts updated** to use new paths (see `scripts/infra/fresh-redeploy.sh`)

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2025-11-08 | Complete reorganization into subdirectories |
| 1.0 | 2025-10-16 | Initial flat structure (legacy) |

---

**Maintainer**: Tirso García Ibáñez
**Last Updated**: 2025-11-08


