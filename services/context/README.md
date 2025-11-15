# Context Service - Complete Documentation

**Version**: v1.0.0
**Status**: ✅ Production Ready
**Pattern**: DDD + Hexagonal Architecture (Ports & Adapters)
**Language**: Python 3.13
**Last Updated**: November 15, 2025

---

## 📋 Executive Summary

**Context Service** is the knowledge rehydration engine of the SWE AI Fleet platform. It provides rich, role-specific context for AI agents through dynamic prompt assembly. Given a story, role, and phase, it rehydrates historical decisions, tasks, alternative solutions, and code quality metrics into a compact, optimized prompt suitable for LLM consumption (200 tokens target).

**Core Purpose:**
- 🧠 Rehydrate context from Neo4j graph (decisions, tasks, alternatives)
- 📊 Calculate token budgets and respect prompt scope policies
- 🎯 Assemble role-specific prompts dynamically
- 💾 Cache and optimize context delivery
- 🔗 Integrate Planning, Orchestrator, and decision data
- 🛡️ Maintain immutability and fail-fast validation

---

## 📚 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Responsibility Matrix](#responsibility-matrix)
3. [Architecture Overview](#architecture-overview)
4. [Domain Model](#domain-model)
5. [Context Rehydration Flow](#context-rehydration-flow)
6. [Prompt Scope Policies](#prompt-scope-policies)
7. [API Reference](#api-reference)
8. [Event Integration](#event-integration)
9. [External Dependencies](#external-dependencies)
10. [Token Budget Strategy](#token-budget-strategy)
11. [Architectural Principles](#architectural-principles)
12. [Testing & Coverage](#testing--coverage)
13. [Getting Started](#getting-started)
14. [Monitoring & Observability](#monitoring--observability)
15. [Troubleshooting](#troubleshooting)

---

## 🎯 Responsibility Matrix

### What This Service DOES ✅

| Responsibility | Mechanism |
|---|---|
| **Rehydrate context from graph** | Query Neo4j for decisions, tasks, alternatives |
| **Calculate token budgets** | Estimate tokens based on role/phase |
| **Assemble prompts dynamically** | Build role-specific, phase-aware prompts |
| **Optimize for LLM consumption** | Target ~200 tokens for agent reasoning |
| **Track decision history** | Access decision graph with alternatives |
| **Provide role-specific views** | Different data for DEV, QA, ARCHITECT, etc. |
| **Cache rehydration results** | Redis-backed caching for performance |
| **Publish context updates** | NATS events when context changes |
| **Report service health** | gRPC `GetStatus()` RPC |

### What This Service DOES NOT ✅

| Non-Responsibility | Owner |
|---|---|
| ❌ Store context permanently | Neo4j (via Planning Service) |
| ❌ Execute tasks or deliberations | Orchestrator Service |
| ❌ Generate tasks from stories | Task Derivation Service |
| ❌ Authenticate users | API Gateway |
| ❌ Route requests | Load Balancer |

---

## 🏗️ Architecture Overview

### Layered Design (DDD + Hexagonal)

```
┌──────────────────────────────────────────────────────┐
│                   Domain Layer                        │
│  • RehydrationRequest (immutable request VO)          │
│  • PromptScopePolicy (role/phase-based policies)      │
│  • TokenBudgetCalculator (token estimation)           │
│  • Pure rehydration logic, zero infrastructure        │
└──────────────────────────────────────────────────────┘
         ↓                                    ↑
┌──────────────────────────────────────────────────────┐
│                Application Layer                      │
│  • SessionRehydrationApplicationService               │
│  • ProjectStory, ProjectTask, ProjectDecision UseCases │
│  • OrchestrationEventsConsumer                        │
│  • Ports for Neo4j, Redis, gRPC                       │
└──────────────────────────────────────────────────────┘
         ↓                                    ↑
┌──────────────────────────────────────────────────────┐
│              Infrastructure Layer                     │
│  • Neo4jQueryStore (read-only graph queries)          │
│  • Neo4jCommandStore (graph updates)                  │
│  • RedisStore (context caching)                       │
│  • RedisPlanningReadAdapter (planning data)           │
│  • gRPC Server + NATS consumers                       │
└──────────────────────────────────────────────────────┘
```

### Directory Structure

```
services/context/
├── server.py                            # gRPC server entrypoint
├── nats_handler.py                      # NATS event handler
├── streams_init.py                      # NATS stream initialization
├── consumers/                           # Event consumers
│   ├── __init__.py
│   ├── orchestration_events_consumer.py # Listen: orchestration.>
│   └── planning/
│       ├── epic_created_consumer.py     # Listen: planning.epic.created
│       ├── project_created_consumer.py  # Listen: planning.project.created
│       ├── story_created_consumer.py    # Listen: planning.story.created
│       ├── story_transitioned_consumer.py
│       ├── task_created_consumer.py     # Listen: planning.task.created
│       └── plan_approved_consumer.py    # Listen: planning.plan.approved
├── handlers/                            # gRPC handlers
│   ├── __init__.py
│   └── (generated during build)
├── infrastructure/
│   ├── mappers/
│   │   └── rehydration_protobuf_mapper.py # VO ↔ protobuf conversion
│   └── dto/                             # Infrastructure DTOs
├── tests/                               # Unit + integration tests
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── gen/                                 # Generated gRPC (not in git)
├── requirements.txt
├── Dockerfile                           # Multi-stage build
├── .dockerignore
└── README.md                            # THIS FILE
```

---

## 🧩 Domain Model

### Value Objects (All Immutable)

#### RehydrationRequest

```python
@dataclass(frozen=True)
class RehydrationRequest:
    story_id: str                       # Story identifier
    role: str                           # Agent role (DEV, QA, ARCHITECT, etc.)
    phase: str                          # Execution phase (PLAN, EXECUTE, REVIEW)
    token_budget: int = 200             # Target token count
```

**Domain Invariants**:
- ✅ story_id cannot be empty
- ✅ role must be valid (predefined set)
- ✅ phase must be valid (PLAN, EXECUTE, REVIEW, etc.)
- ✅ token_budget must be > 0
- ✅ Immutable (frozen)

#### PromptScopePolicy

```python
@dataclass(frozen=True)
class PromptScopePolicy:
    role: str                           # Agent role
    phase: str                          # Execution phase
    include_decisions: bool             # Include decision history
    include_alternatives: bool          # Include alternative solutions
    include_metrics: bool               # Include code quality metrics
    max_tokens: int                     # Maximum tokens allowed
```

---

## 🔄 Context Rehydration Flow

### Complete Rehydration Sequence

```
1. Client calls gRPC GetContext(story_id, role, phase)
   ↓
2. ContextServiceServicer receives request
   ├─ Convert protobuf → RehydrationRequest VO
   └─ Validate role and phase
   ↓
3. SessionRehydrationApplicationService.rehydrate()
   ├─ Look up PromptScopePolicy for (role, phase)
   ├─ Calculate TokenBudget based on scope
   └─ Delegate to data retrieval
   ↓
4. Neo4jQueryStore queries graph:
   MATCH (s:Story {id: $story_id})
   OPTIONAL MATCH (s)-[:HAS_TASK]->(t:Task)
   OPTIONAL MATCH (d:Decision)-[:AFFECTS]->(t)
   OPTIONAL MATCH (alt:Decision)-[:ALTERNATIVE_OF]->(d)
   RETURN s, collect(t) as tasks, collect(d) as decisions,
           collect(alt) as alternatives
   ↓
5. RedisPlanningReadAdapter enriches with:
   ├─ Full story details (title, brief, description)
   ├─ Task descriptions and estimates
   └─ Decision rationale and scores
   ↓
6. TokenBudgetCalculator estimates:
   ├─ Decisions: ~20 tokens each
   ├─ Tasks: ~15 tokens each
   ├─ Alternatives: ~10 tokens each
   └─ Total: respect ~200 token target
   ↓
7. PromptBlockAssembler builds output:
   ├─ Story context block
   ├─ Task list block
   ├─ Decision history block (if applicable)
   ├─ Code metrics block (if applicable)
   └─ Alternative solutions block (if applicable)
   ↓
8. Cache result in Redis:
   context:{story_id}:{role}:{phase} → JSON payload (TTL: 1 hour)
   ↓
9. Return GetContextResponse to client
   ├─ formatted_context: ~200 tokens of assembled blocks
   ├─ token_count: actual token count
   ├─ scope: which blocks were included
   ├─ cached: whether result came from cache
   └─ timestamp: when context was generated
```

---

## 📊 Prompt Scope Policies

### Role-Based Scopes (config/prompt_scopes.yaml)

```yaml
phases:
  PLAN:
    DEV:
      scope_blocks:
        - story_context
        - existing_tasks
        - recent_decisions
      max_tokens: 200
    QA:
      scope_blocks:
        - story_context
        - test_requirements
        - quality_metrics
      max_tokens: 200
    ARCHITECT:
      scope_blocks:
        - story_context
        - all_decisions
        - alternatives
        - quality_metrics
      max_tokens: 250
  EXECUTE:
    DEV:
      scope_blocks:
        - task_details
        - dependencies
        - recent_context
      max_tokens: 150
    QA:
      scope_blocks:
        - test_plan
        - code_coverage
        - quality_criteria
      max_tokens: 150
  REVIEW:
    ARCHITECT:
      scope_blocks:
        - implementation_summary
        - decisions_made
        - alternatives_considered
        - metrics
      max_tokens: 300
```

---

## 📡 API Reference

### gRPC Services

**Port**: 50054 (internal-context:50054)
**Proto Spec**: See `specs/fleet/context/v1/context.proto`

#### GetContext

```protobuf
rpc GetContext(GetContextRequest) returns (GetContextResponse)

message GetContextRequest {
  string story_id = 1;            # Story identifier
  string role = 2;                # Agent role
  string phase = 3;               # Execution phase (optional, defaults to PLAN)
  int32 token_budget = 4;         # Target tokens (optional, defaults to 200)
}

message GetContextResponse {
  string formatted_context = 1;   # Assembled prompt blocks (~200 tokens)
  int32 token_count = 2;          # Actual token count
  string scope = 3;               # Scope applied (JSON with included blocks)
  bool cached = 4;                # Whether from cache
  int64 timestamp = 5;            # Generation timestamp (Unix)
}
```

#### GetStatus

```protobuf
rpc GetStatus(GetStatusRequest) returns (GetStatusResponse)

message GetStatusResponse {
  string status = 1;              # "healthy", "degraded", "unhealthy"
  map<string, string> info = 2;   # Service info (version, uptime, etc.)
}
```

---

## 📡 Event Integration

### NATS Event Consumers

**Purpose**: Subscribe to Planning Service events and maintain Neo4j graph

| Consumer | Topic | Purpose | Handlers |
|----------|-------|---------|----------|
| **ProjectCreatedConsumer** | `planning.project.created` | Create project node | Neo4jCommandStore |
| **EpicCreatedConsumer** | `planning.epic.created` | Create epic node | Neo4jCommandStore |
| **StoryCreatedConsumer** | `planning.story.created` | Create story node | Neo4jCommandStore |
| **TaskCreatedConsumer** | `planning.task.created` | Create task node, relationships | Neo4jCommandStore |
| **StoryTransitionedConsumer** | `planning.story.transitioned` | Update story state | Neo4jCommandStore |
| **PlanApprovedConsumer** | `planning.plan.approved` | Create plan node | Neo4jCommandStore |
| **OrchestrationEventsConsumer** | `orchestration.deliberation.>` | Track deliberation decisions | Neo4jCommandStore |

### Published Events

| Event | Topic | Purpose | Consumers |
|-------|-------|---------|-----------|
| **context.updated** | `context.updated` | Context cache invalidated | Task Derivation, Orchestrator |

---

## 🔌 External Dependencies

### Neo4j Graph Database
- **Address**: bolt://neo4j:7687
- **Purpose**: Persistent knowledge graph (stories, tasks, decisions, alternatives)
- **Adapter**: `Neo4jQueryStore` + `Neo4jCommandStore`
- **Role**: Primary data source for rehydration

### Redis Cache
- **Address**: redis://redis:6379
- **Purpose**: Fast context caching (1-hour TTL)
- **Adapter**: `RedisStore`
- **Keys**: `context:{story_id}:{role}:{phase}`

### NATS JetStream
- **Address**: nats://nats.swe-ai-fleet.svc.cluster.local:4222
- **Purpose**: Event subscriptions (Planning, Orchestrator events)
- **Consumers**: 7 event consumers listening to planning.> and orchestration.>

### Planning Service
- **Interaction**: Via Redis `RedisPlanningReadAdapter`
- **Purpose**: Access story details, task descriptions
- **No gRPC**: Read-only access to Planning's Redis cache

---

## 🛡️ Architectural Principles

### 1. **Immutability & Fail-Fast**
- All VOs are `@dataclass(frozen=True)`
- Validation in `__post_init__` (throws immediately)
- No silent defaults

### 2. **No Reflection / No Dynamic Mutation**
- ❌ NO `getattr()`, `setattr()`, `__dict__`
- ✅ Direct attribute access
- ✅ Explicit VO validation

### 3. **Separation of Concerns**
- **Domain**: Pure rehydration logic (token calc, scope policies)
- **Application**: Context assembly orchestration
- **Infrastructure**: Neo4j queries, Redis caching, NATS events

### 4. **Read-Optimized**
- Neo4j for graph traversal (rehydration)
- Redis for caching (performance)
- NATS for event updates (eventual consistency)

### 5. **Token Budget Awareness**
- Respect ~200 token target for LLM prompts
- Scope policies control inclusion
- TokenBudgetCalculator estimates actual tokens

---

## 🧪 Testing & Coverage

### Test Organization

```
tests/
├── unit/                                # Fast, <5 seconds
│   ├── test_rehydration_service.py     # Context assembly logic
│   ├── test_token_budget_calculator.py # Token estimation
│   ├── test_prompt_scope_policy.py     # Scope validation
│   └── test_value_objects.py           # VO validation
├── integration/                         # With Neo4j + Redis
│   ├── test_neo4j_query_store.py
│   ├── test_redis_store.py
│   └── test_nats_consumers.py
└── e2e/                                 # Full system
    └── test_context_rehydration_e2e.py
```

### Running Tests

```bash
# Unit tests (fast)
make test-unit

# Integration tests (requires Neo4j + Redis)
bash scripts/test/integration.sh

# E2E tests (full system)
bash scripts/test/e2e.sh

# Coverage report
bash scripts/test/coverage.sh
```

### Coverage Targets

| Layer | Target | Current | Status |
|-------|--------|---------|--------|
| **Domain** | 100% | 100% | ✅ |
| **Application** | 95%+ | 95% | ✅ |
| **Infrastructure** | 85%+ | 85% | ✅ |
| **Overall** | 90% | >90% | ✅ |

---

## 🚀 Getting Started

### Prerequisites

```bash
# Python 3.13
# Neo4j running (bolt://neo4j:7687)
# Redis running (redis://redis:6379)
# NATS JetStream running

# Activate venv
source .venv/bin/activate

# Install dependencies
cd services/context
pip install -e .
```

### Configuration (Environment Variables)

```bash
# Required
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
REDIS_HOST=redis
REDIS_PORT=6379
NATS_URL=nats://nats:4222

# Optional
CONTEXT_PORT=50054                      # gRPC port
LOG_LEVEL=INFO                          # Logging level
CONTEXT_CACHE_TTL=3600                  # Cache TTL in seconds
TOKEN_BUDGET=200                        # Default token budget
```

### Running Locally

```bash
# Generate gRPC code
bash scripts/test/_generate_protos.sh

# Run tests
make test-unit

# Run server
python services/context/server.py
```

### Deployment to Kubernetes

```bash
# Build image
podman build -t registry.underpassai.com/swe-fleet/context:v1.0.0 \
  -f services/context/Dockerfile .

# Push to registry
podman push registry.underpassai.com/swe-fleet/context:v1.0.0

# Deploy
kubectl apply -f deploy/k8s-integration/

# Verify
kubectl get pods -n swe-ai-fleet -l app=context
```

---

## 📊 Monitoring & Observability

### View Logs

```bash
kubectl logs -n swe-ai-fleet -l app=context -f
```

### Check Service Health

```bash
grpcurl -plaintext context.swe-ai-fleet.svc.cluster.local:50054 \
  context.v1.ContextService/GetStatus
```

### Query Context

```bash
grpcurl -plaintext -d '{
  "story_id": "story-001",
  "role": "DEV",
  "phase": "PLAN"
}' \
  context.swe-ai-fleet.svc.cluster.local:50054 \
  context.v1.ContextService/GetContext
```

### Monitor Cache Hit Rate

```bash
# Check Redis cache size
redis-cli --latency-history

# Monitor NATS consumer lag
nats consumer info swe-ai-fleet planning_consumer
```

---

## 🔍 Troubleshooting

### Issue: "Context not found"
```
❌ Error: No context found for story story-001
```
**Solution**:
1. Verify story exists in Neo4j
2. Check Planning Service has published `planning.story.created` event
3. Verify consumers are subscribed to NATS streams

### Issue: "Neo4j connection failed"
```
❌ Error: Failed to connect to Neo4j bolt://neo4j:7687
```
**Solution**:
1. Check `NEO4J_URI` environment variable
2. Verify Neo4j is running
3. Check network connectivity

### Issue: "Redis connection failed"
```
❌ Error: Failed to connect to Redis redis:6379
```
**Solution**:
1. Check `REDIS_HOST` and `REDIS_PORT`
2. Verify Redis is running
3. Check network connectivity

### Issue: "Token count exceeds budget"
```
⚠️  Warning: Generated 250 tokens > budget 200
```
**Solution**:
1. Reduce scope blocks in `prompt_scopes.yaml`
2. Increase token budget
3. Check TokenBudgetCalculator estimation accuracy

---

## ✅ Compliance Checklist

### DDD Principles ✅
- ✅ Value Objects with immutability
- ✅ Domain logic in SessionRehydrationService
- ✅ No infrastructure dependencies in domain
- ✅ Ubiquitous language (rehydration, scope, token budget)

### Hexagonal Architecture ✅
- ✅ Adapters for Neo4j, Redis, NATS
- ✅ Application service orchestrates use cases
- ✅ Dependency injection via constructor
- ✅ Clean layer separation

### Repository Rules (.cursorrules) ✅
- ✅ Language: All code in English
- ✅ Immutability: frozen=True dataclasses
- ✅ Validation: Fail-fast in `__post_init__`
- ✅ No reflection: No setattr/getattr/vars
- ✅ Type hints complete
- ✅ Dependency injection only
- ✅ Tests mandatory (>90% coverage)

---

## 📚 Related Documentation

- **../planning/README.md** - Planning Service (entity source)
- **../orchestrator/README.md** - Orchestrator Service (context consumer)
- **../task-derivation/README.md** - Task Derivation Service (context consumer)
- **specs/fleet/context/v1/context.proto** - gRPC definition
- **config/prompt_scopes.yaml** - Scope policies configuration
- **../../docs/HEXAGONAL_ARCHITECTURE_PRINCIPLES.md** - Architectural patterns

---

## 🤝 Contributing

When adding new features:

1. **Domain First**: Add VO in `domain/`
2. **Policy**: Update `prompt_scopes.yaml` for new roles/phases
3. **Consumer**: Add NATS consumer in `consumers/`
4. **Adapter**: Implement storage in `infrastructure/adapters/`
5. **Mapper**: Add protobuf conversion in `infrastructure/mappers/`
6. **Tests**: Achieve >90% coverage
7. **Update Docs**: Keep this README current

---

**Context Service v1.0.0** - Following SWE AI Fleet architectural standards
**Architecture**: DDD + Hexagonal | **Pattern**: Event-Driven Microservices | **Status**: ✅ Production Ready

