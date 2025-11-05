# Deployment & Redeployment Operations

**Status**: ✅ Production-Ready  
**Last Updated**: 2025-11-04  
**Namespace**: `swe-ai-fleet`  
**Registry**: `registry.underpassai.com/swe-ai-fleet`

This document describes **standard operating procedures** for deploying and redeploying SWE AI Fleet microservices to Kubernetes.

---

## 🎯 Quick Reference

```bash
# Initial deployment (first time only)
cd scripts/infra && ./deploy-all.sh

# Redeploy after code changes (MAIN COMMAND)
cd scripts/infra && ./fresh-redeploy.sh

# Verify system health
cd scripts/infra && ./verify-health.sh
```

---

## 🚀 Initial Deployment (First Time Only)

### Prerequisites

Before deployment:

- ✅ Kubernetes cluster (1.28+) accessible
- ✅ `kubectl` configured to correct context
- ✅ Podman for building images (NOT Docker - paid software)
- ✅ cert-manager installed (for TLS certificates)
- ✅ ingress-nginx installed (for external access)
- ✅ Registry `registry.underpassai.com` accessible

**Verify prerequisites:**
```bash
cd scripts/infra
./00-verify-prerequisites.sh
```

### Deploy Full System

```bash
cd scripts/infra
./deploy-all.sh
```

**What it does:**
1. Creates `swe-ai-fleet` namespace
2. Deploys NATS JetStream (messaging backbone)
3. Initializes NATS streams (PLANNING_EVENTS, CONTEXT, etc.)
4. Deploys ConfigMaps (FSM, profiles, service URLs)
5. Deploys all microservices (orchestrator, context, ray-executor, monitoring)
6. Verifies pod health

**Duration:** ~5-10 minutes  
**Expected output:**
```
✓ NATS:         Running (1/1)
✓ Orchestrator: Running (1/1)
✓ Context:      Running (2/2)
✓ Ray-Executor: Running (1/1)
✓ Monitoring:   Running (1/1)
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

### Issue: `consumer is already bound to a subscription`

**Symptoms:**
```
nats.js.errors.Error: consumer is already bound to a subscription
Pod: CrashLoopBackOff
```

**Cause:** Multiple pods trying to use same NATS durable consumer (happens during rolling updates)

**Fix:** `fresh-redeploy.sh` handles this automatically by scaling to 0 first.

**Manual fix if needed:**
```bash
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=0
sleep 10
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=1
kubectl wait --for=condition=ready pod -l app=orchestrator -n swe-ai-fleet --timeout=120s
```

---

### Issue: `CrashLoopBackOff`

**Diagnosis:**
```bash
# Get failing pod
POD=$(kubectl get pod -n swe-ai-fleet -l app=orchestrator -o jsonpath='{.items[0].metadata.name}')

# Check logs
kubectl logs -n swe-ai-fleet $POD --tail=100

# Check events
kubectl describe pod -n swe-ai-fleet $POD | grep -A10 "Events:"

# Check previous container
kubectl logs -n swe-ai-fleet $POD --previous
```

**Common causes:**
- ❌ NATS not ready → Wait for `nats-0` pod
- ❌ Missing ConfigMap → `kubectl get cm -n swe-ai-fleet`
- ❌ Wrong image tag → Check deployment image
- ❌ Import errors → Check logs for ModuleNotFoundError
- ❌ Consumer conflicts → Run `fresh-redeploy.sh` again

---

### Issue: `ImagePullBackOff`

**Symptoms:**
```
Pod: ImagePullBackOff
ErrImagePull: failed to pull image
```

**Diagnosis:**
```bash
# Check image exists in registry
curl -k https://registry.underpassai.com/v2/swe-ai-fleet/orchestrator/tags/list

# Check pod events
kubectl describe pod -n swe-ai-fleet $POD | grep -A5 "Failed to pull image"
```

**Fix:** Rebuild and push image:
```bash
cd scripts/infra
./fresh-redeploy.sh  # Will rebuild and push
```

---

### Issue: Service Not Receiving NATS Messages

**Diagnosis:**
```bash
# Check consumer status
kubectl exec -n swe-ai-fleet nats-0 -- nats consumer ls PLANNING_EVENTS

# Check if service subscribed
kubectl logs -n swe-ai-fleet -l app=orchestrator | grep "subscribe\|consumer"

# Publish test message
kubectl exec -n swe-ai-fleet nats-0 -- \
  nats pub planning.story.transitioned '{"story_id":"test-001"}'

# Check if received
kubectl logs -n swe-ai-fleet -l app=orchestrator --since=10s | grep "test-001"
```

**Fix:** Reset NATS streams:
```bash
cd scripts/infra
./fresh-redeploy.sh --reset-nats
```

---

## 🔄 Rollback Procedures

### Rollback to Previous Version

```bash
# View rollout history
kubectl rollout history deployment/orchestrator -n swe-ai-fleet

# Rollback to previous revision
kubectl rollout undo deployment/orchestrator -n swe-ai-fleet

# Verify rollback
kubectl rollout status deployment/orchestrator -n swe-ai-fleet --timeout=120s
```

### Emergency: Complete System Reset

**⚠️ WARNING:** This deletes ALL data (Neo4j, Valkey, NATS streams)

```bash
# Complete cleanup
kubectl delete namespace swe-ai-fleet

# Redeploy from scratch
cd scripts/infra
./deploy-all.sh
```

**Use only when:** Irrecoverable state, testing, demo reset

---

## 🎯 Best Practices

### 1. Always Test Locally First

```bash
# Run tests before deployment
make test-unit

# Check coverage
make test-unit | grep "TOTAL"

# Expected: >85% coverage
```

### 2. Use Fresh Redeploy for Code Changes

**When you:**
- Merge feature branch
- Fix bugs
- Update dependencies
- Change configuration

**Always run:**
```bash
cd scripts/infra
./fresh-redeploy.sh
```

**Why fresh-redeploy.sh instead of kubectl rolling update:**
- ✅ Handles NATS consumer conflicts (scales to 0 first)
- ✅ Rebuilds AND deploys in one command
- ✅ Generates unique tags (timestamp-based)
- ✅ Verifies health after deployment
- ✅ Graceful shutdown before update

### 3. Monitor Logs During Deployment

```bash
# In separate terminal, watch logs
kubectl logs -n swe-ai-fleet -l app=orchestrator -f

# Watch pod status
kubectl get pods -n swe-ai-fleet -w
```

### 4. Verify After Deployment

```bash
# Check all services
./verify-health.sh

# Check specific service startup
kubectl logs -n swe-ai-fleet -l app=orchestrator --tail=30 | grep "listening\|started\|ready"

# Expected:
# ✓ NATS handler connected
# ✓ DeliberationResultCollector started
# ✓ All NATS consumers started
# 🚀 Orchestrator Service listening on port 50055
```

---

## 📊 Deployment Checklist

### Before Deployment

- [ ] All tests passing (`make test-unit`)
- [ ] Coverage ≥ 85%
- [ ] Code merged to main (or testing in feature branch)
- [ ] Git committed and pushed
- [ ] CHANGELOG.md updated (if production)

### During Deployment

- [ ] Run `./fresh-redeploy.sh`
- [ ] Monitor logs in separate terminal
- [ ] Watch for CrashLoopBackOff
- [ ] Verify NATS connectivity

### After Deployment

- [ ] Run `./verify-health.sh`
- [ ] Check logs for errors
- [ ] Test basic functionality (create story, run deliberation)
- [ ] Monitor for 5-10 minutes

---

## 🏛️ Services Deployed

| Service | Port | NATS Consumer? | Scale to 0? | Purpose |
|---------|------|----------------|-------------|---------|
| **orchestrator** | 50055 | ✅ Yes | ✅ Required | Deliberation orchestration |
| **context** | 50054 | ✅ Yes | ✅ Required | Context management |
| **planning** | 50051 | ✅ Yes | ✅ Required | User story FSM |
| **monitoring-dashboard** | 8080 | ✅ Yes | ✅ Required | System monitoring |
| **ray-executor** | 50056 | ❌ No | ❌ Not needed | Agent task execution |
| **nats** | 4222 | N/A | ❌ Never | Message broker |
| **neo4j** | 7687 | N/A | ❌ Never | Graph database |
| **valkey** | 6379 | N/A | ❌ Never | KV storage |

**Why scale to 0?**

NATS JetStream uses **durable consumers** (one per subject). If old pod is still running when new pod starts:
```
Error: consumer is already bound to a subscription
```

Scaling to 0 **releases all consumers cleanly**, then new pod subscribes without conflicts.

`fresh-redeploy.sh` handles this automatically ✅

---

## 📚 Available Scripts

### Main Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| **`deploy-all.sh`** | Initial deployment | First time setup |
| **`fresh-redeploy.sh`** | Redeploy after changes | After git pull/merge |
| **`verify-health.sh`** | Health check | After deployment |
| `00-verify-prerequisites.sh` | Check cluster | Before first deploy |

### Individual Steps (Advanced)

These are called by `deploy-all.sh`, use only for debugging:

| Script | Description |
|--------|-------------|
| `01-deploy-namespace.sh` | Create namespace |
| `02-deploy-nats.sh` | Deploy NATS JetStream |
| `03-deploy-config.sh` | Deploy ConfigMaps |
| `04-deploy-services.sh` | Deploy microservices |
| `06-expose-ui.sh` | Expose UI publicly |
| `07-expose-ray-dashboard.sh` | Expose Ray dashboard |
| `08-deploy-context.sh` | Deploy context service |

**For normal operations, always use `fresh-redeploy.sh` instead of individual scripts.**

---

## 🔧 Advanced Operations

### Reset NATS Streams

**When:** Consumer conflicts, testing from clean slate

```bash
cd scripts/infra
./fresh-redeploy.sh --reset-nats
```

This will:
1. Scale down all NATS-dependent services
2. Delete existing NATS streams and consumers
3. Recreate streams from scratch
4. Redeploy services
5. Services reconnect to fresh streams

### Skip Image Build

**When:** Images already built and pushed

```bash
cd scripts/infra
./fresh-redeploy.sh --skip-build
```

**Duration:** ~2-3 minutes (vs ~8-12 minutes for full rebuild)

**Use case:** Configuration changes only (ConfigMaps, replica counts), no code changes

---

## 📊 Monitoring & Logs

### Watch Deployment

```bash
# Watch all pods (live updates)
kubectl get pods -n swe-ai-fleet -w

# Watch specific deployment
kubectl rollout status deployment/orchestrator -n swe-ai-fleet

# Watch events
kubectl get events -n swe-ai-fleet -w --sort-by='.lastTimestamp'
```

### Access Dashboards

```bash
# Port-forward to monitoring dashboard
kubectl port-forward -n swe-ai-fleet svc/monitoring-dashboard 8080:8080
# Then open: http://localhost:8080
```

**Or via Ingress:**
- Monitoring: http://monitoring.underpassai.com
- UI: https://swe-fleet.underpassai.com
- Ray: https://ray.underpassai.com

---

## 🎯 Common Workflows

### After Merging Feature Branch

```bash
# 1. Update local main
git checkout main
git pull origin main

# 2. Redeploy to cluster
cd scripts/infra
./fresh-redeploy.sh

# 3. Verify
./verify-health.sh

# 4. Monitor logs for 5-10 minutes
kubectl logs -n swe-ai-fleet -l app=orchestrator -f
```

### After Hotfix

```bash
# 1. Apply fix, commit, push
git add .
git commit -m "fix: critical bug"
git push origin main

# 2. Quick redeploy
cd scripts/infra
./fresh-redeploy.sh

# 3. Verify fix deployed
kubectl logs -n swe-ai-fleet -l app=orchestrator --tail=50 | grep "version\|build"
```

### Testing Feature Branch (Before Merge)

```bash
# 1. Checkout feature branch
git checkout feature/new-feature

# 2. Deploy from feature branch
cd scripts/infra
./fresh-redeploy.sh

# 3. Test functionality
# (API calls, UI testing, etc.)

# 4. If issues, fix and redeploy
git add .
git commit -m "fix: issue"
./fresh-redeploy.sh

# 5. When ready, merge to main
git checkout main
git merge --no-ff feature/new-feature
./fresh-redeploy.sh  # Final deploy from main
```

---

## 🔗 System URLs

**Production:**
- Registry: https://registry.underpassai.com
- Monitoring Dashboard: http://monitoring.underpassai.com  
- UI: https://swe-fleet.underpassai.com
- Ray Dashboard: https://ray.underpassai.com

**Internal (ClusterIP):**
- Orchestrator: `orchestrator.swe-ai-fleet.svc.cluster.local:50055`
- Context: `context.swe-ai-fleet.svc.cluster.local:50054`
- Ray-Executor: `ray-executor.swe-ai-fleet.svc.cluster.local:50056`
- NATS: `nats.swe-ai-fleet.svc.cluster.local:4222`

---

## 📚 Related Documentation

- [Scripts README](../../scripts/infra/README.md) - Detailed script documentation
- [K8S Troubleshooting](./K8S_TROUBLESHOOTING.md) - Issue resolution
- [Microservices Architecture](../architecture/MICROSERVICES_ARCHITECTURE.md) - System design
- [Getting Started](../getting-started/README.md) - First-time setup

---

**Maintained by**: Tirso García (Platform Team)  
**Review Frequency**: After each deployment change  
**Last Updated**: 2025-11-04 (RBAC Level 1 merge)
