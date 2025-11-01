# VLLMAgent - Diagramas de Secuencia

**Versión**: Impresión
**Fecha**: 26 Oct 2025
**Última actualización**: 50fb174

---

## 📋 Tabla de Contenidos

1. [Flujo Principal: execute_task() (Estático)](#1-flujo-principal-execute_task-estático)
2. [Flujo Iterativo: execute_task() (ReAct)](#2-flujo-iterativo-execute_task-react)
3. [Generación de Plan con vLLM](#3-generación-de-plan-con-vllm)
4. [Ejecución de Tools](#4-ejecución-de-tools)

---

## 1. Flujo Principal: execute_task() (Estático)

Este es el flujo por defecto donde el agente:
1. Genera un plan completo (usando vLLM o patrón simple)
2. Ejecuta todas las operaciones en secuencia
3. Retorna resultado con audit trail

```mermaid
sequenceDiagram
    participant RayExecutor
    participant VLLMAgent
    participant GeneratePlanUseCase
    participant VLLMClientAdapter
    participant Tools (FileTool, GitTool, TestTool)
    participant AgentResult

    RayExecutor->>VLLMAgent: execute_task(task, context, constraints)
    VLLMAgent->>VLLMAgent: _execute_task_static(task, context)

    Note over VLLMAgent: Generate Execution Plan
    VLLMAgent->>GeneratePlanUseCase: execute(task, context, role, tools)
    GeneratePlanUseCase->>VLLMClientAdapter: generate(system_prompt, user_prompt)
    VLLMClientAdapter->>VLLMClientAdapter: Call vLLM API
    VLLMClientAdapter-->>GeneratePlanUseCase: JSON plan response
    GeneratePlanUseCase-->>VLLMAgent: ExecutionPlan(steps, reasoning)

    Note over VLLMAgent: Execute Tools Sequentially
    VLLMAgent->>VLLMAgent: For each step in plan:
    VLLMAgent->>Tools: Execute tool operation
    Tools-->>VLLMAgent: Operation result

    Note over VLLMAgent: Collect Results
    VLLMAgent->>VLLMAgent: Add operation to audit trail
    VLLMAgent->>VLLMAgent: Collect artifacts
    VLLMAgent->>AgentResult: Create result object
    VLLMAgent-->>RayExecutor: AgentResult(success, operations, artifacts)
```

---

## 2. Flujo Iterativo: execute_task() (ReAct)

Flujo ReAct (Reasoning + Acting) donde el agente:
1. Ejecuta una acción
2. Observa el resultado
3. Decide la siguiente acción
4. Repite hasta completar o fallar

```mermaid
sequenceDiagram
    participant RayExecutor
    participant VLLMAgent
    participant GenerateNextActionUseCase
    participant VLLMClientAdapter
    participant Tools
    participant Observation History

    RayExecutor->>VLLMAgent: execute_task(task, context, {"iterative": True})
    VLLMAgent->>VLLMAgent: _execute_task_iterative(task, context)

    loop Until done or max_iterations
        Note over VLLMAgent: Decide Next Action (ReAct)
        VLLMAgent->>GenerateNextActionUseCase: execute(task, observations, completed_ops)
        GenerateNextActionUseCase->>VLLMClientAdapter: generate(system_prompt, user_prompt)
        VLLMClientAdapter-->>GenerateNextActionUseCase: {"done": false, "step": {...}}
        GenerateNextActionUseCase-->>VLLMAgent: NextAction(step, reasoning)

        Note over VLLMAgent: Execute Action
        VLLMAgent->>Tools: Execute operation from NextAction
        Tools-->>VLLMAgent: Result

        Note over VLLMAgent: Observe & Learn
        VLLMAgent->>ObservationHistory: Add observation(result)
        VLLMAgent->>VLLMAgent: Update reasoning_log

        alt Task Complete
            VLLMAgent->>VLLMAgent: break loop
        else Continue
            VLLMAgent->>VLLMAgent: continue loop
        end
    end

    VLLMAgent->>AgentResult: Create result
    VLLMAgent-->>RayExecutor: AgentResult(success, operations, artifacts)
```

---

## 3. Generación de Plan con vLLM

Detalle del proceso de generación de plan usando arquitectura hexagonal:

```mermaid
sequenceDiagram
    participant VLLMAgent
    participant GeneratePlanUseCase
    participant LLMClientPort (Interface)
    participant VLLMClientAdapter
    participant vLLM Server
    participant ExecutionPlan

    VLLMAgent->>GeneratePlanUseCase: execute(task, context, role, available_tools)

    Note over GeneratePlanUseCase: Build Prompts
    GeneratePlanUseCase->>GeneratePlanUseCase: Build system_prompt (role-specific)
    GeneratePlanUseCase->>GeneratePlanUseCase: Build user_prompt (task + context + tools)

    Note over GeneratePlanUseCase: Call LLM via Port
    GeneratePlanUseCase->>LLMClientPort: generate(system_prompt, user_prompt, temp, max_tokens)
    LLMClientPort->>VLLMClientAdapter: generate(...)

    Note over VLLMClientAdapter: API Call to vLLM
    VLLMClientAdapter->>VLLMClientAdapter: Prepare payload
    VLLMClientAdapter->>vLLM Server: POST /v1/chat/completions
    vLLM Server-->>VLLMClientAdapter: JSON response
    VLLMClientAdapter->>VLLMClientAdapter: Parse response
    VLLMClientAdapter-->>LLMClientPort: Generated text
    LLMClientPort-->>GeneratePlanUseCase: Raw LLM response

    Note over GeneratePlanUseCase: Parse & Validate
    GeneratePlanUseCase->>GeneratePlanUseCase: Extract JSON from markdown
    GeneratePlanUseCase->>GeneratePlanUseCase: Parse steps and reasoning
    GeneratePlanUseCase->>GeneratePlanUseCase: Create ExecutionPlan
    GeneratePlanUseCase->>ExecutionPlan: Initialize with steps
    GeneratePlanUseCase-->>VLLMAgent: ExecutionPlan(steps, reasoning)
```

---

## 4. Ejecución de Tools

Proceso de ejecución de herramientas con patrones de seguridad por rol:

```mermaid
sequenceDiagram
    participant VLLMAgent
    participant ToolExecutorAdapter
    participant ToolInterface (ABC)
    participant FileTool
    participant GitTool
    participant TestTool
    participant AuditCallback

    VLLMAgent->>ToolExecutorAdapter: execute_operation(operation)

    Note over ToolExecutorAdapter: Route to Correct Tool
    ToolExecutorAdapter->>ToolExecutorAdapter: Get tool from registry

    alt Operation is "read_file"
        ToolExecutorAdapter->>FileTool: read_file(path)
        FileTool->>FileTool: Validate path exists
        FileTool->>FileTool: Read file contents
        FileTool-->>ToolExecutorAdapter: File contents
    else Operation is "write_file"
        alt Role is DEV
            ToolExecutorAdapter->>FileTool: write_file(path, content)
            FileTool->>FileTool: Validate write permissions
            FileTool->>FileTool: Backup original
            FileTool->>FileTool: Write new content
            FileTool-->>ToolExecutorAdapter: Success
        else Role is QA (read-only)
            ToolExecutorAdapter-->>VLLMAgent: Error: Write not allowed for QA
        end
    else Operation is "git.commit"
        ToolExecutorAdapter->>GitTool: commit(message)
        GitTool->>GitTool: Stage changes
        GitTool->>GitTool: Create commit
        GitTool->>AuditCallback: audit_entry(commit_data)
        GitTool-->>ToolExecutorAdapter: Commit SHA
    else Operation is "pytest"
        ToolExecutorAdapter->>TestTool: pytest(path, markers)
        TestTool->>TestTool: Run tests
        TestTool->>TestTool: Parse results
        TestTool-->>ToolExecutorAdapter: Test results
    end

    Note over ToolExecutorAdapter: Wrap Result
    ToolExecutorAdapter->>ToolExecutorAdapter: Create OperationResult
    ToolExecutorAdapter-->>VLLMAgent: OperationResult(success, data, error)

    Note over VLLMAgent: Update Audit Trail
    VLLMAgent->>AuditCallback: audit_entry(operation, result)
    VLLMAgent->>AgentResult: Add operation to result
```

---

## 🔍 Detalles Arquitectónicos

### Arquitectura Hexagonal Aplicada

**Domain Layer (Ports):**
- `LLMClientPort`: Interface para generación de texto
- `ToolExecutorPort`: Interface para ejecución de herramientas

**Application Layer (Use Cases):**
- `GeneratePlanUseCase`: Genera planes de ejecución
- `GenerateNextActionUseCase`: Decide siguiente acción (ReAct)
- `ExecutePlanUseCase`: Ejecuta plan completo
- `ExecuteOperationUseCase`: Ejecuta operación individual

**Infrastructure Layer (Adapters):**
- `VLLMClientAdapter`: Implementa `LLMClientPort` con llamadas a API vLLM
- `ToolExecutorAdapter`: Implementa `ToolExecutorPort` con herramientas reales

### Patrones de Seguridad por Rol

```mermaid
graph LR
    A[Agent Role] -->|DEV| B[Full Access]
    A -->|QA| C[Read + Test]
    A -->|ARCHITECT| D[Read + Analyze]
    A -->|DEVOPS| E[Build + Deploy]
    A -->|DATA| F[Schema + Query]

    B --> G[files.write, git.commit]
    C --> H[files.read, tests.pytest]
    D --> I[files.read, git.log]
    E --> J[docker.build, http.get]
    F --> K[db.query, files.read]
```

### Flujo de Auditoría

```mermaid
sequenceDiagram
    participant ToolExecution
    participant AuditEntry
    participant AgentResult
    participant Monitoring Service

    ToolExecution->>AuditEntry: Create entry(operation, result)
    AuditEntry->>AuditEntry: Capture timestamp, success, data
    AuditEntry->>AgentResult: Add to audit_trail

    Note over AgentResult: After task completion
    AgentResult->>Monitoring Service: Report audit trail
    Monitoring Service->>Monitoring Service: Store in Neo4j
    Monitoring Service->>Monitoring Service: Update metrics
```

---

## 📊 Estadísticas de Ejecución

| Operación | Tiempo Promedio | Tokens Usados | API Calls |
|-----------|----------------|---------------|-----------|
| Generate Plan | 500ms | 2K | 1 |
| Read File | 50ms | 0 | 0 |
| Write File | 100ms | 0 | 0 |
| Run Tests | 5s | 0 | 0 |
| Git Commit | 200ms | 0 | 0 |
| **Task completo** | **10-30s** | **2-4K** | **1-10** |

---

## 🎯 Ejemplo Real: "Add JWT Authentication"

```mermaid
sequenceDiagram
    participant ContextService
    participant VLLMAgent
    participant vLLM
    participant FileTool
    participant GitTool
    participant TestTool

    ContextService->>VLLMAgent: GetContext(story="US-123", role="DEV")
    ContextService-->>VLLMAgent: Smart Context (2K tokens)

    VLLMAgent->>vLLM: Generate plan("Add JWT", context)
    vLLM-->>VLLMAgent: Plan: [read, edit, test, commit]

    VLLMAgent->>FileTool: read_file("src/auth/middleware.py")
    FileTool-->>VLLMAgent: Current middleware code

    VLLMAgent->>FileTool: edit_file("src/auth/middleware.py", old, new)
    FileTool-->>VLLMAgent: File updated

    VLLMAgent->>TestTool: pytest("tests/auth/")
    TestTool-->>VLLMAgent: Tests passed

    VLLMAgent->>GitTool: commit("feat: add JWT authentication")
    GitTool-->>VLLMAgent: commit_sha="abc123"

    VLLMAgent-->>ContextService: Result: success, operations, artifacts
```

---

## 🔄 Relación con Otros Componentes

```mermaid
graph TB
    subgraph "SWE AI Fleet System"
        A[Context Service] -->|Smart Context| B[VLLMAgent]
        B -->|Plan/Execute| C[Tools]
        B -->|Results| D[Monitoring Service]
        D -->|Store| E[Neo4j Graph]
        D -->|Metrics| F[NATS Stream]
    end

    subgraph "Agent Internals (Hexagonal)"
        B --> G[GeneratePlanUseCase]
        B --> H[GenerateNextActionUseCase]
        G --> I[VLLMClientAdapter]
        H --> I
        I --> J[vLLM Server]
    end
```

---

**Documento generado para impresión**
**Sistema**: SWE AI Fleet
**Componente**: VLLMAgent
**Arquitectura**: Hexagonal (Ports & Adapters)
**Patrón**: ReAct (Reasoning + Acting)

