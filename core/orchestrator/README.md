# Core Orchestrator Bounded Context

**Package**: `core.orchestrator`
**Type**: Domain Logic & Application Services (Hexagonal Architecture)

## 📖 Overview

The **Orchestrator** bounded context is the "brain" of the execution engine. It is responsible for coordinating multi-agent work, specifically focusing on **Deliberation**—a process where multiple agents (forming a "Council") propose, critique, and revise solutions to achieve high-quality results.

Unlike the **Planning Service** (which defines *what* to do via User Stories and Plans) or the **Workflow Service** (which manages the lifecycle state FSM), the **Orchestrator** focuses on *how* to execute a specific task.

## 🏗 Architecture

This module follows **Domain-Driven Design (DDD)** and **Hexagonal Architecture**.

```
core/orchestrator/
├── domain/             # Pure business logic (Entities, Value Objects)
│   ├── agents/         # Agent interfaces, Roles, Architect selection
│   ├── tasks/          # Task definitions, Constraints
│   └── check_results/  # Scoring logic, Policy/Lint checks
├── usecases/           # Application logic (Orchestrate, Deliberate)
├── adapters/           # Interface implementations (Repositories, Queues)
├── handler/            # Event handlers and Workers (e.g., Ray Agent Jobs)
└── config_module/      # Configuration definitions
```

## 🔑 Core Concepts

### 1. Deliberation
The core value proposition of SWE AI Fleet. Instead of a single LLM call, tasks undergo a rigor process:
1.  **Generate**: Multiple agents (divergent thinking) propose solutions.
2.  **Critique**: Peer agents review proposals against rubrics.
3.  **Revise**: Authors improve their proposals based on feedback.
4.  **Select**: An "Architect" agent (or logic) picks the best solution.

### 2. Councils
A **Council** is a group of agents specialized in a specific **Role** (e.g., DEV, QA, ARCHITECT). The Orchestrator routes tasks to the appropriate council.

### 3. Use Cases & Handlers

*   **`Orchestrate`** (`orchestrate_usecase.py`): The high-level entry point. It routes a `Task` to the correct Council, executes the deliberation, and uses the `ArchitectSelectorService` to choose the winner.
*   **`Deliberate`** (`peer_deliberation_usecase.py`): Handles the synchronous/in-memory logic of the generate-critique-revise loop.
*   **`DeliberateAsync`** (`deliberate_async_usecase.py`): The production implementation for distributed execution. It:
    *   Submits jobs to the **Ray Executor** service via gRPC.
    *   Handles asynchronous completion via **NATS**.
    *   Manages `task_id` and `deliberation_id` tracking.
*   **`AgentJobWorker`** (`handler/agent_job_worker.py`): A Ray remote actor that implements an autonomous worker loop (Rehydrate -> Select Task -> Execute -> Update). This represents the "Pull" model of execution where agents autonomously pick up tasks from the Context graph.

## 💻 Usage

### Orchestration Flow (Push Model)

```python
from core.orchestrator.usecases import Orchestrate
from core.orchestrator.domain.tasks import Task, TaskConstraints
from core.orchestrator.domain.agents import Role

# 1. Define the work
task = Task(description="Implement a JWT auth middleware in Python")
role = Role(name="DEV")
constraints = TaskConstraints(rubric={"security": "critical"})

# 2. Execute (Conceptual)
# In production, this is typically triggered via NATS events
result = await orchestrator.execute(role, task, constraints)

print(f"Winner: {result['winner'].proposal.content}")
```

### Distributed Execution (Ray + NATS)

The system uses `DeliberateAsync` to offload heavy LLM inference to the Ray cluster:

1.  **Request**: Orchestrator sends `ExecuteDeliberationRequest` (gRPC) to Ray Executor.
2.  **Execution**: Ray Workers (vLLM) process the prompts.
3.  **Result**: Results are published back to NATS streams (`agent.responses`).

## 🔌 Integration & Consumers

This core module is primarily consumed by **`services/orchestrator`**, which wraps the domain logic in a gRPC server and provides the infrastructure plumbing.

*   **Service Wrapper**: `services/orchestrator/server.py`
*   **Usage Pattern**:
    *   Initializes `DeliberateAsync` with injected gRPC/NATS adapters.
    *   Initializes `Orchestrate` use case with a registry of `Councils`.
    *   Exposes RPCs (`Deliberate`, `Orchestrate`) that delegate directly to core use cases.
    *   Handles `CreateCouncil`/`RegisterAgent` via `AgentFactory` ports (which may instantiate `VLLMAgent` or `MockAgent` from core config).

## 🛠 Current Implementation Status

*   **Domain Layer**: Mature. `Agent`, `Task`, `DeliberationResult`, and `Scoring` logic are well-defined.
*   **Use Cases**:
    *   `DeliberateAsync` is the primary path for cluster execution.
    *   `PeerDeliberation` contains the core logic for multi-turn refinement.
*   **Adapters**: Currently relies on direct gRPC stubs (in `DeliberateAsync`) rather than separated adapter classes in `adapters/`.
