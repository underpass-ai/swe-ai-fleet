# Planning Service

**User Story Management with FSM and Decision Approval Workflow**

---

## 🎯 Purpose

Planning Service manages the lifecycle of user stories in the SWE AI Fleet platform. It implements a Finite State Machine (FSM) for story states and provides approval/rejection workflow for Product Owner decision-making.

---

## 🏗 Architecture

**Pattern**: DDD (Domain-Driven Design) + Hexagonal Architecture

```
planning/
├── domain/               # Core business logic
│   ├── entities/
│   │   └── story.py     # Story (Aggregate Root)
│   └── value_objects/
│       ├── story_id.py
│       ├── story_state.py  # FSM states
│       └── dor_score.py    # Definition of Ready score
├── application/          # Use cases and ports
│   ├── ports/
│   │   ├── storage_port.py    # Dual persistence interface
│   │   └── messaging_port.py  # NATS events
│   └── usecases/
│       ├── create_story_usecase.py
│       ├── transition_story_usecase.py
│       ├── list_stories_usecase.py
│       ├── approve_decision_usecase.py
│       └── reject_decision_usecase.py
└── infrastructure/       # Adapters
    └── adapters/
        ├── dual_storage_adapter.py   # Neo4j + Valkey
        └── nats_messaging_adapter.py # NATS JetStream
```

---

## 📊 FSM (Finite State Machine)

```
DRAFT → PO_REVIEW → READY_FOR_PLANNING → PLANNED → READY_FOR_EXECUTION →
IN_PROGRESS → CODE_REVIEW → TESTING → READY_TO_REVIEW → ACCEPTED → DONE → ARCHIVED

States:
- DRAFT: Initial state (story created)
- PO_REVIEW: Awaiting PO approval for scope
- READY_FOR_PLANNING: Approved, ready for task derivation
- PLANNED: Tasks derived and assigned
- READY_FOR_EXECUTION: Queued for execution, waiting for agent pickup
- IN_PROGRESS: Agent actively executing
- CODE_REVIEW: Technical code review by architect/peer agents
- TESTING: Automated testing phase
- READY_TO_REVIEW: Tests passed, awaiting final PO/QA examination
- ACCEPTED: PO/QA accepted the work (story functionally complete)
- CARRY_OVER: Sprint ended incomplete, needs reevaluation and re-estimation
- DONE: Sprint/agile cycle finished (formal closure)
- ARCHIVED: Archived (terminal state)

Sprint Closure Flows:
- ACCEPTED → DONE (normal completion when sprint ends)
- READY_FOR_EXECUTION/IN_PROGRESS/CODE_REVIEW/TESTING/READY_TO_REVIEW → CARRY_OVER
  (incomplete when sprint ends)

Note: PLANNED stories are NOT carried over (not yet in sprint backlog)

Carry-Over Resolution:
- CARRY_OVER → DRAFT (PO reevaluates and repuntuates DoR score)
- CARRY_OVER → READY_FOR_EXECUTION (continue as-is in next sprint)
- CARRY_OVER → ARCHIVED (PO cancels story)

Rework Flows:
- Any state → DRAFT (reset)
- PO_REVIEW → DRAFT (scope rejection)
- CODE_REVIEW → IN_PROGRESS (code rejected, rework)
- TESTING → IN_PROGRESS (tests failed, rework)
- READY_TO_REVIEW → IN_PROGRESS (PO/QA rejected final result, rework)
```

---

## 🔌 APIs

### gRPC (planning.proto)

```protobuf
service PlanningService {
  rpc CreateStory(CreateStoryRequest) returns (CreateStoryResponse);
  rpc ListStories(ListStoriesRequest) returns (ListStoriesResponse);
  rpc TransitionStory(TransitionStoryRequest) returns (TransitionStoryResponse);
  rpc ApproveDecision(ApproveDecisionRequest) returns (ApproveDecisionResponse);
  rpc RejectDecision(RejectDecisionRequest) returns (RejectDecisionResponse);
  rpc GetStory(GetStoryRequest) returns (Story);
}
```

**Port**: 50054

---

## 💾 Persistence Strategy (Dual)

### Neo4j (Graph Database - Knowledge Structure)
- **Purpose**: Graph structure, relationships, observability
- **Stores**:
  - Story nodes with minimal properties (id, state)
  - Relationships: CREATED_BY, HAS_TASK, etc.
  - Enables rehydration from specific node
  - Supports alternative solutions queries
- **Queries**: Graph navigation, relationship traversal

### Valkey (Permanent Storage - Content Details)
- **Purpose**: Detailed content storage (permanent, not cache)
- **Stores**:
  - Story details (title, brief, timestamps, etc.) as Hashes
  - FSM state for fast lookups
  - Sets for indexing (by state, all stories)
- **Persistence**: AOF + RDB (survives pod restarts)
- **TTL**: None (permanent storage)

### Data Flow

**Write Path**:
```
Story Created
    ↓
1. Save details to Valkey Hash (permanent)
2. Create node in Neo4j Graph (structure)
    ↓
Both stores updated
```

**Read Path**:
```
Get Story
    ↓
Retrieve from Valkey (has all details)
```

**Graph Query Path**:
```
Rehydrate Context from Story X
    ↓
Neo4j: Get Story node + relationships (tasks, decisions, alternatives)
    ↓
For each related ID: Retrieve details from Valkey
```

---

## 📡 Events Published (NATS)

| Event | Subject | Consumers |
|-------|---------|-----------|
| **story.created** | `planning.story.created` | Orchestrator, Context, Monitoring |
| **story.transitioned** | `planning.story.transitioned` | Orchestrator, Context |
| **decision.approved** | `planning.decision.approved` | Orchestrator (triggers execution) |
| **decision.rejected** | `planning.decision.rejected` | Orchestrator (triggers re-deliberation) |

---

## 🧪 Testing

### Unit Tests
```bash
pytest tests/unit/ -v --cov=planning
```

**Coverage target**: >90%

**Tests**:
- Domain layer (entities + value objects): 100% coverage
- Application layer (use cases): >90% coverage
- All tests use mocks (no real infrastructure)

### Integration Tests
```bash
pytest tests/integration/ -v -m integration
```

**Requirements**:
- Neo4j running on localhost:7687
- Valkey/Redis running on localhost:6379
- NATS running on localhost:4222

---

## 🚀 Running Locally

### 1. Install dependencies
```bash
cd services/planning
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ../../  # Install core dependencies
```

### 2. Generate gRPC code
```bash
# From services/planning/
make generate-grpc

# Or manually:
cd services/planning
python -m grpc_tools.protoc \
  -I../../specs/fleet/planning/v2 \
  --python_out=planning/gen \
  --pyi_out=planning/gen \
  --grpc_python_out=planning/gen \
  ../../specs/fleet/planning/v2/planning.proto

# Fix imports
sed -i 's/^import planning_pb2/from . import planning_pb2/' \
  planning/gen/planning_pb2_grpc.py
```

**Note**: Generated files are NOT committed to git. They are generated:
- During Docker build (in container)
- By `scripts/test/unit.sh` (for local tests)
- Manually with `make generate-grpc` (for development)

**Proto version**: v2 (`specs/fleet/planning/v2/planning.proto`)

### 3. Set environment variables
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password"
export VALKEY_HOST="localhost"
export VALKEY_PORT="6379"
export NATS_URL="nats://localhost:4222"
export GRPC_PORT="50054"
```

### 4. Configure Valkey for persistence
```bash
# valkey.conf
appendonly yes
appendfsync everysec
save 900 1
save 300 10
save 60 10000
```

This ensures data survives restarts (permanent storage, not cache).

### 5. Run server
```bash
python server.py
```

---

## 🐳 Docker

### Build
```bash
# From services/planning/
podman build -t registry.underpassai.com/swe-ai-fleet/planning:v0.1.0 .
```

### Run
```bash
podman run -d \
  --name planning-service \
  -p 50054:50054 \
  -e NEO4J_URI="bolt://neo4j:7687" \
  -e NEO4J_USER="neo4j" \
  -e NEO4J_PASSWORD="password" \
  -e VALKEY_HOST="valkey" \
  -e VALKEY_PORT="6379" \
  -e NATS_URL="nats://nats:4222" \
  registry.underpassai.com/swe-ai-fleet/planning:v0.1.0
```

---

## ☸️ Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: planning-service
  namespace: swe-ai-fleet
spec:
  replicas: 2
  selector:
    matchLabels:
      app: planning-service
  template:
    metadata:
      labels:
        app: planning-service
    spec:
      containers:
      - name: planning
        image: registry.underpassai.com/swe-ai-fleet/planning:v0.1.0
        ports:
        - containerPort: 50054
          name: grpc
        env:
        - name: NEO4J_URI
          value: "bolt://neo4j:7687"
        - name: NEO4J_USER
          value: "neo4j"
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: neo4j-credentials
              key: password
        - name: VALKEY_HOST
          value: "valkey"
        - name: VALKEY_PORT
          value: "6379"
        - name: NATS_URL
          value: "nats://nats:4222"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: internal-planning
  namespace: swe-ai-fleet
spec:
  selector:
    app: planning-service
  ports:
  - port: 50054
    targetPort: 50054
    protocol: TCP
    name: grpc
  type: ClusterIP
```

---

## 📋 Domain Model

### Story (Aggregate Root)
- `story_id`: Unique identifier (UUID)
- `title`: User story title
- `brief`: Description + acceptance criteria
- `state`: Current FSM state
- `dor_score`: Definition of Ready score (0-100)
- `created_by`: User who created the story
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Business Rules
- Story starts in DRAFT state
- Initial DoR score is 0
- State transitions follow FSM rules
- DoR >= 80 required for READY_FOR_PLANNING state
- Title and brief cannot be empty
- All dataclasses are frozen (immutable)

---

## 🧪 Quality Gates

- ✅ Unit test coverage: >90%
- ✅ Integration tests: Pass
- ✅ No reflection or dynamic mutation
- ✅ All dataclasses frozen
- ✅ Fail-fast validation
- ✅ Type hints complete
- ✅ Linter errors: 0 (Ruff)

---

## 📚 Related Services

- **Context Service**: Manages context and decision graph
- **Orchestrator**: Consumes story events, triggers deliberation
- **API Gateway**: REST→gRPC translation for UI
- **Monitoring**: Tracks story lifecycle metrics

---

## 🔧 Development

### Run tests
```bash
# Unit tests only
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=planning --cov-report=html

# Integration tests (requires infrastructure)
pytest tests/integration/ -v -m integration

# All tests
pytest -v
```

### Lint
```bash
ruff check . --fix
```

---

**Planning Service v0.1.0** - Part of SWE AI Fleet

