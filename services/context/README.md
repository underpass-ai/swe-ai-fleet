# Context Service

**Status**: ✅ Production Ready | **Version**: v1.0.0 | **Pattern**: DDD + Hexagonal

The **Context Service** is the "brain" of the SWE AI Fleet. It is responsible for **Context Rehydration**—the process of assembling a surgical, role-specific prompt for AI agents by traversing the knowledge graph (Neo4j) and current state (Redis).

Unlike traditional RAG which relies on vector similarity, the Context Service uses a **Decision-Centric Graph** to understand *why* code exists, not just *what* it is.

## 🧠 Core Responsibilities

1.  **Session Rehydration**: Rebuilds the "mental state" for an agent (Developer, QA, Architect) by fetching:
    *   **Graph Context**: Decisions, dependencies, and alternatives from Neo4j.
    *   **Planning State**: Current tasks, story details, and acceptance criteria from Redis.
    *   **Event History**: Recent milestones and timeline events.
2.  **Prompt Assembly**: Dynamically assembles `System`, `Context`, and `Tools` blocks, respecting a strict token budget (~200-500 tokens).
3.  **Scope Enforcement**: Applies `PromptScopePolicy` to ensure agents only see what they need (e.g., Developers see implementation details, Architects see strategic decisions).
4.  **Context Updates**: Records new decisions, subtasks, and status changes back to the graph via CQRS command handlers.

## 🏗️ Architecture

The service follows **Hexagonal Architecture (Ports & Adapters)** and **Domain-Driven Design (DDD)**.

```mermaid
graph TB
    subgraph "Infrastructure (Adapters)"
        GRPC[gRPC Server\n(Primary Adapter)]
        NATS[NATS Consumers\n(Primary Adapter)]
        Neo4j[Neo4j Adapter\n(Secondary Adapter)]
        Redis[Redis Adapter\n(Secondary Adapter)]
    end

    subgraph "Application Layer"
        Rehydrator[SessionRehydration\nService]
        UseCases[Use Cases\n(ProjectStory, Decision, etc.)]
    end

    subgraph "Domain Layer (Core)"
        Model[Entities: Decision, Task, Story]
        Policies[PromptScopePolicy]
        Logic[TokenBudgetCalculator]
    end

    GRPC --> Rehydrator
    GRPC --> UseCases
    NATS --> UseCases

    Rehydrator --> Model
    UseCases --> Model

    Rehydrator --> Neo4j
    Rehydrator --> Redis
    UseCases --> Neo4j
```

### Directory Structure

*   **`server.py`**: Main entry point. Initializes DI container, gRPC server, and NATS consumers.
*   **`consumers/`**: NATS event consumers (Planning & Orchestration events).
*   **`handlers/`**: gRPC request handlers.
*   **`infrastructure/`**: Adapters for Neo4j, Redis, and Mappers.
*   **`gen/`**: Generated gRPC code (not in git).

## 📡 API Reference (gRPC)

**Port**: `50054`
**Proto**: `specs/fleet/context/v1/context.proto`

### 1. Context Retrieval

*   **`GetContext(story_id, role, phase, [subtask_id])`**
    *   Retrieves hydrated context for a specific agent role and phase.
    *   Returns: `formatted_context`, `token_count`, `scopes` (applied policies).

*   **`RehydrateSession(case_id, roles, ...)`**
    *   Rebuilds a complete session bundle for multiple roles (used for handoffs).
    *   Returns: `RehydrateSessionResponse` with full context packs.

*   **`ValidateScope(role, phase, provided_scopes)`**
    *   Checks if the requested scopes are allowed by the `PromptScopePolicy`.

### 2. State Management (Write Side)

*   **`UpdateContext(story_id, task_id, role, changes)`**
    *   Records changes made by an agent (e.g., new decisions, subtask updates).
    *   Uses `ProcessContextChangeUseCase` (CQRS).

*   **`CreateStory(story_id, title, description, ...)`**
    *   Initializes a new `ProjectCase` node in Neo4j and caches it in Redis.

*   **`CreateTask(task_id, story_id, ...)`**
    *   Creates a `Task` node and links it to the Story (`BELONGS_TO`).

*   **`AddProjectDecision(story_id, decision_type, rationale, ...)`**
    *   Records a `Decision` node in the graph.

*   **`TransitionPhase(story_id, from_phase, to_phase, rationale)`**
    *   Updates the phase of a Story and records the transition event.

## ⚡ Event Integration (NATS)

The service subscribes to events from the **Planning Service** to maintain an up-to-date Knowledge Graph.

### Consumers (Inbound)

| Consumer | Topic | Action |
| :--- | :--- | :--- |
| **StoryCreated** | `planning.story.created` | Creates `ProjectCase` node. |
| **StoryTransitioned** | `planning.story.transitioned` | Updates phase/status in graph. |
| **TaskCreated** | `planning.task.created` | Creates `Task` node & relations. |
| **ProjectCreated** | `planning.project.created` | Creates `Project` node. |
| **EpicCreated** | `planning.epic.created` | Creates `Epic` node. |
| **PlanApproved** | `planning.plan.approved` | Records plan baseline. |
| **OrchestrationEvents** | `orchestration.deliberation.>` | Records deliberation results. |
| **ContextHandler** | `context.update.request` | Handles async update requests. |
| **ContextHandler** | `context.rehydrate.request` | Handles async rehydration. |

### Publishers (Outbound)

*   **`context.events.updated`**: Published when context changes (version bump).
*   **`context.update.response`**: Response to async update requests.
*   **`context.rehydrate.response`**: Response to async rehydration requests.

## 🛠️ Configuration

The service is configured via environment variables:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `GRPC_PORT` | `50054` | Service port. |
| `NEO4J_URI` | `bolt://neo4j:7687` | Graph database URI. |
| `NEO4J_USER` | `neo4j` | Database user. |
| `NEO4J_PASSWORD` | *Required* | Database password. |
| `REDIS_HOST` | `redis` | Cache host. |
| `REDIS_PORT` | `6379` | Cache port. |
| `NATS_URL` | `nats://nats:4222` | Message bus URL. |
| `ENABLE_NATS` | `true` | Enable/disable NATS. |

**Scope Configuration**: `config/prompt_scopes.yaml` defines the visibility rules per Role/Phase.

## 🚀 Development

### Prerequisites

*   Python 3.13+
*   Neo4j 5.14+
*   Redis/Valkey 8.0+
*   NATS JetStream

### Running Locally

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install dependencies
pip install -e ".[grpc,integration]"

# 3. Generate gRPC protos (required)
bash scripts/test/_generate_protos.sh

# 4. Run the server
export NEO4J_PASSWORD=your_password
python services/context/server.py
```

### Running Tests

The service has a comprehensive test suite including Unit, Integration, and E2E tests.

```bash
# Unit tests (Fast)
pytest services/context/tests/unit

# E2E tests (Requires Docker/Podman)
pytest tests/integration/services/context/ -v -m e2e
```

## 📦 Deployment

The service is deployed as a stateless container in Kubernetes.

*   **Dockerfile**: Multi-stage build, generates protos during build.
*   **Image**: `registry.underpassai.com/swe-fleet/context:v1.0.0`
*   **Replicas**: 2 (High Availability).
*   **Resources**: 200m CPU / 512Mi RAM request.

See `deploy/k8s-integration/` for Kubernetes manifests.

