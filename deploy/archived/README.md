# Archived Deployment Methods

**Date Archived**: 2025-11-08  
**Reason**: Obsolete - No longer used in production  

---

## Archived Directories

### cri-o-standalone/

**What**: CRI-O Pod/Container manifests for running services without Kubernetes  
**Why Archived**: Cluster now uses Kubernetes with CRI-O as container runtime (not standalone)  
**Status**: Experimental, never used in production  
**References**: `docs/INFRA_ARCHITECTURE.md` (needs update)

---

### helm-experimental/

**What**: Helm chart for deploying Redis, Neo4j, KubeRay  
**Why Archived**: Project uses direct kubectl apply (YAMLs in deploy/k8s/)  
**Status**: Experimental, version 0.1.0, never deployed  
**Note**: If multi-tenancy needed in future, consider reviving Helm approach

---

### kustomize-calico-patch/

**What**: Kustomize patch for Calico CNI (MTU, IP detection)  
**Why Archived**: Patch already applied during cluster setup  
**Status**: One-time use, no longer needed  
**Note**: Calico configuration now stable

---

### kong-experimental/

**What**: Kong API Gateway with podman-compose  
**Why Archived**: Cluster uses ingress-nginx (not Kong)  
**Status**: Experimental, never deployed  
**Note**: ingress-nginx sufficient for current needs

---

## Current Deployment Method

See `deploy/k8s/` for production-ready Kubernetes manifests.

**Structure**:
- `00-foundation/` - Namespace, ConfigMaps, Secrets
- `10-infrastructure/` - NATS, Neo4j, Valkey
- `20-streams/` - NATS JetStream init
- `30-microservices/` - Core services
- `40-monitoring/` - Grafana, Loki
- `50-ingress/` - Ingress resources
- `90-debug/` - Debug tools
- `99-jobs/` - Utility jobs

---

## Recovery

If you need to recover archived files:

```bash
# View archived content
ls deploy/archived/

# Restore specific file
git log --all --full-history -- "deploy/crio/*"
git checkout <commit> -- deploy/crio/
```

---

**Archived by**: AI Assistant  
**Date**: 2025-11-08  
**Cluster**: Kubernetes v1.34.1 (wrx80-node1)  
