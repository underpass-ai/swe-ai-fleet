# Workflow Orchestration Service - Interactions

**Service Name:** Workflow Orchestration Service
**Port:** 50056 (gRPC)
**Protocol:** gRPC + NATS Events
**Purpose:** RBAC Level 2 - Workflow Action Control
**Created:** 2025-11-05

---

## 🎯 Service Purpose

**Bounded Context:** Task Execution Workflow Coordination

**Responsibilities:**
1. Manage task execution FSM (12 states)
2. Validate RBAC actions (APPROVE_DESIGN, REJECT_DESIGN, etc.)
3. Route tasks between roles (Dev → Architect → QA → PO)
4. Process agent work completion events
5. Publish task assignment events

**What it does NOT do:**
- Execute agent tasks (Orchestrator does this)
- Manage story lifecycle (Planning Service does this)
- Store code/artifacts (Git/Workspace does this)
- Provide context (Context Service does this)

---

## 🔄 Interactions Overview

```
┌──────────────┐  1. agent.work.completed   ┌─────────────────────┐
│  VLLMAgent   ├───────────────────────────>│   Workflow Service  │
│  (Any Role)  │  (NATS Event)               │   Port: 50056       │
└──────────────┘                             │                     │
                                             │  - Validate action  │
┌──────────────┐  2. gRPC Call               │  - Transition FSM   │
│ Orchestrator ├───────────────────────────>│  - Store state      │
│   :50055     │  GetWorkflowState()         │  - Route to next    │
│              │  (non-blocking)             │                     │
│              │<───────────────────────────┤                     │
└──────┬───────┘  Returns immediately        └──────┬──────────────┘
       │                                             │
       │ 3. workflow.task.assigned (NATS)            │
       │<────────────────────────────────────────────┘
       │
       │ 4. Assign to Agent
       ↓
┌──────────────┐
│  VLLMAgent   │  5. Execute task
│  (Next Role) │
└──────────────┘
```

---

## 📥 Inbound Interactions

### 1. VLLMAgent → Workflow Service (NATS Event)

**Subject:** `agent.work.completed`
**Pattern:** Event-driven (asynchronous)
**Frequency:** After every agent task completion

**Payload:**
```json
{
  "task_id": "task-001",
  "agent_id": "agent-dev-001",
  "role": "developer",
  "action_performed": "COMMIT_CODE",
  "result": {
    "success": true,
    "operations_count": 5,
    "artifacts": {
      "commit_sha": "abc123def456",
      "files_changed": ["src/auth.py", "tests/test_auth.py"]
    },
    "reasoning": "Implemented JWT authentication with..."
  },
  "timestamp": "2025-11-05T19:00:00Z"
}
```

**Consumer:** `AgentWorkCompletedConsumer` (PULL subscription)
**Processing:**
1. Validate action is allowed (RBAC)
2. Execute FSM transition
3. Store new state in Neo4j + Valkey
4. Publish events (state_changed, task_assigned if needed)

---

### 2. Orchestrator → Workflow Service (gRPC)

**RPC:** `GetWorkflowState(task_id)`
**Pattern:** Synchronous request/response
**Frequency:** Before assigning task to agent

**Request:**
```protobuf
GetWorkflowStateRequest {
  task_id: "task-001"
}
```

**Response:**
```protobuf
WorkflowStateResponse {
  task_id: "task-001"
  current_state: "pending_arch_review"
  role_in_charge: "architect"
  required_action: "APPROVE_DESIGN"
  history: [...]
  feedback: null
  updated_at: 1730833200
  retry_count: 0
}
```

**Use Case:** Orchestrator needs to know:
- Which role should work on this task?
- What action is required?
- Is there previous feedback (if rejected)?

---

### 3. Orchestrator → Workflow Service (gRPC)

**RPC:** `GetPendingTasks(role, limit)`
**Pattern:** Synchronous request/response
**Frequency:** When orchestrator has available agents

**Request:**
```protobuf
GetPendingTasksRequest {
  role: "architect"
  limit: 10
}
```

**Response:**
```protobuf
PendingTasksResponse {
  tasks: [
    {
      task_id: "task-001",
      story_id: "story-123",
      current_state: "pending_arch_review",
      required_action: "APPROVE_DESIGN",
      work: {
        commit_sha: "abc123",
        files_changed: ["src/auth.py"],
        implementation_summary: "JWT auth"
      },
      waiting_since: 1730830000,
      priority: 8
    }
  ],
  total_count: 3
}
```

**Use Case:** Orchestrator queries for work when architect agent becomes available

---

### 4. Planning Service → Workflow Service (NATS Event)

**Subject:** `planning.story.transitioned`
**Pattern:** Event-driven (asynchronous)
**Frequency:** When story changes state

**Payload:**
```json
{
  "story_id": "story-123",
  "from_state": "PLANNED",
  "to_state": "READY_FOR_EXECUTION",
  "tasks": ["task-001", "task-002", "task-003"],
  "timestamp": "2025-11-05T19:00:00Z"
}
```

**Consumer:** `PlanningEventsConsumer` (PULL subscription)
**Processing:**
1. Create workflow state for each task (initial state: "todo")
2. Assign first task to developer
3. Publish `workflow.task.assigned`

---

## 📤 Outbound Interactions

### 1. Workflow Service → Orchestrator (NATS Event)

**Subject:** `workflow.task.assigned`
**Pattern:** Event-driven (asynchronous)
**Frequency:** After each state transition requiring new role

**Payload:**
```json
{
  "task_id": "task-001",
  "story_id": "story-123",
  "assigned_to_role": "architect",
  "required_action": "APPROVE_DESIGN",
  "work_to_validate": {
    "commit_sha": "abc123",
    "files_changed": ["src/auth.py"],
    "implementation_summary": "Implemented JWT auth",
    "context_preview": "Added JWT token generation..."
  },
  "previous_feedback": null,
  "timestamp": "2025-11-05T19:05:00Z"
}
```

**Consumer:** Orchestrator (listens for task assignments)
**Orchestrator Action:**
1. See architect is needed
2. Call `Context.GetContext(task_id, role=architect, workflow_state=pending_arch_review)`
3. Create VLLMAgent(role=architect)
4. Execute review task

---

### 2. Workflow Service → Context Service (NATS Event)

**Subject:** `workflow.state.changed`
**Pattern:** Event-driven (asynchronous)
**Frequency:** After every state transition

**Payload:**
```json
{
  "task_id": "task-001",
  "story_id": "story-123",
  "from_state": "implementing",
  "to_state": "pending_arch_review",
  "triggered_by_action": "COMMIT_CODE",
  "actor_role": "developer",
  "actor_agent_id": "agent-dev-001",
  "timestamp": "2025-11-05T19:05:00Z"
}
```

**Consumer:** Context Service (enriches graph)
**Context Action:**
1. Update Neo4j: Add WorkflowTransition node
2. Create relationship: Task → TRANSITIONED_TO → WorkflowState
3. Cache workflow state for fast retrieval

---

### 3. Workflow Service → Neo4j (Write)

**Pattern:** Direct database write
**Frequency:** Every state transition

**Cypher:**
```cypher
// Create workflow state node
MERGE (ws:WorkflowState {task_id: $task_id})
SET ws.current_state = $current_state,
    ws.role_in_charge = $role_in_charge,
    ws.required_action = $required_action,
    ws.updated_at = $timestamp,
    ws.retry_count = $retry_count

// Link to task
MATCH (t:Task {task_id: $task_id})
MERGE (t)-[:HAS_WORKFLOW]->(ws)

// Create transition audit trail
CREATE (st:StateTransition {
  from_state: $from_state,
  to_state: $to_state,
  action: $action,
  actor_role: $actor_role,
  timestamp: $timestamp,
  feedback: $feedback
})
MERGE (ws)-[:TRANSITIONED_VIA]->(st)
```

---

### 4. Workflow Service → Valkey (Read/Write)

**Pattern:** Cache layer
**Frequency:** Every read/write

**Keys:**
```python
# Current state (fast lookup)
f"workflow:task:{task_id}:state"
→ {"current_state": "pending_arch_review", "role": "architect", ...}

# Pending tasks by role (assignment queue)
f"workflow:pending:architect"
→ SET {"task-001", "task-005", "task-012"}

# Task claim lock (prevent duplicate work)
f"workflow:claim:{task_id}"
→ {"agent_id": "agent-arch-001", "claimed_at": 1730833200}
```

**TTL:**
- State: 1 hour (refreshed on each update)
- Pending sets: No TTL (persistent queue)
- Claim locks: 30 minutes (auto-release if agent crashes)

---

## 🔄 Complete Flow Example: Happy Path

```
Step 1: Developer Implements
  ┌─────────────────────────────────────────────────────────┐
  │ VLLMAgent (role=developer)                              │
  │   - Executes task: "Implement JWT auth"                │
  │   - Commits code                                        │
  │   - Publishes:                                          │
  │     NATS: agent.work.completed {                        │
  │       role: "developer",                                │
  │       action_performed: "COMMIT_CODE",                  │
  │       artifacts: {commit_sha: "abc123"}                 │
  │     }                                                    │
  └─────────────────────────────────────────────────────────┘
                           ↓
Step 2: Workflow Service Processes Event
  ┌─────────────────────────────────────────────────────────┐
  │ Workflow Service                                        │
  │   Consumer: agent.work.completed                        │
  │   1. Load state: "implementing"                         │
  │   2. Validate: developer.can_perform(COMMIT_CODE) ✅    │
  │   3. Check guard: commit_sha exists ✅                  │
  │   4. Transition: implementing → dev_completed           │
  │   5. Auto-transition: dev_completed → pending_arch_review│
  │   6. Store in Neo4j + Valkey                            │
  │   7. Publish: workflow.task.assigned {                  │
  │        assigned_to_role: "architect",                   │
  │        required_action: "APPROVE_DESIGN"                │
  │     }                                                    │
  └─────────────────────────────────────────────────────────┘
                           ↓
Step 3: Orchestrator Sees Assignment
  ┌─────────────────────────────────────────────────────────┐
  │ Orchestrator                                            │
  │   Consumer: workflow.task.assigned                      │
  │   1. Sees: role=architect, action=APPROVE_DESIGN        │
  │   2. gRPC: workflow.GetWorkflowState(task-001)          │
  │      → current_state: "pending_arch_review"             │
  │      → feedback: null                                   │
  │   3. gRPC: context.GetContext(task-001, role=architect) │
  │      → Returns architect-scoped context (8-12K tokens)  │
  │   4. Create VLLMAgent(role=architect, tools=read-only)  │
  │   5. Execute review task                                │
  └─────────────────────────────────────────────────────────┘
                           ↓
Step 4: Architect Reviews
  ┌─────────────────────────────────────────────────────────┐
  │ VLLMAgent (role=architect)                              │
  │   - Reviews code in commit abc123                       │
  │   - Validates architectural consistency                 │
  │   - Approves design                                     │
  │   - Publishes:                                          │
  │     NATS: agent.work.completed {                        │
  │       role: "architect",                                │
  │       action_performed: "APPROVE_DESIGN",               │
  │       feedback: "LGTM - good implementation"            │
  │     }                                                    │
  └─────────────────────────────────────────────────────────┘
                           ↓
Step 5: Workflow Routes to QA
  ┌─────────────────────────────────────────────────────────┐
  │ Workflow Service                                        │
  │   1. Validate: architect.can_perform(APPROVE_DESIGN) ✅ │
  │   2. Transition: arch_reviewing → arch_approved         │
  │   3. Auto-transition: arch_approved → pending_qa        │
  │   4. Publish: workflow.task.assigned {                  │
  │        assigned_to_role: "qa",                          │
  │        required_action: "RUN_TESTS"                     │
  │     }                                                    │
  └─────────────────────────────────────────────────────────┘

... (QA → PO → DONE continues same pattern)
```

---

## 🔄 Complete Flow Example: Rejection Path

```
Step 1-3: Same as happy path (Dev implements, routes to Architect)

Step 4: Architect Rejects
  ┌─────────────────────────────────────────────────────────┐
  │ VLLMAgent (role=architect)                              │
  │   - Reviews code                                        │
  │   - Finds security issue                                │
  │   - Rejects design                                      │
  │   - Publishes:                                          │
  │     NATS: agent.work.completed {                        │
  │       role: "architect",                                │
  │       action_performed: "REJECT_DESIGN",                │
  │       feedback: "Security issue: passwords in plaintext"│
  │     }                                                    │
  └─────────────────────────────────────────────────────────┘
                           ↓
Step 5: Workflow Routes Back to Developer
  ┌─────────────────────────────────────────────────────────┐
  │ Workflow Service                                        │
  │   1. Validate: architect.can_perform(REJECT_DESIGN) ✅  │
  │   2. Check guard: feedback provided ✅                  │
  │   3. Transition: arch_reviewing → arch_rejected         │
  │   4. Store feedback in state                            │
  │   5. Transition: arch_rejected → implementing           │
  │   6. Publish: workflow.task.assigned {                  │
  │        assigned_to_role: "developer",                   │
  │        required_action: "REVISE_CODE",                  │
  │        feedback: "Security: passwords in plaintext"     │
  │     }                                                    │
  └─────────────────────────────────────────────────────────┘
                           ↓
Step 6: Developer Receives Feedback
  ┌─────────────────────────────────────────────────────────┐
  │ Orchestrator                                            │
  │   Consumer: workflow.task.assigned                      │
  │   1. gRPC: context.GetContext(task-001, role=developer) │
  │      Context now includes:                              │
  │      - workflow_state: "implementing"                   │
  │      - previous_feedback: "Security: passwords..."      │
  │   2. Create VLLMAgent(role=developer)                   │
  │   3. LLM prompt includes feedback                       │
  │   4. Developer revises code                             │
  └─────────────────────────────────────────────────────────┘

... (Loop: Dev commits → Architect re-reviews)
```

---

## 🔌 Dependencies

### Services Called BY Workflow Service

| Service | Interaction | Purpose |
|---------|-------------|---------|
| **Neo4j** | Cypher queries | Persist workflow state + transitions |
| **Valkey** | GET/SET/SADD | Cache state, pending queues, claim locks |
| **NATS** | Publish events | Notify other services of state changes |

### Services that CALL Workflow Service

| Service | Interaction | Purpose |
|---------|-------------|---------|
| **Orchestrator** | gRPC: GetWorkflowState | Determine which role to assign |
| **Orchestrator** | gRPC: GetPendingTasks | Find work for available agents |
| **VLLMAgent** | NATS: agent.work.completed | Report work completion |
| **Planning Service** | NATS: planning.story.transitioned | Initialize task workflows |

---

## 📡 NATS Events

### Consumes (PULL Subscriptions)

| Subject | Stream | Durable | Purpose |
|---------|--------|---------|---------|
| `agent.work.completed` | AGENT_RESPONSES | `workflow-agent-work` | Process agent completions |
| `planning.story.transitioned` | PLANNING_EVENTS | `workflow-planning` | Initialize task workflows |

### Publishes

| Subject | Consumers | Purpose |
|---------|-----------|---------|
| `workflow.state.changed` | Context, Monitoring | State transition notifications |
| `workflow.task.assigned` | Orchestrator | Route task to next role |
| `workflow.task.completed` | Planning | All tasks in story done |
| `workflow.rbac.violation` | Monitoring, Security | RBAC validation failures |

---

## 🗄️ Data Storage

### Neo4j Schema

```cypher
// Workflow State node
(:WorkflowState {
  task_id: string,
  current_state: string,
  role_in_charge: string,
  required_action: string,
  updated_at: int64,
  retry_count: int32
})

// State Transition node (audit trail)
(:StateTransition {
  from_state: string,
  to_state: string,
  action: string,
  actor_role: string,
  timestamp: int64,
  feedback: string
})

// Relationships
(:Task)-[:HAS_WORKFLOW]->(:WorkflowState)
(:WorkflowState)-[:TRANSITIONED_VIA]->(:StateTransition)
(:Agent)-[:PERFORMED {action: string, timestamp: int64}]->(:StateTransition)
```

### Valkey Schema

```
workflow:task:{task_id}:state
  → Hash with current state fields (TTL: 1h)

workflow:pending:{role}
  → Set of task_ids waiting for this role (no TTL)

workflow:claim:{task_id}
  → Hash with agent_id and claimed_at (TTL: 30min)

workflow:stats:{story_id}
  → Hash with aggregated metrics (TTL: 10min)
```

---

## 🔒 Security & RBAC

### RBAC Validation

**Before every transition:**
```python
# 1. Load Role entity
role = RoleFactory.create_role_by_name(event.role)

# 2. Create Action entity
action = Action(value=ActionEnum(event.action_performed))

# 3. Validate (RBAC Level 1 check)
if not role.can_perform(action):
    logger.error(f"RBAC Violation: {role.value} cannot {action.value}")
    publish_rbac_violation(task_id, role, action)
    return  # Reject event

# 4. Validate state allows this action (FSM check)
if not fsm.can_transition(current_state, action, role):
    logger.error(f"Invalid transition: {current_state} + {action}")
    return  # Reject event

# 5. Execute transition ✅
```

### Audit Trail

**Every action logged:**
- Who (agent_id, role)
- What (action, result)
- When (timestamp)
- Why (feedback if rejecting)
- Outcome (new state)

**Stored in:**
- Neo4j: Full audit trail (StateTransition nodes)
- NATS events: Real-time audit stream
- Logs: Structured JSON logs

---

## ⚡ Performance Characteristics

### Expected Latencies

| Operation | Target | Max |
|-----------|--------|-----|
| GetWorkflowState (cache hit) | < 5ms | 20ms |
| GetWorkflowState (cache miss) | < 50ms | 100ms |
| RequestValidation (RPC) | < 10ms | 30ms |
| Event processing | < 100ms | 500ms |
| GetPendingTasks | < 20ms | 50ms |

### Throughput

- **Events processed:** 100-500 events/sec
- **gRPC calls:** 1000-2000 req/sec
- **State transitions:** 50-200 transitions/sec

### Scalability

- **Horizontal:** 2-4 replicas (stateless, event-driven)
- **State storage:** Neo4j + Valkey (can scale independently)
- **Event processing:** NATS queue groups (load balancing)

---

## 📊 Monitoring & Observability

### Metrics (Prometheus)

```
workflow_tasks_total{state="pending_arch_review"}
workflow_transitions_total{action="APPROVE_DESIGN"}
workflow_rbac_violations_total{role="developer",action="APPROVE_DESIGN"}
workflow_state_duration_seconds{state="pending_arch_review"}
workflow_rejection_rate{role="architect"}
```

### Logs (Structured JSON)

```json
{
  "level": "INFO",
  "msg": "Workflow transition executed",
  "task_id": "task-001",
  "from_state": "implementing",
  "to_state": "pending_arch_review",
  "action": "COMMIT_CODE",
  "actor_role": "developer",
  "timestamp": "2025-11-05T19:05:00Z"
}
```

### Traces (OpenTelemetry)

- Span: `workflow.process_event`
- Span: `workflow.execute_transition`
- Span: `workflow.persist_state`

---

## 🚀 Deployment

**Service Type:** ClusterIP (internal only)
**Replicas:** 2
**Port:** 50056 (gRPC)
**Resources:**
- CPU: 500m request, 1000m limit
- Memory: 512Mi request, 1Gi limit

**Environment Variables:**
- `NATS_URL`: `nats://nats.swe-ai-fleet.svc.cluster.local:4222`
- `NEO4J_URI`: `bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687`
- `VALKEY_URL`: `valkey://valkey.swe-ai-fleet.svc.cluster.local:6379`
- `FSM_CONFIG`: `/app/config/workflow.fsm.yaml`
- `GRPC_PORT`: `50056`

---

## 📋 Service Health

### Readiness Probe

```python
# Check:
✅ NATS connected
✅ Neo4j connected
✅ Valkey connected
✅ FSM config loaded
✅ gRPC server listening
```

### Liveness Probe

```python
# Check:
✅ Event consumers running
✅ No deadlocks
✅ Valkey responsive
```

---

**Created:** 2025-11-05
**Author:** Tirso García Ibáñez
**Status:** Design Complete - Ready for Implementation
**Next Step:** Implement domain layer

