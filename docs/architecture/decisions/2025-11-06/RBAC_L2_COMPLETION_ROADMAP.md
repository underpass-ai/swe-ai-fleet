# RBAC Level 2 - Completion Roadmap

**Date:** 2025-11-06
**Branch:** feature/rbac-level-2-orchestrator
**Current Status:** 95% Complete (Core Logic Done)
**Target:** 100% Complete + Deployed to Production

---

## 📊 Current Status Summary

### ✅ COMPLETED (95%)

- ✅ Domain layer (11 entities, 3 services)
- ✅ Application layer (3 use cases, 3 ports)
- ✅ Infrastructure adapters (4 adapters)
- ✅ FSM engine + configuration
- ✅ RBAC validation (L1 + L2)
- ✅ Unit tests (76 tests, >90% coverage)
- ✅ Shared Kernel implementation
- ✅ Documentation (2000+ lines)
- ✅ gRPC servicer implemented

### ⚠️ PENDING (5%)

- ⚠️ Protobuf spec (specs/workflow.proto)
- ⚠️ PlanningEventsConsumer
- ⚠️ Orchestrator integration
- ⚠️ K8s deployment
- ⚠️ E2E integration tests

---

## 🎯 TODO List (10 Tasks)

### Priority 1: Critical Path (Required for Production)

#### ✅ Task 1: Create Protobuf API Spec
**Status:** Pending
**Estimate:** 1-2 hours
**Priority:** P0 (Blocker)

**Description:**
Create `specs/workflow.proto` defining the gRPC API for Workflow Service.

**Deliverables:**
```protobuf
// specs/workflow.proto
syntax = "proto3";
package workflow;

service WorkflowOrchestration {
  rpc GetWorkflowState(GetWorkflowStateRequest) returns (WorkflowStateResponse);
  rpc GetPendingTasks(GetPendingTasksRequest) returns (PendingTasksResponse);
  rpc ExecuteWorkflowAction(ExecuteWorkflowActionRequest) returns (ExecuteWorkflowActionResponse);
  rpc RequestValidation(RequestValidationRequest) returns (RequestValidationResponse);
}

// 10 message types (requests/responses)
```

**Acceptance Criteria:**
- [x] Defined based on INTERACTIONS.md
- [ ] 4 RPC methods defined
- [ ] All message types complete
- [ ] Compatible with existing servicer implementation
- [ ] Reviewed by architect

**Files to Create:**
- `specs/workflow.proto`

**References:**
- `services/workflow/INTERACTIONS.md` (lines 95-166)
- `services/workflow/infrastructure/grpc_servicer.py` (current implementation)

---

#### ✅ Task 2: Generate Protobuf Code
**Status:** Pending
**Estimate:** 30 minutes
**Priority:** P0 (Blocker)
**Depends on:** Task 1

**Commands:**
```bash
cd specs/
python -m grpc_tools.protoc \
  -I. \
  --python_out=../services/workflow/gen/ \
  --grpc_python_out=../services/workflow/gen/ \
  workflow.proto

# Fix imports
sed -i 's/^import workflow_pb2/from . import workflow_pb2/' \
  services/workflow/gen/workflow_pb2_grpc.py
```

**Acceptance Criteria:**
- [ ] workflow_pb2.py generated
- [ ] workflow_pb2_grpc.py generated
- [ ] Imports fixed
- [ ] No linter errors
- [ ] Added to .gitignore (gen/ excluded from commits)

---

#### ✅ Task 3: Implement PlanningEventsConsumer
**Status:** Pending
**Estimate:** 2-3 hours
**Priority:** P0 (Critical)

**Description:**
Implement consumer for `planning.story.transitioned` events to initialize workflow states for tasks.

**Location:** `services/workflow/infrastructure/consumers/planning_events_consumer.py`

**Implementation:**
```python
from dataclasses import dataclass
from typing import Protocol
import nats
from nats.js import JetStreamContext

@dataclass
class PlanningStoryTransitioned:
    story_id: str
    from_state: str
    to_state: str
    tasks: list[str]
    timestamp: str

class PlanningEventsConsumer:
    """Consume planning.story.transitioned events."""

    def __init__(
        self,
        js: JetStreamContext,
        workflow_repo: WorkflowStateRepositoryPort,
        messaging: MessagingPort,
    ) -> None:
        self._js = js
        self._workflow_repo = workflow_repo
        self._messaging = messaging

    async def start(self) -> None:
        """Start consuming events (PULL subscription)."""
        sub = await self._js.pull_subscribe(
            subject="planning.story.transitioned",
            durable="workflow-planning-consumer",
            stream="PLANNING_EVENTS",
        )

        while True:
            msgs = await sub.fetch(batch=10, timeout=5.0)
            for msg in msgs:
                await self._handle_story_transitioned(msg)
                await msg.ack()

    async def _handle_story_transitioned(self, msg) -> None:
        """Initialize workflow states for all tasks in story."""
        event = self._parse_event(msg.data)

        if event.to_state == "READY_FOR_EXECUTION":
            for task_id in event.tasks:
                # Create initial workflow state
                state = WorkflowState.create_initial(
                    task_id=TaskId(value=task_id),
                    story_id=StoryId(value=event.story_id),
                )

                # Persist
                await self._workflow_repo.save(state)

                # Publish assignment (first task → developer)
                await self._messaging.publish(
                    subject="workflow.task.assigned",
                    payload={
                        "task_id": task_id,
                        "story_id": event.story_id,
                        "assigned_to_role": "developer",
                        "required_action": "CLAIM_TASK",
                    },
                )
```

**Acceptance Criteria:**
- [ ] Consumer implemented with PULL subscription
- [ ] Creates WorkflowState(current_state=TODO) for each task
- [ ] Publishes workflow.task.assigned events
- [ ] Error handling (retries, DLQ)
- [ ] Unit tests (>90% coverage)
- [ ] Integrated in server.py

**Tests Required:**
- test_planning_consumer_creates_initial_states()
- test_planning_consumer_publishes_assignments()
- test_planning_consumer_handles_errors()

---

#### ✅ Task 4: Update Orchestrator Integration
**Status:** Pending
**Estimate:** 3-4 hours
**Priority:** P0 (Critical)

**Description:**
Update Orchestrator to call Workflow Service via gRPC before assigning tasks to agents.

**Files to Modify:**
- `src/swe_ai_fleet/orchestrator/usecases/orchestrate.py`
- `src/swe_ai_fleet/orchestrator/ports/workflow_port.py` (new)
- `src/swe_ai_fleet/orchestrator/adapters/grpc_workflow_adapter.py` (new)

**Implementation:**
```python
# orchestrator/ports/workflow_port.py
from typing import Protocol

class WorkflowPort(Protocol):
    async def get_workflow_state(self, task_id: str) -> WorkflowStateDTO: ...
    async def get_pending_tasks(self, role: str, limit: int) -> list[TaskDTO]: ...

# orchestrator/adapters/grpc_workflow_adapter.py
import grpc
from workflow_pb2 import GetWorkflowStateRequest
from workflow_pb2_grpc import WorkflowOrchestrationStub

class GrpcWorkflowAdapter:
    def __init__(self, workflow_url: str) -> None:
        self._channel = grpc.aio.insecure_channel(workflow_url)
        self._stub = WorkflowOrchestrationStub(self._channel)

    async def get_workflow_state(self, task_id: str) -> WorkflowStateDTO:
        request = GetWorkflowStateRequest(task_id=task_id)
        response = await self._stub.GetWorkflowState(request)

        return WorkflowStateDTO(
            task_id=response.task_id,
            current_state=response.current_state,
            role_in_charge=response.role_in_charge,
            required_action=response.required_action,
            feedback=response.feedback,
        )

# orchestrator/usecases/orchestrate.py
class OrchestrateUseCase:
    def __init__(
        self,
        workflow_port: WorkflowPort,  # NEW
        context_port: ContextPort,
        # ... other ports
    ) -> None:
        self._workflow = workflow_port
        self._context = context_port

    async def execute(self, task_id: str) -> None:
        # 1. Get workflow state
        workflow_state = await self._workflow.get_workflow_state(task_id)

        # 2. Determine which role should work
        role = workflow_state.role_in_charge
        required_action = workflow_state.required_action

        # 3. Get role-specific context
        context = await self._context.get_context(
            task_id=task_id,
            role=role,
            workflow_state=workflow_state.current_state,
        )

        # 4. Create agent with correct role
        agent = await self._create_agent(role=role)

        # 5. Execute task with workflow context
        result = await agent.execute(
            task_id=task_id,
            context=context,
            required_action=required_action,
            previous_feedback=workflow_state.feedback,
        )

        # 6. Agent publishes agent.work.completed (Workflow Service consumes)
```

**Acceptance Criteria:**
- [ ] WorkflowPort interface defined
- [ ] GrpcWorkflowAdapter implemented
- [ ] Orchestrator calls workflow before assigning
- [ ] Dependency injection configured
- [ ] Unit tests with mocks
- [ ] Integration test (orchestrator → workflow)

---

#### ✅ Task 5: Create Dockerfile for Workflow Service
**Status:** Pending
**Estimate:** 1 hour
**Priority:** P0 (Blocker for deployment)

**Location:** `services/workflow/Dockerfile`

**Implementation:**
```dockerfile
# Multi-stage build
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy proto spec and generate code
COPY specs/workflow.proto /app/specs/
RUN python -m grpc_tools.protoc \
    -I/app/specs \
    --python_out=/app/gen \
    --grpc_python_out=/app/gen \
    /app/specs/workflow.proto

# Fix imports
RUN sed -i 's/^import workflow_pb2/from . import workflow_pb2/' \
    /app/gen/workflow_pb2_grpc.py

# ---

FROM python:3.13-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /app/gen /app/services/workflow/gen

# Copy application code
COPY services/workflow /app/services/workflow
COPY core /app/core
COPY config/workflow.fsm.yaml /app/config/

# Set Python path
ENV PYTHONPATH=/app

# Expose gRPC port
EXPOSE 50056

# Run server
CMD ["python", "-m", "services.workflow.server"]
```

**Acceptance Criteria:**
- [ ] Multi-stage build (smaller image)
- [ ] Protobuf generation in builder stage
- [ ] Production dependencies only
- [ ] FSM config mounted
- [ ] Port 50056 exposed
- [ ] Builds successfully
- [ ] Image size < 200MB

---

#### ✅ Task 6: Create K8s Deployment
**Status:** Pending
**Estimate:** 1-2 hours
**Priority:** P0 (Blocker for production)

**Location:** `deploy/k8s-integration/workflow-service.yaml`

**Implementation:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: workflow-service
  namespace: swe-ai-fleet
spec:
  type: ClusterIP
  ports:
    - port: 50056
      targetPort: 50056
      protocol: TCP
      name: grpc
  selector:
    app: workflow-service
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: workflow-service
  namespace: swe-ai-fleet
spec:
  replicas: 2
  selector:
    matchLabels:
      app: workflow-service
  template:
    metadata:
      labels:
        app: workflow-service
    spec:
      containers:
      - name: workflow-service
        image: registry.underpassai.com/swe-ai-fleet/workflow:v1.0.0
        ports:
        - containerPort: 50056
          name: grpc
        env:
        - name: NATS_URL
          value: "nats://nats.swe-ai-fleet.svc.cluster.local:4222"
        - name: NEO4J_URI
          value: "bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687"
        - name: NEO4J_USER
          valueFrom:
            secretKeyRef:
              name: neo4j-auth
              key: username
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: neo4j-auth
              key: password
        - name: VALKEY_URL
          value: "redis://valkey.swe-ai-fleet.svc.cluster.local:6379"
        - name: GRPC_PORT
          value: "50056"
        - name: FSM_CONFIG
          value: "/app/config/workflow.fsm.yaml"
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        readinessProbe:
          exec:
            command: ["/bin/grpc_health_probe", "-addr=:50056"]
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          exec:
            command: ["/bin/grpc_health_probe", "-addr=:50056"]
          initialDelaySeconds: 30
          periodSeconds: 10
```

**Acceptance Criteria:**
- [ ] ClusterIP service (internal only)
- [ ] 2 replicas for HA
- [ ] Resource limits defined
- [ ] Health probes configured
- [ ] Env vars from config/secrets
- [ ] FSM config mounted
- [ ] Deploys successfully
- [ ] Pods reach Ready state

---

### Priority 2: Quality & Observability

#### ✅ Task 7: E2E Integration Tests
**Status:** Pending
**Estimate:** 4-5 hours
**Priority:** P1 (High)

**Description:**
Create end-to-end integration tests covering full workflow: Developer → Architect → QA → PO.

**Location:** `tests/integration/test_workflow_e2e.py`

**Test Scenarios:**

1. **Happy Path:**
   - Developer implements → commits
   - Architect reviews → approves
   - QA tests → passes
   - PO validates → approves
   - Task → DONE

2. **Rejection Path:**
   - Developer implements
   - Architect reviews → rejects (with feedback)
   - Developer receives feedback → revises
   - Architect re-reviews → approves
   - Continue to QA...

3. **Multi-Rejection:**
   - QA finds bugs → rejects
   - Developer fixes → commits
   - Architect re-approves
   - QA re-tests → passes

4. **RBAC Violation:**
   - Developer tries APPROVE_DESIGN
   - Should fail with RBAC error

**Acceptance Criteria:**
- [ ] 4 test scenarios implemented
- [ ] Uses real NATS, Neo4j, Valkey (in containers)
- [ ] Tests full state transitions
- [ ] Tests RBAC validation
- [ ] Tests event publishing/consuming
- [ ] All tests pass
- [ ] Added to CI pipeline

---

#### ✅ Task 8: Update LLM Prompts
**Status:** Pending
**Estimate:** 2-3 hours
**Priority:** P1 (High)

**Description:**
Update VLLMAgent prompts to include workflow context (current state, required action, feedback).

**Files to Modify:**
- `core/agents_and_tools/agents/vllm_agent.py`
- Prompt templates

**Implementation:**
```python
class VLLMAgent:
    async def execute(
        self,
        task_id: str,
        context: str,
        required_action: str,  # NEW
        previous_feedback: str | None = None,  # NEW
    ) -> ExecutionResult:
        # Build workflow-aware prompt
        workflow_context = self._build_workflow_context(
            required_action=required_action,
            previous_feedback=previous_feedback,
        )

        prompt = f"""
{context}

WORKFLOW CONTEXT:
{workflow_context}

TASK:
{task_description}
"""

    def _build_workflow_context(
        self,
        required_action: str,
        previous_feedback: str | None,
    ) -> str:
        if required_action == "REVISE_CODE" and previous_feedback:
            return f"""
You are REVISING code based on feedback:

FEEDBACK FROM REVIEWER:
{previous_feedback}

Your job: Address the feedback and improve the implementation.
When done, use COMMIT_CODE action to submit for re-review.
"""

        elif required_action == "APPROVE_DESIGN":
            return """
You are REVIEWING code implementation.

Your job: Validate architectural consistency, design patterns, security.
Actions available:
- APPROVE_DESIGN: If implementation is good
- REJECT_DESIGN: If changes are needed (provide detailed feedback)
"""

        elif required_action == "CLAIM_TASK":
            return """
You are IMPLEMENTING a feature.

Your job: Write code, tests, and documentation.
When done, use COMMIT_CODE to submit for architect review.
"""

        # ... other actions
```

**Acceptance Criteria:**
- [ ] Prompts include workflow state
- [ ] Different prompts per required_action
- [ ] Feedback prominently displayed
- [ ] Next steps clearly stated
- [ ] Tested with actual LLM
- [ ] Agent follows workflow correctly

---

#### ✅ Task 9: Update Monitoring Dashboard
**Status:** Pending
**Estimate:** 2-3 hours
**Priority:** P2 (Medium)

**Description:**
Add workflow metrics to monitoring dashboard.

**Metrics to Add:**
```python
# Prometheus metrics
workflow_tasks_total{state="pending_arch_review"}
workflow_tasks_total{state="implementing"}
workflow_tasks_total{state="done"}

workflow_transitions_total{action="APPROVE_DESIGN"}
workflow_transitions_total{action="REJECT_DESIGN"}

workflow_rbac_violations_total{role="developer", action="APPROVE_DESIGN"}

workflow_state_duration_seconds{state="pending_arch_review"}

workflow_rejection_rate{from_role="architect"}
workflow_rejection_rate{from_role="qa"}
```

**Dashboard Panels:**
1. **Workflow States** (pie chart)
2. **Transitions Rate** (time series)
3. **RBAC Violations** (counter)
4. **Average Review Time** (gauge)
5. **Rejection Rate by Role** (bar chart)

**Acceptance Criteria:**
- [ ] Metrics exported by Workflow Service
- [ ] Dashboard updated with new panels
- [ ] Metrics visible in Grafana
- [ ] Alerts configured (high rejection rate, RBAC violations)

---

#### ✅ Task 10: Deploy to K8s & Verify
**Status:** Pending
**Estimate:** 1-2 hours
**Priority:** P0 (Blocker)
**Depends on:** Tasks 1-6

**Commands:**
```bash
# Build and push image
cd services/workflow
podman build -t registry.underpassai.com/swe-ai-fleet/workflow:v1.0.0 .
podman push registry.underpassai.com/swe-ai-fleet/workflow:v1.0.0

# Deploy to K8s
kubectl apply -f deploy/k8s-integration/workflow-service.yaml

# Verify deployment
kubectl get pods -n swe-ai-fleet -l app=workflow-service
kubectl logs -n swe-ai-fleet -l app=workflow-service --tail=50

# Test gRPC endpoint
grpcurl -plaintext workflow-service.swe-ai-fleet.svc.cluster.local:50056 list

# Check health
kubectl exec -n swe-ai-fleet <pod-name> -- grpc_health_probe -addr=:50056
```

**Acceptance Criteria:**
- [ ] Image built successfully
- [ ] Pushed to registry
- [ ] Deployment created
- [ ] 2 pods running (Ready 1/1)
- [ ] gRPC endpoint accessible
- [ ] Health probes passing
- [ ] NATS connection established
- [ ] Neo4j connection established
- [ ] Valkey connection established
- [ ] No errors in logs

---

## 📊 Completion Progress

### Tasks by Priority

**P0 (Critical Path):** 6 tasks
- Task 1: Protobuf spec
- Task 2: Generate code
- Task 3: PlanningEventsConsumer
- Task 4: Orchestrator integration
- Task 5: Dockerfile
- Task 6: K8s deployment
- Task 10: Deploy & verify

**P1 (High):** 2 tasks
- Task 7: E2E tests
- Task 8: LLM prompts

**P2 (Medium):** 1 task
- Task 9: Monitoring

**Total:** 10 tasks

---

## ⏱️ Time Estimates

### Minimum Path (P0 only): 9-14 hours
- Task 1: 1-2h
- Task 2: 0.5h
- Task 3: 2-3h
- Task 4: 3-4h
- Task 5: 1h
- Task 6: 1-2h
- Task 10: 1-2h

### Full Completion (P0 + P1 + P2): 15-24 hours
- Minimum path: 9-14h
- E2E tests: 4-5h
- LLM prompts: 2-3h
- Monitoring: 2-3h

**Realistic Timeline:**
- **Sprint 1 (P0):** 2-3 days (critical path to production)
- **Sprint 2 (P1):** 1-2 days (quality improvements)
- **Sprint 3 (P2):** 1 day (observability)

**Total: 4-6 days to 100% completion**

---

## 🎯 Success Criteria

### Definition of Done (RBAC L2)

- [ ] All 10 tasks completed
- [ ] Workflow Service deployed to K8s
- [ ] 2 replicas running and healthy
- [ ] Orchestrator calling Workflow Service
- [ ] Full workflow flow working (Dev → Arch → QA → PO)
- [ ] E2E tests passing
- [ ] Monitoring dashboard showing metrics
- [ ] No RBAC violations
- [ ] Performance targets met (< 50ms for GetWorkflowState)
- [ ] Documentation updated
- [ ] Architect approval

### Production Readiness Checklist

- [ ] Code reviewed
- [ ] Tests passing (unit + integration + E2E)
- [ ] Performance tested
- [ ] Security audit passed
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Rollback plan documented
- [ ] Runbook created
- [ ] On-call team trained

---

## 📈 Risks & Mitigations

### Risk 1: Orchestrator Integration Complexity
**Probability:** Medium
**Impact:** High

**Mitigation:**
- Start with read-only integration (GetWorkflowState)
- Gradual rollout (1 story at a time)
- Fallback: Skip workflow validation temporarily

### Risk 2: Performance Issues
**Probability:** Low
**Impact:** Medium

**Mitigation:**
- Valkey cache should keep latency < 20ms
- Load test before production
- Auto-scaling configured (HPA)

### Risk 3: Event Ordering Issues
**Probability:** Medium
**Impact:** High

**Mitigation:**
- NATS JetStream guarantees ordering
- Idempotent event handlers
- Sequence numbers in events

---

## 📚 References

- **RBAC Strategy:** `docs/sessions/2025-11-05/RBAC_LEVELS_2_AND_3_STRATEGY.md`
- **Interactions:** `services/workflow/INTERACTIONS.md`
- **FSM Config:** `config/workflow.fsm.yaml`
- **Verification:** `docs/architecture/decisions/2025-11-06/RBAC_L2_VERIFICATION.md`
- **Shared Kernel:** `docs/architecture/decisions/2025-11-06/SHARED_KERNEL_FINAL_DESIGN.md`

---

**Created by:** AI Assistant
**Date:** 2025-11-06
**Status:** Roadmap Ready
**Next Action:** Start Task 1 (Protobuf spec)

**Awaiting:** Architect approval to proceed with implementation

