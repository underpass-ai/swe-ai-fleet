# Workflow Orchestration Service - Architecture Design

**Version:** 1.0
**Date:** 2025-11-04
**Status:** 🔵 DESIGN PHASE
**Type:** New Microservice Proposal

---

## 🎯 Objective

Crear un **Workflow Orchestration Service** que:
- Coordina interacciones entre agentes multi-rol
- Implementa máquina de estados para validaciones
- Procesa eventos de VLLMAgent asíncronamente
- Rutea tareas basado en Actions y estados
- **NO bloqueante** - event-driven

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     EVENT-DRIVEN ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐         NATS Events          ┌─────────────────────┐
│              │  agent.work.completed        │   Workflow          │
│  VLLMAgent   ├─────────────────────────────>│   Orchestration     │
│  (Worker)    │                               │   Service           │
│              │<─────────────────────────────┤   (New)             │
└──────────────┘  workflow.task.assigned      │                     │
                                               │   - State Machine   │
┌──────────────┐                               │   - Action Router   │
│              │                               │   - Validator       │
│ Orchestrator │  gRPC (non-blocking)          │                     │
│ Service      ├──────────────────────────────>│                     │
│              │  RequestValidation(...)       │                     │
│              │<──────────────────────────────┤                     │
└──────────────┘  ValidationRequested          └─────────────────────┘
                  (returns immediately)                     │
                                                           │
┌──────────────┐                               ┌───────────┴─────────┐
│   Context    │  workflow.state.changed       │                     │
│   Service    │<──────────────────────────────┤   Stores state in   │
│              │                               │   Neo4j + Valkey    │
└──────────────┘                               └─────────────────────┘

┌──────────────┐
│   Planning   │  agile.events
│   Service    ├─────────────────────────────> FSM triggers
│              │  (story transitions)          workflow transitions
└──────────────┘
```

---

## 🔄 Workflow State Machine

### Estados del Workflow

```yaml
# config/workflow.fsm.yaml (NEW)

states:
  # Developer states
  - id: todo
    description: "Tarea pendiente de implementación"
    allowed_roles: [developer]

  - id: implementing
    description: "Developer está implementando"
    allowed_roles: [developer]
    entry_action: CLAIM_TASK

  - id: dev_completed
    description: "Developer completó implementación"
    allowed_roles: [developer]
    exit_action: REQUEST_REVIEW

  # Architect states
  - id: pending_arch_review
    description: "Esperando revisión de Architect"
    allowed_roles: [architect]
    entry_notification: architect  # Notificar a architects

  - id: arch_reviewing
    description: "Architect está revisando"
    allowed_roles: [architect]
    entry_action: REVIEW_ARCHITECTURE

  - id: arch_approved
    description: "Architect aprobó diseño"
    allowed_roles: [architect]
    exit_action: APPROVE_DESIGN

  - id: arch_rejected
    description: "Architect rechazó diseño"
    allowed_roles: [architect]
    exit_action: REJECT_DESIGN

  # QA states
  - id: pending_qa
    description: "Esperando testing de QA"
    allowed_roles: [qa]
    entry_notification: qa

  - id: qa_testing
    description: "QA está probando"
    allowed_roles: [qa]
    entry_action: RUN_TESTS

  - id: qa_passed
    description: "QA aprobó tests"
    allowed_roles: [qa]
    exit_action: APPROVE_TESTS

  - id: qa_failed
    description: "Tests fallaron"
    allowed_roles: [qa]
    exit_action: REJECT_TESTS

  # PO states
  - id: pending_po_approval
    description: "Esperando aprobación de PO"
    allowed_roles: [po]
    entry_notification: po

  - id: po_approved
    description: "PO aprobó story"
    allowed_roles: [po]
    exit_action: APPROVE_STORY

  - id: done
    description: "Workflow completo"
    allowed_roles: []
    terminal: true

transitions:
  # Developer → Architect
  - from: implementing
    to: dev_completed
    action: COMMIT_CODE
    guard: code_committed == true

  - from: dev_completed
    to: pending_arch_review
    action: REQUEST_REVIEW
    auto: true  # Automatic transition

  # Architect review cycle
  - from: pending_arch_review
    to: arch_reviewing
    action: CLAIM_REVIEW
    role_required: architect

  - from: arch_reviewing
    to: arch_approved
    action: APPROVE_DESIGN
    role_required: architect

  - from: arch_reviewing
    to: arch_rejected
    action: REJECT_DESIGN
    role_required: architect

  # Rejected → back to Dev
  - from: arch_rejected
    to: implementing
    action: REVISE_CODE
    role_required: developer
    feedback_required: true

  # Approved → QA
  - from: arch_approved
    to: pending_qa
    auto: true  # Automatic routing to QA

  # QA testing cycle
  - from: pending_qa
    to: qa_testing
    action: CLAIM_TESTING
    role_required: qa

  - from: qa_testing
    to: qa_passed
    action: APPROVE_TESTS
    role_required: qa

  - from: qa_testing
    to: qa_failed
    action: REJECT_TESTS
    role_required: qa

  # QA failed → back to Dev
  - from: qa_failed
    to: implementing
    action: FIX_BUGS
    role_required: developer

  # QA passed → PO
  - from: qa_passed
    to: pending_po_approval
    auto: true  # Automatic routing to PO

  # PO approval
  - from: pending_po_approval
    to: po_approved
    action: APPROVE_STORY
    role_required: po

  - from: po_approved
    to: done
    auto: true  # Final state

guards:
  - name: code_committed
    check: artifacts.commit_sha exists

  - name: tests_passing
    check: test_results.passed > 0.9
```

---

## 📡 Event-Driven Communication

### NATS Streams/Subjects

```yaml
# New NATS subjects for workflow orchestration

subjects:
  # 1. Agent work completion events
  agent.work.completed:
    description: "VLLMAgent publishes when completes assigned work"
    publisher: VLLMAgent
    consumer: Workflow Orchestration Service
    schema:
      task_id: string
      agent_id: string
      role: string  # developer, architect, qa, po
      action_performed: string  # COMMIT_CODE, APPROVE_DESIGN, etc.
      result: object
      artifacts:
        commit_sha: string
        files_changed: array
        test_results: object
    example:
      task_id: "task-001"
      agent_id: "agent-dev-001"
      role: "developer"
      action_performed: "COMMIT_CODE"
      result:
        success: true
        operations: 5
      artifacts:
        commit_sha: "abc123"
        files_changed: ["src/auth.py"]

  # 2. Workflow state changes
  workflow.state.changed:
    description: "Workflow Service publishes state transitions"
    publisher: Workflow Orchestration Service
    consumer: [Context Service, Monitoring, UI]
    schema:
      task_id: string
      from_state: string
      to_state: string
      triggered_by_action: string
      actor_role: string
      timestamp: datetime
    example:
      task_id: "task-001"
      from_state: "dev_completed"
      to_state: "pending_arch_review"
      triggered_by_action: "REQUEST_REVIEW"
      actor_role: "developer"

  # 3. Task assignments
  workflow.task.assigned:
    description: "Workflow Service assigns tasks to roles"
    publisher: Workflow Orchestration Service
    consumer: Orchestrator
    schema:
      task_id: string
      assigned_to_role: string  # architect, qa, po
      required_action: string  # APPROVE_DESIGN, RUN_TESTS, etc.
      work_to_validate:
        commit_sha: string
        files: array
        context: string
    example:
      task_id: "task-001"
      assigned_to_role: "architect"
      required_action: "APPROVE_DESIGN"
      work_to_validate:
        commit_sha: "abc123"
        files: ["src/auth.py"]

  # 4. Validation requests (from Orchestrator)
  workflow.validation.requested:
    description: "Orchestrator requests workflow validation/transition"
    publisher: Orchestrator
    consumer: Workflow Orchestration Service
    schema:
      task_id: string
      role: string
      action: string
      result: object
```

---

## 🔧 Workflow Orchestration Service Components

### 1. State Machine Engine

```python
# services/workflow/domain/state_machine.py

@dataclass(frozen=True)
class WorkflowState:
    """Current state of a task in the workflow."""
    task_id: str
    current_state: str  # "implementing", "pending_arch_review", etc.
    role_in_charge: str | None  # Who should act now
    required_action: ActionEnum | None  # What action is needed
    history: tuple[StateTransition, ...]  # Audit trail
    feedback: str | None  # Feedback from validators

@dataclass(frozen=True)
class StateTransition:
    """Record of a state transition."""
    from_state: str
    to_state: str
    action: ActionEnum
    actor_role: str
    timestamp: datetime
    feedback: str | None

class WorkflowStateMachine:
    """Domain service for workflow state management."""

    def __init__(self, config: WorkflowFSMConfig):
        self.states = config.states
        self.transitions = config.transitions

    def can_transition(
        self,
        current_state: str,
        action: ActionEnum,
        actor_role: str
    ) -> bool:
        """Check if transition is allowed."""
        transition = self._find_transition(current_state, action)
        if not transition:
            return False

        # Validate role is allowed to perform action
        if transition.role_required and transition.role_required != actor_role:
            return False

        return True

    def execute_transition(
        self,
        workflow_state: WorkflowState,
        action: ActionEnum,
        actor_role: str,
        result: dict,
    ) -> WorkflowState:
        """Execute state transition (immutable)."""
        if not self.can_transition(workflow_state.current_state, action, actor_role):
            raise ValueError(
                f"Invalid transition: {workflow_state.current_state} "
                f"with action {action} by {actor_role}"
            )

        transition = self._find_transition(workflow_state.current_state, action)
        new_state = transition.to_state

        # Determine next role and required action
        next_role, next_action = self._get_next_role_and_action(new_state)

        # Create new workflow state (immutable)
        new_transition = StateTransition(
            from_state=workflow_state.current_state,
            to_state=new_state,
            action=action,
            actor_role=actor_role,
            timestamp=datetime.now(),
            feedback=result.get("feedback")
        )

        return WorkflowState(
            task_id=workflow_state.task_id,
            current_state=new_state,
            role_in_charge=next_role,
            required_action=next_action,
            history=workflow_state.history + (new_transition,),
            feedback=result.get("feedback")
        )
```

### 2. Event Consumer (NATS)

```python
# services/workflow/infrastructure/consumers/agent_work_consumer.py

class AgentWorkCompletedConsumer:
    """
    Consumes agent.work.completed events from VLLMAgent.

    Non-blocking: processes events asynchronously and updates workflow state.
    """

    def __init__(
        self,
        nats_client: NATSClient,
        state_machine: WorkflowStateMachine,
        state_repository: WorkflowStateRepository,
        event_publisher: WorkflowEventPublisher,
    ):
        self.nats = nats_client
        self.fsm = state_machine
        self.repo = state_repository
        self.publisher = event_publisher

    async def start(self):
        """Start consuming events (non-blocking)."""
        await self.nats.subscribe(
            subject="agent.work.completed",
            queue_group="workflow-orchestration",
            callback=self.handle_agent_work_completed
        )

    async def handle_agent_work_completed(self, msg: NATSMessage):
        """Process agent work completion event."""
        payload = json.loads(msg.data)

        task_id = payload["task_id"]
        role = payload["role"]
        action_performed = ActionEnum(payload["action_performed"])
        result = payload["result"]

        # 1. Load current workflow state
        workflow_state = await self.repo.get_state(task_id)

        # 2. Validate action is allowed
        agent_role = RoleFactory.create_role_by_name(role)
        action_obj = Action(value=action_performed)

        if not agent_role.can_perform(action_obj):
            logger.error(
                f"RBAC Violation in workflow: {role} cannot perform {action_performed}"
            )
            await self.publisher.publish_violation(task_id, role, action_performed)
            return  # Reject event

        # 3. Execute state transition
        try:
            new_state = self.fsm.execute_transition(
                workflow_state=workflow_state,
                action=action_performed,
                actor_role=role,
                result=result
            )
        except ValueError as e:
            logger.error(f"Invalid workflow transition: {e}")
            return  # Reject event

        # 4. Persist new state
        await self.repo.save_state(new_state)

        # 5. Publish state change event
        await self.publisher.publish_state_changed(
            task_id=task_id,
            from_state=workflow_state.current_state,
            to_state=new_state.current_state,
            triggered_by=action_performed,
            actor_role=role
        )

        # 6. Auto-route if next role assigned
        if new_state.role_in_charge:
            await self.publisher.publish_task_assigned(
                task_id=task_id,
                assigned_to_role=new_state.role_in_charge,
                required_action=new_state.required_action,
                work_to_validate=result.get("artifacts", {})
            )

        # Ack message (non-blocking)
        await msg.ack()
```

### 3. gRPC API (Non-Blocking)

```protobuf
// specs/workflow_orchestration.proto

syntax = "proto3";

package workflow.v1;

// Workflow Orchestration Service
service WorkflowOrchestrationService {
  // Get current workflow state
  rpc GetWorkflowState(GetWorkflowStateRequest) returns (WorkflowStateResponse);

  // Request validation (non-blocking, returns immediately)
  rpc RequestValidation(RequestValidationRequest) returns (RequestValidationResponse);

  // Query tasks pending for a role
  rpc GetPendingTasks(GetPendingTasksRequest) returns (PendingTasksResponse);

  // Claim a task for processing
  rpc ClaimTask(ClaimTaskRequest) returns (ClaimTaskResponse);
}

message GetWorkflowStateRequest {
  string task_id = 1;
}

message WorkflowStateResponse {
  string task_id = 1;
  string current_state = 2;
  string role_in_charge = 3;  // Who should act now
  string required_action = 4;  // What action is needed (APPROVE_DESIGN, etc.)
  repeated StateTransitionDTO history = 5;
  string feedback = 6;  // Feedback from previous validator
}

message RequestValidationRequest {
  string task_id = 1;
  string role = 2;  // developer, architect, qa, po
  string action = 3;  // COMMIT_CODE, APPROVE_DESIGN, etc.
  WorkResult result = 4;
}

message RequestValidationResponse {
  // Non-blocking: returns immediately
  string status = 1;  // "accepted", "rejected"
  string message = 2;
  string current_state = 3;  // Updated state
  string next_role = 4;  // Who should act next
  string next_action = 5;  // What action is needed next
}

message WorkResult {
  bool success = 1;
  map<string, string> artifacts = 2;  // commit_sha, files_changed, etc.
  string reasoning = 3;
  int32 operations_count = 4;
}

message GetPendingTasksRequest {
  string role = 1;  // architect, qa, po
  int32 limit = 2;
}

message PendingTasksResponse {
  repeated PendingTask tasks = 1;
}

message PendingTask {
  string task_id = 1;
  string current_state = 2;
  string required_action = 3;
  WorkToValidate work = 4;
  string context = 5;
}

message WorkToValidate {
  string commit_sha = 1;
  repeated string files_changed = 2;
  string implementation_summary = 3;
}
```

---

## 🔄 Flow Examples

### Flow 1: Developer → Architect → QA → PO (Happy Path)

```
1. Developer implements feature
   ┌─────────────────────────────────────────────────────────┐
   │ VLLMAgent (role=developer)                              │
   │   - Executes task: "Implement JWT auth"                │
   │   - Uses tools: files.write, git.commit, tests.pytest  │
   │   - Publishes:                                          │
   │     NATS: agent.work.completed {                        │
   │       task_id: "task-001",                              │
   │       role: "developer",                                │
   │       action_performed: "COMMIT_CODE",                  │
   │       artifacts: {commit_sha: "abc123"}                 │
   │     }                                                    │
   └─────────────────────────────────────────────────────────┘
                           ↓
   ┌─────────────────────────────────────────────────────────┐
   │ Workflow Orchestration Service                          │
   │   - Receives agent.work.completed                       │
   │   - Current state: "implementing"                       │
   │   - Validates: developer.can_execute(COMMIT_CODE) ✅    │
   │   - Transition: implementing → dev_completed            │
   │   - Auto-transition: dev_completed → pending_arch_review│
   │   - Publishes:                                          │
   │     NATS: workflow.task.assigned {                      │
   │       task_id: "task-001",                              │
   │       assigned_to_role: "architect",                    │
   │       required_action: "APPROVE_DESIGN",                │
   │       work_to_validate: {commit_sha: "abc123"}          │
   │     }                                                    │
   └─────────────────────────────────────────────────────────┘
                           ↓
2. Architect reviews
   ┌─────────────────────────────────────────────────────────┐
   │ Orchestrator                                            │
   │   - Consumes workflow.task.assigned                     │
   │   - Sees: role=architect, action=APPROVE_DESIGN         │
   │   - Calls Context.GetContext(task_id, role=architect)   │
   │   - Creates VLLMAgent (role=architect, enable_tools=F)  │
   │   - Task: "Review JWT implementation in commit abc123"  │
   │   - Architect analyzes code (read-only)                 │
   │   - Publishes:                                          │
   │     NATS: agent.work.completed {                        │
   │       task_id: "task-001",                              │
   │       role: "architect",                                │
   │       action_performed: "APPROVE_DESIGN",               │
   │       feedback: "Good implementation, LGTM"             │
   │     }                                                    │
   └─────────────────────────────────────────────────────────┘
                           ↓
   ┌─────────────────────────────────────────────────────────┐
   │ Workflow Orchestration Service                          │
   │   - Validates: architect.can_execute(APPROVE_DESIGN) ✅ │
   │   - Transition: pending_arch_review → arch_approved     │
   │   - Auto-transition: arch_approved → pending_qa         │
   │   - Publishes:                                          │
   │     NATS: workflow.task.assigned {                      │
   │       assigned_to_role: "qa",                           │
   │       required_action: "RUN_TESTS"                      │
   │     }                                                    │
   └─────────────────────────────────────────────────────────┘
                           ↓
3. QA tests
   (Similar flow: QA → APPROVE_TESTS → PO → APPROVE_STORY → DONE)
```

---

### Flow 2: Architect Rejects (Loop Back to Dev)

```
1. Architect reviews and rejects
   ┌─────────────────────────────────────────────────────────┐
   │ VLLMAgent (role=architect)                              │
   │   - Reviews code                                        │
   │   - Finds security issue                                │
   │   - Publishes:                                          │
   │     NATS: agent.work.completed {                        │
   │       action_performed: "REJECT_DESIGN",                │
   │       feedback: "Security: passwords in plaintext"      │
   │     }                                                    │
   └─────────────────────────────────────────────────────────┘
                           ↓
   ┌─────────────────────────────────────────────────────────┐
   │ Workflow Orchestration Service                          │
   │   - Validates: architect.can_execute(REJECT_DESIGN) ✅  │
   │   - Transition: arch_reviewing → arch_rejected          │
   │   - Auto-transition: arch_rejected → implementing       │
   │   - Stores feedback in state                            │
   │   - Publishes:                                          │
   │     NATS: workflow.task.assigned {                      │
   │       assigned_to_role: "developer",                    │
   │       required_action: "REVISE_CODE",                   │
   │       feedback: "Security: passwords in plaintext"      │
   │     }                                                    │
   └─────────────────────────────────────────────────────────┘
                           ↓
2. Developer revises with feedback
   ┌─────────────────────────────────────────────────────────┐
   │ VLLMAgent (role=developer)                              │
   │   - Receives task with architect feedback               │
   │   - Context includes:                                   │
   │     "Previous feedback: passwords in plaintext"         │
   │   - Revises code                                        │
   │   - Publishes: agent.work.completed (COMMIT_CODE)       │
   └─────────────────────────────────────────────────────────┘
                           ↓
   (Loop: back to Architect for re-review)
```

---

## 🎨 LLM Context Enhancement

### Current Prompt (Tool-Level Only):

```python
# generate_plan_usecase.py - Current
system_prompt = f"""
{role_prompt}  # "You are an expert software developer"

You have access to the following tools:
{tools_json}  # [files, git, tests]

Mode: {mode}  # full

Generate a step-by-step execution plan...
"""
```

### Enhanced Prompt (With Workflow Context):

```python
# generate_plan_usecase.py - Enhanced
system_prompt = f"""
{role_prompt}  # "You are an expert software developer"

You have access to the following tools:
{tools_json}  # [files, git, tests]

Mode: {mode}  # full

WORKFLOW CONTEXT:
{workflow_context}  # ← NEW

Generate a step-by-step execution plan...
"""

# Where workflow_context comes from Context Service:
workflow_context = f"""
Your Role in Workflow:
- You are implementing a feature that will be reviewed by ARCHITECT
- Current State: {workflow_state.current_state}
- Required Action: {workflow_state.required_action}

Coordination Protocol:
1. Implement the feature using available tools
2. When done, use COMMIT_CODE action (git.commit)
3. Your work will automatically route to ARCHITECT for validation
4. Architect will APPROVE_DESIGN or REJECT_DESIGN
5. If rejected, you will receive feedback and REVISE_CODE
6. If approved, work routes to QA for testing

Previous Feedback:
{workflow_state.feedback or "None - first implementation"}
"""
```

---

## ♻️ Recovery & Retry Strategy

### Design Decision: Retry Completo (NO Checkpoints)

**Principle:** Simplicidad > Complejidad

#### ✅ What We DO:

```python
# Si task se interrumpe por cualquier motivo:
# - Timeout
# - Error en step
# - Agent crash
# - Network failure

# → RETRY COMPLETO desde el inicio
workflow_service.retry_task(task_id)
# ✅ NO guardar steps parciales
# ✅ NO reanudar desde último step
# ✅ Task es idempotente
```

#### ❌ What We DON'T DO:

```python
# NO guardar checkpoints de steps individuales:
{
  "task_id": "task-001",
  "steps_completed": [
    {"step": 1, "status": "completed", "result": "..."},
    {"step": 2, "status": "completed", "result": "..."},
    {"step": 3, "status": "failed"}  # ← Resume from here
  ]
}
# ❌ Demasiado complejo
# ❌ Mucho estado a mantener
# ❌ Difícil consistencia
```

#### Rationale:

**Benefits:**
- ✅ Código más simple
- ✅ Menos estado a mantener
- ✅ Más fácil de razonar
- ✅ Idempotencia natural
- ✅ Sin inconsistencias de estado parcial

**Trade-offs:**
- ⚠️ Re-ejecuta steps ya completados
- ⚠️ Slightly more compute/time

**Decision:** ✅ **Simplicity wins** - Tasks son rápidas (segundos/minutos), retry completo es aceptable.

#### Implementation:

```python
# workflow_orchestration_service.py

class WorkflowOrchestrationService:
    async def handle_task_failure(self, task_id: str, error: str):
        """Handle task failure with complete retry."""
        workflow_state = await self.repo.get_state(task_id)
        
        # 1. Log failure (for observability)
        logger.warning(
            f"Task {task_id} failed in state {workflow_state.current_state}: {error}"
        )
        
        # 2. Reset to initial state for retry
        reset_state = WorkflowState(
            task_id=task_id,
            current_state="todo",  # ✅ Back to start
            role_in_charge="developer",
            required_action=ActionEnum.IMPLEMENT_FEATURE,
            history=workflow_state.history + (
                StateTransition(
                    from_state=workflow_state.current_state,
                    to_state="todo",
                    action=ActionEnum.RETRY,
                    actor_role="system",
                    timestamp=datetime.now(),
                    feedback=f"Retry due to: {error}"
                ),
            ),
            feedback=None  # Clear feedback for fresh start
        )
        
        # 3. Save reset state
        await self.repo.save_state(reset_state)
        
        # 4. Publish retry event
        await self.publisher.publish_task_assigned(
            task_id=task_id,
            assigned_to_role="developer",
            required_action="IMPLEMENT_FEATURE",
            retry_count=len([t for t in reset_state.history if t.action == ActionEnum.RETRY])
        )
        
        # ✅ NO guardar steps parciales
        # ✅ Task retries desde el principio
```

#### What We Store:

```yaml
# Only store workflow-level state, NOT step-level checkpoints

Workflow State (Neo4j):
  task_id: "task-001"
  current_state: "implementing"  # Workflow state, not step index
  role_in_charge: "developer"
  required_action: "IMPLEMENT_FEATURE"
  retry_count: 2  # How many times retried
  last_error: "Agent timeout"  # Why it failed
  
# ✅ Simple
# ✅ Only high-level state
# ✅ NO step-by-step checkpoints
```

---

## 🗄️ Data Storage

### Neo4j (Graph Model)

```cypher
// Workflow state nodes
(:WorkflowState {
  task_id: "task-001",
  current_state: "pending_arch_review",
  role_in_charge: "architect",
  required_action: "APPROVE_DESIGN",
  created_at: timestamp,
  updated_at: timestamp
})

// State transitions (audit trail)
(:WorkflowState)-[:TRANSITIONED_TO {
  action: "REQUEST_REVIEW",
  actor_role: "developer",
  timestamp: timestamp,
  feedback: null
}]->(:WorkflowState)

// Relationships with existing graph
(:Task {id: "task-001"})-[:HAS_WORKFLOW]->(:WorkflowState)
(:Agent {id: "agent-dev-001"})-[:PERFORMED {
  action: "COMMIT_CODE",
  timestamp: timestamp
}]->(:WorkflowState)
```

### Valkey (Cache)

```python
# Fast lookup for current state
valkey.set(
    f"workflow:task:{task_id}:state",
    json.dumps({
        "current_state": "pending_arch_review",
        "role_in_charge": "architect",
        "required_action": "APPROVE_DESIGN"
    }),
    ex=3600  # 1 hour TTL
)

# Pending tasks by role (for assignment)
valkey.sadd(
    f"workflow:pending:architect",
    task_id
)
```

---

## 📋 Service Responsibilities

### Workflow Orchestration Service

**Bounded Context:** Workflow Coordination

**Responsibilities:**
1. **State Management**
   - Maintain workflow state per task
   - Validate state transitions
   - Enforce transition guards

2. **Action Routing**
   - Route tasks to correct roles
   - Notify role-in-charge
   - Track pending work by role

3. **RBAC Validation**
   - Validate actor can perform action
   - Enforce role-based transitions
   - Log RBAC violations

4. **Event Publishing**
   - workflow.state.changed
   - workflow.task.assigned
   - workflow.validation.completed

**Does NOT:**
- Execute agent tasks (Orchestrator does this)
- Store code/artifacts (Git/Workspace does this)
- Make business decisions (Agents do this)

---

## 🔌 Integration Points

### 1. VLLMAgent → Workflow Service

**VLLMAgent Changes:**
```python
# vllm_agent.py - After task execution
async def execute_task(...) -> AgentResult:
    result = await self.execute_task_usecase.execute(...)

    # NEW: Publish work completion to workflow service
    if self.workflow_publisher:  # Optional dependency
        await self.workflow_publisher.publish_work_completed(
            task_id=self.task_id,
            role=self.role.get_name(),
            action_performed=self._determine_action(result),  # COMMIT_CODE, etc.
            result=result,
            artifacts=result.artifacts
        )

    return result

def _determine_action(self, result: AgentResult) -> ActionEnum:
    """Determine which Action was performed based on result."""
    if result.artifacts.get("commit_sha"):
        return ActionEnum.COMMIT_CODE
    elif result.artifacts.get("test_results"):
        return ActionEnum.RUN_TESTS
    # ... etc
```

### 2. Orchestrator → Workflow Service

**Orchestrator Changes:**
```python
# orchestrator/usecases/orchestrate_with_workflow.py - NEW

class OrchestratewithWorkflow:
    def __init__(
        self,
        workflow_client: WorkflowOrchestrationServiceStub,  # gRPC client
        nats_client: NATSClient,
    ):
        self.workflow = workflow_client
        self.nats = nats_client

    async def execute(self, task: Task) -> dict:
        # 1. Get workflow state to determine role
        state = self.workflow.GetWorkflowState(
            GetWorkflowStateRequest(task_id=task.id)
        )

        # 2. Determine which role should work
        if not state.role_in_charge:
            # New task, start with developer
            role = RoleEnum.DEVELOPER
            action = ActionEnum.IMPLEMENT_FEATURE
        else:
            # Workflow in progress, use assigned role
            role = RoleEnum(state.role_in_charge)
            action = ActionEnum(state.required_action)

        # 3. Get context for this role
        context = await self.context_service.get_context(
            task_id=task.id,
            role=role,
            workflow_state=state.current_state,  # NEW: Include workflow state
            previous_feedback=state.feedback  # NEW: Include feedback if rejected
        )

        # 4. Execute agent task (existing logic)
        agent_result = await self._execute_agent(
            role=role,
            task=task,
            context=context
        )

        # 5. Request validation (NON-BLOCKING)
        validation_response = self.workflow.RequestValidation(
            RequestValidationRequest(
                task_id=task.id,
                role=role.value,
                action=action.value,
                result=agent_result
            )
        )

        # Returns immediately ✅
        return {
            "task_id": task.id,
            "status": validation_response.status,
            "current_state": validation_response.current_state,
            "next_role": validation_response.next_role,
            "next_action": validation_response.next_action
        }
```

### 3. Context Service Integration

**Context Service Enhancement:**
```python
# context_service/usecases/get_context_usecase.py - Enhanced

async def execute(
    self,
    task_id: str,
    role: str,
    workflow_state: str | None = None,  # NEW
    previous_feedback: str | None = None,  # NEW
) -> ContextDTO:
    # Existing logic...
    context = {
        "story_id": ...,
        "decisions": ...,
        "code_structure": ...,
    }

    # NEW: Add workflow context if provided
    if workflow_state:
        workflow_info = self._get_workflow_info(role, workflow_state, previous_feedback)
        context["workflow"] = workflow_info

    return ContextDTO(**context)

def _get_workflow_info(self, role: str, state: str, feedback: str | None) -> dict:
    """Get workflow-specific context for LLM."""
    return {
        "current_state": state,
        "your_responsibilities": WORKFLOW_RESPONSIBILITIES.get(role, {}).get(state),
        "next_validator": WORKFLOW_ROUTING.get(state),
        "previous_feedback": feedback,
        "coordination_protocol": self._get_protocol(role, state)
    }

# Configuration:
WORKFLOW_RESPONSIBILITIES = {
    "developer": {
        "implementing": "Implement feature. When done, commit code.",
        "arch_rejected": "Revise code based on architect feedback."
    },
    "architect": {
        "pending_arch_review": "Review developer's implementation. Approve or reject design."
    },
    "qa": {
        "pending_qa": "Test the implementation. Validate quality and create test cases."
    },
    "po": {
        "pending_po_approval": "Validate business value. Approve story if requirements met."
    }
}
```

---

## 🚀 Deployment

### New Microservice

```yaml
# deploy/k8s/workflow-orchestration/deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: workflow-orchestration
  namespace: swe-ai-fleet
spec:
  replicas: 2
  selector:
    matchLabels:
      app: workflow-orchestration
  template:
    metadata:
      labels:
        app: workflow-orchestration
    spec:
      containers:
      - name: workflow-orchestration
        image: registry.underpassai.com/swe-fleet/workflow-orchestration:v1.0.0
        ports:
        - containerPort: 50056  # gRPC
        env:
        - name: NATS_URL
          value: "nats://nats:4222"
        - name: NEO4J_URI
          value: "bolt://neo4j:7687"
        - name: VALKEY_URL
          value: "valkey://valkey:6379"
        resources:
          limits:
            cpu: "1000m"
            memory: "1Gi"
```

---

## 📊 Benefits of This Design

### ✅ Non-Blocking Architecture

- Orchestrator makes gRPC call → returns immediately
- Workflow Service processes events asynchronously
- No waiting for validations (event-driven)

### ✅ Separation of Concerns

| Service | Responsibility |
|---------|---------------|
| **VLLMAgent** | Execute tasks with tools |
| **Orchestrator** | Assign tasks to agents |
| **Workflow Service** | Coordinate multi-role workflows |
| **Context Service** | Provide smart context |
| **Planning Service** | Manage user stories (FSM) |

### ✅ RBAC Enforcement at Multiple Levels

```
Level 1: Tool Access (VLLMAgent)
  → "Can QA use docker?" → NO ✅

Level 2: Action Validation (Workflow Service)
  → "Can Developer approve design?" → NO ✅

Level 3: State Transition (Workflow FSM)
  → "Can transition to QA without Architect approval?" → NO ✅
```

### ✅ Scalability

- Stateless workflow service (state in Neo4j/Valkey)
- Horizontal scaling (multiple replicas)
- Event-driven (no polling)

---

## 🎯 Implementation Roadmap

### Sprint 1: Foundation
- [ ] Create Workflow Service skeleton (Go)
- [ ] Implement FSM engine
- [ ] Define workflow.fsm.yaml
- [ ] NATS event consumers

### Sprint 2: Integration
- [ ] Integrate with VLLMAgent (publish events)
- [ ] Integrate with Orchestrator (gRPC API)
- [ ] Update Context Service (workflow context)
- [ ] Neo4j/Valkey persistence

### Sprint 3: Testing & Docs
- [ ] Integration tests (full workflow)
- [ ] E2E tests (Dev → Arch → QA → PO)
- [ ] Documentation
- [ ] Deployment

---

**Status:** 🔵 DESIGN COMPLETE - Ready for implementation
**Priority:** 🟡 MEDIUM (next sprint after RBAC merge)
**Author:** AI Assistant + Tirso García
**Date:** 2025-11-04

