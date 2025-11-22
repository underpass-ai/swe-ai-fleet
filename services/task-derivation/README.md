# Task Derivation Service

**Package**: `services.task-derivation`
**Type**: Microservice (Worker / Event-Driven)
**Architecture**: Hexagonal (Ports & Adapters) + DDD
**Status**: 🚧 Beta

## 📖 Overview

The **Task Derivation Service** is a specialized worker microservice responsible for automatically breaking down high-level **Plans** into executable **Tasks** using Large Language Models (LLMs).

It acts as the bridge between the **Planning Service** (which defines *what* to do) and the execution layer. When a Plan is approved by a Product Owner, this service:
1.  Rehydrates the full context (Plan details + User Story context).
2.  Constructs a specialized prompt for an Architect AI Agent.
3.  Offloads the inference to the **Ray Executor Service**.
4.  Parses the LLM response into a structured **Dependency Graph**.
5.  Persists the generated Tasks back into the Planning Service.

## 🏗 Architecture

This service follows **Hexagonal Architecture** (Ports & Adapters) to isolate the complex derivation logic from external dependencies.

```mermaid
graph TD
    subgraph "Infrastructure (Adapters)"
        NATSIn[NATS Consumers]
        PlanningAdapter[Planning Adapter (gRPC)]
        ContextAdapter[Context Adapter (gRPC)]
        RayAdapter[Ray Executor Adapter (gRPC)]
        NATSOut[NATS Producer]
    end

    subgraph "Application Layer (Use Cases)"
        DeriveUC[DeriveTasksUseCase]
        ProcessUC[ProcessTaskDerivationResultUseCase]
        Ports[Ports Interfaces]
    end

    subgraph "Domain Layer (Pure Python)"
        Graph[DependencyGraph]
        Context[PlanContext]
        Prompt[LLMPrompt]
        Cmd[TaskCreationCommand]
    end

    NATSIn --> DeriveUC
    NATSIn --> ProcessUC

    DeriveUC --> Ports
    ProcessUC --> Ports

    Ports -.-> PlanningAdapter
    Ports -.-> ContextAdapter
    Ports -.-> RayAdapter
    Ports -.-> NATSOut

    DeriveUC --> Context
    DeriveUC --> Prompt
    ProcessUC --> Graph
    ProcessUC --> Cmd
```

### Directory Structure

```
services/task-derivation/task_derivation/
├── application/          # Orchestration logic
│   ├── ports/            # Interfaces for external dependencies
│   └── usecases/         # Core workflows (Derive, Process)
├── domain/               # Business logic (No dependencies)
│   ├── events/           # Domain events
│   └── value_objects/    # Rich domain models (Graph, Context, Content)
├── infrastructure/       # Concrete implementations
│   ├── adapters/         # gRPC & NATS clients
│   ├── consumers/        # NATS message handlers
│   └── mappers/          # Data transformation
└── tests/                # Unit and Integration tests
```

## ⚡ Key Workflows

### 1. Derivation Request Flow
Triggered when a Plan is approved in the Planning Service.

1.  **Ingest**: `TaskDerivationRequestConsumer` receives `task.derivation.requested`.
2.  **Fetch Data**: `DeriveTasksUseCase` fetches:
    *   **Plan Snapshot** (Description, Acceptance Criteria) via `PlanningPort`.
    *   **Story Context** (Chat history, files) via `ContextPort`.
3.  **Construct Prompt**: Uses `TaskDerivationConfig` to build a prompt containing the plan and context.
4.  **Submit Job**: Sends the prompt to `RayExecutorPort` (gRPC) for asynchronous processing.
5.  **Ack**: Acknowledges the message once the job is successfully submitted.

### 2. Result Processing Flow
Triggered when the Ray Executor completes the LLM inference.

1.  **Ingest**: `TaskDerivationResultConsumer` receives `agent.response.completed`.
2.  **Parse**: `LLMTaskDerivationMapper` converts the raw LLM text response into a structured list of `TaskNode` objects.
3.  **Build Graph**: `ProcessTaskDerivationResultUseCase` builds a `DependencyGraph` to resolve dependencies and ordering.
4.  **Persist**:
    *   Creates tasks in the Planning Service via `PlanningPort.create_tasks`.
    *   Saves dependency edges via `PlanningPort.save_task_dependencies`.
5.  **Notify**: Publishes `task.derivation.completed` (or `failed`) to NATS.

## 🔌 Ports & Adapters

| Port Interface | Adapter Implementation | Type | Purpose |
| :--- | :--- | :--- | :--- |
| `PlanningPort` | `PlanningServiceAdapter` | Out | Fetch Plan data, Create Tasks |
| `ContextPort` | `ContextServiceAdapter` | Out | Fetch rehydrated context |
| `RayExecutorPort` | `RayExecutorAdapter` | Out | Submit LLM jobs |
| `MessagingPort` | `NatsMessagingAdapter` | Out | Publish success/failure events |

## 📡 Events & API

### Consumed Events (NATS)
*   `task.derivation.requested` (Topic: `task.derivation.requested`)
    *   Payload: `{ "plan_id": "...", "story_id": "...", "roles": [...] }`
*   `agent.response.completed` (Topic: `agent.response.completed`)
    *   Payload: `{ "plan_id": "...", "result": { "proposal": "..." } }`

### Produced Events (NATS)
*   `task.derivation.completed`: Tasks successfully created.
*   `task.derivation.failed`: Parsing or persistence failed (requires manual review).

## 💾 Domain Model

The domain layer contains sophisticated logic for handling task dependencies:
*   **`DependencyGraph`**: Directed Acyclic Graph (DAG) to manage task ordering.
*   **`ExecutionPlan`**: A linearized sequence of steps derived from the graph.
*   **`PlanContext`**: Immutable snapshot of all data needed for derivation.

## 🛠 Development

### Prerequisites
*   Python 3.11+
*   NATS JetStream
*   Dependencies: `pip install -r requirements.txt`

### Running Tests
The service maintains high test coverage for the complex parsing and graph logic.

```bash
# Run unit tests
pytest tests/unit

# Run coverage report
pytest --cov=task_derivation tests/unit
```

