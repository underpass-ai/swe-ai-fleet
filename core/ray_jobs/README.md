# Core: Ray Jobs Bounded Context

## Overview

`core/ray_jobs` contains the **domain logic and execution adapters** for running AI Agent tasks on the Ray cluster.

This bounded context is designed to run **inside a Ray Worker**. It is responsible for the actual "thinking" and "acting" phase of an agent's lifecycle. It receives a task, connects to an LLM (via vLLM), optionally uses tools, and publishes the results back to the system (via NATS).

It strictly follows **Hexagonal Architecture (Ports & Adapters)** to decouple the execution logic from the underlying infrastructure (Ray, NATS, vLLM).

---

## 🏗 Architecture

### Layers

1.  **Domain Layer** (`domain/`)
    *   **Entities & Value Objects**: `AgentTask`, `ExecutionRequest`, `AgentResult`, `AgentConfig`.
    *   **Ports (Interfaces)**:
        *   `IResultPublisher`: Contract for sending results back (e.g., to NATS).
        *   `IVLLMClient`: Contract for generating text via an LLM.
        *   `IAsyncExecutor`: Contract for handling async execution within synchronous Ray workers.
    *   *Responsibility*: Pure business logic, validation, and defining the "what".

2.  **Application Layer** (`application/`)
    *   **Use Cases**:
        *   `ExecuteAgentTask`: The primary coordinator. Orchestrates the flow: Connect -> Decide Strategy (Tools vs. Text) -> Execute -> Publish Result.
        *   `GenerateProposal`: specialized logic for text-only planning/reasoning.
    *   *Responsibility*: Orchestration of domain objects and ports.

3.  **Infrastructure Layer** (`infrastructure/`)
    *   **Adapters**:
        *   `RayAgentExecutor`: The **Entry Point**. A thin synchronous wrapper that Ray calls. It injects dependencies and delegates to the Use Case.
        *   `NATSResultPublisher`: Implements `IResultPublisher` using NATS JetStream.
        *   `VLLMHTTPClient`: Implements `IVLLMClient` to talk to a vLLM server via HTTP.
        *   `AsyncioExecutor`: Implements `IAsyncExecutor` to run asyncio loops.

---

## 🔑 Key Components

### RayAgentExecutor
This is the main class exposed to the Ray cluster. It acts as the **Infrastructure Adapter** for Ray.

**Role:**
*   Initializes the environment.
*   Injects concrete adapters (`NATSResultPublisher`, `VLLMHTTPClient`) into the Use Case.
*   Provides a synchronous `run()` method that Ray can execute without complexity.

### ExecuteAgentTask (Use Case)
The brain of the operation. It handles:
1.  **Strategy Selection**: Checks `AgentConfig.enable_tools`.
    *   If `True`: Delegates to `VLLMAgent` (tool-enabled execution).
    *   If `False`: Delegates to `GenerateProposal` (text-only reasoning).
2.  **Result Publishing**: Ensures success/failure events are sent to NATS streams (`agent.response.completed`, `agent.response.failed`).
3.  **Error Handling**: Catches exceptions and ensures a valid `FailureResult` is reported.

---

## 🔌 Integration

### With vLLM
This context assumes a **vLLM Service** is reachable via HTTP.
*   The `VLLMHTTPClient` sends chat completion requests to `{vllm_url}/v1/chat/completions`.
*   It handles timeouts and response parsing.

### With NATS
This context acts as a **Publisher**.
*   It connects to NATS JetStream to publish results.
*   Streams used: `agent.response.*`

### With Ray
This code is meant to be packaged and pickled by Ray.
*   The `RayAgentExecutor` is instantiated on a Ray Head or Worker.
*   Its `run()` method is the "Job" payload.

---

## 💻 Usage Example

This is how the `RayAgentExecutor` is typically instantiated and run (usually by a higher-level service or a Ray Remote Function wrapper):

```python
from core.ray_jobs.infrastructure.adapters import (
    RayAgentExecutor,
    NATSResultPublisher,
    VLLMHTTPClient,
    AsyncioExecutor
)
from core.ray_jobs.domain import AgentConfig, AgentRole

# 1. Configure dependencies
config = AgentConfig(
    agent_id="agent-123",
    role=AgentRole.DEV,
    model="meta-llama/Meta-Llama-3-8B-Instruct",
    vllm_url="http://vllm-server:8000",
    enable_tools=False
)

publisher = NATSResultPublisher(nats_url="nats://nats:4222")
vllm_client = VLLMHTTPClient(
    vllm_url=config.vllm_url,
    agent_id=config.agent_id,
    role=str(config.role),
    model=config.model
)
async_executor = AsyncioExecutor()

# 2. Instantiate Executor (The Adapter)
executor = RayAgentExecutor(
    config=config,
    publisher=publisher,
    vllm_client=vllm_client,
    async_executor=async_executor
)

# 3. Run Task (Synchronous call for Ray)
result = executor.run(
    task_id="task-abc-789",
    task_description="Implement a binary search tree in Python",
    constraints={"language": "python", "timeout": 120}
)

print(f"Execution Result: {result['status']}")
```
