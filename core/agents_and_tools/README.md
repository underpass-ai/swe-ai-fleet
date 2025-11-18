# Agents & Tools Bounded Context

The **Agents & Tools** bounded context is the "doing" arm of the SWE AI Fleet. It provides the autonomous agents, their capabilities (tools), and the infrastructure to execute tasks safely within an isolated environment.

## 🎯 Core Responsibilities

1.  **Autonomous Agents**: Providing the `VLLMAgent` implementation that combines LLM reasoning with tool execution.
2.  **Tool Execution**: A comprehensive, safe, and auditable toolset (Git, Docker, Files, Tests) for software engineering tasks.
3.  **Safety & Isolation**: Enforcing RBAC (Role-Based Access Control) and running operations within isolated workspaces/containers.
4.  **Infrastructure Abstraction**: Following Hexagonal Architecture to decouple domain logic from external services (vLLM, File System, Docker Daemon).

---

## 🏗 Architecture

This context strictly follows **Hexagonal Architecture (Ports & Adapters)** and **Domain-Driven Design (DDD)**.

```mermaid
graph TD
    subgraph Domain
        Agent[Agent (Aggregate)]
        Capabilities[AgentCapabilities]
        Plan[ExecutionPlan]
        Tools[ToolRegistry]
        Ports[Ports]
    end

    subgraph Ports
        LLM[LLMClientPort]
        Exec[ToolExecutionPort]
    end

    subgraph Infrastructure
        VLLMAdapter[VLLMClientAdapter]
        ToolAdapter[ToolExecutionAdapter]
        ToolFactory[ToolFactory]
        Mappers[Mappers]
    end

    Agent --> Capabilities
    Agent --> Plan
    Agent --> Ports
    VLLMAdapter ..|> LLM
    ToolAdapter ..|> Exec
    ToolAdapter --> ToolFactory
```

### Layer Breakdown

*   **Domain (`domain/`)**: Contains core business logic, entities (`Agent`, `ExecutionPlan`, `Action`), and Port definitions. It knows *nothing* about infrastructure.
*   **Application (`application/`)**: Contains Use Cases (`ExecuteTaskUseCase`, `GeneratePlanUseCase`) that orchestrate the domain logic.
*   **Infrastructure (`infrastructure/`)**: Contains Adapters (`VLLMClientAdapter`, `ToolExecutionAdapter`) and concrete implementations.
*   **Tools (`tools/`)**: The actual tool implementations (`GitTool`, `FileTool`, `DockerTool`), treated as infrastructure plugins.

---

## 🤖 Agents

The primary entity is the **`VLLMAgent`** (`agents/vllm_agent.py`). Unlike traditional systems with separate classes for "DevAgent" or "TestAgent", we use a **Universal Agent** pattern where behavior is defined by **Roles** and **Profiles**.

### 1. Roles & RBAC
The `Agent` aggregate root enforces permissions. An agent's role determines what it *can* do:

| Role | Allowed Tools | Typical Actions |
|------|--------------|-----------------|
| **DEV** | Files, Git, Tests | Edit code, commit changes, run unit tests |
| **QA** | Files, Tests, HTTP | Write/run tests, validate APIs |
| **ARCHITECT** | Files, Git, DB | Analyze code, review designs (Read-Only focus) |
| **DEVOPS** | Docker, HTTP, Files | Build images, deploy, monitor |
| **DATA** | DB, Files | Run migrations, query data |

### 2. Profiles
Profiles (`resources/profiles/*.yaml`) define the LLM configuration for each role (Model, Temperature, Context Window).
*   *Example*: Architects use high-reasoning models (e.g., Databricks DBRX) with low temperature. Developers use coding models (e.g., DeepSeek Coder) with moderate temperature.

### 3. Execution Modes
*   **Static Planning**: Generates a full plan upfront, then executes.
*   **Iterative (ReAct)**: Executes a step, observes the result, then decides the next step.
*   **Read-Only**: Used for planning/analysis phases; write operations are blocked.

---

## 🛠 Tools

Tools are accessed via the `ToolExecutionPort`. All tools provide **Audit Trails**, **Input Validation**, and **Workspace Isolation**.

### ToolFactory
The `ToolFactory` (`infrastructure/adapters/tool_factory.py`) manages the lifecycle of tools. It supports lazy loading and dependency injection.

### Available Tools

#### 1. 📂 File Tool (`files`)
Safe file system manipulation within the workspace.
*   **Operations**: `read_file`, `write_file`, `edit_file` (search/replace), `search_in_files` (ripgrep), `diff_files`, `list_files`.
*   **Safety**: Prevents path traversal (`../../`), limits file sizes, blocks binary files.

#### 2. 🐙 Git Tool (`git`)
Complete git integration.
*   **Operations**: `clone`, `status`, `add`, `commit`, `push`, `pull`, `checkout`, `branch`, `diff`, `log`.
*   **Usage**:
    ```python
    # Domain-level usage via Port
    tool_port.execute_operation("git", "clone", {"repo_url": "..."})
    tool_port.execute_operation("git", "commit", {"message": "feat: add feature"})
    ```

#### 3. 🐳 Docker Tool (`docker`)
Advanced container management supporting Docker and Podman.
*   **Note**: Unlike other tools, `DockerTool` uses **DDD Value Objects** (`ContainerRunConfig`, `ContainerBuildConfig`) for strict configuration validation.
*   **Operations**: `build`, `run`, `exec`, `ps`, `logs`, `stop`, `rm`.
*   **Usage**:
    ```python
    from core.agents_and_tools.tools.domain.container_run_config import ContainerRunConfig

    # Requires Config Object
    config = ContainerRunConfig(image="python:3.11", command=["python", "app.py"])
    tool_port.execute_operation("docker", "run", {"config": config})
    ```

#### 4. 🧪 Test Tool (`tests`)
Unified test runner.
*   **Operations**: `pytest`, `go_test`, `npm_test`, `cargo_test`.
*   **Features**: Auto-parses output (JUnit XML), measures coverage.

#### 5. 🌐 HTTP Tool (`http`)
For external API interaction.
*   **Operations**: `get`, `post`, `put`, `delete`.

#### 6. 🗄 Database Tool (`db`)
*   **Operations**: `postgresql_query`, `redis_command`, `neo4j_query`.

---

## 🔌 Infrastructure Adapters

### VLLMClientAdapter
*   **Location**: `agents/infrastructure/adapters/vllm_client_adapter.py`
*   **Purpose**: Raw communication with vLLM servers.
*   **Responsibility**: Handles HTTP, retries, and JSON formatting. *No business logic.*

### ToolExecutionAdapter
*   **Location**: `agents/infrastructure/adapters/tool_execution_adapter.py`
*   **Purpose**: Implements `ToolExecutionPort`.
*   **Responsibility**: Delegates to `ToolFactory`, converts raw results into Domain Entities (`FileExecutionResult`, etc.).

### YamlProfileAdapter
*   **Location**: `agents/infrastructure/adapters/yaml_profile_adapter.py`
*   **Purpose**: Loads role configurations from YAML files.

---

## 🚦 Runner Integration

The tools are designed to run inside the **Runner** container.
*   **Workspace**: All tools operate relative to a strict `/workspace` root.
*   **Runner Tool**: A special tool (`tools/runner/runner_tool.py`) that orchestrates the execution of an entire task definition (TaskSpec) and returns a structured result (TaskResult).

## 📝 Developing New Tools

To add a new tool:
1.  **Define Domain**: Create Entities/Value Objects in `tools/domain/`.
2.  **Implement Tool**: Create `MyTool` class in `tools/` implementing `execute`.
3.  **Add to Enum**: Add to `ToolType` in `agents/domain/entities`.
4.  **Register**: Update `ToolFactory` to instantiate your tool.
5.  **Map**: Create a Mapper to convert raw results to Domain Entities.
6.  **Test**: Add unit tests in `tests/unit/tools/`.

## 🔒 Security & Audit

*   **Audit Log**: Every tool operation is logged via `audit_callback` (Redis/Neo4j/File).
*   **Fail-Fast**: Configuration objects and tools validate inputs immediately (`__post_init__`).
*   **Isolation**: Tools cannot access files outside the workspace.

