# VLLMAgent RBAC Integration

**Version:** 1.0
**Date:** 2025-11-04
**Status:** ✅ Production Ready

---

## 📋 Tabla de Contenidos

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [RBAC Components in VLLMAgent](#rbac-components-in-vllmagent)
4. [Capability Filtering](#capability-filtering)
5. [Usage Examples](#usage-examples)
6. [Security Model](#security-model)

---

## Overview

**VLLMAgent** es la puerta de entrada (infrastructure layer) que **contiene** y **usa** el **Agent aggregate root** (domain layer) para enforcement de RBAC.

### Key Points

- ✅ **VLLMAgent es Infrastructure** - Thin facade que delega al dominio
- ✅ **Agent es Domain** - Aggregate Root con lógica de negocio RBAC
- ✅ **Capabilities Auto-Filtered** - Por rol al momento de inicialización
- ✅ **Zero Configuration** - RBAC aplicado automáticamente
- ✅ **Tell, Don't Ask** - VLLMAgent delega decisiones al Agent

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                       │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                     VLLMAgent                          │  │
│  │  (Thin Facade - Delegates to Domain)                  │  │
│  │                                                        │  │
│  │  Initialization (line 194-285):                       │  │
│  │  1. Receive Role object from config                   │  │
│  │  2. Get all available capabilities                    │  │
│  │  3. Filter by role.allowed_tools                      │  │
│  │  4. Create Agent aggregate root                       │  │
│  │                                                        │  │
│  │  RBAC Enforcement Methods:                            │  │
│  │  • get_available_tools() → agent.capabilities         │  │
│  │  • can_execute(action) → agent.can_execute()          │  │
│  │  • can_use_tool(tool) → agent.can_use_tool()          │  │
│  └────────────────────────────────────────────────────────┘  │
│                             │                                 │
│                             │ delegates to                    │
│                             ▼                                 │
└──────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────┐
│                      Domain Layer                             │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Agent (Aggregate Root)                    │  │
│  │  (Business Logic - RBAC Enforcement)                   │  │
│  │                                                        │  │
│  │  Properties:                                           │  │
│  │  • agent_id: AgentId                                   │  │
│  │  • role: Role (with allowed_actions + allowed_tools)  │  │
│  │  • name: str                                           │  │
│  │  • capabilities: AgentCapabilities (RBAC-filtered)    │  │
│  │                                                        │  │
│  │  RBAC Business Logic:                                  │  │
│  │  • can_execute(action) -> bool                         │  │
│  │  • can_use_tool(tool) -> bool                          │  │
│  │  • can_execute_capability(cap) -> bool                 │  │
│  │  • get_executable_capabilities() -> list               │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## RBAC Components in VLLMAgent

### 1. Initialization (Lines 194-285)

VLLMAgent recibe un `Role` object y crea el Agent aggregate root con capabilities RBAC-filtered:

```python
# core/agents_and_tools/agents/vllm_agent.py

def __init__(
    self,
    config: AgentInitializationConfig,  # Contains role: Role
    llm_client_port: LLMClientPort,
    tool_execution_port: ToolExecutionPort,
    generate_plan_usecase: GeneratePlanUseCase,
    generate_next_action_usecase: GenerateNextActionUseCase,
    step_mapper: ExecutionStepMapper,
    execute_task_usecase: ExecuteTaskUseCase,
    execute_task_iterative_usecase: ExecuteTaskIterativeUseCase,
):
    # 1. Store Role value object (RBAC)
    self.role = config.role  # Role with allowed_actions + allowed_tools

    # ... other initialization ...

    # 2. Get ALL available capabilities from toolset
    all_capabilities = self.tool_execution_port.get_available_tools_description(
        enable_write_operations=self.enable_tools
    )

    # 3. Filter capabilities by role's allowed_tools (RBAC ENFORCEMENT)
    filtered_capabilities = all_capabilities.filter_by_allowed_tools(
        self.role.allowed_tools  # frozenset[str]
    )

    # 4. Create Agent aggregate root with RBAC-filtered capabilities
    self.agent = Agent(
        agent_id=AgentId(self.agent_id),
        role=self.role,
        name=f"{self.role.get_name()} Agent ({self.agent_id})",
        capabilities=filtered_capabilities,  # Only role-allowed tools
    )
```

**What Happens Here:**
1. **Role** contiene `allowed_tools: frozenset[str]` (e.g., `{"files", "git", "tests"}`)
2. **all_capabilities** tiene TODAS las tools disponibles (files, git, tests, docker, db, http)
3. **filter_by_allowed_tools()** filtra para mantener SOLO las tools permitidas por rol
4. **Agent** se crea con capabilities YA filtradas - NO puede acceder tools no permitidas

### 2. Get Available Tools (Lines 287-313)

Retorna capabilities RBAC-filtered del Agent:

```python
def get_available_tools(self) -> AgentCapabilities:
    """
    Get description of available tools and their operations (RBAC-filtered).

    Returns capabilities filtered by the agent's role permissions.
    Only tools that the role is allowed to use are included.
    """
    # Return RBAC-filtered capabilities from Agent aggregate root
    return self.agent.capabilities
```

**Example:**
```python
# Developer agent
developer_agent = VLLMAgent(config=dev_config)  # role=developer
tools = developer_agent.get_available_tools()
print(tools.tools.get_tool_names())  # ['files', 'git', 'tests'] ✅

# Architect agent
architect_agent = VLLMAgent(config=arch_config)  # role=architect
tools = architect_agent.get_available_tools()
print(tools.tools.get_tool_names())  # ['files', 'git', 'db', 'http'] ✅
# NOTE: Architect NO tiene 'docker' ❌
```

### 3. Can Execute Action (Lines 315-334)

Delega RBAC check al Agent aggregate root:

```python
def can_execute(self, action: Action) -> bool:
    """
    Check if agent can execute the given action (RBAC enforcement).

    Delegates to Agent aggregate root for RBAC logic.
    """
    return self.agent.can_execute(action)
```

**Example:**
```python
from core.agents_and_tools.agents.domain.entities.rbac import Action, ActionEnum

# Architect agent
architect_agent = VLLMAgent(config=arch_config)

# Check permissions
approve_design = Action(value=ActionEnum.APPROVE_DESIGN)
architect_agent.can_execute(approve_design)  # ✅ True (architect can approve)

deploy_docker = Action(value=ActionEnum.DEPLOY_DOCKER)
architect_agent.can_execute(deploy_docker)  # ❌ False (only devops can deploy)
```

### 4. Can Use Tool (Lines 336-354)

Delega tool access check al Agent:

```python
def can_use_tool(self, tool_name: str) -> bool:
    """
    Check if agent can use the given tool (RBAC enforcement).

    Delegates to Agent aggregate root for RBAC logic.
    """
    return self.agent.can_use_tool(tool_name)
```

**Example:**
```python
# QA agent
qa_agent = VLLMAgent(config=qa_config)

# Check tool access
qa_agent.can_use_tool("files")   # ✅ True
qa_agent.can_use_tool("tests")   # ✅ True
qa_agent.can_use_tool("http")    # ✅ True
qa_agent.can_use_tool("docker")  # ❌ False (QA doesn't have docker)
qa_agent.can_use_tool("db")      # ❌ False (QA doesn't have db)
```

### 5. Logging with Role (Line 642)

VLLMAgent usa `role.get_name()` para logging consistente:

```python
def _log_thought(
    self,
    reasoning_log: ReasoningLogs,
    iteration: int,
    thought_type: str,
    content: str,
    related_operations: list[str] | None = None,
    confidence: float | None = None,
) -> None:
    """Log agent's internal thought/reasoning."""
    reasoning_log.add(
        agent_id=self.agent_id,
        role=self.role.get_name(),  # Tell, Don't Ask: Role knows its name
        iteration=iteration,
        thought_type=thought_type,
        content=content,
        related_operations=related_operations,
        confidence=confidence,
    )
```

---

## Capability Filtering

### How Filtering Works

**Step-by-Step Process:**

1. **ToolFactory** crea `AgentCapabilities` con TODAS las tools disponibles:
   ```python
   # All tools: files, git, tests, docker, db, http
   all_tools = ["files", "git", "tests", "docker", "db", "http"]
   ```

2. **Role** define `allowed_tools`:
   ```python
   # Developer role
   role = Role(
       value=RoleEnum.DEVELOPER,
       allowed_actions=frozenset([...]),
       allowed_tools=frozenset(["files", "git", "tests"]),  # Only 3 tools
       scope=ScopeEnum.TECHNICAL,
   )
   ```

3. **AgentCapabilities.filter_by_allowed_tools()** filtra:
   ```python
   # Filter tools
   filtered_capabilities = all_capabilities.filter_by_allowed_tools(
       role.allowed_tools  # frozenset({"files", "git", "tests"})
   )

   # Result: Only tools in allowed_tools are kept
   # filtered_capabilities.tools = ["files", "git", "tests"]
   # docker, db, http are REMOVED ❌
   ```

4. **Agent** recibe capabilities YA filtradas:
   ```python
   agent = Agent(
       agent_id=AgentId("agent-dev-001"),
       role=role,
       name="Developer Agent",
       capabilities=filtered_capabilities,  # Pre-filtered ✅
   )
   ```

### Example: Developer vs Architect

**Developer Agent:**
```python
# Role
developer_role = RoleFactory.create_developer()
# allowed_tools = {"files", "git", "tests"}

# Initialization
dev_agent = VLLMAgent(config=AgentInitializationConfig(
    agent_id="agent-dev-001",
    role=developer_role,
    ...
))

# Available tools (RBAC-filtered)
tools = dev_agent.get_available_tools()
print(tools.tools.get_tool_names())
# Output: ['files', 'git', 'tests'] ✅

# Tool checks
dev_agent.can_use_tool("files")   # ✅ True
dev_agent.can_use_tool("git")     # ✅ True
dev_agent.can_use_tool("tests")   # ✅ True
dev_agent.can_use_tool("docker")  # ❌ False
dev_agent.can_use_tool("db")      # ❌ False
```

**Architect Agent:**
```python
# Role
architect_role = RoleFactory.create_architect()
# allowed_tools = {"files", "git", "db", "http"}

# Initialization
arch_agent = VLLMAgent(config=AgentInitializationConfig(
    agent_id="agent-arch-001",
    role=architect_role,
    ...
))

# Available tools (RBAC-filtered)
tools = arch_agent.get_available_tools()
print(tools.tools.get_tool_names())
# Output: ['db', 'files', 'git', 'http'] ✅

# Tool checks
arch_agent.can_use_tool("files")   # ✅ True
arch_agent.can_use_tool("git")     # ✅ True
arch_agent.can_use_tool("db")      # ✅ True
arch_agent.can_use_tool("http")    # ✅ True
arch_agent.can_use_tool("tests")   # ❌ False (architect doesn't test)
arch_agent.can_use_tool("docker")  # ❌ False (architect doesn't deploy)
```

---

## Usage Examples

### Example 1: Create Agent with RBAC

```python
from core.agents_and_tools.agents.domain.entities.rbac import RoleFactory
from core.agents_and_tools.agents.infrastructure.dtos import AgentInitializationConfig
from core.agents_and_tools.agents.infrastructure.factories import VLLMAgentFactory

# 1. Create Role (defines allowed_actions + allowed_tools)
developer_role = RoleFactory.create_developer()

# 2. Create config with Role
config = AgentInitializationConfig(
    agent_id="agent-dev-001",
    role=developer_role,  # Role value object
    workspace_path="/workspace/project",
    vllm_url="http://vllm:8000",
    enable_tools=True,  # Full execution mode
)

# 3. Create agent (RBAC applied automatically)
agent = VLLMAgentFactory.create(config)

# Agent now has:
# - agent.role: Role object
# - agent.agent: Agent aggregate root with RBAC-filtered capabilities
# - agent.get_available_tools(): Returns only allowed tools
```

### Example 2: Check Permissions Before Execution

```python
from core.agents_and_tools.agents.domain.entities.rbac import Action, ActionEnum

# Create QA agent
qa_config = AgentInitializationConfig(
    agent_id="agent-qa-001",
    role=RoleFactory.create_qa(),
    ...
)
qa_agent = VLLMAgentFactory.create(qa_config)

# Check action permissions
approve_tests = Action(value=ActionEnum.APPROVE_TESTS)
if qa_agent.can_execute(approve_tests):
    print("QA can approve tests ✅")
else:
    print("QA cannot approve tests ❌")

# Check tool permissions
if qa_agent.can_use_tool("tests"):
    print("QA can use tests tool ✅")

if not qa_agent.can_use_tool("docker"):
    print("QA cannot use docker ❌")
```

### Example 3: Get Available Tools for LLM Prompt

```python
# Create architect agent
architect_agent = VLLMAgentFactory.create(arch_config)

# Get RBAC-filtered capabilities
capabilities = architect_agent.get_available_tools()

# Use in LLM prompt
prompt = f"""
You are an {architect_agent.role.get_name()} agent.

Available tools:
{capabilities.summary}

Tools you can use:
{', '.join(capabilities.tools.get_tool_names())}

Available operations:
{len(capabilities.operations)} operations

Task: Analyze codebase architecture
"""
```

### Example 4: Role-Based Task Execution

```python
# Developer executes feature implementation
dev_agent = VLLMAgentFactory.create(dev_config)

result = await dev_agent.execute_task(
    task="Add hello_world() function to src/utils.py",
    context="Python project with pytest",
    constraints=ExecutionConstraints(max_operations=10),
)

# Developer can:
# ✅ Read files (files.read_file)
# ✅ Write files (files.write_file)
# ✅ Run tests (tests.pytest)
# ✅ Commit (git.commit)
# ❌ Deploy docker (docker.build) - NOT ALLOWED

# QA validates implementation
qa_agent = VLLMAgentFactory.create(qa_config)

result = await qa_agent.execute_task(
    task="Validate hello_world() function",
    context="Function should return 'Hello, World!'",
    constraints=ExecutionConstraints(max_operations=5),
)

# QA can:
# ✅ Read files (files.read_file)
# ✅ Run tests (tests.pytest)
# ✅ Make HTTP requests (http.get) for validation
# ❌ Write files (files.write_file) - READ ONLY for QA
# ❌ Commit (git.commit) - QA doesn't commit
```

---

## Security Model

### RBAC Enforcement Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: INITIALIZATION (Lines 265-280)                     │
│ ✅ Capabilities filtered by role.allowed_tools              │
│ ✅ Agent created with ONLY allowed tools                    │
│ ✅ No access to disallowed tools from start                 │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: CAPABILITY QUERIES (Lines 287-313)                 │
│ ✅ get_available_tools() returns filtered capabilities      │
│ ✅ LLM receives ONLY allowed tools in prompt                │
│ ✅ Agent can't "see" disallowed tools                       │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: PERMISSION CHECKS (Lines 315-354)                  │
│ ✅ can_execute(action) validates against role               │
│ ✅ can_use_tool(tool) validates against allowed_tools       │
│ ✅ Explicit permission check before operations              │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: DOMAIN ENFORCEMENT (Agent aggregate root)          │
│ ✅ Agent.can_execute_capability() validates role + tool     │
│ ✅ Business logic enforces RBAC at domain level             │
│ ✅ Impossible to bypass - immutable capabilities            │
└─────────────────────────────────────────────────────────────┘
```

### Key Security Properties

1. **Immutable Capabilities**:
   - `AgentCapabilities` is `@dataclass(frozen=True)`
   - Once created, capabilities CANNOT be modified
   - Agent CANNOT escalate privileges

2. **Filtered at Creation**:
   - Tools filtered BEFORE Agent creation
   - Agent never "sees" disallowed tools
   - No way to access filtered tools

3. **Domain Enforcement**:
   - RBAC logic in domain layer (not infrastructure)
   - Business rules cannot be bypassed
   - Type-safe (Role is value object, not string)

4. **Zero Configuration**:
   - RBAC applied automatically at initialization
   - No manual permission checks needed
   - Fail-fast if role invalid

---

## Summary

**VLLMAgent RBAC Integration:**

| Aspect | Implementation |
|--------|---------------|
| **Role Storage** | `self.role: Role` (value object) |
| **Agent Creation** | Creates `Agent` aggregate root with filtered capabilities |
| **Capability Filtering** | Automatic via `filter_by_allowed_tools()` at init |
| **Permission Checks** | Delegates to `agent.can_execute()` and `agent.can_use_tool()` |
| **Tool Access** | Returns `agent.capabilities` (pre-filtered) |
| **Logging** | Uses `role.get_name()` for consistent role names |
| **Security** | Immutable, domain-enforced, impossible to bypass |

**Key Principle:**
> VLLMAgent is a **thin infrastructure facade** that **delegates RBAC to the domain layer** (Agent aggregate root).
> RBAC is **automatic**, **immutable**, and **enforced at initialization** - no runtime bypasses possible.

---

**Author:** AI Assistant + Tirso García
**Last Updated:** 2025-11-04
**Version:** 1.0

