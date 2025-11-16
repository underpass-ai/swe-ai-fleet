# Deployment & Redeployment Operations

**Status**: ✅ Production-Ready
**Last Updated**: 2025-11-04
**Namespace**: `swe-ai-fleet`
**Registry**: `registry.underpassai.com/swe-ai-fleet`

This document describes **standard operating procedures** for deploying and redeploying SWE AI Fleet microservices to Kubernetes.

---

## 🎯 Quick Reference

```bash
# Deploy to cluster (MAIN COMMAND)
cd scripts/infra && ./fresh-redeploy.sh

# Deploy with clean NATS streams (first time or reset)
cd scripts/infra && ./fresh-redeploy.sh --reset-nats

# Verify system health
cd scripts/infra && ./verify-health.sh
```

---

## 🚀 Initial Deployment (First Time)

### Prerequisites

Before deployment:

- ✅ Kubernetes cluster (1.28+) accessible
- ✅ `kubectl` configured to correct context
- ✅ Podman for building images (NOT Docker - paid software)
- ✅ cert-manager installed (for TLS certificates)
- ✅ ingress-nginx installed (for external access)
- ✅ Registry `registry.underpassai.com` accessible
- ✅ Namespace, NATS, Neo4j, Valkey already deployed

**Verify prerequisites:**
```bash
cd scripts/infra
./00-verify-prerequisites.sh
```

### Deploy Full System

```bash
cd scripts/infra

# First time: deploy infrastructure + services with fresh NATS streams
./fresh-redeploy.sh --reset-nats
```

**What it does:**
1. Scales down services with NATS consumers (if any exist)
2. Resets NATS streams (clean slate)
3. Builds all service images (orchestrator, ray-executor, context, planning, workflow, monitoring)
4. Pushes images to registry
5. Updates/creates Kubernetes deployments
6. Scales services up
7. Verifies pod health

**Duration:** ~10-15 minutes
**Expected output:**
```
✓ Orchestrator: v3.0.0-{timestamp}
✓ Ray-Executor: v3.0.0-{timestamp}
✓ Context: v2.0.0-{timestamp}
✓ Planning: v2.0.0-{timestamp}
✓ Workflow: v1.0.0-{timestamp}
✓ Monitoring: v3.2.1-{timestamp}
```

---

## 🔄 Redeploy After Code Changes (MAIN WORKFLOW)

**Use:** After git pull, feature merge, bug fixes, code changes

### Full Redeploy (Recommended)

```bash
cd scripts/infra
./fresh-redeploy.sh
```

**What it does:**
0. ✅ Cleans up zombie pods (Unknown status) - prevents vLLM restart issues
1. ✅ Scales down services with NATS consumers (releases durable consumers)
2. ✅ Rebuilds all service images with Podman
3. ✅ Pushes images to registry (`registry.underpassai.com`)
4. ✅ Updates Kubernetes deployments
5. ✅ Scales services back up
6. ✅ Waits for rollout completion
7. ✅ Verifies pod health

**Duration:** ~8-12 minutes

**Services redeployed:**
- Orchestrator: `v3.0.0-{timestamp}`
- Ray-Executor: `v3.0.0-{timestamp}`
- Context: `v2.0.0-{timestamp}`
- Planning: `v2.0.0-{timestamp}`
- Monitoring: `v3.2.1-{timestamp}`

**Example output:**
```
════════════════════════════════════════════════════════
  SWE AI Fleet - Fresh Redeploy All Microservices
════════════════════════════════════════════════════════

▶ STEP 1: Scaling down services with NATS consumers...
✓ All NATS-dependent services scaled down

▶ STEP 3: Building and pushing images...
  Build timestamp: 20251104-153045
  Orchestrator: v3.0.0-20251104-153045
✓ Orchestrator built
✓ Ray-executor built
✓ Context built
✓ Monitoring built

▶ Pushing images to registry...
✓ orchestrator pushed
✓ ray_executor pushed
✓ context pushed
✓ monitoring pushed

▶ STEP 4: Updating Kubernetes deployments...
✓ Orchestrator updated
✓ Ray-executor updated
✓ Context updated
✓ Monitoring updated

▶ STEP 5: Scaling services back up...
✓ orchestrator scaled to 1
✓ context scaled to 2
✓ monitoring-dashboard scaled to 1

▶ STEP 6: Verifying deployment health...
✓ orchestrator is ready
✓ ray-executor is ready
✓ context is ready
✓ monitoring-dashboard is ready

✓ All pods are running!

════════════════════════════════════════════════════════
  ✓ Fresh Redeploy Complete!
════════════════════════════════════════════════════════
```

---

### Options

```bash
# Skip building (use existing images, only redeploy)
./fresh-redeploy.sh --skip-build

# Also reset NATS streams (clean slate)
./fresh-redeploy.sh --reset-nats

# Help
./fresh-redeploy.sh --help
```

**Skip build duration:** ~2-3 minutes
**With NATS reset:** ~3-5 minutes extra

---

## 🔍 Verification

### Check Deployment Health

```bash
cd scripts/infra
./verify-health.sh
```

**Expected output:**
```
✓ NATS:         Running (1/1)
✓ Orchestrator: Running (1/1)
✓ Context:      Running (2/2)
✓ Ray-Executor: Running (1/1)
✓ Monitoring:   Running (1/1)
✓ Planning:     Running (2/2)
✓ StoryCoach:   Running (2/2)
✓ Workspace:    Running (2/2)
```

### Check Specific Service

```bash
# Pods for service
kubectl get pods -n swe-ai-fleet -l app=orchestrator

# Logs (last 50 lines)
kubectl logs -n swe-ai-fleet -l app=orchestrator --tail=50

# Follow logs (live)
kubectl logs -n swe-ai-fleet -l app=orchestrator -f

# Previous container (after crash)
POD=$(kubectl get pod -n swe-ai-fleet -l app=orchestrator -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n swe-ai-fleet $POD --previous
```

### Verify NATS Connectivity

```bash
# Check if service connected to NATS
kubectl logs -n swe-ai-fleet -l app=orchestrator --tail=20 | grep "NATS"

# Expected:
# ✓ NATS handler connected
# ✓ All NATS consumers started
```

---

## 🚨 Troubleshooting

See `docs/operations/K8S_TROUBLESHOOTING.md` for detailed scenarios.

---

## 🎯 Best Practices

1. Always run tests locally before deployment.
2. Prefer `fresh-redeploy.sh` over manual kubectl steps.
3. Monitor logs during rollout; verify health after.

---

**Maintained by**: Platform Team
**Review Frequency**: After each deployment change

