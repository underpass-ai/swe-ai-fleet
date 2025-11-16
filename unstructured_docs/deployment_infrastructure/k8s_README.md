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

See `scripts/infra/FRESH_REDEPLOY_FIXES.md` for details.

---

### Option 2: Manual Step-by-Step

```bash
# 1. Foundation
kubectl apply -f 00-foundation/00-namespace.yaml
kubectl apply -f 00-foundation/00-configmaps.yaml
kubectl apply -f ../01-secrets.yaml  # Lives in deploy/k8s/ root (gitignored)

# 2. Infrastructure
kubectl apply -f 10-infrastructure/nats.yaml
kubectl apply -f 10-infrastructure/nats-internal-dns.yaml
kubectl apply -f 10-infrastructure/neo4j.yaml
kubectl apply -f 10-infrastructure/valkey.yaml
kubectl apply -f 10-infrastructure/container-registry.yaml

# Wait for infrastructure ready
kubectl wait --for=condition=ready pod -l app=nats -n swe-ai-fleet --timeout=120s
kubectl wait --for=condition=ready pod -l app=neo4j -n swe-ai-fleet --timeout=120s
kubectl wait --for=condition=ready pod -l app=valkey -n swe-ai-fleet --timeout=120s

# 3. NATS Streams
kubectl apply -f 20-streams/nats-streams-init.yaml
kubectl wait --for=condition=complete job/nats-streams-init -n swe-ai-fleet --timeout=60s

# 4. Microservices
kubectl apply -f 30-microservices/
kubectl rollout status deployment/context -n swe-ai-fleet --timeout=120s
kubectl rollout status deployment/orchestrator -n swe-ai-fleet --timeout=120s
kubectl rollout status deployment/planning -n swe-ai-fleet --timeout=120s
kubectl rollout status deployment/workflow -n swe-ai-fleet --timeout=120s
kubectl rollout status deployment/ray-executor -n swe-ai-fleet --timeout=120s

# 5. Monitoring (optional)
kubectl apply -f 40-monitoring/

# 6. Ingress (optional)
kubectl apply -f 50-ingress/
```

---

## 📊 Service Inventory

### Core Microservices (30-microservices/)

| Service | Port | Replicas | Purpose |
|---------|------|----------|---------|
| Context | 50054 | 2 | Knowledge graph context |
| Orchestrator | 50055 | 2 | Multi-agent orchestration |
| Planning | 50054 | 2 | Story FSM ⚠️ Port fixed 2025-11-08 |
| Workflow | 50056 | 2 | Task FSM + RBAC L2 |
| Ray Executor | 50057 | 1 | GPU task execution |
| vLLM Server | 8000 | 1 | LLM model serving |

### Infrastructure (10-infrastructure/)

| Service | Port | Purpose |
|---------|------|---------|
| NATS | 4222 | Event-driven messaging |
| Neo4j | 7687 | Knowledge graph storage |
| Valkey | 6379 | Redis-compatible cache |
| Registry | 5000 | Internal container registry |

---

## 🔐 Secrets Management

**File**: `01-secrets.yaml` (lives in `deploy/k8s/` root)

⚠️ **EXCLUDED FROM GIT** - See `SECRETS_README.md` for management.

Required secrets:
- `neo4j-auth` (NEO4J_USER, NEO4J_PASSWORD)
- `huggingface-token` (HF_TOKEN)
- `grafana-admin` (admin-user, admin-password)

---

## 🧹 Obsolete Files (DO NOT USE)

The following files in root `deploy/k8s/` are **obsolete** and kept only for backward compatibility:

```
❌ 04-services.yaml          # Frankenstein file (use 30-microservices/ instead)
❌ 07-neo4j-secret.yaml      # Duplicate of 01-secrets.yaml
⚠️  03-configmaps.yaml       # Verify if duplicate before deleting
```

**All numbered files** (`01-`, `02-`, etc.) in root are **legacy** - use subdirectories instead.

---

## 📖 Documentation

- **Deploy Guide**: `docs/operations/DEPLOYMENT.md`
- **Troubleshooting**: `docs/operations/K8S_TROUBLESHOOTING.md`
- **Secrets Management**: `deploy/k8s/SECRETS_README.md`
- **Fresh Redeploy Fixes**: `scripts/infra/FRESH_REDEPLOY_FIXES.md`
- **Complete Audit**: `deploy/AUDIT_2025-11-08.md`
- **Restoration Runbook**: `deploy/CLUSTER_RESTORATION_2025-11-08.md`

---

## ✅ Health Check

```bash
# Check all pods
kubectl get pods -n swe-ai-fleet

# Expected: 27/28 Running (96%)
# - 6 microservices: 9 pods total (2+2+2+2+1+1)
# - Infrastructure: 3 StatefulSets (nats, neo4j, valkey)
# - Monitoring: 3 pods
# - UI & Debug: ~12 pods
```

---

## 🎯 Migration from Old Structure

If you're migrating from old flat structure:

1. **New deployments** use subdirectories (00-foundation/, 30-microservices/, etc.)
2. **Old numbered files** (01-, 02-, etc.) are legacy - being phased out
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
