# Orchestrator Service - Complete Documentation

**Version**: v1.0.0
**Status**: ✅ Production Ready
**Pattern**: DDD + Hexagonal Architecture (Ports & Adapters)
**Language**: Python 3.13
**Last Updated**: November 15, 2025

---

## 📋 Executive Summary

**Orchestrator Service** is the central coordinator of the SWE AI Fleet platform. It orchestrates multi-agent deliberation, manages councils of AI agents, and coordinates distributed task execution across the Ray cluster. It serves as the primary orchestration engine, integrating all other microservices (Planning, Context, Ray Executor, etc.) into a cohesive deliberation workflow.

**Core Purpose:**
- 🎯 Create and manage councils of AI agents by role (DEV, QA, ARCHITECT, DEVOPS, DATA)
- 💬 Orchestrate multi-agent deliberation with peer review and scoring
- 🔄 Coordinate task execution across distributed Ray workers
- 📊 Track execution statistics and performance metrics
- 🛡️ Maintain immutability and fail-fast validation
- 📡 Integrate with Planning Service, Context Service, and Ray Executor

---

## 📚 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Responsibility Matrix](#responsibility-matrix)
3. [Architecture Overview](#architecture-overview)
4. [Domain Model](#domain-model)
5. [Ports & Adapters](#ports--adapters)
6. [Use Cases](#use-cases)
7. [Event Integration](#event-integration)
8. [External Dependencies](#external-dependencies)
9. [Request Flow](#request-flow)
10. [Architectural Principles](#architectural-principles)
11. [Testing & Coverage](#testing--coverage)
12. [Getting Started](#getting-started)
13. [Monitoring & Observability](#monitoring--observability)
14. [Troubleshooting](#troubleshooting)

---

## 🎯 Responsibility Matrix

### What This Service DOES ✅

| Responsibility | Mechanism |
|---|---|
| **Create deliberation councils** | gRPC `CreateCouncil()` RPC with agent factory |
| **Orchestrate multi-agent deliberation** | gRPC `Deliberate()` RPC with council execution |
| **Select architect agent** | Architect selection logic from council |
| **Execute full orchestration** | gRPC `Orchestrate()` RPC (deliberation + architect) |
| **List active councils** | gRPC `ListCouncils()` RPC |
| **Delete councils** | gRPC `DeleteCouncil()` RPC |
| **Track statistics** | In-memory stats (deliberations, duration, success/fail) |
| **Query deliberation results** | gRPC `GetDeliberationResult()` RPC |
| **Report service health** | gRPC `GetStatus()` RPC |

### What This Service DOES NOT ✅

| Non-Responsibility | Owner |
|---|---|
| ❌ Persist tasks to database | Planning Service |
| ❌ Manage story lifecycle | Planning Service |
| ❌ Rehydrate context for agents | Context Service |
| ❌ Execute LLM inference | Ray Executor (via vLLM workers) |
| ❌ Manage user sessions | Workflow Service |
| ❌ Route HTTP requests | API Gateway |

---

## 🏗️ Architecture Overview

### Layered Design (DDD + Hexagonal)

```
┌──────────────────────────────────────────────────────┐
│                   Domain Layer                        │
│  • Entities (Council, Agent, DeliberationResult)      │
│  • Value Objects (AgentConfig, TaskConstraints)       │
│  • Pure deliberation logic, zero infrastructure       │
└──────────────────────────────────────────────────────┘
         ↓                                    ↑
┌──────────────────────────────────────────────────────┐
│                Application Layer                      │
│  • Ports (7 interfaces for external services)         │
│  • Use Cases (CreateCouncil, Deliberate, etc.)        │
│  • Orchestrates domain logic, no infra calls          │
└──────────────────────────────────────────────────────┘
         ↓                                    ↑
┌──────────────────────────────────────────────────────┐
│              Infrastructure Layer                     │
│  • 7 Adapters (Ray, Config, Scoring, etc.)            │
│  • NATS event consumers (agent, context, planning)    │
│  • Mappers (domain ↔ gRPC/NATS conversions)           │
│  • gRPC Server (external API)                         │
└──────────────────────────────────────────────────────┘
```

### Directory Structure

```
services/orchestrator/
├── orchestrator/
│   ├── domain/                          # Pure business logic (NO I/O)
│   │   ├── entities/
│   │   │   ├── agent_collection.py          # Collection of agents
│   │   │   ├── agent_config.py              # Agent configuration VO
│   │   │   ├── agent_type.py                # Agent type enum
│   │   │   ├── check_suite.py               # Code quality checks
│   │   │   ├── council_registry.py          # Registry of all councils
│   │   │   ├── deliberation_result_data.py  # Deliberation results
│   │   │   ├── deliberation_status.py       # Status enum
│   │   │   ├── deliberation_submission.py   # Submission data
│   │   │   ├── role_collection.py           # Collection of roles
│   │   │   ├── service_configuration.py     # Service config VO
│   │   │   └── statistics.py                # Execution statistics
│   │   ├── value_objects/
│   │   │   ├── check_results.py             # Code check results VO
│   │   │   ├── deliberation.py              # Deliberation VO
│   │   │   ├── metadata.py                  # Metadata VO
│   │   │   └── task_constraints.py          # Task constraints VO
│   │   └── ports/
│   │       ├── agent_factory_port.py        # Create agents interface
│   │       ├── architect_port.py            # Architect selection interface
│   │       ├── configuration_port.py        # Configuration interface
│   │       ├── council_factory_port.py      # Create councils interface
│   │       ├── council_query_port.py        # Query councils interface
│   │       ├── ray_executor_port.py         # Ray execution interface
│   │       └── scoring_port.py              # Scoring/validation interface
│   │
│   ├── application/                     # Use Cases & Orchestration
│   │   └── usecases/
│   │       ├── create_council_usecase.py       # Create council
│   │       ├── deliberate_usecase.py           # Run deliberation
│   │       ├── delete_council_usecase.py       # Delete council
│   │       └── list_councils_usecase.py        # List councils
│   │
│   ├── infrastructure/                  # External Integrations
│   │   ├── adapters/
│   │   │   ├── architect_adapter.py           # Architect selection
│   │   │   ├── council_query_adapter.py       # Query implementation
│   │   │   ├── deliberate_council_factory_adapter.py
│   │   │   ├── environment_configuration_adapter.py
│   │   │   ├── grpc_ray_executor_adapter.py   # Ray Executor gRPC
│   │   │   ├── scoring_adapter.py             # Scoring logic
│   │   │   └── vllm_agent_factory_adapter.py  # Agent creation via vLLM
│   │   │
│   │   ├── consumers/                   # NATS JetStream consumers
│   │   │   ├── agent_response_consumer.py    # agent.response.>
│   │   │   ├── context_consumer.py           # context.updated
│   │   │   ├── planning_consumer.py          # planning.>
│   │   │   ├── deliberation_collector.py     # Result aggregator
│   │   │   └── nats_handler.py               # Main NATS handler
│   │   │
│   │   ├── mappers/                    # Domain ↔ gRPC/NATS conversions
│   │   │   ├── check_suite_mapper.py
│   │   │   ├── council_info_mapper.py
│   │   │   ├── deliberate_response_mapper.py
│   │   │   ├── deliberation_result_data_mapper.py
│   │   │   ├── deliberation_status_mapper.py
│   │   │   ├── metadata_mapper.py
│   │   │   ├── orchestrate_response_mapper.py
│   │   │   ├── orchestrator_stats_mapper.py
│   │   │   ├── proposal_mapper.py
│   │   │   └── task_constraints_mapper.py
│   │   │
│   │   └── dto/
│   │       └── __init__.py              # Wraps orchestrator_pb2
│   │
│   ├── gen/                             # Generated gRPC (not in git)
│   ├── server.py                        # gRPC server + DI wiring
│   ├── init_councils.py                 # Council auto-initialization
│   └── __init__.py
│
├── tests/
│   ├── unit/                            # 112+ unit tests, >90% coverage
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── integration/                     # Integration tests
│   └── e2e/                             # End-to-end tests
│
├── Dockerfile                           # Multi-stage build (Python 3.13)
├── requirements.txt                     # Dependencies
├── README.md                            # THIS FILE
└── .gitignore
```

---

## 🧩 Domain Model

### Entities (All Immutable)

All entities are `@dataclass(frozen=True)` with **fail-fast validation** in `__post_init__`.

#### Council

```python
@dataclass(frozen=True)
class Council:
    council_id: str                     # Unique council identifier
    role: str                           # Role (DEV, QA, ARCHITECT, DEVOPS, DATA)
    agents: Tuple[Agent, ...]           # Participating agents
    config: CouncilConfig               # Configuration
    status: CouncilStatus               # Status (ACTIVE, INACTIVE)
    created_at: datetime
    updated_at: datetime
```

**Domain Invariants**:
- ✅ At least one agent required
- ✅ Role must be valid (from predefined set)
- ✅ All frozen (immutable)

#### Agent

```python
@dataclass(frozen=True)
class Agent:
    agent_id: str                       # Unique agent identifier
    role: str                           # Agent role
    model: str                          # Model name (e.g., Qwen/Qwen3-0.6B)
    type: AgentType                     # VLLM (production only)
    config: AgentConfig                 # Agent configuration
```

#### DeliberationResult

```python
@dataclass(frozen=True)
class DeliberationResult:
    proposals: Tuple[Proposal, ...]     # Agent proposals
    metadata: Metadata                  # Deliberation metadata
    duration_ms: int                    # Execution time
    status: str                         # Status (COMPLETED, FAILED)
    scores: Dict[str, float]            # Proposal scores
```

#### OrchestratorStatistics

```python
@dataclass(frozen=True)
class OrchestratorStatistics:
    total_deliberations: int            # Total executed
    deliberations_per_role: Dict        # Count by role
    average_duration_ms: float          # Average time
    success_rate: float                 # Success percentage
    failed_deliberations: int           # Failed count
```

### Value Objects

#### AgentConfig

```python
@dataclass(frozen=True)
class AgentConfig:
    prompt_template: Optional[str]      # Optional custom prompt
    temperature: float = 0.7            # Sampling temperature
    max_tokens: int = 2048              # Max output tokens
```

#### TaskConstraints

```python
@dataclass(frozen=True)
class TaskConstraints:
    story_id: str                       # Story identifier
    plan_id: str                        # Plan identifier
    timeout_seconds: int = 300          # Max execution time
    max_retries: int = 3                # Max retry attempts
```

---

## 🔌 Ports & Adapters

### Ports (Interfaces)

| Port | Purpose | Adapter |
|------|---------|---------|
| **RayExecutorPort** | Submit deliberations to Ray | `GRPCRayExecutorAdapter` |
| **CouncilQueryPort** | Query council state | `CouncilQueryAdapter` |
| **AgentFactoryPort** | Create agent instances | `VLLMAgentFactoryAdapter` |
| **CouncilFactoryPort** | Create council instances | `DeliberateCouncilFactoryAdapter` |
| **ConfigurationPort** | Load configuration | `EnvironmentConfigurationAdapter` |
| **ScoringPort** | Score proposals | `ScoringAdapter` |
| **ArchitectPort** | Select architect agent | `ArchitectAdapter` |

### Key Adapters

**GRPCRayExecutorAdapter**
- Submits deliberation tasks to Ray Executor via gRPC
- Timeout: 30 seconds
- Address: configured via env var

**EnvironmentConfigurationAdapter**
- Reads configuration from environment variables
- Provides defaults for optional settings
- Fail-fast on missing required configuration

**VLLMAgentFactoryAdapter**
- Creates agent instances for councils
- Uses vLLM for agent behavior
- Production-only (no mocks)

---

## 🎯 Use Cases

### 1. CreateCouncilUseCase

Creates a new deliberation council with configured agents.

**Input**: Role, agent type, model config, number of agents
**Output**: `CouncilCreationResult` (council_id, agents_created, agent_ids, duration_ms)
**Business Rules**:
- Agent type must be `VLLM` (production only)
- Model must be specified
- At least 1 agent required
- Registers council in global registry

### 2. DeliberateUseCase

Executes multi-agent deliberation on a task.

**Input**: Council, role, task description, constraints
**Output**: `DeliberationResult` (proposals, metadata, duration_ms, scores)
**Business Rules**:
- Task description cannot be empty
- Records execution duration
- Updates statistics
- Delegates to council's `execute()` method
- Publishes result via NATS

### 3. DeleteCouncilUseCase

Removes a council and returns its information.

**Input**: Role
**Output**: `CouncilDeletionResult` (council, agents, role)
**Business Rules**:
- Council must exist (fail-fast if not found)
- Returns both council and agents for auditing
- Removes from global registry

### 4. ListCouncilsUseCase

Lists all active councils with optional agent details.

**Input**: include_agents flag
**Output**: List of `CouncilInfo` objects
**Business Rules**:
- Queries all registered councils
- Optionally includes agent information
- Returns immutable council snapshots

---

## 📡 Event Integration

### NATS Event Consumers

| Consumer | Topic | Purpose | Handler |
|----------|-------|---------|---------|
| **agent_response_consumer** | `agent.response.>` | LLM completion results | DeliberationCollector |
| **context_consumer** | `context.updated` | Context updates | Context aggregator |
| **planning_consumer** | `planning.>` | Planning events | Planning handler |

### Published Events

| Event | Topic | Purpose | Consumers |
|-------|-------|---------|-----------|
| **deliberation.started** | `orchestration.deliberation.started` | Deliberation began | Monitoring |
| **deliberation.completed** | `orchestration.deliberation.completed` | Result ready | Planning, Monitoring |
| **deliberation.failed** | `orchestration.deliberation.failed` | Execution failed | Monitoring |
| **council.created** | `orchestration.council.created` | New council created | Monitoring |
| **council.deleted** | `orchestration.council.deleted` | Council removed | Monitoring |

---

## 🔌 External Dependencies

### Ray Executor Service
- **Address**: Configured via `RAY_EXECUTOR_ADDRESS` env var
- **Purpose**: Distributed task execution on GPU workers
- **Adapter**: `GRPCRayExecutorAdapter`
- **RPCs**: `SubmitTaskDerivation`, `GetDeliberationStatus`

### Planning Service
- **Interaction**: Consumes `planning.>` events
- **Purpose**: Task and story updates
- **Consumer**: `PlanningConsumer`

### Context Service
- **Interaction**: Consumes `context.updated` events
- **Purpose**: Story context rehydration
- **Consumer**: `ContextConsumer`

### NATS JetStream
- **Address**: `nats://nats.swe-ai-fleet.svc.cluster.local:4222`
- **Purpose**: Event streaming and result aggregation
- **Role**: Central event fabric

---

## 🔄 Request Flow Sequence

```
1. Client calls gRPC CreateCouncil(role, config)
   ↓
2. RayExecutorServiceServicer receives request
   ├─ Convert protobuf → CreateCouncilRequest domain object
   └─ Validate role and configuration
   ↓
3. CreateCouncilUseCase.execute(request)
   ├─ Call AgentFactoryPort.create_agents()
   ├─ Call CouncilFactoryPort.create_council()
   ├─ Register council in CouncilRegistry
   └─ Publish council.created event to NATS
   ↓
4. VLLMAgentFactoryAdapter.create_agents()
   ├─ Create agent instances using vLLM
   └─ Return configured agents
   ↓
5. DeliberateCouncilFactoryAdapter.create_council()
   ├─ Assemble council from agents
   └─ Return initialized council
   ↓
6. Return CouncilCreationResponse to client
   ├─ council_id, agents_created, agent_ids, duration_ms
   ↓
7. Later, client calls gRPC Deliberate(council_id, task)
   ↓
8. DeliberateUseCase.execute(council, task, constraints)
   ├─ Call council.execute(task) (domain logic)
   ├─ Publish deliberation.started event
   ├─ Wait for results via NATS consumers
   └─ Publish deliberation.completed event
   ↓
9. Council executes LLM deliberation (async)
   ├─ Submit to Ray Executor via RayExecutorPort
   ├─ Ray workers execute with vLLM
   └─ Ray publishes results to NATS
   ↓
10. DeliberationCollector aggregates results
   ├─ Listens to agent.response.> events
   └─ Updates DeliberationResult
   ↓
11. Return DeliberationResponse to client
    ├─ proposals, metadata, duration_ms, scores
```

---

## 🛡️ Architectural Principles

### 1. **Immutability & Fail-Fast**
- All domain entities are `@dataclass(frozen=True)`
- Validation happens in `__post_init__` (throws immediately)
- No silent defaults

### 2. **No Reflection / No Dynamic Mutation**
- ❌ NO `getattr()`, `setattr()`, `__dict__`
- ✅ Direct attribute access or structured try-except
- ✅ Explicit field access through proto contracts

### 3. **Separation of Concerns**
- **Domain**: Pure deliberation logic (no I/O, no Ray/NATS knowledge)
- **Application**: Use cases & orchestration (no gRPC details)
- **Infrastructure**: Adapters for Ray/Config/Scoring (serialization, I/O)

### 4. **Dependency Injection Only**
- Use cases receive ports via constructor
- NO direct instantiation of adapters inside use cases
- All external services injected as protocols

### 5. **Single Responsibility**
- Each use case has one responsibility
- Each adapter implements one port
- Each entity models one concept

---

## ⚠️ Error Codes & Recovery

### gRPC Errors

| Code | Scenario | Recovery |
|---|---|---|
| `INVALID_ARGUMENT` | Empty task, invalid deliberation config | Validate input |
| `NOT_FOUND` | Task/agent not found | Verify IDs exist |
| `FAILED_PRECONDITION` | Deliberation already running | Wait for completion |
| `RESOURCE_EXHAUSTED` | Ray cluster full | Wait for slot or scale up |
| `UNAVAILABLE` | Ray/NATS down | Wait for recovery |

---

## 📊 Performance Characteristics

### Latency (p95)

| Operation | Latency | Notes |
|---|---|---|
| `ExecuteDeliberation` | 200ms | Dispatch to Ray |
| `GetDeliberationStatus` | 10ms | Redis read |
| `GetDeliberationResult` | 15ms | Redis read |

### Throughput
- **Deliberations/sec**: ~20 (depends on Ray cluster)
- **Concurrent deliberations**: 50+

### Resource Usage (per pod)

| Resource | Request | Limit |
|---|---|---|
| CPU | 200m | 400m |
| Memory | 256Mi | 512Mi |

---

## 🎯 SLA & Monitoring

### Service Level Objectives

| SLO | Target |
|---|---|
| **Availability** | 99.5% (depends on Ray) |
| **Latency (p95)** | <1s |
| **Error Rate** | <0.5% |

### Prometheus Metrics
```
orchestrator_deliberations_total
orchestrator_deliberation_latency_ms
orchestrator_ray_dispatch_errors_total
orchestrator_deliberation_rounds_total
```

---

## 🧪 Testing & Coverage

### Test Organization

```
tests/
├── unit/                                # 112+ tests, all passing ✅
│   ├── domain/                          # Entity tests (100% coverage)
│   ├── application/                     # Use case tests (95% coverage)
│   └── infrastructure/                  # Adapter tests (90% coverage)
├── integration/                         # Tests with NATS/Ray
└── e2e/                                 # Full system tests
```

### Running Tests

```bash
# Unit tests (fast, <5 seconds)
make test-unit

# Integration tests (requires containers)
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
| **Infrastructure** | 90%+ | 90% | ✅ |
| **Overall** | 90% | >90% | ✅ |

### Testing Philosophy

1. **Fast Unit Tests**: No I/O, pure logic, <0.3s per test
2. **Ports as Test Doubles**: Easy mocking via interfaces
3. **Tell, Don't Ask Tests**: Test behavior, not implementation
4. **Fail-Fast Validation**: Tests verify early error detection

---

## 🚀 Getting Started

### Prerequisites

```bash
# Python 3.13
# NATS JetStream running
# Ray Executor running
# vLLM inference server running

# Activate venv
source .venv/bin/activate

# Install dependencies
cd services/orchestrator
pip install -e .
```

### Configuration (Environment Variables)

```bash
# Required
ORCHESTRATOR_PORT=50060                 # gRPC server port
NATS_URL=nats://nats:4222               # NATS address
RAY_EXECUTOR_ADDRESS=ray-executor:50056 # Ray Executor gRPC
VLLM_URL=http://vllm:8000               # vLLM inference URL
VLLM_MODEL=Qwen/Qwen3-0.6B              # Default model

# Optional
NUM_AGENTS_PER_COUNCIL=3                # Agents per council
LOG_LEVEL=INFO                          # Logging level
```

### Running Locally

```bash
# Generate gRPC code
bash scripts/test/_generate_protos.sh

# Run tests
make test-unit

# Run server
python services/orchestrator/server.py

# Run council initialization (in separate terminal)
python services/orchestrator/init_councils.py
```

### Deployment to Kubernetes

```bash
# Build image
podman build -t registry.underpassai.com/swe-fleet/orchestrator:v1.0.0 \
  -f services/orchestrator/Dockerfile .

# Push to registry
podman push registry.underpassai.com/swe-fleet/orchestrator:v1.0.0

# Deploy
kubectl apply -f deploy/k8s-integration/

# Verify
kubectl get pods -n swe-ai-fleet -l app=orchestrator
```

---

## 📊 Monitoring & Observability

### gRPC Endpoints

| Endpoint | Purpose |
|----------|---------|
| `CreateCouncil` | Create new council with agents |
| `DeleteCouncil` | Remove existing council |
| `ListCouncils` | List all active councils |
| `Deliberate` | Execute deliberation on council |
| `Orchestrate` | Full orchestration (deliberation + architect) |
| `GetDeliberationResult` | Query deliberation status and results |
| `GetStatus` | Service health and statistics |

### View Logs

```bash
kubectl logs -n swe-ai-fleet -l app=orchestrator -f
```

### Check Service Health

```bash
grpcurl -plaintext orchestrator.swe-ai-fleet.svc.cluster.local:50060 \
  orchestrator.v1.OrchestratorService/GetStatus
```

### Statistics Tracked

- Total deliberations executed
- Deliberations per role
- Average deliberation duration (ms)
- Success rate (%)
- Failed deliberation count

---

## 🔍 Troubleshooting

### Issue: "Council not found"
```
❌ Error: Council for role "DEV" not found
```
**Solution**: Run `init_councils.py` or call `CreateCouncil` RPC first

### Issue: "Ray Executor connection failed"
```
❌ Error: Failed to connect to Ray Executor
```
**Solution**:
1. Verify Ray Executor is running
2. Check `RAY_EXECUTOR_ADDRESS` environment variable
3. Verify network connectivity

### Issue: "NATS connection failed"
```
❌ Error: Failed to connect to NATS
```
**Solution**:
1. Verify NATS is running
2. Check `NATS_URL` environment variable
3. Verify network connectivity

### Issue: Low test coverage
```
❌ SonarCloud: Coverage 65% < 70%
```
**Solution**:
```bash
make test-unit
make coverage-report
# Open htmlcov/index.html and identify uncovered code
```

---

## ✅ Compliance Checklist

### DDD Principles ✅
- ✅ Entities are immutable with validation
- ✅ Value Objects are immutable
- ✅ Domain logic in domain layer
- ✅ No infrastructure dependencies in domain
- ✅ Ubiquitous language (Council, Deliberation, Agent)

### Hexagonal Architecture ✅
- ✅ Ports define interfaces
- ✅ Adapters implement ports
- ✅ Use cases depend on ports only
- ✅ Dependency injection via constructor
- ✅ Clean layer separation

### Repository Rules (.cursorrules) ✅
- ✅ Language: All code in English
- ✅ Immutability: frozen=True dataclasses
- ✅ Validation: Fail-fast in `__post_init__`
- ✅ No reflection: No setattr/getattr/vars
- ✅ No to_dict/from_dict in domain
- ✅ Type hints complete
- ✅ Dependency injection only
- ✅ Tests mandatory (112+ tests, >90% coverage)

---

## 📚 Related Documentation

- **ARCHITECTURE.md** - Detailed architectural design (if exists)
- **../planning/README.md** - Planning Service
- **../task-derivation/README.md** - Task Derivation Service
- **../ray_executor/README.md** - Ray Executor Service
- **../context/README.md** - Context Service
- **specs/fleet/orchestrator/v1/orchestrator.proto** - gRPC definition
- **../../docs/HEXAGONAL_ARCHITECTURE_PRINCIPLES.md** - Architectural patterns

---

## 🤝 Contributing

When adding new features:

1. **Domain First**: Create entities/VOs in `domain/`
2. **Port Definition**: Define interface in `domain/ports/`
3. **Use Case**: Implement orchestration in `application/usecases/`
4. **Adapter**: Implement port in `infrastructure/adapters/`
5. **Mapper**: Add DTO conversion in `infrastructure/mappers/`
6. **Tests**: Achieve >90% coverage
7. **Update Docs**: Keep this README current

---

**Orchestrator Service v1.0.0** - Following SWE AI Fleet architectural standards
**Architecture**: DDD + Hexagonal | **Pattern**: Event-Driven Microservices | **Status**: ✅ Production Ready
