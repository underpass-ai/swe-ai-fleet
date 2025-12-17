# System Architecture Overview

**SWE AI Fleet** is a production-grade, autonomous software engineering platform. It differentiates itself from traditional "copilots" by using a **Decision-Centric Architecture** rather than just a code-centric one.

## 🧠 The Core Thesis: Decision-Centric AI

Traditional coding assistants (like Copilot) rely on "Code Context"—feeding the LLM the surrounding lines of code. This often leads to hallucinations or code that looks correct but violates architectural patterns.

**SWE AI Fleet** relies on **Decision Context**. We maintain a Knowledge Graph that captures:
1.  **Why** a component exists (linked to Epic/Story).
2.  **What** decisions were made in the past (e.g., "Use OAuth2", "Switch to Neo4j").
3.  **How** components relate to each other.

When an agent starts a task, it doesn't just get code; it gets a **Surgical Context** (~4k tokens) containing the relevant history, decisions, and constraints.

---

## 🏗️ High-Level Architecture

The system follows a **Microservices Architecture** with strict **Hexagonal (Ports & Adapters)** enforcement.

```mermaid
graph TB
    User((User/PO))

    subgraph "Control Plane (K8s)"
        UI[PO UI]
        Planning[Planning Service]
        Workflow[Workflow Service]
    end

    subgraph "Intelligence Plane (K8s)"
        Context[Context Service]
        Orchestrator[Orchestrator Service]
    end

    subgraph "Compute Plane (Ray Cluster)"
        Executor[Ray Executor Service]
        Workers[Ray Workers (GPU)]
    end

    subgraph "Data Plane"
        Neo4j[(Neo4j Graph)]
        NATS[NATS JetStream]
        Redis[(Redis/Valkey)]
    end

    User --> UI
    UI --> Planning

    Planning --"1. Plan Approved"--> NATS
    NATS --"2. Derive Tasks"--> TaskDerivation[Task Derivation]
    TaskDerivation --> Executor

    Executor --"3. Agent Execution"--> Workers
    Workers --"4. Rehydrate"--> Context
    Context --> Neo4j

    Workers --"5. Deliberate"--> Orchestrator
    Orchestrator --> Executor
```

### Layers

1.  **Control Plane**: Manages the "What".
    -   **Planning Service**: Manages User Stories, Epics, and Plans.
    -   **Workflow Service**: Tracks the lifecycle state of tasks (FSM) and enforces RBAC.

2.  **Intelligence Plane**: Manages the "Why" and "How".
    -   **Context Service**: The "Brain". Rehydrates session context from the Graph.
    -   **Orchestrator Service**: The "Conductor". Manages Multi-Agent Councils and Deliberation.

3.  **Compute Plane**: The "Muscle".
    -   **Ray Cluster**: Distributed GPU computing.
    -   **Ray Executor**: Gateway to the cluster. Runs `VLLMAgent` instances.

4.  **Data Plane**:
    -   **Neo4j**: Stores the Knowledge Graph (Nodes + Decision Edges).
    -   **NATS JetStream**: Asynchronous Event Bus (Domain Events).
    -   **Redis (Valkey)**: Fast state cache and ephemeral data.

---

## 🗝️ Key Concepts

### 1. Hexagonal Architecture
Every service and core module strictly separates **Domain** (Business Logic) from **Infrastructure** (Adapters).
- **Domain**: Pure Python/Go. No DB imports, no HTTP calls.
- **Ports**: Interfaces defining *what* the domain needs.
- **Adapters**: Implementations (Neo4jAdapter, NATSAdapter) injected at runtime.

### 2. Multi-Agent Deliberation ("The Council")
We do not rely on a single zero-shot generation. Tasks are executed by a **Council of Agents**:
1.  **Generate**: Multiple agents propose solutions.
2.  **Critique**: Peer agents review proposals against a rubric.
3.  **Revise**: Authors improve their code.
4.  **Select**: An Architect agent (or logic) picks the winner.

### 3. Surgical Context
Instead of flooding the context window with 100k tokens, we use the **Context Service** to assemble a focused prompt (~2k-5k tokens) specific to the **Role** (Dev, QA, Architect) and **Task**.

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Languages** | Python 3.13+ (Intelligence), Go (Control Plane) |
| **Runtime** | Kubernetes (K8s), Ray (Distributed Compute) |
| **Messaging** | NATS JetStream |
| **Database** | Neo4j (Graph), Valkey (Redis-compatible) |
| **Inference** | vLLM (Serving Qwen, Llama 3, etc.) |
| **Frontend** | React + Tailwind |


