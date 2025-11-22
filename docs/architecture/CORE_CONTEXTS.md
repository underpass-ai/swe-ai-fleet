# Core Bounded Contexts

The `core/` directory contains the reusable domain logic and libraries that power the SWE AI Fleet. These components are often shared between services or executed remotely on the Ray cluster.

## 1. Agents & Tools (`core.agents_and_tools`)

This context defines **what an agent is** and **what it can do**.

### 🤖 VLLM Agent
The primary agent implementation (`VLLMAgent`) designed to work with open-source models (Qwen, Llama) hosted on vLLM. It supports:
-   **Role-Based Configuration**: Agents are instantiated with a `Role` (e.g., DEV, ARCHITECT) which dictates their system prompt and permissions.
-   **Tool Use**: Can execute tools if enabled.
-   **Profiles**: Loads YAML-based profiles defining temperature, top_p, and model selection per role.

### 🛠️ ToolSet
A secure, audited set of tools for software engineering:
-   **Git**: Full version control (`clone`, `commit`, `push`, `branch`).
-   **File**: Safe filesystem access (`read`, `write`, `edit`, `grep`).
-   **Docker**: Container management (`build`, `run`, `exec`).
-   **Test**: Unified runner for `pytest`, `go test`, `npm test`.
-   **Audit**: Every tool execution is logged to Neo4j/Redis for traceability.

---

## 2. Context (`core.context`)

The **"Brain"** of the system. This module implements the **Decision-Centric Knowledge Graph**.

### 🧠 Graph Domain
It models the software lifecycle as a graph in Neo4j:
-   **Nodes**: `Project` → `Epic` → `Story` → `Task` → `Decision`.
-   **Edges**: `HAS_DECISION`, `DEPENDS_ON`, `IMPLEMENTS`.

### 🔄 Session Rehydration
The unique value proposition of SWE AI Fleet. Instead of naive RAG, it "rehydrates" a session by:
1.  Traversing the graph to find relevant decisions.
2.  Fetching ephemeral state from Valkey (Redis).
3.  Applying **PromptScopePolicy** (RBAC) to ensure the agent only sees what it needs.
4.  Assembling a surgical prompt (~4k tokens).

---

## 3. Orchestrator (`core.orchestrator`)

The **"Conductor"** of the multi-agent system. It implements the **Deliberation Patterns**.

### ⚖️ The Council
A group of agents that collaborate to solve a problem.
-   **Generate**: Agents produce initial solutions.
-   **Critique**: Agents review each other's work.
-   **Revise**: Agents improve based on feedback.
-   **Select**: The best solution is chosen.

### 🎯 Use Cases
-   **`OrchestrateUseCase`**: High-level coordination of a Task.
-   **`DeliberateUseCase`**: Peer review logic.
-   **`ArchitectSelector`**: Logic for choosing the "winner" proposal.

---

## 4. Ray Jobs (`core.ray_jobs`)

The **"Execution Payload"**. This context bridges the gap between the Kubernetes control plane and the Ray compute plane.

### 📦 Remote Execution
Code in this module is designed to be pickled and sent to the Ray Cluster.
-   **`RayAgentExecutor`**: The wrapper that runs on a Ray Worker.
-   ~~**`AgentJobWorker`**~~ (REMOVED): Was planned for autonomous loop (Pull model), but never implemented and has been removed.

It isolates the `services/ray_executor` (which submits jobs) from the actual code running on the GPU nodes.

