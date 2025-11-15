# Planning Service - Architecture

**Bounded Context**: Planning
**Pattern**: DDD + Hexagonal Architecture
**Version**: v0.1.0

---

## 🎯 Responsibility

Manage user story lifecycle with FSM (Finite State Machine) and decision approval workflow.

**Core Responsibilities**:
1. **Create and persist entities** in hierarchy: Project → Epic → Story → Task
2. **Enforce domain invariants**: Task MUST belong to Story, Story MUST belong to Epic, Epic MUST belong to Project
3. **Manage user story lifecycle** with FSM (DRAFT → PO_REVIEW → READY → IN_PROGRESS → DONE)
4. **Decision approval/rejection workflow** (PO human-in-the-loop)
5. **Request Task Derivation** (event-driven): Publish `task.derivation.requested` events (delegated to Task Derivation Service)
6. **Publish domain events** for orchestrator integration

**Task Derivation Flow (delegated to Task Derivation Service)**:
- **Planning Service** publishes `task.derivation.requested` event when plan is approved
- **Task Derivation Service** (separate microservice) handles:
  - Fetching plan context from Planning Service (gRPC)
  - Fetching rehydrated context from Context Service (gRPC)
  - Building LLM prompts
  - Submitting to Ray Executor
  - Processing LLM results
  - Creating tasks via Planning Service (gRPC)
- **Task Derivation Service** publishes `task.derivation.completed` or `task.derivation.failed` events
- **Planning Service** validates tasks and manages story lifecycle

---

## 🏗 Hexagonal Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Domain Layer                        │
│  ┌────────────────────────────────────────────────┐  │
│  │  Entities                                      │  │
│  │    Project (Root)                              │  │
│  │    Epic (Groups Stories)                       │  │
│  │    Story (Aggregate Root)                      │  │
│  │    Task (Atomic Work Unit)                     │  │
│  │                                                │  │
│  │  Value Objects                                 │  │
│  │    ProjectId, EpicId, StoryId, TaskId         │  │
│  │    StoryState, DORScore, Title, Brief          │  │
│  │    PlanId (used in events, NOT persisted)      │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
         ↓                       ↑
┌──────────────────────────────────────────────────────┐
│                Application Layer                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  Ports (Interfaces)                            │  │
│  │    StoragePort, MessagingPort                  │  │
│  │                                                │  │
│  │  Use Cases                                     │  │
│  │    Project: CreateProject, GetProject, ListProjects │  │
│  │    Epic: CreateEpic, GetEpic, ListEpics       │  │
│  │    Story: CreateStory, TransitionStory, ListStories │  │
│  │    Task: CreateTask, GetTask, ListTasks        │  │
│  │    Task Derivation: DeriveTasksFromPlan        │  │
│  │    Decision: ApproveDecision, RejectDecision  │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
         ↓                       ↑
┌──────────────────────────────────────────────────────┐
│              Infrastructure Layer                     │
│  ┌────────────────────────────────────────────────┐  │
│  │  Adapters (Implementations)                    │  │
│  │    Neo4jAdapter     - Graph structure          │  │
│  │    ValkeyAdapter    - Permanent details        │  │
│  │    StorageAdapter   - Composite (Neo4j+Valkey) │  │
│  │    NATSAdapter      - Event publishing         │  │
│  │    RayExecutorAdapter - Task derivation (vLLM) │  │
│  │    gRPC Server      - External API             │  │
│  │                                                │  │
│  │  Consumers (Event-Driven)                      │  │
│  │    PlanApprovedConsumer - planning.plan.approved │  │
│  │    TaskDerivationResultConsumer - agent.response.completed │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

---

## 💾 Dual Persistence Pattern

### Why Dual Storage?

**Neo4j (Graph) + Valkey (Details)** provide complementary capabilities:

| Aspect | Neo4j | Valkey |
|--------|-------|--------|
| **Purpose** | Knowledge graph structure | Detailed content storage |
| **Stores** | Nodes (id, state) + Relationships | Full story data (Hash) |
| **Queries** | Graph traversal, rehydration | Fast key-value lookups |
| **Use Cases** | Navigate alternatives, observability | CRUD operations, FSM |
| **Persistence** | Native (always persistent) | AOF + RDB snapshots |

---

### Neo4j: Graph Structure (Observability + Rehydration)

**What it stores**:
```cypher
// Story node (minimal properties)
(:Story {id: "s-uuid", state: "DRAFT"})

// Relationships
(:User {id: "po-001"})-[:CREATED]->(:Story {id: "s-001"})
(:Story {id: "s-001"})-[:HAS_TASK]->(:Task {id: "t-001"})
(:Decision {id: "d-001"})-[:AFFECTS]->(:Task {id: "t-001"})
(:Decision {id: "d-002"})-[:ALTERNATIVE_OF]->(:Decision {id: "d-001"})
```

**Enables**:
1. **Rehydration**: From any node, traverse graph to rebuild context
2. **Alternative Solutions**: Query decisions with `[:ALTERNATIVE_OF]` relationships
3. **Observability**: Visualize complete project graph
4. **Auditing**: Who created what, when, and how

**Example Query** (Rehydrate context from Story X):
```cypher
MATCH (s:Story {id: $story_id})
OPTIONAL MATCH (s)-[:HAS_TASK]->(t:Task)
OPTIONAL MATCH (d:Decision)-[:AFFECTS]->(t)
OPTIONAL MATCH (alt:Decision)-[:ALTERNATIVE_OF]->(d)
RETURN s, collect(DISTINCT t) AS tasks,
       collect(DISTINCT d) AS decisions,
       collect(DISTINCT alt) AS alternatives
```

---

### Valkey: Permanent Details Storage

**What it stores**:
```
// Full story details as Hash (permanent, no TTL)
planning:story:s-001 → Hash {
  story_id: "s-001",
  title: "As a user, I want authentication",
  brief: "Implement JWT with refresh tokens...",
  state: "DRAFT",
  dor_score: "85",
  created_by: "po-001",
  created_at: "2025-11-02T10:00:00Z",
  updated_at: "2025-11-02T11:30:00Z"
}

// FSM state for fast lookups
planning:story:s-001:state → String "DRAFT"

// Indexing sets
planning:stories:all → Set {"s-001", "s-002", "s-003"}
planning:stories:state:DRAFT → Set {"s-001", "s-003"}
planning:stories:state:IN_PROGRESS → Set {"s-002"}
```

**Persistence Configuration** (K8s ConfigMap):
```yaml
# valkey.conf
appendonly yes           # Enable AOF (Append-Only File)
appendfsync everysec     # Sync every second (balance performance/safety)
save 900 1               # RDB snapshot: after 900s if 1 change
save 300 10              # RDB snapshot: after 300s if 10 changes
save 60 10000            # RDB snapshot: after 60s if 10000 changes
```

**Benefits**:
- ✅ Permanent storage (survives pod restarts)
- ✅ Fast reads (in-memory with disk persistence)
- ✅ Efficient indexing (Sets for state filtering)
- ✅ No TTL (data never expires)

---

## 🔄 Data Flow

### Write Path (Create Story)

```
1. Client calls gRPC CreateStory()
   ↓
2. CreateStoryUseCase.execute()
   ↓
3. Create Story entity (domain validation)
   ↓
4. StorageAdapter.save_story()
   ├─→ ValkeyAdapter: Save Hash with all details (permanent)
   └─→ Neo4jAdapter: Create node with (id, state) + CREATED_BY relationship
   ↓
5. NATSAdapter: Publish story.created event
   ↓
6. Return Story to client
```

### Read Path (Get Story)

```
1. Client calls gRPC GetStory(id)
   ↓
2. StorageAdapter.get_story(id)
   ↓
3. ValkeyAdapter: HGETALL planning:story:{id}
   ↓
4. Convert Hash → Story entity
   ↓
5. Return Story to client
```

### Graph Query Path (Rehydration)

```
1. Context Service needs to rehydrate from Story X
   ↓
2. Query Neo4j:
   MATCH (s:Story {id: "s-001"})-[:HAS_TASK]->(t:Task)
   OPTIONAL MATCH (d:Decision)-[:AFFECTS]->(t)
   RETURN s.id, collect(t.id) AS task_ids, collect(d.id) AS decision_ids
   ↓
3. For each ID (task, decision):
   Get details from Valkey: HGETALL planning:task:{id}
   ↓
4. Assemble complete context with relationships
   ↓
5. Return enriched context
```

---

## 🧩 Domain Model

### Hierarchy: Project → Epic → Story → Task

**Business Rule (Domain Invariants)**:
- ✅ **Task MUST belong to a Story** (`task.story_id` is REQUIRED)
- ✅ **Story MUST belong to an Epic** (`story.epic_id` is REQUIRED)
- ✅ **Epic MUST belong to a Project** (`epic.project_id` is REQUIRED)
- ✅ **Project is the root** (no parent)

**Planning Service Responsibility**:
- ✅ Creates and persists all entities in this hierarchy
- ✅ Enforces domain invariants (fail-fast validation)
- ✅ Manages lifecycle of all entities

**Note on Plan (Agile Iteration/Sprint)**:
- ⚠️ **Plan is NOT a persisted entity** in Planning Service
- **Plan = PO's decision on which Stories to work on in the next iteration**
- **Plan = Sprint/Iteration** that contains the User Stories selected by PO
- Plan is created/approved by PO (Product Owner) - human-in-the-loop decision
- Plan information comes from `planning.plan.approved` event (from another service)
- Planning Service uses Plan data from the event to derive Tasks for Stories in the Plan
- In agile context: **Plan (PO's Sprint selection) → Stories → Tasks**
- Plan represents the set of User Stories that PO decided will be executed in the next agile iteration

### Project (Root Entity)

```python
@dataclass(frozen=True)
class Project:
    project_id: ProjectId
    name: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    owner: str = ""
    created_at: datetime  # REQUIRED
    updated_at: datetime  # REQUIRED
```

**Domain Invariants**:
- ✅ Name cannot be empty
- ✅ Project is root (no parent)
- ✅ All dataclasses are frozen (immutable)

### Epic (Groups Stories)

```python
@dataclass(frozen=True)
class Epic:
    epic_id: EpicId
    project_id: ProjectId  # REQUIRED - domain invariant
    title: str
    description: str = ""
    status: EpicStatus = EpicStatus.ACTIVE
    created_at: datetime  # REQUIRED
    updated_at: datetime  # REQUIRED
```

**Domain Invariants**:
- ✅ Title cannot be empty
- ✅ **MUST belong to a Project** (`project_id` is REQUIRED)
- ✅ All dataclasses are frozen (immutable)

### Story (Aggregate Root)

```python
@dataclass(frozen=True)
class Story:
    story_id: StoryId
    epic_id: EpicId  # REQUIRED - domain invariant
    title: Title
    brief: Brief
    state: StoryState        # FSM state
    dor_score: DORScore      # Definition of Ready (0-100)
    created_by: UserName
    created_at: datetime
    updated_at: datetime

    def transition_to(self, target_state: StoryState) -> Story:
        """Immutable state transition (returns new instance)."""
        ...

    def meets_dor_threshold(self) -> bool:
        """Check if DoR score >= 80."""
        return self.dor_score.is_ready()

    def can_be_planned(self) -> bool:
        """Check if story can be planned now (DoR + state check)."""
        return (
            self.meets_dor_threshold()
            and self.state.value == StoryStateEnum.READY_FOR_PLANNING
        )

    def is_planned_or_beyond(self) -> bool:
        """Business rule: DoR >= 80 AND state >= READY_FOR_PLANNING."""
        ...
```

**Domain Invariants** (fail-fast validation):
- ✅ Title and brief cannot be empty
- ✅ **MUST belong to an Epic** (`epic_id` is REQUIRED)
- ✅ State transitions must follow FSM rules
- ✅ DoR score must be 0-100
- ✅ created_at cannot be after updated_at
- ✅ All dataclasses are frozen (immutable)

### Task (Atomic Work Unit)

```python
@dataclass(frozen=True)
class Task:
    task_id: TaskId  # Planning Service generates
    story_id: StoryId  # REQUIRED - domain invariant (Task belongs to Story)
    plan_id: PlanId  # Optional - reference to Plan (Sprint/Iteration) from event
    title: str  # From vLLM
    description: str = ""  # From vLLM
    estimated_hours: int = 0  # From vLLM
    assigned_to: str = ""  # Planning Service assigns (RBAC)
    type: TaskType = TaskType.DEVELOPMENT
    status: TaskStatus = TaskStatus.TODO
    priority: int = 1  # From vLLM
    created_at: datetime  # REQUIRED
    updated_at: datetime  # REQUIRED
```

**Domain Invariants** (fail-fast validation):
- ✅ Title cannot be empty
- ✅ **MUST belong to a Story** (`story_id` is REQUIRED)
- ✅ `plan_id` is optional reference to Plan (Sprint/Iteration) - Plan is NOT persisted in Planning Service
- ✅ estimated_hours cannot be negative
- ✅ priority must be >= 1
- ✅ created_at and updated_at are REQUIRED
- ✅ All dataclasses are frozen (immutable)

**Agile Context**:
- **Plan = PO's decision** on which Stories to work on in the next iteration (Sprint)
- **Plan = Sprint/Iteration** selected by PO (contains multiple Stories)
- **Story** (contains multiple Tasks)
- **Task** belongs to Story, Story belongs to Epic, Epic belongs to Project
- Plan is created/approved by PO (human-in-the-loop) and managed by another service
- Planning Service only references Plan via `plan_id` from events


### FSM (Finite State Machine)

```
Normal Flow:
DRAFT → PO_REVIEW → READY_FOR_PLANNING → PLANNED → READY_FOR_EXECUTION →
IN_PROGRESS → CODE_REVIEW → TESTING → READY_TO_REVIEW → ACCEPTED → DONE → ARCHIVED

Sprint Closure:
READY_FOR_EXECUTION/IN_PROGRESS/CODE_REVIEW/TESTING/READY_TO_REVIEW → CARRY_OVER →
[DRAFT | READY_FOR_EXECUTION | ARCHIVED]

Note: PLANNED is NOT carried over (tasks derived but not committed to sprint)

States Explained:
- DRAFT: Story created, initial state
- PO_REVIEW: Awaiting Product Owner review and approval for scope
- READY_FOR_PLANNING: PO approved scope, ready for task derivation
- PLANNED: Tasks have been derived (story→tasks decomposition done)
- READY_FOR_EXECUTION: Tasks assigned and queued, waiting for agent pickup
- IN_PROGRESS: Agent actively executing tasks
- CODE_REVIEW: Technical code review by architect/peer agents
- TESTING: Automated testing and validation phase
- READY_TO_REVIEW: Tests passed, awaiting final PO/QA examination
- ACCEPTED: PO/QA accepted the work (story functionally complete, sprint ongoing)
- CARRY_OVER: Sprint ended with story incomplete, requires reevaluation and re-estimation
- DONE: Sprint/agile cycle finished (formal closure, story closed)
- ARCHIVED: Story archived (terminal state)

Sprint Closure Handling:
- Stories in ACCEPTED → transition to DONE when sprint ends (normal completion)
- Stories committed to sprint (READY_FOR_EXECUTION, IN_PROGRESS, CODE_REVIEW,
  TESTING, READY_TO_REVIEW) → transition to CARRY_OVER when sprint ends (incomplete work)
- Stories NOT committed yet (DRAFT, PO_REVIEW, READY_FOR_PLANNING, PLANNED) →
  stay in current state (not affected by sprint closure)
- From CARRY_OVER, PO decides:
  * CARRY_OVER → DRAFT: Reevaluate requirements, repuntuar DoR score
  * CARRY_OVER → READY_FOR_EXECUTION: Continue as-is in next sprint
  * CARRY_OVER → ARCHIVED: Cancel/deprioritize story

Alternative flows:
- Any state → DRAFT (reset/restart)
- PO_REVIEW → DRAFT (scope rejection by PO)
- CODE_REVIEW → IN_PROGRESS (code rejected, rework needed)
- TESTING → IN_PROGRESS (tests failed, rework needed)
- READY_TO_REVIEW → IN_PROGRESS (PO/QA rejected final result, rework needed)
```

---

## 📡 Integration

### Consumes (NATS Events)

| Event | Subject | Purpose | Handler |
|-------|---------|---------|---------|
| **plan.approved** | `planning.plan.approved` | Trigger task derivation | `PlanApprovedConsumer` |
| **agent.response.completed** | `agent.response.completed` | Process task derivation results from vLLM | `TaskDerivationResultConsumer` |

**Note**: Planning Service consumes events for task derivation workflow (vLLM creates tasks, Planning stores them).

### Produces (NATS Events)

| Event | Subject | Payload | Consumer |
|-------|---------|---------|----------|
| **story.created** | `planning.story.created` | {story_id, title, created_by} | Orchestrator, Context |
| **story.transitioned** | `planning.story.transitioned` | {story_id, from_state, to_state} | Orchestrator, Context |
| **story.tasks_not_ready** | `planning.story.tasks_not_ready` | {story_id, reason, task_ids_without_priority, total_tasks} | PO-UI (human-in-the-loop) |
| **task.created** | `planning.task.created` | {task_id, story_id, plan_id, ...} | Orchestrator, Context |
| **tasks.derived** | `planning.tasks.derived` | {plan_id, task_count, timestamp} | Monitoring |
| **task.derivation.failed** | `planning.task.derivation.failed` | {plan_id, reason, requires_manual_review} | PO-UI |
| **decision.approved** | `planning.decision.approved` | {story_id, decision_id, approved_by} | Orchestrator (triggers execution) |
| **decision.rejected** | `planning.decision.rejected` | {story_id, decision_id, reason} | Orchestrator (triggers re-deliberation) |

---

## 🔌 External Dependencies

- **Neo4j**: Graph database (bolt://neo4j:7687)
- **Valkey**: Permanent storage (redis://valkey:6379)
- **NATS JetStream**: Event streaming (nats://nats:4222)

**Dependencies**:
- **Ray Executor Service** (gRPC): For task derivation (vLLM execution)
  - Planning Service sends Plan to Ray Executor
  - Ray Executor executes vLLM and generates tasks
  - Results come back via NATS (`agent.response.completed`)

**No dependencies on other bounded contexts** (core/context, core/memory, etc.)

---

## ✅ DDD Compliance Checklist

- ✅ **No reflection** (`setattr`, `object.__setattr__`, `__dict__`)
- ✅ **No dynamic mutation** (all dataclasses frozen)
- ✅ **Fail-fast validation** (ValueError in `__post_init__`)
- ✅ **No to_dict/from_dict in domain** (mappers in infrastructure)
- ✅ **Dependency injection** (use cases receive ports via constructor)
- ✅ **Immutability** (builder methods return new instances)
- ✅ **Type hints complete** (all functions, methods, parameters)
- ✅ **Layer boundaries respected** (domain → application → infrastructure)
- ✅ **Bounded context isolation** (no imports from core/*)

---

## 🔄 Task Derivation Delegation

**MIGRATED TO TASK DERIVATION SERVICE** (see `services/task-derivation/README.md` for full flow)

Planning Service's role is now simplified:

1. **PlanApprovedConsumer** listens to `planning.plan.approved`
2. **RequestTaskDerivationUseCase** publishes `task.derivation.requested` event
3. **Task Derivation Service** (separate microservice) handles the entire derivation workflow
4. Planning Service listens for `task.derivation.completed` or `task.derivation.failed` events
5. Tasks are created via gRPC calls from Task Derivation Service back to Planning Service

**Benefits of separation**:
- ✅ Single Responsibility Principle (Planning = lifecycle, Task Derivation = LLM integration)
- ✅ Independent scaling (Task Derivation Service can scale with GPU cluster)
- ✅ Clear event contracts between services
- ✅ Easier testing and maintenance

---

**Planning Service Architecture** - Following SWE AI Fleet architectural principles

