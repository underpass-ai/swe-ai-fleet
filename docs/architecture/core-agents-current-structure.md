# Core Agents - Current Structure Analysis

**Date**: 2025-01-27
**Branch**: hexagonal-refactor-v2
**Status**: Analysis Phase

## Current Structure

```
core/agents/
├── __init__.py                    # Exports: AgentResult, AgentThought, VLLMAgent
├── vllm_agent.py                  # Main agent class (1306 lines)
├── vllm_client.py                 # vLLM API client (290 lines)
├── profile_loader.py              # Role-specific model profiles
└── [archives from failed attempt]
    ├── application/
    ├── infrastructure/
    └── domain/ (deleted)
```

## Architecture Diagrams

### 1. Current Module Structure

```mermaid
graph TB
    subgraph "core.agents"
        VLLMAgent[VLLMAgent<br/>1306 lines]
        VLLMClient[VLLMClient<br/>290 lines]
        ProfileLoader[profile_loader.py]

        VLLMAgent --> VLLMClient
        VLLMAgent --> ProfileLoader

        subgraph "Embedded Classes"
            AgentResult[AgentResult]
            AgentThought[AgentThought]
            ExecutionPlan[ExecutionPlan]
        end

        VLLMAgent -.contains.-> AgentResult
        VLLMAgent -.contains.-> AgentThought
        VLLMAgent -.contains.-> ExecutionPlan
    end

    subgraph "core.tools"
        FileTool[FileTool]
        GitTool[GitTool]
        TestTool[TestTool]
        HttpTool[HttpTool]
        DockerTool[DockerTool]
        DatabaseTool[DatabaseTool]
    end

    VLLMAgent --> FileTool
    VLLMAgent --> GitTool
    VLLMAgent --> TestTool
    VLLMAgent --> HttpTool
    VLLMAgent --> DockerTool
    VLLMAgent --> DatabaseTool

    style VLLMAgent fill:#ff9999
    style VLLMClient fill:#99ccff
    style AgentResult fill:#ffcc99
    style AgentThought fill:#ffcc99
    style ExecutionPlan fill:#ffcc99
```

### 2. VLLMAgent Internal Structure

```mermaid
graph LR
    subgraph "VLLMAgent Class (1306 lines)"
        subgraph "Initialization"
            Init[__init__]
            Workspace[workspace_path]
            Role[role]
            VLLMURL[vllm_url]
            Tools[enable_tools]
        end

        subgraph "Core Methods"
            ExecuteTask[execute_task]
            ExecuteStatic[_execute_task_static]
            ExecuteIterative[_execute_task_iterative]
            DecideNext[_decide_next_action]
            GeneratePlan[_generate_plan]
        end

        subgraph "Planning Methods"
            PlanAddFunction[_plan_add_function]
            PlanFixBug[_plan_fix_bug]
            PlanRunTests[_plan_run_tests]
        end

        subgraph "Helper Methods"
            LogThought[_log_thought]
            IsReadOnly[_is_read_only_operation]
            SummarizeResult[_summarize_result]
            CollectArtifacts[_collect_artifacts]
        end

        Init --> ExecuteTask
        ExecuteTask --> ExecuteStatic
        ExecuteTask --> ExecuteIterative
        ExecuteStatic --> GeneratePlan
        ExecuteStatic --> ExecuteIterative
        GeneratePlan --> PlanAddFunction
        GeneratePlan --> PlanFixBug
        GeneratePlan --> PlanRunTests
        ExecuteIterative --> DecideNext
        ExecuteIterative --> LogThought
        ExecuteIterative --> SummarizeResult
        ExecuteIterative --> CollectArtifacts
    end

    style ExecuteTask fill:#ff9999
    style GeneratePlan fill:#99ccff
```

### 3. Data Flow - Agent Execution

```mermaid
sequenceDiagram
    participant User
    participant VLLMAgent
    participant VLLMClient
    participant FileTool
    participant GitTool
    participant TestTool

    User->>VLLMAgent: execute_task("Add function", context)

    VLLMAgent->>VLLMClient: generate_plan(task, context, role)
    VLLMClient-->>VLLMAgent: ExecutionPlan

    VLLMAgent->>FileTool: read_file("src/utils.py")
    FileTool-->>VLLMAgent: file_content

    VLLMAgent->>FileTool: append_file("src/utils.py", content)
    FileTool-->>VLLMAgent: success

    VLLMAgent->>TestTool: pytest(TESTS_PATH)
    TestTool-->>VLLMAgent: test_results

    VLLMAgent->>GitTool: status()
    GitTool-->>VLLMAgent: git_status

    VLLMAgent-->>User: AgentResult(success, operations, artifacts)
```

### 4. Current Class Dependencies

```mermaid
graph TB
    subgraph "VLLMAgent Dependencies"
        VLLM[VLLMAgent<br/>- vllm_client: VLLMClient<br/>- agent_id, role, workspace<br/>- tools dict]

        subgraph "Embedded Data Classes"
            AR[AgentResult<br/>- success: bool<br/>- operations: list[dict]<br/>- artifacts: dict<br/>- audit_trail: list<br/>- reasoning_log: list]

            AT[AgentThought<br/>- reasoning_log: list<br/>- iteration, thought_type<br/>- content, related_ops<br/>- confidence]

            EP[ExecutionPlan<br/>- steps: list[dict]<br/>- reasoning: str]
        end

        VLLM --> AR
        VLLM --> AT
        VLLM --> EP

        subgraph "External Imports"
            Tools[core.tools.*]
            VLLMClient[VLLMClient]
            Profile[profile_loader]
        end

        VLLM --> Tools
        VLLM --> VLLMClient
        VLLM --> Profile
    end

    style VLLM fill:#ff9999
    style AR fill:#ffcc99
    style AT fill:#ffcc99
    style EP fill:#ffcc99
```

### 5. Test Coverage Map

```mermaid
graph LR
    subgraph "Tests"
        TU[test_vllm_agent_unit.py<br/>~30 tests]
        TG[test_vllm_agent_gaps.py<br/>~10 tests]
    end

    subgraph "Under Test"
        VLLM[VLLMAgent]
        Client[VLLMClient]
        Profiles[ProfileLoader]
    end

    subgraph "Mocks"
        MockFile[Mock FileTool]
        MockGit[Mock GitTool]
        MockTest[Mock TestTool]
    end

    TU --> VLLM
    TG --> VLLM
    TU -.mocks.-> MockFile
    TU -.mocks.-> MockGit
    TU -.mocks.-> MockTest

    style VLLM fill:#ff9999
    style TU fill:#99ff99
    style TG fill:#99ff99
```

### 6. Current Issues Summary

```mermaid
mindmap
  root((Current Issues))
    Structure
      Flat organization
      Everything in vllm_agent.py
      No clear separation
    Embedded Classes
      AgentResult in vllm_agent.py
      AgentThought in vllm_agent.py
      ExecutionPlan in vllm_agent.py
    Data Structures
      operations: list[dict]
      artifacts: dict
      audit_trail: list
    Testing
      1340 passing
      17 failing (after reorganization)
    Dependencies
      Coupled to core.tools
      Direct imports everywhere
    Refactoring Attempt
      hexagonal-refactor_failed
      application/ domain/ infrastructure/
      Not commited to main
```

## File Statistics

### core/agents/vllm_agent.py
- **Lines**: 1,306
- **Classes**:
  - `AgentResult` (dataclass)
  - `AgentThought` (dataclass)
  - `ExecutionPlan` (dataclass)
  - `VLLMAgent` (main class)
- **Methods**: ~30 public/private methods
- **Dependencies**: core.tools, VLLMClient, profile_loader

### core/agents/vllm_client.py
- **Lines**: 290
- **Classes**: `VLLMClient`
- **Methods**: generate(), decide_next_action()
- **Dependencies**: aiohttp, VLLM API

### core/agents/profile_loader.py
- **Lines**: ~200
- **Function**: get_profile_for_role()
- **Dependencies**: yaml files in core/models/profiles/

## Key Findings

1. **Monolithic Design**: 1306 lines in one file with embedded classes
2. **Mixed Concerns**: Domain logic, application logic, and infrastructure mixed
3. **Strong Coupling**: Direct dependencies on core.tools, VLLMClient
4. **Data as Dicts**: operations, artifacts stored as dicts (not type-safe)
5. **Test Gap**: 17/1357 tests failing after reorganization attempt

## Recommendations

### Phase 1: Prepare (Now)
- ✅ Document current structure (this file)
- ⏸️ Identify real domain entities vs utilities
- ⏸️ Map all dependencies

### Phase 2: Incremental Refactor
- Start small: Extract one class at a time
- Run tests after each change
- Don't reorganize directories yet
- Focus on separation of concerns

### Phase 3: DDD Where It Makes Sense
- AgentResult, ExecutionPlan → Real entities
- Everything else → Keep simple

**Estimated Effort**: 3-5 days for basic refactor, 2-3 weeks for full hexagonal

