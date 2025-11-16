# Getting Started with SWE AI Fleet

**Last Updated:** 2025-11-07
**Status:** ✅ Production-Ready
**Deployment Time:** ~10-15 minutes

---

## 🎯 What is SWE AI Fleet?

SWE AI Fleet is a **production-ready AI software development platform** that orchestrates teams of AI agents to collaboratively develop software. It features:

### **Core Capabilities**

- **🤖 Multi-Agent Deliberation** - Teams of 3 agents collaborate with peer review
- **🔐 3-Level RBAC System** - Tool, Workflow, and Data access control
- **📊 FSM-Driven Workflows** - Story and Task lifecycle management
- **🧠 Precision Context** - Knowledge graph-powered surgical context (200 tokens vs 100K)
- **⚡ GPU-Accelerated** - Ray + vLLM (self-hosted, 7B-13B models)
- **🏗️ Hexagonal Architecture** - DDD + Ports & Adapters (all 6 services)
- **🔍 Full Observability** - Complete LLM reasoning visible

### **Why SWE AI Fleet?**

✅ **100% Self-Hostable** - No cloud AI dependencies
✅ **Data Sovereignty** - Code never leaves your network
✅ **Small Models Work** - 7B-13B models perform like GPT-4 (precision context)
✅ **Predictable Costs** - Add GPUs (CapEx) not API calls (OpEx)
✅ **Production-Ready** - 1,265 tests, 90% coverage, clean architecture

---

## 🚀 Quick Start (10 Minutes)

### Prerequisites

**Required:**
- Kubernetes cluster (1.28+)
- kubectl configured to cluster
- Podman (for building images)
- Registry accessible (registry.underpassai.com or local)

**Optional (for GPU agents):**
- NVIDIA GPU (RTX 3090/4090)
- GPU operator installed
- Ray cluster

**Verify prerequisites:**
```bash
cd scripts/infra
./00-verify-prerequisites.sh
```

---

### Deploy to Kubernetes

```bash
# 1. Clone repository
git clone https://github.com/underpass-ai/swe-ai-fleet
cd swe-ai-fleet

# 2. Verify prerequisites
./scripts/infra/00-verify-prerequisites.sh

# 3. Deploy all services (first time: reset NATS streams)
cd scripts/infra
./fresh-redeploy.sh --reset-nats

# 4. Verify health
./verify-health.sh
```

**Expected output:**
```
✓ orchestrator built
✓ context built
✓ planning built
✓ workflow built
✓ ray-executor built
✓ monitoring built

✓ All images pushed to registry

✓ orchestrator is ready
✓ context is ready
✓ planning is ready
✓ workflow is ready
✓ ray-executor is ready
✓ monitoring-dashboard is ready

✓ All pods are running!
```

**Duration:** ~10-15 minutes (first time with --reset-nats)

---

## 🏗️ What Gets Deployed

### **6 Microservices**

| Service | Port | Purpose | Status |
|---------|------|---------|--------|
| **Orchestrator** | 50055 | Multi-agent deliberation | ✅ Running |
| **Context** | 50054 | Knowledge graph context | ✅ Running |
| **Planning** | 50051 | Story FSM & lifecycle | ✅ Running |
| **Workflow** | 50056 | Task FSM + RBAC L2 | ✅ Running |
| **Ray Executor** | 50057 | GPU agent execution | ✅ Running |
| **Monitoring** | 8080 | System health dashboard | ✅ Running |

### **Infrastructure**

- NATS JetStream (messaging backbone)
- Neo4j (knowledge graph)
- Valkey (cache)

### **NATS Streams Created**

- `PLANNING_EVENTS` - Story state transitions
- `AGENT_WORK` - Agent execution results
- `WORKFLOW_EVENTS` - Task workflow events
- `CONTEXT_EVENTS` - Context updates

---

## 🔍 Verify Deployment

### Check All Services

```bash
cd scripts/infra
./verify-health.sh
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

### Check Specific Service

```bash
# View pods
kubectl get pods -n swe-ai-fleet -l app=workflow

# View logs
kubectl logs -n swe-ai-fleet -l app=workflow --tail=50

# Follow logs (live)
kubectl logs -n swe-ai-fleet -l app=workflow -f
```

### Test gRPC APIs

```bash
# Port-forward Workflow Service
kubectl port-forward -n swe-ai-fleet svc/workflow 50056:50056

# Use grpcurl (install: go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest)
grpcurl -plaintext localhost:50056 list
grpcurl -plaintext localhost:50056 fleet.workflow.v1.WorkflowOrchestrationService/GetWorkflowState
```

---

## 🌐 Access Services

### Internal Access (within cluster)

Services are available via ClusterIP DNS:

```
orchestrator.swe-ai-fleet.svc.cluster.local:50055
context.swe-ai-fleet.svc.cluster.local:50054
planning.swe-ai-fleet.svc.cluster.local:50051
workflow.swe-ai-fleet.svc.cluster.local:50056
ray-executor.swe-ai-fleet.svc.cluster.local:50057
monitoring.swe-ai-fleet.svc.cluster.local:8080
nats.swe-ai-fleet.svc.cluster.local:4222
```

### External Access (optional)

**Monitoring Dashboard:**
```bash
# Port-forward
kubectl port-forward -n swe-ai-fleet svc/monitoring-dashboard 8080:8080

# Access: http://localhost:8080
```

**Or configure Ingress:**
- Edit `deploy/k8s/13-monitoring-dashboard.yaml`
- Add Ingress resource with your domain

**Ray Dashboard** (if RayCluster deployed):
```bash
./scripts/infra/07-expose-ray-dashboard.sh
# Access: https://ray.underpassai.com
```

---

## 🔄 After Code Changes

### Redeploy Services

```bash
cd scripts/infra

# Standard redeploy (keeps NATS streams)
./fresh-redeploy.sh

# With NATS stream reset (clean slate)
./fresh-redeploy.sh --reset-nats

# Skip build (only redeploy, faster)
./fresh-redeploy.sh --skip-build
```

**Duration:**
- Full rebuild: ~10-12 minutes
- Skip build: ~2-3 minutes

### View Rollout Status

```bash
# Watch deployment
kubectl rollout status deployment/workflow -n swe-ai-fleet

# Watch all pods
kubectl get pods -n swe-ai-fleet -w
```

---

## 🆘 Troubleshooting

### Issue: CrashLoopBackOff

**Diagnosis:**
```bash
# Get pod name
POD=$(kubectl get pod -n swe-ai-fleet -l app=workflow -o jsonpath='{.items[0].metadata.name}')

# Check logs
kubectl logs -n swe-ai-fleet $POD --tail=100

# Check previous container (if crashed)
kubectl logs -n swe-ai-fleet $POD --previous

# Check events
kubectl describe pod -n swe-ai-fleet $POD | grep -A10 Events
```

**Common causes:**
- NATS not ready → Wait for `nats-0` pod
- Missing ConfigMap → `kubectl get cm -n swe-ai-fleet`
- Import errors → Check logs for ModuleNotFoundError
- Consumer conflicts → Run `./fresh-redeploy.sh` again

### Issue: ImagePullBackOff

**Diagnosis:**
```bash
# Check image exists
kubectl describe pod -n swe-ai-fleet $POD | grep "Failed to pull image"
```

**Fix:**
```bash
cd scripts/infra
./fresh-redeploy.sh  # Rebuilds and pushes images
```

### Issue: Service Not Receiving NATS Messages

**Diagnosis:**
```bash
# Check consumer status
kubectl exec -n swe-ai-fleet nats-0 -- nats consumer ls WORKFLOW_EVENTS

# Check service logs
kubectl logs -n swe-ai-fleet -l app=workflow | grep "subscribe\|consumer"

# Publish test message
kubectl exec -n swe-ai-fleet nats-0 -- \
  nats pub workflow.task.assigned '{"task_id":"test-001"}'

# Check if received
kubectl logs -n swe-ai-fleet -l app=workflow --since=10s | grep "test-001"
```

**Fix:**
```bash
cd scripts/infra
./fresh-redeploy.sh --reset-nats  # Reset NATS streams
```

---

## 📚 Next Steps

### 1. Understand the Architecture

- [Microservices Architecture](../architecture/MICROSERVICES_ARCHITECTURE.md) - System design
- [RBAC System](../architecture/RBAC_REAL_WORLD_TEAM_MODEL.md) - 3-level access control
- [Hexagonal Architecture](../normative/HEXAGONAL_ARCHITECTURE_PRINCIPLES.md) - Design principles

### 2. Explore the System

```bash
# View all resources
kubectl get all -n swe-ai-fleet

# Monitor NATS streams
kubectl exec -n swe-ai-fleet nats-0 -- nats stream ls

# Check Neo4j
kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n)"

# Check Valkey
kubectl exec -n swe-ai-fleet valkey-0 -- valkey-cli DBSIZE
```

### 3. Run Example Workflows

**Create a story:**
```bash
# Port-forward Planning Service
kubectl port-forward -n swe-ai-fleet svc/planning 50051:50051

# Use grpcurl
grpcurl -plaintext -d '{
  "brief": "Implement user authentication",
  "title": "As a user, I want to log in securely"
}' localhost:50051 fleet.planning.v1.PlanningService/CreateStory
```

**Check workflow status:**
```bash
# Port-forward Workflow Service
kubectl port-forward -n swe-ai-fleet svc/workflow 50056:50056

# Query workflow state
grpcurl -plaintext -d '{"task_id": "task-123"}' \
  localhost:50056 fleet.workflow.v1.WorkflowOrchestrationService/GetWorkflowState
```

### 4. Monitor System Health

```bash
# Access Monitoring Dashboard
kubectl port-forward -n swe-ai-fleet svc/monitoring-dashboard 8080:8080

# Open in browser: http://localhost:8080
```

---

## 🛠️ Development Workflow

### Make Code Changes

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes to services/workflow/ (for example)
# ... edit code ...

# 3. Run tests
make test-unit

# 4. Deploy to cluster
cd scripts/infra
./fresh-redeploy.sh

# 5. Verify
./verify-health.sh
kubectl logs -n swe-ai-fleet -l app=workflow --tail=50
```

### Run Tests Locally

```bash
# Unit tests (~20s)
make test-unit

# Integration tests (~45s)
make test-integration

# E2E tests (~3-5min, requires cluster)
make test-e2e

# All tests
make test-all
```

---

## 🔗 Important Links

### Documentation
- [Architecture Overview](../architecture/MICROSERVICES_ARCHITECTURE.md)
- [Deployment Guide](../operations/DEPLOYMENT.md)
- [Roadmap](../../ROADMAP.md)
- [Testing Strategy](../TESTING_ARCHITECTURE.md)

### Operations
- [Troubleshooting](../operations/K8S_TROUBLESHOOTING.md)
- [Monitoring Setup](../monitoring/OBSERVABILITY_SETUP.md)

### Development
- [Contributing Guide](../development/CONTRIBUTING.md)
- [Git Workflow](../GIT_WORKFLOW.md)

---

## 📊 System Requirements

### Minimum (Development)

- **Kubernetes:** 1.28+ (K3s, kind, minikube OK)
- **CPU:** 4 cores
- **Memory:** 16GB RAM
- **Storage:** 50GB SSD

**Services run, but agents will be mock** (no GPU)

### Recommended (Production)

- **Kubernetes:** 1.28+ (production cluster)
- **CPU:** 32 cores
- **Memory:** 128GB RAM
- **GPU:** 4× NVIDIA RTX 3090/4090 (24GB each)
- **Storage:** 500GB SSD

**Full agent execution with deliberation**

### For Detailed Requirements

See [prerequisites.md](prerequisites.md)

---

## 🎓 Learning Path

### Day 1: Deployment & Basics
1. Deploy system (`fresh-redeploy.sh --reset-nats`)
2. Verify health (`verify-health.sh`)
3. Explore monitoring dashboard
4. Read [MICROSERVICES_ARCHITECTURE.md](../architecture/MICROSERVICES_ARCHITECTURE.md)

### Day 2: Architecture Deep-Dive
1. Study [Hexagonal Architecture](../normative/HEXAGONAL_ARCHITECTURE_PRINCIPLES.md)
2. Read [RBAC Strategy](../architecture/RBAC_REAL_WORLD_TEAM_MODEL.md)
3. Explore codebase (start with Workflow Service)
4. Run tests (`make test-unit`)

### Day 3: Development
1. Create feature branch
2. Modify a service (add feature)
3. Write tests
4. Deploy to cluster
5. Verify functionality

---

## 🚀 Quick 10-Minute Demo (Local Services)

For a rapid demo using local CRI-O services without Kubernetes:

### Prerequisites

```bash
# Redis with auth
sudo crictl runp deploy/crio/redis-pod.json | tee /tmp/redis.pod
POD=$(cat /tmp/redis.pod)
sudo crictl create "$POD" deploy/crio/redis-ctr.json deploy/crio/redis-pod.json | tee /tmp/redis.ctr
sudo crictl start $(cat /tmp/redis.ctr)

# Neo4j
sudo crictl runp deploy/crio/neo4j-pod.json | tee /tmp/neo4j.pod
POD=$(cat /tmp/neo4j.pod)
sudo crictl create "$POD" deploy/crio/neo4j-ctr.json deploy/crio/neo4j-pod.json | tee /tmp/neo4j.ctr
sudo crictl start $(cat /tmp/neo4j.ctr)

# (Optional) RedisInsight UI
sudo crictl runp deploy/crio/redisinsight-pod.json | tee /tmp/ri.pod
POD=$(cat /tmp/ri.pod)
sudo crictl create "$POD" deploy/crio/redisinsight-ctr.json deploy/crio/redisinsight-pod.json | tee /tmp/ri.ctr
sudo crictl start $(cat /tmp/ri.ctr)

# (Optional) vLLM GPU
sudo crictl runp --runtime nvidia deploy/crio/vllm-pod.json | tee /tmp/vllm.pod
POD=$(cat /tmp/vllm.pod)
sudo crictl create "$POD" deploy/crio/vllm-ctr.json deploy/crio/vllm-pod.json | tee /tmp/vllm.ctr
sudo crictl start $(cat /tmp/vllm.ctr)
# vLLM health: curl -fsS http://127.0.0.1:8000/health && echo ok
```

Default ports: Redis 6379, RedisInsight 5540, Neo4j 7474/7687, vLLM 8000

### Seed Demo Data

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .

export REDIS_URL=redis://:swefleet-dev@localhost:6379/0
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=swefleet-dev

python scripts/seed_context_example.py
```

### Run Frontend

```bash
pip install -e .[web]

HOST=0.0.0.0 PORT=8080 \
REDIS_URL=redis://:swefleet-dev@localhost:6379/0 \
NEO4J_URI=bolt://localhost:7687 \
NEO4J_USER=neo4j \
NEO4J_PASSWORD=swefleet-dev \
swe_ai_fleet-web
```

### Verify Demo

- UI: http://localhost:8080/ui/report?case_id=CTX-001
- API: http://localhost:8080/api/report?case_id=CTX-001&persist=false

### Quick Cleanup

```bash
for f in /tmp/{redis,ri,vllm,neo4j}.ctr; do [ -f "$f" ] && sudo crictl rm -f $(cat "$f"); done
for f in /tmp/{redis,ri,vllm,neo4j}.pod; do [ -f "$f" ] && sudo crictl rmp -f $(cat "$f"); done
```

---

## 🛠️ Development Practices

### Domain-Driven Design (DDD)

SWE AI Fleet strictly follows DDD to maintain clean, testable code:

**Domain Objects:**
```python
@dataclass(frozen=True)
class ContextSection:
    content: str
    section_type: str
    priority: int = 0

@dataclass
class ContextSections:
    sections: list[ContextSection] = field(default_factory=list)

    def add_section(self, content: str, section_type: str, priority: int = 0) -> None:
        section = ContextSection(content=content, section_type=section_type, priority=priority)
        self.sections.append(section)
```

**Ports & Adapters Pattern:**
```python
class GraphAnalyticsReadPort(Protocol):
    """Read-only analytics queries over decision graph."""
    def get_critical_decisions(self, case_id: str, limit: int = 10) -> list[CriticalNode]: ...
    def find_cycles(self, case_id: str, max_depth: int = 6) -> list[PathCycle]: ...

class Neo4jGraphAnalyticsReadAdapter(GraphAnalyticsReadPort):
    """Concrete implementation using Neo4j."""
    def __init__(self, store: Neo4jStore) -> None:
        self._store = store
```

**Use Cases:**
```python
class ImplementationReportUseCase:
    def __init__(
        self,
        planning_store: PlanningReadPort,
        analytics_port: GraphAnalyticsReadPort | None = None,
    ) -> None:
        self.store = planning_store
        self.analytics_port = analytics_port
```

### Code Organization

```
src/swe_ai_fleet/
├── core/                    # Domain layer
│   ├── domain/             # Entities, Value Objects, Events
│   ├── usecases/           # Application logic
│   └── ports/              # Interfaces
├── services/               # Microservices
│   ├── orchestrator/
│   ├── context/
│   └── ... (others)
└── infrastructure/         # Adapters, database, messaging
    ├── adapters/
    ├── persistence/
    └── messaging/
```

### Testing Strategy

Follow the **Testing Pyramid**:
- **70% Unit Tests** - Fast, isolated, mocked
- **20% Integration Tests** - Real components, containerized
- **10% E2E Tests** - Full system, K8s cluster

See [reference/testing.md](../reference/testing.md) for complete testing guide.

### Quality Standards

- **Coverage:** Minimum 90% on new code
- **Linting:** `ruff check . --fix`
- **Type Checking:** Full Python type hints required
- **Documentation:** Every module must have docstrings

Run quality checks:
```bash
make test-unit        # Run tests + coverage
ruff check . --fix    # Lint + fix
```

---

## 🆘 Need Help?

### Common Issues

**"Pods in CrashLoopBackOff"**
→ Check logs: `kubectl logs -n swe-ai-fleet -l app=<service> --tail=100`

**"ImagePullBackOff"**
→ Rebuild: `cd scripts/infra && ./fresh-redeploy.sh`

**"consumer is already bound"**
→ Reset: `./fresh-redeploy.sh --reset-nats`

**"Tests failing"**
→ See which service: `make test-unit` (shows failed services)

### Support Channels

- **Documentation:** [docs/](../)
- **Issues:** [GitHub Issues](https://github.com/underpass-ai/swe-ai-fleet/issues)
- **Email:** contact@underpassai.com

---

## 📝 Configuration

### Change Registry

Edit `scripts/infra/fresh-redeploy.sh`:
```bash
REGISTRY="your-registry.com/swe-ai-fleet"
```

### Adjust Resources

Edit K8s manifests in `deploy/k8s/`:
```yaml
# Example: deploy/k8s/15-workflow-service.yaml
resources:
  requests:
    memory: "1Gi"    # Increase if needed
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

Then redeploy:
```bash
cd scripts/infra && ./fresh-redeploy.sh
```

### Change Replica Counts

Edit K8s manifests:
```yaml
spec:
  replicas: 3  # Increase for high availability
```

Workflow and Planning support multiple replicas (NATS PULL consumers).

---

## 🎯 What's Next?

After successful deployment:

1. ✅ **Explore Services**
   - Try gRPC APIs (grpcurl)
   - Monitor NATS streams
   - Query Neo4j graph

2. ✅ **Read Documentation**
   - [MICROSERVICES_ARCHITECTURE.md](../architecture/MICROSERVICES_ARCHITECTURE.md)
   - [RBAC_REAL_WORLD_TEAM_MODEL.md](../architecture/RBAC_REAL_WORLD_TEAM_MODEL.md)
   - [DEPLOYMENT.md](../operations/DEPLOYMENT.md)

3. ✅ **Run Example Workflows**
   - Create story (Planning Service)
   - Monitor workflow (Workflow Service)
   - Execute agent tasks (Orchestrator)

4. ✅ **Contribute**
   - Pick an issue
   - Create feature branch
   - Submit PR

---

## 🏆 Production Checklist

Before going to production:

- [ ] All 6 services deployed and healthy
- [ ] NATS streams initialized
- [ ] Neo4j persistence working
- [ ] Valkey cache working
- [ ] Tests passing (make test-unit)
- [ ] Monitoring dashboard accessible
- [ ] Logs structured and queryable
- [ ] Resource limits configured
- [ ] Backup strategy defined
- [ ] Runbooks created

---

## 📊 System Status (Nov 7, 2025)

**Deployment Status:** ✅ **Production-Ready**

| Component | Status | Tests | Coverage |
|-----------|--------|-------|----------|
| Orchestrator | ✅ Production | 142 | 65% |
| Context | ✅ Production | - | 96% |
| Planning | ✅ Production | 278 | 95% |
| Workflow | ✅ Ready | 138 | 94% |
| Ray Executor | ✅ Production | - | 90% |
| Monitoring | ✅ Production | 305 | 98% |
| **TOTAL** | **✅ Ready** | **1,265** | **90%** |

**RBAC Status:**
- Level 1 (Tool Access): ✅ Production
- Level 2 (Workflow Actions): ✅ Production-Ready
- Level 3 (Data Access): ⏳ Next Sprint

**Infrastructure:** NATS, Neo4j, Valkey all production-ready

---

## 🔗 Related Documentation

- **[Deployment Guide](../operations/DEPLOYMENT.md)** - Operations procedures
- **[Architecture](../architecture/MICROSERVICES_ARCHITECTURE.md)** - System design
- **[Roadmap](../../ROADMAP.md)** - Project timeline
- **[Troubleshooting](../operations/K8S_TROUBLESHOOTING.md)** - Issue resolution

---

**Maintained by:** Tirso García Ibáñez
**Review Frequency:** After each major deployment
**Next Update:** After RBAC L3 implementation
