# Archived: CRI-O Standalone Documentation

**Date Archived**: 2025-11-08  
**Reason**: Obsolete - Documentation for CRI-O standalone deployment (no Kubernetes)

---

## What's Archived

### INFRA_ARCHITECTURE.md
- **Original Title**: "Infrastructure Architecture (CRI‑O now; Kubernetes next)"
- **Why Obsolete**: Claims "CRI-O is current phase", but Kubernetes has been production for 23+ days
- **Content**: Host-networked services with manual `crictl` commands

### INSTALLATION.md
- **Original Title**: "Installation Guide"
- **Why Obsolete**: CRI-O-focused installation, mentions "optional steps for Kubernetes"
- **Reality**: Kubernetes IS the deployment method, not optional

---

## Current Documentation

For current deployment methods, see:

- **Getting Started**: `docs/getting-started/README.md`
- **Kubernetes Setup**: `docs/infrastructure/INSTALL_K8S_CRIO_GPU.md`
- **Deployment**: `docs/operations/DEPLOYMENT.md`
- **Deploy Structure**: `deploy/k8s/README.md`

---

## Why CRI-O Standalone Was Abandoned

**Original Approach**:
- Run Redis, Neo4j, vLLM with `crictl runp` commands
- Host networking (no isolation)
- Manual container management
- No orchestration

**Current Approach**:
- Kubernetes cluster (v1.34.1)
- StatefulSets for databases
- Deployments for services
- Automatic scheduling, health checks, scaling
- Production-grade orchestration

**Benefits of Migration**:
- ✅ Automatic pod restarts
- ✅ Health checks (liveness/readiness)
- ✅ Service discovery (DNS)
- ✅ Rolling updates
- ✅ Resource limits
- ✅ RBAC & security
- ✅ Horizontal scaling

---

## Date

**CRI-O Standalone Used**: 2025-08 to 2025-10 (experimental phase)  
**Kubernetes Adopted**: 2025-10-16 (production)  
**Documentation Archived**: 2025-11-08  

---

## Recovery

If you need to reference this documentation:

```bash
# View archived docs
ls docs/archived/cri-o-standalone/

# Restore if needed
git log --all --full-history -- "docs/INFRA_ARCHITECTURE.md"
```

But **strongly recommend using Kubernetes approach** instead.
