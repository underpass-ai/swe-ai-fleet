# SWE AI Fleet - Quick Start Guide

**Get the system running in 10 minutes**

**Last Updated:** 2025-11-07
**Deployment Target:** Kubernetes 1.28+
**Status:** ✅ Production-Ready

---

## 🎯 What You'll Deploy

**6 Production Microservices** (all Python):
- Orchestrator (50055) - Multi-agent deliberation
- Context (50054) - Knowledge graph context
- Planning (50051) - Story FSM
- Workflow (50056) - Task FSM + RBAC L2
- Ray Executor (50057) - GPU agents
- Monitoring (8080) - System health

**Infrastructure:**
- NATS JetStream (messaging)
- Neo4j (graph database)
- Valkey (cache)

---

## ⚡ Option 1: Kubernetes (Recommended)

### Prerequisites

**Required:**
- ✅ Kubernetes cluster 1.28+ (K3s, kind, minikube, or production cluster)
- ✅ kubectl configured (`kubectl cluster-info`)
- ✅ Podman installed (for building images)
- ✅ Registry accessible (or use local registry)

**Optional (for GPU agents):**
- NVIDIA GPU (RTX 3090/4090)
- GPU operator installed
- Ray cluster

### Step 1: Clone & Verify

```bash
# Clone repository
git clone https://github.com/underpass-ai/swe-ai-fleet
cd swe-ai-fleet

# Verify prerequisites
./scripts/infra/00-verify-prerequisites.sh
```

**Expected output:**
```
✅ kubectl: Found
✅ Kubernetes cluster: Accessible
✅ Podman: Found
✅ NATS: Ready (if pre-deployed)
```

### Step 2: Deploy System

```bash
cd scripts/infra

# First time: Deploy with clean NATS streams
./fresh-redeploy.sh --reset-nats
```

**What happens:**
1. Builds 6 service images (multi-stage Dockerfiles)
2. Pushes to registry
3. Creates/updates K8s deployments
4. Initializes NATS streams
5. Waits for pods to be ready
6. Verifies health

**Duration:** ~10-15 minutes

**Output:**
```
▶ STEP 3: Building and pushing images...
  Build timestamp: 20251107-180000
  ✓ Orchestrator built
  ✓ Ray-executor built
  ✓ Context built
  ✓ Planning built
  ✓ Workflow built
  ✓ Monitoring built

▶ Pushing images to registry...
  ✓ All images pushed

▶ STEP 4: Updating Kubernetes deployments...
  ✓ All deployments updated

▶ STEP 6: Verifying deployment health...
  ✓ orchestrator is ready
  ✓ ray-executor is ready
  ✓ context is ready
  ✓ planning is ready
  ✓ workflow is ready
  ✓ monitoring-dashboard is ready

✓ All pods are running!

════════════════════════════════════════════════════════
  ✓ Fresh Redeploy Complete!
════════════════════════════════════════════════════════
```

### Step 3: Verify Deployment

```bash
# Check health
./verify-health.sh

# View pods
kubectl get pods -n swe-ai-fleet

# View services
kubectl get svc -n swe-ai-fleet
```

**Expected:**
```
✓ NATS:         Running (1/1)
✓ Orchestrator: Running (1/1)
✓ Context:      Running (2/2)
✓ Planning:     Running (2/2)
✓ Workflow:     Running (2/2)
✓ Ray-Executor: Running (1/1)
✓ Monitoring:   Running (1/1)
```

---

## 🧪 Test the System

### Test 1: Planning Service (Create Story)

```bash
# Port-forward Planning Service
kubectl port-forward -n swe-ai-fleet svc/planning 50051:50051 &

# Install grpcurl (if not installed)
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest

# List available methods
grpcurl -plaintext localhost:50051 list fleet.planning.v1.PlanningService

# Create a story
grpcurl -plaintext -d '{
  "title": "As a user, I want to authenticate securely",
  "brief": "Implement JWT-based authentication with refresh tokens"
}' localhost:50051 fleet.planning.v1.PlanningService/CreateStory

# Output: {"story_id": "story-abc123", "state": "draft", ...}
```

### Test 2: Workflow Service (Check Task State)

```bash
# Port-forward Workflow Service
kubectl port-forward -n swe-ai-fleet svc/workflow 50056:50056 &

# List methods
grpcurl -plaintext localhost:50056 list fleet.workflow.v1.WorkflowOrchestrationService

# Get pending tasks for developer
grpcurl -plaintext -d '{
  "role": "developer",
  "limit": 10
}' localhost:50056 fleet.workflow.v1.WorkflowOrchestrationService/GetPendingTasks
```

### Test 3: NATS Events

```bash
# Install NATS CLI
go install github.com/nats-io/natscli/nats@latest

# Port-forward NATS
kubectl port-forward -n swe-ai-fleet nats-0 4222:4222 &

# List streams
nats --server nats://localhost:4222 stream ls

# View stream info
nats --server nats://localhost:4222 stream info PLANNING_EVENTS
nats --server nats://localhost:4222 stream info WORKFLOW_EVENTS

# Subscribe to events (watch live)
nats --server nats://localhost:4222 sub 'planning.>'
nats --server nats://localhost:4222 sub 'workflow.>'
```

### Test 4: Monitoring Dashboard

```bash
# Port-forward Monitoring
kubectl port-forward -n swe-ai-fleet svc/monitoring-dashboard 8080:8080 &

# Open in browser
open http://localhost:8080
```

**Dashboard shows:**
- Service health status
- NATS stream metrics
- Consumer lag
- Orchestrator info

---

## 🔄 After Code Changes

### Redeploy Specific Service

```bash
cd scripts/infra

# Rebuild and redeploy all services
./fresh-redeploy.sh

# Skip build (only redeploy, faster)
./fresh-redeploy.sh --skip-build
```

**Duration:**
- Full rebuild: ~10-12 min
- Skip build: ~2-3 min

### Watch Deployment

```bash
# Watch pods update
kubectl get pods -n swe-ai-fleet -w

# Watch specific service rollout
kubectl rollout status deployment/workflow -n swe-ai-fleet

# View logs
kubectl logs -n swe-ai-fleet -l app=workflow -f
```

---

## 🐛 Troubleshooting

### Issue: CrashLoopBackOff

```bash
# Get pod name
POD=$(kubectl get pod -n swe-ai-fleet -l app=workflow -o jsonpath='{.items[0].metadata.name}')

# Check logs
kubectl logs -n swe-ai-fleet $POD --tail=100

# Check previous container (after crash)
kubectl logs -n swe-ai-fleet $POD --previous

# Describe pod (see events)
kubectl describe pod -n swe-ai-fleet $POD
```

**Common causes:**
- ❌ NATS not ready → Wait for nats-0 pod
- ❌ Missing environment variables → Check deployment manifest
- ❌ Import errors → Check logs for ModuleNotFoundError
- ❌ Consumer conflicts → Run `./fresh-redeploy.sh` again

### Issue: ImagePullBackOff

```bash
# Rebuild and push image
cd scripts/infra
./fresh-redeploy.sh
```

### Issue: "consumer is already bound to a subscription"

**Cause:** Multiple pods trying to use same NATS durable consumer

**Fix:**
```bash
cd scripts/infra
./fresh-redeploy.sh  # Automatically scales to 0 first
```

**Or manually:**
```bash
kubectl scale deployment/workflow -n swe-ai-fleet --replicas=0
sleep 10
kubectl scale deployment/workflow -n swe-ai-fleet --replicas=2
```

### Issue: Service Not Responding

```bash
# Check if pod is running
kubectl get pods -n swe-ai-fleet -l app=workflow

# Check service endpoint
kubectl get endpoints -n swe-ai-fleet workflow

# Test connectivity from another pod
kubectl run -n swe-ai-fleet test-pod --rm -it --image=curlimages/curl -- sh
# Inside pod:
curl -v workflow:50056
```

---

## 🎓 Next Steps

### Learn the Architecture

1. **[MICROSERVICES_ARCHITECTURE.md](../architecture/MICROSERVICES_ARCHITECTURE.md)**
   - System design
   - Service responsibilities
   - DDD + Hexagonal Architecture

2. **[RBAC_REAL_WORLD_TEAM_MODEL.md](../architecture/RBAC_REAL_WORLD_TEAM_MODEL.md)**
   - 3-level RBAC system
   - Role definitions
   - Policy enforcement

3. **[DEPLOYMENT.md](../operations/DEPLOYMENT.md)**
   - Deployment procedures
   - Troubleshooting guide
   - Operations runbook

### Run Tests Locally

```bash
# Unit tests (fast, ~20s)
make test-unit

# Integration tests (~45s)
make test-integration

# E2E tests (requires cluster, ~3-5min)
make test-e2e

# All tests
make test-all
```

### Explore Code

```bash
# Start with Workflow Service (newest, cleanest architecture)
cd services/workflow

# Domain layer (pure business logic)
ls domain/entities/       # WorkflowState, StateTransition
ls domain/services/       # WorkflowStateMachine (FSM)
ls domain/value_objects/  # TaskId, Role, WorkflowStateEnum

# Application layer (use cases)
ls application/usecases/  # ExecuteWorkflowAction, etc.
ls application/dto/       # Data contracts

# Infrastructure layer (adapters)
ls infrastructure/adapters/   # Neo4j, Valkey, NATS
ls infrastructure/consumers/  # NATS event handlers
ls infrastructure/mappers/    # Serialization logic
```

### Make Your First Change

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes (example: add logging)
# Edit services/workflow/server.py

# 3. Run tests
make test-unit

# 4. Deploy to cluster
cd scripts/infra
./fresh-redeploy.sh

# 5. Verify
./verify-health.sh
kubectl logs -n swe-ai-fleet -l app=workflow --tail=50 | grep "my new log"
```

---

## 📚 Resources

### Essential Documentation

- **[README.md](../../README.md)** - Project overview
- **[ROADMAP.md](../../ROADMAP.md)** - Project timeline & milestones
- **[Architecture](../architecture/)** - System design docs
- **[Operations](../operations/)** - Deployment & troubleshooting

### Development

- **[Testing Architecture](../TESTING_ARCHITECTURE.md)** - Testing strategy (normative)
- **[Hexagonal Principles](../normative/HEXAGONAL_ARCHITECTURE_PRINCIPLES.md)** - Architecture rules
- **[Git Workflow](../GIT_WORKFLOW.md)** - Branch strategy

### APIs

- **[specs/](../../specs/)** - Protocol Buffers definitions
- **[gRPC Testing](../specs/INTERACTIVE_API_TESTING.md)** - grpcurl, grpcui usage

---

## 🆘 Getting Help

### Troubleshooting Steps

1. Check logs: `kubectl logs -n swe-ai-fleet -l app=<service> --tail=100`
2. Check pod status: `kubectl describe pod -n swe-ai-fleet <pod-name>`
3. Check NATS: `nats stream ls`
4. Review [Troubleshooting Guide](../operations/K8S_TROUBLESHOOTING.md)

### Support Channels

- **GitHub Issues:** [underpass-ai/swe-ai-fleet/issues](https://github.com/underpass-ai/swe-ai-fleet/issues)
- **Documentation:** [docs/](../)
- **Email:** contact@underpassai.com

---

## ✅ Success Checklist

After deployment, verify:

- [ ] All 6 service pods running
- [ ] NATS streams created (PLANNING_EVENTS, WORKFLOW_EVENTS, AGENT_WORK)
- [ ] Neo4j accessible
- [ ] Valkey accessible
- [ ] Monitoring dashboard accessible (port-forward to :8080)
- [ ] gRPC APIs responding (grpcurl tests)
- [ ] NATS events flowing (nats sub)
- [ ] No CrashLoopBackOff pods
- [ ] Logs show "Service started" messages

---

**🎉 You're Ready!** System is deployed and healthy.

**Next:** [Read the Architecture Docs](../architecture/MICROSERVICES_ARCHITECTURE.md)

---

**Maintained by:** Tirso García Ibáñez
**Last Updated:** Nov 7, 2025
