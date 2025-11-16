# Task Derivation Service

**Version:** 1.0.0
**Status:** ✅ Production Ready
**Architecture:** Domain-Driven Design (DDD) + Hexagonal Architecture (Ports & Adapters)
**Language:** Python 3.13+

---

## 📋 Executive Summary

**Task Derivation Service** is a specialized microservice that automatically decomposes planning stories into executable tasks using Large Language Models (LLM). It operates as an asynchronous, event-driven system within the SWE AI Fleet, orchestrating interactions between the Planning Service, Context Service, and Ray Executor cluster.

**Core Purpose:**
- 🎯 Transform high-level plans into granular, executable tasks
- 📊 Analyze dependencies and create execution graphs
- 🔄 Provide event-driven integration with Planning and Workflow services
- 🛡️ Maintain immutability and fail-fast validation at all layers

---

## 🏗️ Architecture Overview

### Layered Design (DDD + Hexagonal)

```
┌─────────────────────────────────────────┐
│        NATS Event Fabric                │
│  (task.derivation.requested/completed)  │
└────────────────────┬────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
┌────▼──────┐  ┌────▼──────┐  ┌────▼──────┐
│ Request   │  │  Result   │  │  NATS     │
│ Consumer  │  │ Consumer  │  │ Publisher │
└────┬──────┘  └────┬──────┘  └────┬──────┘
     │              │               │
     └──────────────┼───────────────┘
                    │
         ┌──────────▼──────────┐
         │  Application Layer  │
         │  (Use Cases)        │
         └──────────┬──────────┘
                    │
      ┌─────────────┼─────────────┐
      │             │             │
 ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
 │ Planning │  │ Context │  │ Ray     │
 │ Adapter  │  │ Adapter │  │ Adapter │
 └────┬─────┘  └────┬────┘  └────┬────┘
      │             │             │
 ┌────▼─────────────▼─────────────▼────┐
 │     External Services (gRPC)        │
 │  Planning | Context | Ray Executor   │
 └────────────────────────────────────────┘
```

### Directory Structure

```
task_derivation/
├── domain/                          # Pure business logic (NO I/O, NO reflection)
│   ├── value_objects/
│   │   ├── identifiers/            # PlanId, StoryId, TaskId, DeliberationId
│   │   ├── content/                # Title, TaskDescription, DependencyReason
│   │   ├── task_attributes/        # Duration, Priority
│   │   └── task_derivation/        # TaskNode, DependencyGraph, LLMPrompt
│   ├── entities/                   # Task, TaskNode (immutable)
│   └── events/                     # TaskDerivationCompletedEvent, Failed
│
├── application/                     # Use Cases & Orchestration
│   ├── ports/                      # Interfaces (Protocol)
│   │   ├── planning_port.py        # Plan retrieval & task persistence
│   │   ├── context_port.py         # Story context retrieval
│   │   ├── ray_executor_port.py    # GPU job submission
│   │   └── messaging_port.py       # Event publishing
│   ├── usecases/
│   │   ├── derive_tasks_usecase.py           # Main orchestration
│   │   └── process_task_derivation_result_usecase.py
│   └── dto/
│       └── task_derivation_request.py
│
└── infrastructure/                  # External Integrations
    ├── adapters/                   # Concrete implementations
    │   ├── planning_service_adapter.py      # Planning gRPC client
    │   ├── context_service_adapter.py       # Context gRPC client
    │   ├── ray_executor_adapter.py          # Ray Executor gRPC client
    │   └── nats_messaging_adapter.py        # NATS publisher
    │
    ├── consumers/                  # NATS JetStream consumers
    │   ├── task_derivation_request_consumer.py   # Listens: task.derivation.requested
    │   └── task_derivation_result_consumer.py    # Listens: agent.response.completed
    │
    ├── mappers/                    # Domain ↔ Proto conversions
    │   ├── context_grpc_mapper.py
    │   ├── planning_grpc_mapper.py
    │   ├── nats_event_mapper.py
    │   └── llm_task_derivation_mapper.py
    │
    ├── dto/                        # Infrastructure DTOs
    │   ├── task_derivation_completed_payload.py
    │   └── task_derivation_failed_payload.py
    │
    └── config/
        └── task_derivation_config.py
```

---

## 🎯 Responsibility Matrix

### What This Service DOES ✅

| Responsibility | Mechanism |
|---|---|
| **Listen for derivation requests** | NATS consumer: `task.derivation.requested` |
| **Fetch plan context** | gRPC call to Planning Service |
| **Fetch rehydrated story context** | gRPC call to Context Service |
| **Build LLM prompts** | Domain logic in `LLMPrompt` + `LLMTaskDerivationMapper` |
| **Submit to GPU workers** | gRPC submission to Ray Executor (fire-and-forget) |
| **Process LLM results** | NATS consumer: `agent.response.completed` |
| **Validate task dependencies** | Domain logic in `DependencyGraph` |
| **Create tasks in Planning** | gRPC batch call: `CreateTasks` RPC |
| **Persist dependencies** | gRPC call: `SaveTaskDependencies` RPC |
| **Publish completion events** | NATS publisher: `task.derivation.completed` |
| **Publish failure events** | NATS publisher: `task.derivation.failed` |

### What This Service DOES NOT ✅

| Non-Responsibility | Owner |
|---|---|
| ❌ Persist tasks directly | Planning Service (via gRPC) |
| ❌ Manage story lifecycle | Planning Service |
| ❌ Validate RBAC permissions | Workflow Service |
| ❌ Execute derived tasks | Orchestrator/Workflow Service |
| ❌ Store LLM cache | Ray Executor (external) |
| ❌ Manage user sessions | Context Service |

---

## 📡 Event Contract (AsyncAPI)

### Published Events

#### 1. `task.derivation.completed`
**When:** Task creation succeeds
**Topic:** `task.derivation.completed`
**Stream:** (JetStream stream name TBD)

**Schema:**
```json
{
  "plan_id": "plan-123",
  "story_id": "story-456",
  "task_count": 5,
  "status": "success",
  "occurred_at": "2025-11-15T10:30:00Z",
  "derivation_request_id": "derive-xyz"  // optional: Ray job ID
}
```

#### 2. `task.derivation.failed`
**When:** Task derivation or creation fails
**Topic:** `task.derivation.failed`
**Stream:** (JetStream stream name TBD)

**Schema:**
```json
{
  "plan_id": "plan-123",
  "story_id": "story-456",
  "status": "failed",
  "reason": "LLM timeout after 30s",
  "requires_manual_review": true,
  "occurred_at": "2025-11-15T10:31:00Z",
  "derivation_request_id": "derive-xyz"  // optional: if Ray job started
}
```

### Consumed Events

#### 1. `task.derivation.requested`
**From:** Planning Service
**Topic:** `task.derivation.requested`
**Consumer:** `TaskDerivationRequestConsumer`

**Expected Schema:**
```json
{
  "plan_id": "plan-123",
  "story_id": "story-456",
  "requested_by": "planning-service",
  "roles": ["developer", "qa"],
  "occurred_at": "2025-11-15T10:00:00Z"
}
```

#### 2. `agent.response.completed`
**From:** Ray Executor / Orchestrator
**Topic:** `agent.response.completed`
**Consumer:** `TaskDerivationResultConsumer`

**Expected Schema:**
```json
{
  "plan_id": "plan-123",
  "story_id": "story-456",
  "role": "developer",
  "result": {
    "proposal": "[{\"title\":\"...\",\"description\":\"...\"}]"
  }
}
```

---

## 🔌 External Dependencies

### Planning Service (gRPC)

**Spec:** `specs/fleet/task_derivation/v1/task_derivation.proto`
**Adapter:** `PlanningServiceAdapter`

**RPCs Called:**
| RPC | Purpose | Caller |
|---|---|---|
| `GetPlanContext(plan_id)` | Fetch plan data | `DeriveTasksUseCase` |
| `CreateTasks(commands)` | Persist derived tasks | `ProcessTaskDerivationResultUseCase` |
| `ListStoryTasks(story_id)` | Deduplication check | `ProcessTaskDerivationResultUseCase` |
| `SaveTaskDependencies(...)` | Persist task edges | `ProcessTaskDerivationResultUseCase` |

**Timeout:** 5 seconds

---

### Context Service (gRPC)

**Spec:** `specs/fleet/context/v1/context.proto`
**Adapter:** `ContextServiceAdapter`

**RPCs Called:**
| RPC | Purpose | Caller |
|---|---|---|
| `GetContext(story_id, role, phase)` | Fetch rehydrated context | `DeriveTasksUseCase` |

**Timeout:** 5 seconds
**Behavior:** Returns formatted context blocks ready for LLM consumption

---

### Ray Executor (gRPC)

**Spec:** `specs/fleet/ray_executor/v1/ray_executor.proto`
**Adapter:** `RayExecutorAdapter`

**RPCs Called:**
| RPC | Purpose | Caller |
|---|---|---|
| `SubmitTaskDerivation(plan_id, prompt, role)` | Submit LLM job to GPU workers | `DeriveTasksUseCase` |

**Timeout:** 5 seconds
**Behavior:** Fire-and-forget; returns job ID for result polling
**Result Delivery:** Via NATS `agent.response.completed` event

---

### NATS JetStream

**Role:** Event fabric for async communication
**Protocol:** NATS 2.10+

**Consumers:**
1. **TaskDerivationRequestConsumer**
   - Subject: `task.derivation.requested`
   - Durable: `task-derivation-request-consumer`
   - Stream: (TBD - likely `planning_events`)

2. **TaskDerivationResultConsumer**
   - Subject: `agent.response.completed`
   - Durable: `task-derivation-result-consumer`
   - Stream: `agent_responses`

**Publishers:**
- `NATSMessagingAdapter` publishes to `task.derivation.completed` and `task.derivation.failed`

---

## 🔄 Request Flow Sequence

```
1. Planning Service publishes "task.derivation.requested" to NATS
   ↓
2. TaskDerivationRequestConsumer receives event
   ↓
3. Call DeriveTasksUseCase.execute(TaskDerivationRequest)
   ├─ Fetch PlanContext via gRPC (PlanningServiceAdapter)
   ├─ Fetch rehydrated context via gRPC (ContextServiceAdapter)
   ├─ Build LLM prompt (domain logic)
   └─ Submit to Ray Executor via gRPC (RayExecutorAdapter)
   ↓
4. Ray Executor processes LLM on GPU cluster (async)
   ↓
5. Ray publishes "agent.response.completed" to NATS
   ↓
6. TaskDerivationResultConsumer receives result
   ↓
7. Call ProcessTaskDerivationResultUseCase.execute(...)
   ├─ Map LLM output to TaskNodes (domain logic)
   ├─ Build DependencyGraph (domain logic)
   ├─ Create tasks via gRPC (PlanningServiceAdapter.CreateTasks)
   ├─ Save dependencies via gRPC (PlanningServiceAdapter.SaveTaskDependencies)
   └─ Publish "task.derivation.completed" event to NATS
   ↓
8. Planning Service receives completion event and updates story status
```

---

## 🛡️ Architectural Principles

### 1. **Immutability & Fail-Fast**
- All domain Value Objects are `@dataclass(frozen=True)`
- Validation happens in `__post_init__` (throws immediately on invalid data)
- No silent defaults; invalid data causes exceptions

**Example:**
```python
@dataclass(frozen=True)
class Duration:
    hours: int

    def __post_init__(self) -> None:
        if self.hours < 0:
            raise ValueError("Duration hours cannot be negative")
```

### 2. **No Reflection / No Dynamic Mutation**
- ❌ NO `getattr()`, `setattr()`, `__dict__`, `hasattr()`
- ✅ Direct attribute access or structured try-except
- ✅ Explicit field access through proto contracts

**Example (BAD):**
```python
# ❌ FORBIDDEN
metadata = getattr(msg, "metadata", None)
deliveries = getattr(metadata, "num_delivered", 1)
```

**Example (GOOD):**
```python
# ✅ ALLOWED
try:
    deliveries = msg.metadata.num_delivered
except AttributeError:
    deliveries = 1
```

### 3. **Separation of Concerns**
- **Domain:** Pure business logic (no I/O, no proto knowledge)
- **Application:** Use cases & orchestration (no infra details)
- **Infrastructure:** Adapters, consumers, mappers (serialization, I/O)

### 4. **Dependency Injection Only**
- Use cases receive ports (interfaces) via constructor
- NO direct instantiation of adapters inside use cases
- All external services injected as protocols/ports

### 5. **Mapper-Based Conversions**
- Domain ↔ Proto conversions live in dedicated mappers
- DTOs (infrastructure layer) never have `to_dict()` / `from_dict()`
- Mappers are pure, stateless functions

**Example:**
```python
# ✅ GOOD: Mapper handles conversion
request = ContextGrpcMapper.to_get_context_request(
    story_id=story_id,
    role=role,
    phase=phase,
)

# ❌ BAD: DTO with serialization logic
class ContextRequest(BaseModel):
    def to_dict(self): ...  # FORBIDDEN
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.13+
- Poetry or pip
- NATS JetStream 2.10+
- Planning Service running
- Context Service running
- Ray Executor running

### Installation

```bash
cd services/task-derivation

# Create venv and install
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Configuration

Create `.env` or environment variables:

```bash
# gRPC Services
PLANNING_SERVICE_ADDRESS=planning-service:50051
CONTEXT_SERVICE_ADDRESS=context-service:50054
RAY_EXECUTOR_ADDRESS=ray-executor:50055

# NATS
NATS_URL=nats://nats:4222
NATS_JETSTREAM_ENABLED=true

# Logging
LOG_LEVEL=INFO
```

### Running

```bash
# Development
python -m task_derivation.server

# With gunicorn (production)
gunicorn --workers 4 --worker-class aiohttp.GunicornWebWorker task_derivation.server:app
```

### Testing

```bash
# Unit tests with coverage
pytest tests/unit --cov=task_derivation --cov-report=html

# Run make target
make test-unit
```

---

## 📊 Monitoring & Observability

### Metrics Published

- `task_derivation_requests_received` (counter)
- `task_derivation_processing_time_ms` (histogram)
- `task_derivation_succeeded` (counter)
- `task_derivation_failed` (counter, with reason labels)

### Logs

- **INFO:** Task derivation started/completed
- **WARN:** Retry attempts, delivery fallbacks
- **ERROR:** Failures with full context (plan_id, story_id, reason)

### Tracing

- OpenTelemetry integration (TBD)
- Trace ID correlation through NATS events

---

## 🤝 How to Interact with This Service

### As a Planning Service Consumer

1. **Trigger derivation:**
   ```bash
   # Publish to NATS
   nats pub task.derivation.requested '{
     "plan_id": "plan-123",
     "story_id": "story-456",
     "roles": ["developer", "qa"],
     "requested_by": "planning-service",
     "occurred_at": "2025-11-15T10:00:00Z"
   }'
   ```

2. **Listen for completion:**
   ```bash
   # Subscribe to completion events
   nats subscribe task.derivation.completed
   ```

### As a Workflow Service Consumer

1. **Listen for completion events:**
   ```bash
   # Subscribe to see when tasks are ready
   nats subscribe task.derivation.completed
   ```

2. **Check task details:**
   Call Planning Service's `GetTask` / `ListTasks` RPCs

### As an Operator

1. **Monitor health:**
   ```bash
   curl localhost:8080/health
   ```

2. **View metrics:**
   ```bash
   curl localhost:8080/metrics
   ```

3. **Check logs:**
   ```bash
   kubectl logs -f deployment/task-derivation
   ```

---

## 🐛 Troubleshooting

### Scenario: Tasks not being created
1. Check Ray Executor is running and responsive
2. Check `agent.response.completed` events are being published
3. Check Planning Service's `CreateTasks` RPC is accepting calls
4. Review error logs for specific failure reasons

### Scenario: High latency
1. Check gRPC service latencies individually
2. Monitor Ray Executor GPU utilization
3. Check NATS JetStream backlog

### Scenario: Events not being consumed
1. Verify NATS JetStream is running
2. Check consumer durables exist
3. Check subjects are correct
4. Monitor consumer lag

---

## 📝 Development Workflow

### Adding a New Use Case

1. **Define domain logic** in `domain/`
2. **Create port interface** in `application/ports/`
3. **Implement use case** in `application/usecases/`
4. **Create adapter** in `infrastructure/adapters/` (if new external service)
5. **Create mapper** in `infrastructure/mappers/` (if proto conversion needed)
6. **Write unit tests** (≥90% coverage)
7. **Update documentation** (this README)

### Code Quality

```bash
# Linting
ruff check .

# Type checking
mypy .

# Formatting
ruff format .

# Tests
pytest tests/unit --cov=task_derivation

# Pre-commit hook
pre-commit run --all-files
```

---

## 📚 Reference Documents

- **AsyncAPI Spec:** `specs/asyncapi.yaml` (task.derivation.*)
- **Proto Specs:**
  - `specs/fleet/task_derivation/v1/task_derivation.proto`
  - `specs/fleet/context/v1/context.proto`
  - `specs/fleet/ray_executor/v1/ray_executor.proto`
- **DDD Principles:** Implemented via immutable Value Objects & domain events
- **Hexagonal Architecture:** Adapters/Ports decouple external services

---

## 🔐 Security & Compliance

- ✅ All gRPC calls use mTLS (production)
- ✅ NATS messages encrypted in transit
- ✅ No secrets logged
- ✅ Input validation at domain layer
- ✅ Rate limiting per Planning Service request

---

**Last Updated:** November 15, 2025
**Maintainers:** AI Engineering Team
**Status:** Production Ready ✅
