# RBAC Levels 2 & 3 - Implementation Strategy

**Date:** 2025-11-05  
**Architect:** Tirso García Ibáñez  
**Session:** Post-Cluster Recovery & Planning  
**Context:** After successful RBAC Level 1 implementation (PR #95)

---

## 🎯 Executive Summary

We have **3 levels of RBAC** in SWE AI Fleet, each solving a different problem:

```
┌──────────────────────────────────────────────────────────────┐
│                    RBAC 3-LEVEL MODEL                         │
└──────────────────────────────────────────────────────────────┘

✅ Level 1: TOOL ACCESS CONTROL (IMPLEMENTED)
   Problem: "¿Puede QA usar Docker?"
   Solution: Role.allowed_tools + runtime validation
   Location: Agent domain (VLLMAgent)
   Status: Production Ready (PR #95 merged)

❌ Level 2: WORKFLOW ACTION CONTROL (TO IMPLEMENT)
   Problem: "¿Cómo sabe Dev que Architect debe validarlo?"
   Solution: Workflow FSM + Action routing
   Location: Orchestrator Service
   Status: TO IMPLEMENT (this PR)

🔵 Level 3: DATA ACCESS CONTROL (DESIGNED)
   Problem: "¿Qué ve cada rol en el grafo Neo4j?"
   Solution: Role-based Context queries
   Location: Context Service
   Status: Designed, future PR
```

---

## 🚀 Level 2: Workflow Action Control (Orchestrator)

### 📋 Problem Statement

**User Question (from session 2025-11-03):**
> "¿Cómo sabe Developer que Architect debe validar su trabajo?  
> ¿Cómo sabe Architect que tiene que revisar las soluciones de los Devs?  
> ¿Cómo sabe QA que tiene que interactuar con PO?"

### 🔍 Current Gap

**What we HAVE:**
- ✅ Actions defined (APPROVE_DESIGN, REJECT_DESIGN, etc.)
- ✅ Role.allowed_actions configured
- ✅ Agent.can_execute(action) validates permissions

**What we DON'T HAVE:**
- ❌ Orchestrator doesn't USE actions
- ❌ No workflow state machine for task lifecycle
- ❌ No automatic routing (Dev → Architect → QA → PO)
- ❌ LLM doesn't know workflow responsibilities

### 🏗️ Proposed Architecture

#### Component 1: Workflow State Machine

**File:** `services/orchestrator/domain/entities/workflow_state.py`

```python
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet

class WorkflowStateEnum(Enum):
    """Task workflow states with validation checkpoints."""
    DRAFT = "draft"                          # Initial state
    IMPLEMENTING = "implementing"            # Dev working
    PENDING_ARCH_REVIEW = "pending_arch_review"  # Waiting Architect
    ARCH_APPROVED = "arch_approved"          # Architect approved
    ARCH_REJECTED = "arch_rejected"          # Architect rejected → back to Dev
    PENDING_QA = "pending_qa"                # Waiting QA
    QA_PASSED = "qa_passed"                  # QA approved
    QA_FAILED = "qa_failed"                  # QA failed → back to Dev
    PENDING_PO_APPROVAL = "pending_po_approval"  # Waiting PO
    DONE = "done"                            # Complete
    CANCELLED = "cancelled"                  # Cancelled by PO

@dataclass(frozen=True)
class WorkflowState:
    """Workflow state value object."""
    value: WorkflowStateEnum
    required_action: ActionEnum | None  # Action needed to exit this state
    required_role: RoleEnum | None      # Role that can perform action
```

#### Component 2: Workflow Transition Rules

**File:** `services/orchestrator/domain/entities/workflow_transitions.py`

```python
@dataclass(frozen=True)
class WorkflowTransition:
    """Defines valid state transitions with required actions."""
    from_state: WorkflowStateEnum
    action: ActionEnum
    to_state_success: WorkflowStateEnum
    to_state_failure: WorkflowStateEnum | None = None
    required_role: RoleEnum

# Example transitions:
WORKFLOW_TRANSITIONS = [
    # Developer completes implementation
    WorkflowTransition(
        from_state=WorkflowStateEnum.IMPLEMENTING,
        action=ActionEnum.REQUEST_REVIEW,
        to_state_success=WorkflowStateEnum.PENDING_ARCH_REVIEW,
        required_role=RoleEnum.DEVELOPER
    ),
    
    # Architect approves design
    WorkflowTransition(
        from_state=WorkflowStateEnum.PENDING_ARCH_REVIEW,
        action=ActionEnum.APPROVE_DESIGN,
        to_state_success=WorkflowStateEnum.PENDING_QA,
        required_role=RoleEnum.ARCHITECT
    ),
    
    # Architect rejects design
    WorkflowTransition(
        from_state=WorkflowStateEnum.PENDING_ARCH_REVIEW,
        action=ActionEnum.REJECT_DESIGN,
        to_state_success=WorkflowStateEnum.ARCH_REJECTED,
        required_role=RoleEnum.ARCHITECT
    ),
    
    # Developer revises after rejection
    WorkflowTransition(
        from_state=WorkflowStateEnum.ARCH_REJECTED,
        action=ActionEnum.REVISE_CODE,
        to_state_success=WorkflowStateEnum.IMPLEMENTING,
        required_role=RoleEnum.DEVELOPER
    ),
    
    # QA approves tests
    WorkflowTransition(
        from_state=WorkflowStateEnum.PENDING_QA,
        action=ActionEnum.APPROVE_TESTS,
        to_state_success=WorkflowStateEnum.PENDING_PO_APPROVAL,
        required_role=RoleEnum.QA
    ),
    
    # PO approves story
    WorkflowTransition(
        from_state=WorkflowStateEnum.PENDING_PO_APPROVAL,
        action=ActionEnum.APPROVE_STORY,
        to_state_success=WorkflowStateEnum.DONE,
        required_role=RoleEnum.PO
    ),
]
```

#### Component 3: Workflow Execution Port

**File:** `services/orchestrator/domain/ports/workflow_execution_port.py`

```python
from typing import Protocol

class WorkflowExecutionPort(Protocol):
    """Port for executing workflow actions (Hexagonal Architecture)."""
    
    async def execute_action(
        self,
        task_id: str,
        action: Action,
        actor_role: Role,
        feedback: str | None = None
    ) -> WorkflowActionResult:
        """Execute a workflow action (approve, reject, revise)."""
        ...
    
    async def get_next_required_action(
        self,
        task_id: str
    ) -> tuple[ActionEnum, RoleEnum]:
        """Get the next required action and who should perform it."""
        ...
    
    async def get_workflow_state(
        self,
        task_id: str
    ) -> WorkflowState:
        """Get current workflow state for a task."""
        ...
```

#### Component 4: Orchestrator Use Case Update

**File:** `services/orchestrator/application/usecases/execute_workflow_action_usecase.py` (NEW)

```python
@dataclass(frozen=True)
class ExecuteWorkflowActionUseCase:
    """Execute workflow action with RBAC validation.
    
    Following Hexagonal Architecture:
    - Uses WorkflowExecutionPort for state management
    - Uses MessagingPort for event publishing
    - Validates action permissions via Agent.can_execute()
    """
    
    workflow_port: WorkflowExecutionPort
    messaging_port: MessagingPort
    
    async def execute(
        self,
        task_id: str,
        action: Action,
        agent: Agent,
        feedback: str | None = None
    ) -> WorkflowActionResult:
        """Execute workflow action with RBAC validation."""
        
        # 1. Validate agent can perform action (RBAC Level 1)
        if not agent.can_execute(action):
            raise PermissionDeniedError(
                f"{agent.get_role_name()} cannot perform {action.value.name}"
            )
        
        # 2. Get current workflow state
        current_state = await self.workflow_port.get_workflow_state(task_id)
        
        # 3. Validate action is allowed in current state
        if not self._is_valid_transition(current_state, action):
            raise InvalidWorkflowTransitionError(
                f"Cannot perform {action.value.name} in state {current_state.value.name}"
            )
        
        # 4. Execute action (transition state)
        result = await self.workflow_port.execute_action(
            task_id=task_id,
            action=action,
            actor_role=agent.role,
            feedback=feedback
        )
        
        # 5. Publish event
        await self.messaging_port.publish(
            subject=f"workflow.action.{action.value.name.lower()}",
            event=WorkflowActionExecutedEvent(
                task_id=task_id,
                action=action.value.name,
                actor_role=agent.get_role_name(),
                new_state=result.new_state.name,
                timestamp=datetime.now(UTC).isoformat()
            )
        )
        
        return result
```

---

## 🔵 Level 3: Data Access Control (Context Service)

### 📋 Problem Statement

**User Insight (from session 2025-11-03):**
> "Developer accede a task + story + epic.  
> Arquitecto accede a epic + todas las stories + todas las tasks.  
> QA accede a story + todas las tasks.  
> Como en equipo real - junior dev no ve tablero completo, tech lead sí"

### 🎯 Design

#### Role-Based Context Scopes

| Role | Sees | Neo4j Query Pattern | Context Size |
|------|------|---------------------|--------------|
| **Developer** | Task + Story + Epic | Narrow (1-hop) | 2-3K tokens |
| **Architect** | Epic + All Stories + All Tasks | Wide (2-3 hops) | 8-12K tokens |
| **QA** | Story + All Tasks + Quality Gates | Medium (2-hops) | 4-6K tokens |
| **PO** | Epic + All Stories (business) | Business view | 3-5K tokens |

#### Implementation Location

**Service:** Context Service  
**File:** `services/context/application/usecases/get_role_based_context_usecase.py` (NEW)

```python
@dataclass(frozen=True)
class GetRoleBasedContextUseCase:
    """Get context filtered by role permissions.
    
    Implements RBAC Level 3 - Data Access Control.
    Each role sees only what it needs (least privilege).
    """
    
    graph_query_port: GraphQueryPort
    cache_port: CachePort
    
    async def execute(
        self,
        story_id: str,
        task_id: str | None,
        role: Role
    ) -> RoleBasedContextDTO:
        """Get context appropriate for the role."""
        
        # Route to role-specific query
        match role.value:
            case RoleEnum.DEVELOPER:
                return await self._get_developer_context(story_id, task_id)
            case RoleEnum.ARCHITECT:
                return await self._get_architect_context(story_id)
            case RoleEnum.QA:
                return await self._get_qa_context(story_id)
            case RoleEnum.PO:
                return await self._get_po_context(story_id)
            case _:
                raise ValueError(f"Unknown role: {role.value}")
    
    async def _get_developer_context(
        self,
        story_id: str,
        task_id: str
    ) -> RoleBasedContextDTO:
        """Developer sees: Task + Story + Epic (narrow)."""
        # Cypher: MATCH (t:Task {task_id})-[:BELONGS_TO]->(s:Story)-[:PART_OF]->(e:Epic)
        ...
    
    async def _get_architect_context(
        self,
        story_id: str
    ) -> RoleBasedContextDTO:
        """Architect sees: Epic + All Stories + All Tasks (wide)."""
        # Cypher: MATCH (e:Epic)<-[:PART_OF]-(s:Story)<-[:BELONGS_TO]-(t:Task)
        ...
```

#### Neo4j Query Patterns

```cypher
-- Developer Context (Narrow - 1 task):
MATCH (task:Task {task_id: $task_id})
-[:BELONGS_TO]->(story:Story)
-[:PART_OF]->(epic:Epic)
RETURN task, story, epic

-- Architect Context (Wide - all tasks in epic):
MATCH (epic:Epic {epic_id: $epic_id})
<-[:PART_OF]-(story:Story)
<-[:BELONGS_TO]-(task:Task)
RETURN epic, story, task
ORDER BY story.created_at, task.created_at

-- QA Context (Medium - all tasks in story):
MATCH (story:Story {story_id: $story_id})
<-[:BELONGS_TO]-(task:Task)
OPTIONAL MATCH (task)-[:HAS_TEST_RESULT]->(test:TestResult)
RETURN story, task, test
```

---

## 📊 Implementation Roadmap

### Phase 1: Level 2 - Workflow Action Control (THIS PR)

**Timeline:** 1-2 weeks  
**Priority:** P0 (Critical)

#### Week 1: Domain Model + Ports

**Tasks:**
1. Create `WorkflowState` value object
2. Create `WorkflowTransition` entity
3. Create `WorkflowExecutionPort` interface
4. Define transition rules (config or code)
5. Unit tests (>90% coverage)

**Deliverables:**
- Domain entities for workflow
- Port definitions
- 30-40 unit tests

#### Week 2: Use Cases + Integration

**Tasks:**
1. Create `ExecuteWorkflowActionUseCase`
2. Create `GetNextRequiredActionUseCase`
3. Update `OrchestrateUseCase` to use actions
4. Integrate with Planning Service FSM
5. Update LLM prompts with workflow context
6. Integration tests

**Deliverables:**
- Orchestrator uses actions for coordination
- Automatic routing (Dev → Arch → QA → PO)
- 20-30 tests

---

### Phase 2: Level 3 - Data Access Control (FUTURE PR)

**Timeline:** 1 week  
**Priority:** P1 (High)

#### Implementation Steps:

**Tasks:**
1. Create `GetRoleBasedContextUseCase`
2. Implement role-specific Neo4j queries
3. Update `GetContext` RPC to accept `role` parameter
4. Add caching layer per role
5. Update documentation
6. Unit + integration tests

**Deliverables:**
- Role-based context filtering
- Least privilege data access
- Optimized context size per role
- 25-35 tests

---

## 🎯 Level 2 - Detailed Design

### Use Case: Developer Implementation Flow

```
1. Orchestrator.execute_task(task_id, role=DEVELOPER)
   ├─ Workflow state: DRAFT → IMPLEMENTING
   ├─ Developer LLM prompt includes:
   │  """
   │  WORKFLOW CONTEXT:
   │  - You are implementing this feature
   │  - After completion, use REQUEST_REVIEW action
   │  - Architect will review your work (APPROVE_DESIGN or REJECT_DESIGN)
   │  - If rejected, you'll receive feedback to REVISE_CODE
   │  """
   ├─ Developer implements
   └─ Developer executes: Action(REQUEST_REVIEW)

2. Orchestrator.execute_workflow_action(task_id, REQUEST_REVIEW, agent)
   ├─ Validate: agent.can_execute(REQUEST_REVIEW) ✅
   ├─ Transition: IMPLEMENTING → PENDING_ARCH_REVIEW
   ├─ Publish: workflow.action.request_review
   └─ Trigger: Route to Architect

3. Orchestrator.execute_task(task_id, role=ARCHITECT)
   ├─ Workflow state: PENDING_ARCH_REVIEW
   ├─ Architect LLM prompt includes:
   │  """
   │  WORKFLOW CONTEXT:
   │  - Developer completed implementation
   │  - Your job: Review architectural consistency
   │  - Actions: APPROVE_DESIGN (if good) or REJECT_DESIGN (if issues)
   │  - If rejecting, provide detailed feedback
   │  """
   ├─ Architect reviews code
   └─ Architect executes: Action(APPROVE_DESIGN) or Action(REJECT_DESIGN)

4a. If APPROVE_DESIGN:
    ├─ Transition: PENDING_ARCH_REVIEW → PENDING_QA
    ├─ Publish: workflow.action.approve_design
    └─ Route to QA

4b. If REJECT_DESIGN:
    ├─ Transition: PENDING_ARCH_REVIEW → ARCH_REJECTED
    ├─ Publish: workflow.action.reject_design
    ├─ Store feedback in Neo4j
    └─ Route back to Developer with feedback

5. QA tests (if approved)
   ├─ Workflow state: PENDING_QA
   ├─ QA executes tests
   └─ QA executes: Action(APPROVE_TESTS) or Action(REJECT_TESTS)

6. PO final approval
   ├─ Workflow state: PENDING_PO_APPROVAL
   ├─ PO reviews via UI
   └─ PO executes: Action(APPROVE_STORY)

7. DONE ✅
```

---

## 🔧 Integration with Existing Services

### 1. Planning Service Integration

**Current:** Planning Service has FSM for story lifecycle  
**New:** Task-level workflow FSM in Orchestrator

**Mapping:**

| Planning State | Orchestrator Workflow State |
|----------------|----------------------------|
| ready_for_dev | DRAFT |
| in_progress | IMPLEMENTING |
| code_review | PENDING_ARCH_REVIEW |
| testing | PENDING_QA |
| done | DONE |

**Integration Point:**
- Planning Service publishes `planning.story.transitioned` events
- Orchestrator consumes these and updates task workflow states
- Bidirectional sync via NATS events

### 2. Context Service Integration

**Current:** Context Service stores task state in Neo4j  
**New:** Context includes workflow state + required action

**Enhanced Context Response:**
```python
context = {
    "task_id": "task-123",
    "story_id": "story-456",
    "epic_id": "epic-789",
    "task_description": "Implement JWT auth",
    "workflow_state": "PENDING_ARCH_REVIEW",  # ← NEW
    "required_action": "APPROVE_DESIGN",      # ← NEW
    "required_role": "ARCHITECT",             # ← NEW
    "previous_feedback": [                    # ← NEW (if rejected before)
        {
            "from_role": "ARCHITECT",
            "action": "REJECT_DESIGN",
            "feedback": "Missing error handling for expired tokens",
            "timestamp": "2025-11-05T10:30:00Z"
        }
    ],
    # ... existing context fields
}
```

---

## 📋 Implementation Checklist

### Domain Layer (1-2 days)
- [ ] Create `WorkflowStateEnum` enum
- [ ] Create `WorkflowState` value object
- [ ] Create `WorkflowTransition` entity
- [ ] Create `WorkflowTransitionRegistry` collection
- [ ] Define all transitions (12 states → ~18 transitions)
- [ ] Unit tests for all domain entities (>90% coverage)

### Application Layer (2-3 days)
- [ ] Create `WorkflowExecutionPort` interface
- [ ] Create `ExecuteWorkflowActionUseCase`
- [ ] Create `GetNextRequiredActionUseCase`
- [ ] Create `GetWorkflowStateUseCase`
- [ ] Unit tests for use cases

### Infrastructure Layer (2-3 days)
- [ ] Create `Neo4jWorkflowAdapter` (implements WorkflowExecutionPort)
- [ ] Store workflow state in Neo4j (Task node properties)
- [ ] Store feedback in Neo4j relationships
- [ ] Create `WorkflowEventPublisher` adapter
- [ ] Integration tests with real Neo4j

### Orchestrator Integration (2-3 days)
- [ ] Update `OrchestrateUseCase` to use workflow actions
- [ ] Update LLM prompt generation with workflow context
- [ ] Add workflow routing logic
- [ ] Handle approval/rejection loops
- [ ] E2E tests for complete workflow

### Documentation (1 day)
- [ ] Document workflow FSM
- [ ] Document action routing
- [ ] Update HEXAGONAL_ARCHITECTURE_PRINCIPLES.md
- [ ] Create workflow diagrams
- [ ] API documentation

**Total Estimated Time:** 8-12 days (1.5-2 weeks)

---

## 🔵 Level 3 - Data Access Control (Future)

### Purpose

**Problem:** All roles currently see the same context (entire graph).  
**Solution:** Role-based queries return only relevant data.

### Implementation Location

**Service:** Context Service  
**Component:** `GetContext` RPC enhancement

### Strategy

#### Phase 1: Role Parameter
- Add `role: string` parameter to `GetContext` RPC
- Add `role` field to `GetContextRequest` proto message

#### Phase 2: Query Router
- Create role-specific Cypher query builders
- Route query based on role parameter
- Return filtered context

#### Phase 3: Caching Strategy
- Cache per role (separate cache keys)
- TTL based on role (Architect cache longer)

### Benefits

1. **Performance:** Developer gets 2-3K tokens (vs 8-12K)
2. **Precision:** Each role sees what it needs
3. **Security:** Least privilege (Dev doesn't see all tasks)
4. **UX:** Faster context loading for narrow scopes

---

## 📝 Decision Log

### Decision 1: Where to Store Workflow State?

**Options:**
- A. Neo4j (Task node properties) ← **CHOSEN**
- B. Redis (temporary state)
- C. Planning Service (reuse existing FSM)

**Rationale:**
- Neo4j provides persistence + audit trail
- Planning Service FSM is story-level, not task-level
- Redis would require dual writes

### Decision 2: Actions in Config or Code?

**Options:**
- A. YAML config file (like agile.fsm.yaml)
- B. Python code (WorkflowTransition dataclasses) ← **CHOSEN**

**Rationale:**
- Workflow transitions are complex (roles, actions, states)
- Python provides type safety
- Easier to test
- Can still load from YAML if needed (future)

### Decision 3: Orchestrator or Separate Service?

**Options:**
- A. Workflow logic in Orchestrator ← **CHOSEN**
- B. New "Workflow Service"

**Rationale:**
- Orchestrator already coordinates agents
- Avoid service proliferation
- Workflow is orchestration logic
- Can extract later if needed

---

## ⚠️ Important Notes

### Why RBAC Level 3 is Separate

**Level 2 (Orchestrator):** Controls WHO can approve WHAT and WHEN  
**Level 3 (Context):** Controls WHO can SEE what data

**Independence:**
- Level 2 can work without Level 3 (all roles see same data)
- Level 3 can work without Level 2 (data filtering without workflow)
- Implementing separately reduces risk

### Testing Strategy

**Level 2 Tests:**
- Unit: Workflow transitions, action validation
- Integration: Neo4j persistence, event publishing
- E2E: Complete workflow (Dev → Arch → QA → PO)

**Level 3 Tests:**
- Unit: Query builders per role
- Integration: Neo4j queries return correct scope
- Performance: Context size validation

---

## 🎯 Success Criteria

### Level 2 (Workflow Action Control)

```
✅ Agent knows its workflow responsibilities
✅ System routes work automatically (Dev → Arch → QA → PO)
✅ Architect can APPROVE_DESIGN or REJECT_DESIGN
✅ Developer receives feedback when rejected
✅ QA validates only after architectural approval
✅ PO final approval gate works
✅ All transitions logged in Neo4j
✅ Events published for each action
✅ >90% test coverage
✅ E2E test passes (Dev → Arch approve → QA approve → PO approve → DONE)
```

### Level 3 (Data Access Control - Future)

```
✅ Developer context: 2-3K tokens (Task + Story + Epic)
✅ Architect context: 8-12K tokens (Epic + All)
✅ QA context: 4-6K tokens (Story + All Tasks)
✅ PO context: 3-5K tokens (Business view)
✅ Cache hit rate > 80%
✅ Query performance < 100ms p95
✅ Tests verify correct scope per role
```

---

## 📚 References

**Previous Sessions:**
- `docs/progress/RBAC_SESSION_2025-11-03.md` - Level 1 implementation
- `docs/audits/current/RBAC_GAP_WORKFLOW_ORCHESTRATION.md` - Gap analysis
- `docs/architecture/RBAC_REAL_WORLD_TEAM_MODEL.md` - Real-world parallels
- `docs/architecture/RBAC_DATA_ACCESS_CONTROL.md` - Level 3 design

**Related PRs:**
- PR #95 - RBAC Level 1: Tool Access Control (MERGED)
- PR #TBD - RBAC Level 2: Workflow Action Control (THIS PR)
- PR #TBD - RBAC Level 3: Data Access Control (FUTURE)

---

**Author:** AI Assistant + Tirso García Ibáñez  
**Created:** 2025-11-05  
**Branch:** `feature/rbac-level-2-orchestrator`  
**Status:** Planning & Design Phase


