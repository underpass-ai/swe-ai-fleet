# Deployment & Redeployment Operations

**Status**: ✅ Production-Ready  
**Last Updated**: 2025-10-23  
**Namespace**: `swe-ai-fleet`  
**Registry**: `registry.underpassai.com/swe-ai-fleet`

This document describes **standard operating procedures** for deploying and redeploying SWE AI Fleet microservices to Kubernetes.

---

## 🎯 Quick Reference

```bash
# Initial deployment
cd scripts/infra && ./deploy-all.sh

# Redeploy after code changes
./scripts/rebuild-and-deploy.sh

# Single service redeploy (with NATS reset)
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=0
sleep 5
podman build -f services/orchestrator/Dockerfile -t registry.underpassai.com/swe-ai-fleet/orchestrator:v3.0.0 .
podman push registry.underpassai.com/swe-ai-fleet/orchestrator:v3.0.0
kubectl set image deployment/orchestrator orchestrator=registry.underpassai.com/swe-ai-fleet/orchestrator:v3.0.0 -n swe-ai-fleet
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=1
```

---

## 📋 Prerequisites

Before deployment:

- ✅ Kubernetes cluster (1.28+) accessible
- ✅ `kubectl` configured to correct context
- ✅ Podman/Buildah for building images (NOT Docker - paid software)
- ✅ cert-manager installed (for TLS certificates)
- ✅ ingress-nginx installed (for external access)
- ✅ Registry `registry.underpassai.com` accessible

**Verify prerequisites:**
```bash
./scripts/infra/00-verify-prerequisites.sh
```

Expected output:
```
✓ kubectl found (v1.31.2)
✓ Cluster reachable (wrx80-node1)
✓ cert-manager ready
✓ ingress-nginx ready
✓ Podman found (v5.2.4)
```

---

## 🚀 Initial Deployment (From Scratch)

### Option 1: Automated (Recommended)

```bash
cd scripts/infra
./deploy-all.sh
```

**What it does:**
1. Creates `swe-ai-fleet` namespace
2. Deploys NATS JetStream (messaging backbone)
3. Initializes NATS streams (PLANNING_EVENTS, CONTEXT, ORCHESTRATOR_EVENTS, etc.)
4. Deploys ConfigMaps (FSM, rigor profiles, service URLs)
5. Deploys all microservices (orchestrator, context, ray-executor, monitoring)
6. Verifies pod health

**Duration:** ~5-10 minutes  
**Exit codes:** 0 (success), 1 (failure)

### Option 2: Manual Step-by-Step

For debugging or fine-grained control:

```bash
# 1. Create namespace
kubectl apply -f deploy/k8s/00-namespace.yaml

# 2. Deploy NATS JetStream
kubectl apply -f deploy/k8s/01-nats.yaml
kubectl wait --for=condition=ready pod/nats-0 -n swe-ai-fleet --timeout=120s

# 3. Initialize NATS streams (CRITICAL - must run before services)
kubectl apply -f deploy/k8s/02b-nats-init-streams.yaml
kubectl wait --for=condition=complete job/nats-init-streams -n swe-ai-fleet --timeout=60s
kubectl logs job/nats-init-streams -n swe-ai-fleet

# 4. Deploy ConfigMaps
kubectl apply -f deploy/k8s/00-configmaps.yaml

# 5. Deploy microservices
kubectl apply -f deploy/k8s/08-context-service.yaml
kubectl apply -f deploy/k8s/10-ray-executor.yaml
kubectl apply -f deploy/k8s/11-orchestrator.yaml
kubectl apply -f deploy/k8s/12-monitoring-dashboard.yaml

# 6. Wait for services to be ready
kubectl wait --for=condition=ready pod -l app=orchestrator -n swe-ai-fleet --timeout=120s
kubectl wait --for=condition=ready pod -l app=context -n swe-ai-fleet --timeout=120s

# 7. Initialize councils (orchestrator needs this)
kubectl apply -f deploy/k8s/11b-orchestrator-init-councils.yaml
kubectl wait --for=condition=complete job/orchestrator-init-councils -n swe-ai-fleet --timeout=120s

# 8. Verify deployment
kubectl get pods -n swe-ai-fleet
```

**Expected state:**
```
NAME                                    READY   STATUS    
context-xxx                             1/1     Running   
monitoring-dashboard-xxx                1/1     Running   
orchestrator-xxx                        1/1     Running   
ray-executor-xxx                        1/1     Running   
nats-0                                  1/1     Running   
neo4j-0                                 1/1     Running   
valkey-0                                1/1     Running   
```

---

## 🔄 Redeployment After Code Changes

### Option A: Automated Rebuild & Redeploy (Recommended)

**Use when:** Code changes in any service, version bumps, bug fixes

```bash
# Full rebuild and redeploy all services
./scripts/rebuild-and-deploy.sh
```

**Versions** (defined in script):
- Orchestrator: `v3.0.0-core-refactor`
- Ray-Executor: `v3.0.0-core-refactor`  
- Context: `v2.0.0-core-refactor`
- Monitoring: `v2.0.0-core-refactor`
- Jobs: `v2.0.0-core-refactor`

**Steps executed:**
1. Builds all service images with Podman
2. Pushes to `registry.underpassai.com/swe-ai-fleet/`
3. Updates Kubernetes deployments
4. Waits for rollout completion (120s timeout)
5. Verifies pod health (checks for CrashLoopBackOff)

**Options:**
```bash
# Skip build (use existing images)
./scripts/rebuild-and-deploy.sh --skip-build

# Don't wait for rollout
./scripts/rebuild-and-deploy.sh --no-wait

# Help
./scripts/rebuild-and-deploy.sh --help
```

**Duration:** ~8-12 minutes (full rebuild)  
**Duration:** ~2-3 minutes (skip build)

### Option B: Manual Single Service Redeploy

**Use when:** Debugging specific service, testing changes, fine-grained control

#### For Services WITH NATS Consumers (orchestrator, context, monitoring)

**⚠️ CRITICAL:** Must scale to 0 first to release NATS durable consumers

```bash
# Example: Redeploying orchestrator

# 1. Scale down (releases NATS consumers)
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=0
sleep 10  # Allow graceful shutdown

# 2. Build new image
podman build -f services/orchestrator/Dockerfile \
  -t registry.underpassai.com/swe-ai-fleet/orchestrator:v3.0.1 .

# 3. Push to registry
podman push registry.underpassai.com/swe-ai-fleet/orchestrator:v3.0.1

# 4. Update deployment
kubectl set image deployment/orchestrator \
  orchestrator=registry.underpassai.com/swe-ai-fleet/orchestrator:v3.0.1 \
  -n swe-ai-fleet

# 5. Scale up
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=1

# 6. Wait for readiness
kubectl wait --for=condition=ready --timeout=120s \
  pod -l app=orchestrator -n swe-ai-fleet

# 7. Verify startup
kubectl logs -n swe-ai-fleet -l app=orchestrator --tail=30

# Expected logs:
# ✓ NATS handler connected
# ✓ DeliberationResultCollector started
# ✓ All NATS consumers started
# 🚀 Orchestrator Service listening on port 50055
```

**Why scale to 0 first?**

NATS JetStream uses **durable consumers** (one per subject). If old pod is still running:
```
nats.js.errors.Error: consumer is already bound to a subscription
```

Scaling to 0 **releases all consumers cleanly**, then new pod subscribes without conflicts.

**Services that MUST scale to 0:**
- ✅ `orchestrator` (subscribes to: `planning.story.transitioned`, `planning.plan.approved`, `agent.response.completed`)
- ✅ `context` (subscribes to: `orchestration.deliberation.completed`, `planning.>`)
- ✅ `monitoring-dashboard` (subscribes to: `planning.>`, `orchestration.>`, `context.>`)

#### For Services WITHOUT NATS (ray-executor, Go services, UI)

**Can use rolling update directly:**

```bash
# Example: ray-executor

# 1. Build
podman build -f services/ray-executor/Dockerfile \
  -t registry.underpassai.com/swe-ai-fleet/ray-executor:v3.0.1 .

# 2. Push
podman push registry.underpassai.com/swe-ai-fleet/ray-executor:v3.0.1

# 3. Update (rolling update automatically)
kubectl set image deployment/ray-executor \
  ray-executor=registry.underpassai.com/swe-ai-fleet/ray-executor:v3.0.1 \
  -n swe-ai-fleet

# 4. Wait
kubectl rollout status deployment/ray-executor -n swe-ai-fleet --timeout=120s
```

---

## 🔧 NATS Stream Management

### When to Reset NATS Streams

**Reset streams when:**
- Consumer binding conflicts (`consumer is already bound to a subscription`)
- Testing event flows from clean slate
- Debugging message processing issues
- After major architecture changes

### Procedure: Clean NATS Slate

```bash
# 1. Scale down ALL services with NATS consumers (CRITICAL)
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=0
kubectl scale deployment/context -n swe-ai-fleet --replicas=0
kubectl scale deployment/monitoring-dashboard -n swe-ai-fleet --replicas=0
sleep 10  # Wait for graceful shutdown

# 2. Delete existing streams and consumers
kubectl delete job nats-delete-streams -n swe-ai-fleet 2>/dev/null || true
kubectl apply -f deploy/k8s/02a-nats-delete-streams.yaml
kubectl wait --for=condition=complete --timeout=60s job/nats-delete-streams -n swe-ai-fleet

# 3. Verify deletion
kubectl logs job/nats-delete-streams -n swe-ai-fleet | grep "Deleted:"

# 4. Recreate streams
kubectl delete job nats-init-streams -n swe-ai-fleet 2>/dev/null || true
kubectl apply -f deploy/k8s/02b-nats-init-streams.yaml
kubectl wait --for=condition=complete --timeout=60s job/nats-init-streams -n swe-ai-fleet

# 5. Verify creation
kubectl logs job/nats-init-streams -n swe-ai-fleet | grep "Created:"

# Expected output:
#   ✅ Created: 5 (PLANNING_EVENTS, AGENT_REQUESTS, AGENT_RESPONSES, CONTEXT, ORCHESTRATOR_EVENTS)

# 6. Scale services back up
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=1
kubectl scale deployment/context -n swe-ai-fleet --replicas=1
kubectl scale deployment/monitoring-dashboard -n swe-ai-fleet --replicas=1

# 7. Verify NATS connectivity
kubectl logs -n swe-ai-fleet -l app=orchestrator --tail=20 | grep "NATS"

# Expected:
# ✓ NATS handler connected
# ✓ All NATS consumers started
```

### List Current Streams

```bash
kubectl exec -n swe-ai-fleet nats-0 -- nats stream ls

# Or with details
kubectl exec -n swe-ai-fleet nats-0 -- nats stream info PLANNING_EVENTS
```

---

## 🏛️ Council Management

### Initialize Default Councils

**When to run:**
- After first deployment of orchestrator
- After deleting councils
- After changing vLLM model/configuration

```bash
# Delete previous job if exists
kubectl delete job orchestrator-init-councils -n swe-ai-fleet 2>/dev/null || true

# Run initialization
kubectl apply -f deploy/k8s/11b-orchestrator-init-councils.yaml

# Wait for completion
kubectl wait --for=condition=complete --timeout=120s \
  job/orchestrator-init-councils -n swe-ai-fleet

# Verify results
kubectl logs job/orchestrator-init-councils -n swe-ai-fleet
```

**Expected output:**
```
🚀 Initializing default councils...
✅ Council DEV created with 3 agents
✅ Council QA created with 3 agents
✅ Council ARCHITECT created with 3 agents
✅ Council DEVOPS created with 3 agents
✅ Council DATA created with 3 agents
✓ All councils initialized successfully
```

**Configuration** (via ConfigMap `service-urls`):
- `VLLM_URL`: `http://vllm.swe-ai-fleet.svc.cluster.local:8000`
- `VLLM_MODEL`: `Qwen/Qwen2.5-0.5B-Instruct` (default)
- `NUM_AGENTS_PER_COUNCIL`: `3`

### Delete All Councils

**When to run:**
- Before reinitializing with different configuration
- Testing council creation
- Resetting system state

```bash
kubectl delete job orchestrator-delete-councils -n swe-ai-fleet 2>/dev/null || true
kubectl apply -f deploy/k8s/11a-orchestrator-delete-councils.yaml
kubectl wait --for=condition=complete --timeout=60s \
  job/orchestrator-delete-councils -n swe-ai-fleet

kubectl logs job/orchestrator-delete-councils -n swe-ai-fleet
```

---

## 🔍 Verification & Health Checks

### Check All Pods

```bash
# All pods in namespace
kubectl get pods -n swe-ai-fleet

# Wide view with node placement
kubectl get pods -n swe-ai-fleet -o wide

# Only running pods
kubectl get pods -n swe-ai-fleet --field-selector=status.phase=Running
```

### Check Specific Service

```bash
# Pods for service
kubectl get pods -n swe-ai-fleet -l app=orchestrator

# Deployment status
kubectl get deployment orchestrator -n swe-ai-fleet

# ReplicaSet history
kubectl get rs -n swe-ai-fleet -l app=orchestrator
```

### Health Check Script

```bash
./scripts/infra/verify-health.sh
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

### Check Logs

```bash
# Recent logs
kubectl logs -n swe-ai-fleet -l app=orchestrator --tail=50

# Follow logs (live streaming)
kubectl logs -n swe-ai-fleet -l app=orchestrator -f

# Previous container (after crash)
POD=$(kubectl get pod -n swe-ai-fleet -l app=orchestrator -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n swe-ai-fleet $POD --previous

# All replicas with prefixes
kubectl logs -n swe-ai-fleet -l app=orchestrator --tail=20 --prefix
```

### Verify Service Endpoints

```bash
# Internal services (ClusterIP)
kubectl get svc -n swe-ai-fleet

# External access (Ingress)
kubectl get ingress -n swe-ai-fleet

# Test internal connectivity
kubectl run test-pod --rm -it --image=curlimages/curl -n swe-ai-fleet -- \
  curl -v http://orchestrator.swe-ai-fleet.svc.cluster.local:50055
```

---

## 🚨 Troubleshooting

### Issue A: `consumer is already bound to a subscription`

**Symptoms:**
```
nats.js.errors.Error: consumer is already bound to a subscription
Pod: CrashLoopBackOff
```

**Cause:** Multiple pods trying to use same NATS durable consumer (happens during rolling updates)

**Fix:**
```bash
# Scale to 0 first, then back to 1
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=0
kubectl wait --for=delete pod -l app=orchestrator -n swe-ai-fleet --timeout=60s
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=1
kubectl wait --for=condition=ready pod -l app=orchestrator -n swe-ai-fleet --timeout=120s
```

**Prevention:** Always scale to 0 before redeploying services with NATS consumers.

---

### Issue B: `CrashLoopBackOff`

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
- ❌ Missing ConfigMap → Verify `kubectl get cm -n swe-ai-fleet`
- ❌ Wrong image tag → Check `kubectl describe deploy/orchestrator -n swe-ai-fleet | grep Image`
- ❌ Import errors (src/ → core/ migration) → Check logs for ModuleNotFoundError
- ❌ Consumer conflicts → Scale to 0 first

---

### Issue C: `ImagePullBackOff`

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

**Fixes:**
```bash
# A) Verify image was pushed
podman images | grep orchestrator

# B) Check registry accessibility from cluster
kubectl run test-registry --rm -it --image=curlimages/curl -n swe-ai-fleet -- \
  curl -k https://registry.underpassai.com/v2/

# C) If TLS issue, check cert-manager
kubectl get certificate -A
```

---

### Issue D: Pods Stuck in `Pending`

**Diagnosis:**
```bash
# Check node resources
kubectl describe nodes | grep -A5 "Allocated resources"

# Check PVC status
kubectl get pvc -n swe-ai-fleet

# Check events
kubectl get events -n swe-ai-fleet --sort-by='.lastTimestamp' | tail -20
```

**Common causes:**
- ❌ Insufficient CPU/memory → Scale down other services or add nodes
- ❌ PVC not bound → Check storage class
- ❌ Taints/tolerations → Check node selectors

---

### Issue E: Service Not Receiving NATS Messages

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

**Fixes:**
```bash
# Reset NATS streams (see "NATS Stream Management" section above)
```

---

## 🔄 Rollback Procedures

### Rollback Single Service

```bash
# View rollout history
kubectl rollout history deployment/orchestrator -n swe-ai-fleet

# Rollback to previous revision
kubectl rollout undo deployment/orchestrator -n swe-ai-fleet

# Rollback to specific revision
kubectl rollout undo deployment/orchestrator --to-revision=3 -n swe-ai-fleet

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

## 📊 Monitoring During Deployment

### Watch Rollout

```bash
# Watch specific deployment
kubectl rollout status deployment/orchestrator -n swe-ai-fleet

# Watch all pods (live updates)
kubectl get pods -n swe-ai-fleet -w

# Watch events in real-time
kubectl get events -n swe-ai-fleet -w --sort-by='.lastTimestamp'
```

### Dashboard Access

```bash
# Port-forward to monitoring dashboard
kubectl port-forward -n swe-ai-fleet svc/monitoring-dashboard 8080:8080

# Open browser
# http://localhost:8080
```

**Or via Ingress (if configured):**
- Monitoring: http://monitoring.underpassai.com
- UI: https://swe-fleet.underpassai.com
- Ray: https://ray.underpassai.com

---

## 🎯 Best Practices

### 1. Version Tagging (Semantic Versioning)

**Pattern:** `vMAJOR.MINOR.PATCH-descriptor`

**Examples:**
| Change Type | Example | When |
|-------------|---------|------|
| Bug fix | `v2.2.2` → `v2.2.3` | Hotfix, no API change |
| New feature (compatible) | `v2.2.3` → `v2.3.0` | New RPC, backward compatible |
| Breaking change | `v2.3.0` → `v3.0.0` | src/→core/ refactor, API change |
| Descriptor | `v3.0.0-core-refactor` | Meaningful tag for tracking |

**Update versions in:** `scripts/rebuild-and-deploy.sh` (lines 20-25)

### 2. Testing Before Deploy

**Always run tests locally:**
```bash
# Activate venv
source .venv/bin/activate

# Unit tests (fast)
make test-unit

# Coverage (verify >90%)
make test-coverage

# Lint (fix errors)
ruff check . --fix
```

**CI must be green** before deploying to production.

### 3. Gradual Rollout for Critical Services

For production deployments:

1. **Deploy to staging first** (if available)
2. **Monitor for 5-10 minutes**
3. **Check logs for errors**
4. **Deploy to production**
5. **Keep previous image** for quick rollback

### 4. Change Communication

**Before deploying breaking changes:**

1. Update `CHANGELOG.md` with changes
2. Tag Git commit: `git tag v3.0.0 && git push origin v3.0.0`
3. Notify team (Slack/Discord)
4. Document migration steps in this file
5. Update `ROADMAP.md` if milestone reached

### 5. Backup Before Major Changes

```bash
# Backup Neo4j data
kubectl exec -n swe-ai-fleet neo4j-0 -- \
  neo4j-admin database dump neo4j --to-path=/backups

# Backup Valkey (if needed)
kubectl exec -n swe-ai-fleet valkey-0 -- \
  redis-cli --rdb /data/dump.rdb SAVE
```

---

## 📚 Related Documentation

- [Kubernetes Troubleshooting](./K8S_TROUBLESHOOTING.md) - Detailed issue resolution
- [Microservices Architecture](../architecture/MICROSERVICES_ARCHITECTURE.md) - System design
- [NATS Consumers Design](../architecture/NATS_CONSUMERS_DESIGN.md) - Messaging patterns
- [Orchestrator Service](../microservices/ORCHESTRATOR_SERVICE.md) - Service details
- [Context Service](../microservices/CONTEXT_SERVICE.md) - Context management
- [Getting Started](../getting-started/README.md) - First-time setup
- [Scripts README](../../scripts/README.md) - Available automation scripts

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

**Maintained by**: Platform Team  
**Review Frequency**: After each deployment change  
**Last Verified**: 2025-10-23 (v3.0.0-core-refactor deployment)
