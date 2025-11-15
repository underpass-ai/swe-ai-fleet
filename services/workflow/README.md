# Workflow Service - Complete Documentation

**Version**: v1.0.0  
**Status**: ✅ Production Ready  
**Pattern**: DDD + Hexagonal Architecture (Ports & Adapters)  
**RBAC Level**: Level 2 - Workflow Action Control  
**Language**: Python 3.13  
**Last Updated**: November 15, 2025

---

## 📋 Executive Summary

**Workflow Service** is the multi-role task execution coordinator of the SWE AI Fleet platform. It manages the complete FSM (Finite State Machine) lifecycle of tasks as they move through different agent roles (Developer → Architect → QA → Product Owner). It validates RBAC permissions, enforces workflow rules, transitions task states, and routes work between roles using a sophisticated state machine with 12 states and role-based authorization.

**Core Purpose:**
- 🔄 Manage task execution FSM (12 states: TODO → DESIGN → CODE → REVIEW → TEST → APPROVED → DONE)
- 🔐 Validate RBAC permissions (APPROVE_DESIGN, REJECT_DESIGN, APPROVE_CODE, etc.)
- 🎯 Route tasks between roles (Developer → Architect → QA → Product Owner)
- 📊 Track task state transitions and history
- 🛡️ Maintain immutability and fail-fast validation
- 📡 Coordinate with Orchestrator, Planning, and agent execution services

---

## 📚 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Responsibility Matrix](#responsibility-matrix)
3. [Architecture Overview](#architecture-overview)
4. [Domain Model](#domain-model)
5. [Task FSM (Finite State Machine)](#task-fsm-finite-state-machine)
6. [RBAC Validation](#rbac-validation)
7. [Workflow State Transitions](#workflow-state-transitions)
8. [API Reference](#api-reference)
9. [Event Integration](#event-integration)
10. [External Dependencies](#external-dependencies)
11. [Request Flow](#request-flow)
12. [Architectural Principles](#architectural-principles)
13. [Testing & Coverage](#testing--coverage)
14. [Getting Started](#getting-started)
15. [Monitoring & Observability](#monitoring--observability)
16. [Troubleshooting](#troubleshooting)

---

## 🎯 Responsibility Matrix

### What This Service DOES ✅

| Responsibility | Mechanism |
|---|---|
| **Manage task FSM** | 12 states with transition rules |
| **Validate RBAC** | Check role permissions before transitions |
| **Initialize workflows** | Create task states when Planning publishes events |
| **Execute transitions** | Agent actions trigger FSM state changes |
| **Route tasks** | Assign to next role based on workflow rules |
| **Track history** | Persist state transitions in Neo4j |
| **Cache state** | Fast lookups via Valkey |
| **Publish events** | Notify Orchestrator of state changes |
| **Query workflow state** | gRPC endpoint for status checks |
| **List pending tasks** | Get tasks awaiting specific role's action |

### What This Service DOES NOT ✅

| Non-Responsibility | Owner |
|---|---|
| ❌ Execute agent tasks | Orchestrator Service |
| ❌ Generate tasks from stories | Task Derivation Service |
| ❌ Store code/artifacts | Git/Workspace Service |
| ❌ Provide context for agents | Context Service |
| ❌ Manage story lifecycle | Planning Service |
| ❌ Authenticate users | API Gateway |

---

## 🏗️ Architecture Overview

### Layered Design (DDD + Hexagonal)

```
┌──────────────────────────────────────────────────────┐
│                   Domain Layer                        │
│  • WorkflowStateMachine (FSM with 12 states)          │
│  • WorkflowTransitionRules (RBAC + business rules)    │
│  • Value Objects (TaskState, Action, Role)            │
│  • Pure workflow logic, zero infrastructure           │
└──────────────────────────────────────────────────────┘
         ↓                                    ↑
┌──────────────────────────────────────────────────────┐
│                Application Layer                      │
│  • ExecuteWorkflowActionUseCase (transition logic)    │
│  • GetWorkflowStateUseCase (status queries)           │
│  • InitializeTaskWorkflowUseCase (task creation)      │
│  • GetPendingTasksUseCase (role-based filtering)      │
│  • Ports for storage, messaging, config               │
└──────────────────────────────────────────────────────┘
         ↓                                    ↑
┌──────────────────────────────────────────────────────┐
│              Infrastructure Layer                     │
│  • Neo4jWorkflowAdapter (persist state)               │
│  • ValkeyWorkflowCacheAdapter (cache state)           │
│  • NatsMessagingAdapter (event publishing)            │
│  • 2 NATS consumers (agent work, planning events)     │
│  • gRPC servicer + dependency injection               │
└──────────────────────────────────────────────────────┘
```

### Directory Structure

```
services/workflow/
├── workflow/
│   ├── domain/
│   │   ├── entities/                     # Workflow domain entities
│   │   │   ├── task_workflow.py          # Main workflow entity
│   │   │   ├── task_action.py            # Action (APPROVE, REJECT, etc.)
│   │   │   └── role.py                   # Role enum (DEV, ARCHITECT, QA, PO)
│   │   ├── value_objects/
│   │   │   ├── task_state.py             # Immutable task state VO
│   │   │   ├── workflow_history.py       # Transition history VO
│   │   │   └── action_result.py          # Action result VO
│   │   ├── services/
│   │   │   ├── workflow_state_machine.py # FSM implementation (12 states)
│   │   │   └── workflow_transition_rules.py # RBAC + business rules
│   │   └── ports/
│   │       ├── workflow_storage_port.py  # Persistence interface
│   │       └── messaging_port.py         # Event publishing interface
│   │
│   ├── application/                      # Use Cases & Orchestration
│   │   └── usecases/
│   │       ├── execute_workflow_action_usecase.py     # Transition logic
│   │       ├── get_workflow_state_usecase.py          # Query state
│   │       ├── initialize_task_workflow_usecase.py    # Init workflow
│   │       └── get_pending_tasks_usecase.py           # List by role
│   │
│   ├── infrastructure/                   # External Integrations
│   │   ├── adapters/
│   │   │   ├── neo4j_workflow_adapter.py        # Neo4j persistence
│   │   │   ├── valkey_workflow_cache_adapter.py # Valkey caching
│   │   │   ├── nats_messaging_adapter.py        # NATS event publishing
│   │   │   └── environment_configuration_adapter.py
│   │   │
│   │   ├── consumers/
│   │   │   ├── agent_work_completed_consumer.py # Listen: agent.work.completed
│   │   │   └── planning_events_consumer.py      # Listen: planning.task.created
│   │   │
│   │   ├── mappers/
│   │   │   ├── workflow_state_mapper.py         # VO ↔ protobuf
│   │   │   └── action_mapper.py                 # Action ↔ protobuf
│   │   │
│   │   ├── dto/
│   │   │   └── server_configuration_dto.py      # Server config DTO
│   │   │
│   │   └── grpc_servicer.py               # gRPC handler
│   │
│   ├── gen/                               # Generated gRPC (not in git)
│   ├── server.py                          # Server entrypoint + DI
│   └── __init__.py
│
├── tests/
│   ├── unit/                              # 50+ unit tests, >90% coverage
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── integration/
│   └── e2e/
│
├── INTERACTIONS.md                        # Service interactions (reference)
├── Dockerfile                             # Multi-stage build (Python 3.13)
├── requirements.txt                       # Dependencies
├── README.md                              # THIS FILE
└── .gitignore
```

---

## 🧩 Domain Model

### Entities (All Immutable)

#### TaskWorkflow

```python
@dataclass(frozen=True)
class TaskWorkflow:
    task_id: str                        # Unique task identifier
    current_state: TaskState            # Current FSM state
    current_role: Role                  # Current assigned role
    history: Tuple[WorkflowTransition, ...] # State transitions
    created_at: datetime
    updated_at: datetime
```

**Domain Invariants**:
- ✅ task_id cannot be empty
- ✅ current_state must be valid (one of 12 states)
- ✅ current_role must match state requirements
- ✅ history is immutable (append-only)
- ✅ All frozen (immutable)

#### TaskAction

```python
@dataclass(frozen=True)
class TaskAction:
    task_id: str                        # Task to act upon
    action: str                         # Action type (APPROVE_DESIGN, REJECT_CODE, etc.)
    agent_id: str                       # Agent performing action
    role: Role                          # Agent's role
    result: dict                        # Result data (artifacts, reasoning, etc.)
    timestamp: datetime
```

### Value Objects

#### TaskState

```python
@dataclass(frozen=True)
class TaskState:
    value: str                          # State name (TODO, DESIGN, CODE, etc.)
    timestamp: datetime                 # When state was entered

    def __post_init__(self) -> None:
        """Validate state is one of 12 valid states."""
        valid_states = {
            "TODO", "DESIGN", "CODE_REVIEW", "TESTING",
            "QA_REVIEW", "APPROVED", "REJECTED", 
            "BLOCKED", "IN_PROGRESS", "COMPLETED",
            "ABANDONED", "ARCHIVED"
        }
        if self.value not in valid_states:
            raise ValueError(f"Invalid state: {self.value}")
```

#### WorkflowTransition

```python
@dataclass(frozen=True)
class WorkflowTransition:
    from_state: str                     # Previous state
    to_state: str                       # New state
    triggered_by: str                   # Agent ID or system
    action: str                         # Action performed
    timestamp: datetime
    metadata: dict                      # Additional transition data
```

---

## 🔄 Task FSM (Finite State Machine)

### 12 States and Transitions

```
                           ┌─────────────┐
                           │    TODO     │  ← Initial state
                           └──────┬──────┘
                                  │ (create task)
                           ┌──────▼──────┐
                           │   DESIGN    │  ← Developer phase
                           └──────┬──────┘
                    ┌─────────────┼─────────────┐
                    │ (approve)   │ (reject)    │
                    ▼             ▼             │
           ┌────────────┐    ┌──────────┐      │
           │   CODE     │    │ REJECTED │←─────┘
           │  _REVIEW   │    └────┬─────┘
           └────┬───────┘         │ (rework)
                │                  │
                └──────────┬───────┘
                           │
                    ┌──────▼──────┐
                    │    CODE     │  ← Developer implementation
                    │ (Arch view) │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  QA_REVIEW  │  ← QA testing phase
                    └──────┬──────┘
                    ┌──────┴──────┐
                    │ (approve)   │
                    ▼             ▼
           ┌─────────────┐   ┌──────────┐
           │  APPROVED   │   │ REJECTED │
           │ (PO sign-off)   │          │
           └──────┬──────┘   └────┬─────┘
                  │               │ (rework)
                  │               │
                  └───────┬───────┘
                          │
                   ┌──────▼──────┐
                   │ COMPLETED   │  ← Final state
                   └─────────────┘

Alternative paths:
- ANY state → BLOCKED (if blocked by dependency)
- ANY state → ABANDONED (if deprioritized)
- ANY state → ARCHIVED (after retention period)
```

### 12 Valid States

| State | Purpose | Triggered By | Next States |
|-------|---------|--------------|-------------|
| **TODO** | Initial creation | System | DESIGN |
| **DESIGN** | Design phase (Dev + Arch) | AgentWorkCompleted | CODE_REVIEW, REJECTED |
| **CODE_REVIEW** | Architect reviews design | AgentWorkCompleted | CODE, REJECTED |
| **CODE** | Development implementation | AgentWorkCompleted | QA_REVIEW, REJECTED |
| **QA_REVIEW** | QA testing phase | AgentWorkCompleted | TESTING, REJECTED |
| **TESTING** | Automated + manual testing | AgentWorkCompleted | APPROVED, REJECTED |
| **APPROVED** | PO approval | AgentWorkCompleted | COMPLETED |
| **REJECTED** | Rejection by reviewer | AgentWorkCompleted | DESIGN (rework) |
| **BLOCKED** | Waiting for dependency | System | (any non-terminal) |
| **IN_PROGRESS** | Currently being worked on | AgentWorkCompleted | (depends on role) |
| **COMPLETED** | Task finished | System | ARCHIVED |
| **ABANDONED** | Deprioritized task | System | ARCHIVED |
| **ARCHIVED** | Terminal state | System | (none) |

---

## 🔐 RBAC Validation

### Allowed Actions by Role

| Role | States Can Enter | Actions Can Perform | Next Role |
|------|------------------|-------------------|-----------|
| **DEV** (Developer) | DESIGN, CODE | APPROVE_DESIGN, REJECT_DESIGN, COMMIT_CODE | ARCHITECT (after design), QA (after code) |
| **ARCHITECT** | CODE_REVIEW | APPROVE_CODE, REQUEST_CHANGES | DEV (if changes), QA (if approved) |
| **QA** | QA_REVIEW, TESTING | APPROVE_TESTING, REQUEST_CHANGES, LOG_BUG | PO (if approved), DEV (if changes) |
| **PO** (Product Owner) | APPROVED | APPROVE_FINAL, REJECT_FINAL | COMPLETED (if approved), DEV (if rejected) |

### Permission Matrix

```
STATE          | DEV | ARCH | QA  | PO  | SYSTEM
───────────────┼─────┼──────┼─────┼─────┼────────
TODO           | -   | -    | -   | -   | ✅ (create)
DESIGN         | ✅  | -    | -   | -   | -
CODE_REVIEW    | -   | ✅   | -   | -   | -
CODE           | ✅  | -    | -   | -   | -
QA_REVIEW      | -   | -    | ✅  | -   | -
TESTING        | -   | -    | ✅  | -   | -
APPROVED       | -   | -    | -   | ✅  | -
REJECTED       | ✅  | ✅   | ✅  | ✅  | - (rework)
COMPLETED      | -   | -    | -   | -   | ✅ (archive)
BLOCKED        | -   | -    | -   | -   | ✅ (system)
ABANDONED      | -   | -    | -   | -   | ✅ (system)
ARCHIVED       | -   | -    | -   | -   | - (terminal)
```

---

## 🔄 Workflow State Transitions

### Complete Transition Sequence

```
1. Planning publishes planning.story.transitioned
   {story_id, from_state, to_state, tasks: [task-001, task-002, ...]}
   ↓
2. PlanningEventsConsumer receives event (PULL subscription)
   ├─ For each task_id in tasks list:
   │  ├─ Create workflow state in Neo4j
   │  └─ Initialize Valkey cache
   ├─ Set initial state: "TODO"
   ├─ Assign first role: "developer"
   └─ Publish workflow.task.assigned events
   ↓
3. Orchestrator receives workflow.task.assigned event (consumer)
   ├─ Extract: task_id, assigned_to_role, required_action
   ├─ Call gRPC GetWorkflowState(task_id) → workflow.task.assigned()
   │  Returns: current_state, role_in_charge, required_action, feedback
   ├─ Call gRPC context.GetContext(task_id, role=developer)
   │  → Returns ~200 tokens of context for agent
   └─ Create VLLMAgent(role=developer)
   ↓
4. Developer Agent executes task
   ├─ Receives: context, required_action (e.g., COMMIT_CODE)
   ├─ Executes work (implementation)
   ├─ Publishes: agent.work.completed event with:
   │  {task_id, agent_id, role, action_performed, result, artifacts}
   ↓
5. AgentWorkCompletedConsumer receives event (PULL subscription)
   ├─ Extract action_performed (e.g., COMMIT_CODE)
   ├─ Load current_state from Valkey cache
   ├─ Call ExecuteWorkflowActionUseCase(task_id, action, role)
   ↓
6. ExecuteWorkflowActionUseCase.execute()
   ├─ Validate RBAC: role.can_perform(action)
   │  └─ developer.can_perform(COMMIT_CODE) ✅
   ├─ Check FSM guards (e.g., commit_sha exists in result)
   ├─ Auto-transition workflow: implementing → dev_completed → pending_arch_review
   ├─ Store state in Neo4j + Valkey
   ├─ Store audit trail in Neo4j (StateTransition node)
   └─ Publish workflow.task.assigned (for architect)
   ↓
7. Orchestrator receives workflow.task.assigned event (consumer)
   ├─ Extract: task_id, assigned_to_role="architect"
   ├─ Call gRPC GetWorkflowState(task_id)
   │  Returns: state="pending_arch_review", role="architect"
   ├─ Call gRPC context.GetContext(task_id, role=architect)
   │  Context includes workflow_state + previous_feedback
   └─ Create VLLMAgent(role=architect, tools=read-only)
   ↓
8. Architect Agent reviews and provides feedback
   ├─ If APPROVE_DESIGN:
   │  └─ Transition: arch_reviewing → arch_approved → (QA next)
   │
   ├─ If REJECT_DESIGN:
   │  ├─ Store feedback in WorkflowState
   │  └─ Transition: arch_reviewing → arch_rejected → implementing (back to DEV)
   │
   └─ Publish agent.work.completed with result + feedback
   ↓
9. AgentWorkCompletedConsumer processes architect's action
   ├─ Validate: architect.can_perform(APPROVE_DESIGN or REJECT_DESIGN)
   ├─ Execute transition with feedback
   ├─ If rejected: route back to developer with feedback
   ├─ If approved: route to QA
   └─ Publish workflow.task.assigned (for next role)
   ↓
10. Flow continues: Developer (rework if rejected) → Architect → QA → PO
    Each role works on task, completes, gets routed to next role
    ↓
11. After all reviews complete and approved:
    ├─ Final state: COMPLETED
    ├─ Publish workflow.task.completed event
    └─ Planning Service marks story as DONE
```

### Key Architectural Details from INTERACTIONS.md

**Inbound Events:**
- `planning.story.transitioned` (PULL subscription on PLANNING_EVENTS stream)
- `agent.work.completed` (PULL subscription on AGENT_RESPONSES stream)

**Outbound Events:**
- `workflow.task.assigned` → Orchestrator (gRPC GetWorkflowState validates)
- `workflow.state.changed` → Context Service (enriches graph)
- `workflow.task.completed` → Planning Service (marks story done)
- `workflow.rbac.violation` → Monitoring (security audit)

**Valkey Cache Keys:**
- `workflow:task:{task_id}:state` (Hash, TTL 1h)
- `workflow:pending:{role}` (Set, no TTL, assignment queue)
- `workflow:claim:{task_id}` (Hash, TTL 30min, prevent duplicate work)

**Rejection/Rework Loop:**
- Architect rejects → stores feedback in WorkflowState
- Workflow auto-transitions back to developer state
- Developer gets feedback in next context retrieval
- Loop continues until approved

---

## 📡 API Reference

### gRPC Services

**Port**: 50056 (internal-workflow:50056)  
**Proto Spec**: See `specs/fleet/workflow/v1/workflow.proto`

#### ExecuteWorkflowAction

```protobuf
rpc ExecuteWorkflowAction(ExecuteWorkflowActionRequest)
  returns (ExecuteWorkflowActionResponse)

message ExecuteWorkflowActionRequest {
  string task_id = 1;
  string action = 2;                    # APPROVE_DESIGN, REJECT_CODE, etc.
  string agent_id = 3;
  string role = 4;
  google.protobuf.Struct result = 5;   # Result data
}

message ExecuteWorkflowActionResponse {
  string task_id = 1;
  string previous_state = 2;
  string current_state = 3;
  string next_role = 4;                # Role to execute next step
  bool transition_allowed = 5;
  string message = 6;
}
```

#### GetWorkflowState

```protobuf
rpc GetWorkflowState(GetWorkflowStateRequest)
  returns (GetWorkflowStateResponse)

message GetWorkflowStateRequest {
  string task_id = 1;
}

message GetWorkflowStateResponse {
  string task_id = 1;
  string current_state = 2;
  string current_role = 3;
  repeated WorkflowTransition history = 4;
  int64 created_at = 5;
  int64 updated_at = 6;
  bool cached = 7;
}
```

#### GetPendingTasks

```protobuf
rpc GetPendingTasks(GetPendingTasksRequest)
  returns (GetPendingTasksResponse)

message GetPendingTasksRequest {
  string role = 1;                      # Filter by role
  string state = 2;                     # Optional: filter by state
}

message GetPendingTasksResponse {
  repeated TaskWorkflowSummary tasks = 1;
  int32 total_count = 2;
}
```

#### InitializeTaskWorkflow

```protobuf
rpc InitializeTaskWorkflow(InitializeTaskWorkflowRequest)
  returns (InitializeTaskWorkflowResponse)

message InitializeTaskWorkflowRequest {
  string task_id = 1;
  string story_id = 2;
}

message InitializeTaskWorkflowResponse {
  string task_id = 1;
  string initial_state = 2;             # Always "TODO"
  string assigned_role = 3;             # DEV
  int64 initialized_at = 4;
}
```

---

## 📡 Event Integration

### NATS Event Consumers

| Consumer | Topic | Purpose |
|----------|-------|---------|
| **PlanningEventsConsumer** | `planning.task.created` | Initialize workflow for new task |
| **AgentWorkCompletedConsumer** | `agent.work.completed` | Execute FSM transition on completion |

### Published Events

| Event | Topic | Purpose | Consumers |
|-------|-------|---------|-----------|
| **workflow.initialized** | `workflow.initialized` | Task workflow created | Monitoring |
| **workflow.transitioned** | `workflow.transitioned` | State changed | Orchestrator |
| **workflow.blocked** | `workflow.blocked` | Task blocked by dependency | Monitoring |
| **workflow.abandoned** | `workflow.abandoned` | Task deprioritized | Planning |

---

## 🔌 External Dependencies

### Neo4j Graph Database
- **Address**: bolt://neo4j:7687
- **Purpose**: Persist workflow state and history
- **Adapter**: `Neo4jWorkflowAdapter`

### Valkey Cache
- **Address**: redis://valkey:6379
- **Purpose**: Fast state lookups (1-hour TTL)
- **Adapter**: `ValkeyWorkflowCacheAdapter`

### NATS JetStream
- **Address**: nats://nats:4222
- **Purpose**: Event consumption and publishing
- **Consumers**: 2 (planning events, agent work)

### Orchestrator Service
- **Interaction**: gRPC `GetWorkflowState()` queries
- **Purpose**: Validate state before agent assignment

### Planning Service
- **Interaction**: NATS event consumer
- **Purpose**: Initialize workflows for new tasks

---

## 🛡️ Architectural Principles

### 1. **Immutability & Fail-Fast**
- All domain entities frozen
- Validation in `__post_init__`
- No silent defaults

### 2. **No Reflection**
- ❌ NO `getattr()`, `setattr()`, `__dict__`
- ✅ Direct attribute access
- ✅ Explicit enum values

### 3. **Separation of Concerns**
- **Domain**: FSM logic + RBAC rules
- **Application**: Use case orchestration
- **Infrastructure**: Neo4j, Valkey, NATS, gRPC

### 4. **Single Responsibility**
- Each use case has one responsibility
- FSM encapsulates state logic
- Transition rules encapsulate RBAC

### 5. **State as First-Class**
- TaskState is immutable VO
- WorkflowTransition is immutable VO
- History is append-only

---

## 🧪 Testing & Coverage

### Test Organization

```
tests/
├── unit/
│   ├── test_workflow_state_machine.py  # FSM logic (20+ tests)
│   ├── test_workflow_transition_rules.py # RBAC validation (15+ tests)
│   ├── test_execute_workflow_action_usecase.py # Transitions (10+ tests)
│   └── test_domain_value_objects.py    # VO validation (10+ tests)
├── integration/
│   ├── test_neo4j_adapter.py
│   └── test_nats_consumers.py
└── e2e/
    └── test_workflow_complete_cycle.py
```

### Running Tests

```bash
make test-unit      # 50+ tests, <3 seconds
make test-integration
make test-e2e
make coverage-report
```

### Coverage Targets

| Layer | Target | Current | Status |
|-------|--------|---------|--------|
| **Domain** | 100% | 100% | ✅ |
| **Application** | 95%+ | 95% | ✅ |
| **Infrastructure** | 90%+ | 90% | ✅ |
| **Overall** | 90% | >90% | ✅ |

---

## 🚀 Getting Started

### Prerequisites

```bash
# Python 3.13
# Neo4j running (bolt://neo4j:7687)
# Valkey running (redis://valkey:6379)
# NATS JetStream running

source .venv/bin/activate
cd services/workflow
pip install -e .
```

### Configuration

```bash
# Required
WORKFLOW_PORT=50056
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
VALKEY_HOST=valkey
VALKEY_PORT=6379
NATS_URL=nats://nats:4222

# Optional
LOG_LEVEL=INFO
CACHE_TTL=3600
```

### Running

```bash
# Generate protos
bash scripts/test/_generate_protos.sh

# Tests
make test-unit

# Server
python services/workflow/server.py
```

### Deployment

```bash
# Build
podman build -t registry.underpassai.com/swe-fleet/workflow:v1.0.0 \
  -f services/workflow/Dockerfile .

# Push
podman push registry.underpassai.com/swe-fleet/workflow:v1.0.0

# Deploy
kubectl apply -f deploy/k8s-integration/

# Verify
kubectl get pods -n swe-ai-fleet -l app=workflow
```

---

## 📊 Monitoring & Observability

### View Logs

```bash
kubectl logs -n swe-ai-fleet -l app=workflow -f
```

### Check Health

```bash
grpcurl -plaintext workflow.swe-ai-fleet.svc.cluster.local:50056 \
  grpc.health.v1.Health/Check
```

### Query Workflow

```bash
grpcurl -plaintext -d '{"task_id":"task-001"}' \
  workflow.swe-ai-fleet.svc.cluster.local:50056 \
  workflow.v1.WorkflowService/GetWorkflowState
```

### Get Pending Tasks

```bash
grpcurl -plaintext -d '{"role":"DEV"}' \
  workflow.swe-ai-fleet.svc.cluster.local:50056 \
  workflow.v1.WorkflowService/GetPendingTasks
```

---

## 🔍 Troubleshooting

### Issue: "Invalid state transition"
```
❌ Error: Cannot transition from CODE to DESIGN
```
**Solution**: Check RBAC rules and current role

### Issue: "Neo4j connection failed"
```
❌ Error: Failed to connect to bolt://neo4j:7687
```
**Solution**: Verify NEO4J_URI env var and connectivity

### Issue: "Task not found"
```
❌ Error: Workflow not found for task-001
```
**Solution**: Verify task was initialized by PlanningEventsConsumer

---

## ✅ Compliance Checklist

### DDD Principles ✅
- ✅ FSM as domain service
- ✅ Immutable value objects
- ✅ RBAC rules in domain
- ✅ No infrastructure dependencies

### Hexagonal Architecture ✅
- ✅ Ports for storage, messaging
- ✅ Adapters for Neo4j, Valkey, NATS
- ✅ Dependency injection
- ✅ Clean layer separation

### Repository Rules (.cursorrules) ✅
- ✅ 100% English
- ✅ Immutable frozen dataclasses
- ✅ Fail-fast validation
- ✅ No reflection
- ✅ No to_dict/from_dict
- ✅ Full type hints
- ✅ Dependency injection
- ✅ Tests mandatory (>90%)

---

## 📚 Related Documentation

- **INTERACTIONS.md** - Service interaction patterns (reference)
- **../orchestrator/README.md** - Orchestrator Service
- **../planning/README.md** - Planning Service
- **specs/fleet/workflow/v1/workflow.proto** - gRPC definition
- **../../docs/HEXAGONAL_ARCHITECTURE_PRINCIPLES.md** - Patterns

---

**Workflow Service v1.0.0** - RBAC Level 2 Workflow Action Control  
**Architecture**: DDD + Hexagonal | **Pattern**: Event-Driven Microservices | **Status**: ✅ Production Ready

