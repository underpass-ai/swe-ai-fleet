# Planning Service - Architecture

**Bounded Context**: Planning  
**Pattern**: DDD + Hexagonal Architecture  
**Version**: v0.1.0

---

## 🎯 Responsibility

Manage user story lifecycle with FSM (Finite State Machine) and decision approval workflow.

**Core Responsibilities**:
1. Create and manage user stories
2. FSM state transitions (DRAFT → PO_REVIEW → READY → IN_PROGRESS → DONE)
3. Decision approval/rejection workflow (PO human-in-the-loop)
4. Publish domain events for orchestrator integration

---

## 🏗 Hexagonal Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Domain Layer                        │
│  ┌────────────────────────────────────────────────┐  │
│  │  Entities                                      │  │
│  │    Story (Aggregate Root)                      │  │
│  │                                                │  │
│  │  Value Objects                                 │  │
│  │    StoryId, StoryState, DORScore               │  │
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
│  │    CreateStory, TransitionStory, ListStories   │  │
│  │    ApproveDecision, RejectDecision             │  │
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
│  │    gRPC Server      - External API             │  │
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

### Story (Aggregate Root)

```python
@dataclass(frozen=True)
class Story:
    story_id: StoryId
    title: str
    brief: str
    state: StoryState        # FSM state
    dor_score: DORScore      # Definition of Ready (0-100)
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    def transition_to(self, target_state: StoryState) -> Story:
        """Immutable state transition (returns new instance)."""
        ...
    
    def is_ready_for_planning(self) -> bool:
        """Business rule: DoR >= 80 AND state >= READY_FOR_PLANNING."""
        ...
```

**Domain Invariants** (fail-fast validation):
- ✅ Title and brief cannot be empty
- ✅ State transitions must follow FSM rules
- ✅ DoR score must be 0-100
- ✅ created_at cannot be after updated_at
- ✅ All dataclasses are frozen (immutable)

### FSM (Finite State Machine)

```
DRAFT → PO_REVIEW → READY_FOR_PLANNING → IN_PROGRESS →
CODE_REVIEW → TESTING → DONE → ARCHIVED

Alternative flows:
- Any state → DRAFT (reset)
- PO_REVIEW → DRAFT (rejection)
- TESTING → IN_PROGRESS (rework)
- CODE_REVIEW → IN_PROGRESS (rework)
```

---

## 📡 Integration

### Consumes (NATS Events)
**None** - Planning Service is a producer, not a consumer

### Produces (NATS Events)

| Event | Subject | Payload | Consumer |
|-------|---------|---------|----------|
| **story.created** | `planning.story.created` | {story_id, title, created_by} | Orchestrator, Context |
| **story.transitioned** | `planning.story.transitioned` | {story_id, from_state, to_state} | Orchestrator, Context |
| **decision.approved** | `planning.decision.approved` | {story_id, decision_id, approved_by} | Orchestrator (triggers execution) |
| **decision.rejected** | `planning.decision.rejected` | {story_id, decision_id, reason} | Orchestrator (triggers re-deliberation) |

---

## 🔌 External Dependencies

- **Neo4j**: Graph database (bolt://neo4j:7687)
- **Valkey**: Permanent storage (redis://valkey:6379)
- **NATS JetStream**: Event streaming (nats://nats:4222)

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

**Planning Service Architecture** - Following SWE AI Fleet architectural principles

