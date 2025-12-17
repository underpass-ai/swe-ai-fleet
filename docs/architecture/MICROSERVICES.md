# Microservices Reference

The SWE AI Fleet is composed of several deployable microservices. Each service follows **Hexagonal Architecture** and communicates via **gRPC** (synchronous) and **NATS JetStream** (asynchronous).

## 1. Planning Service (`services/planning`)
**"The Project Manager"**

Responsible for the high-level definition of work.
-   **Responsibilities**:
    -   Manages the hierarchy: `Project` → `Epic` → `Story` → `Plan`.
    -   Implements the Story Lifecycle FSM (Draft → PO Review → Planned).
    -   Triggers Task Derivation when a Plan is approved.
-   **Key Tech**: Python, Neo4j, Valkey.
-   **Events Published**: `planning.story.created`, `planning.plan.approved`.

## 2. Workflow Service (`services/workflow`)
**"The Traffic Controller"**

Responsible for the execution lifecycle of individual Tasks.
-   **Responsibilities**:
    -   Manages the Task Lifecycle FSM (ToDo → In Progress → Review → Done).
    -   Enforces **RBAC** (Role-Based Access Control) on transitions (e.g., only Architect can approve designs).
    -   Maintains an immutable audit trail of state changes.
-   **Key Tech**: Python, Neo4j (Audit), Valkey (State Cache).

## 3. Orchestrator Service (`services/orchestrator`)
**"The Execution Engine"**

The runtime environment for Multi-Agent Councils.
-   **Responsibilities**:
    -   Receives `DeliberationRequest` via gRPC.
    -   Coordinates the Generate-Critique-Revise loop.
    -   Dispatches jobs to the **Ray Executor**.
-   **Key Tech**: Python, NATS.

## 4. Context Service (`services/context`)
**"The Brain"**

Provides surgical context to agents.
-   **Responsibilities**:
    -   **Rehydration**: Fetches relevant graph data and state for a session.
    -   **Prompt Assembly**: Builds token-optimized prompts.
    -   **Graph Updates**: Writes new decisions and artifacts back to Neo4j.
-   **Key Tech**: Python, Neo4j, Valkey.

## 5. Ray Executor (`services/ray_executor`)
**"The Compute Gateway"**

Bridges the K8s control plane with the Ray GPU cluster.
-   **Responsibilities**:
    -   Submits jobs to Ray Head Node via Ray Client.
    -   Monitors job status.
    -   Streams execution logs back to NATS.
-   **Key Tech**: Python, Ray Client.

## 6. Task Derivation Service (`services/task_derivation`)
**"The Planner"**

A specialized worker that uses LLMs to break down Plans into Tasks.
-   **Responsibilities**:
    -   Listens for `planning.plan.approved`.
    -   Uses an "Architect" agent to decompose the plan.
    -   Generates a dependency graph of Tasks.
    -   Writes Tasks back to the Planning Service.
-   **Key Tech**: Python, NATS (Worker Pattern).
