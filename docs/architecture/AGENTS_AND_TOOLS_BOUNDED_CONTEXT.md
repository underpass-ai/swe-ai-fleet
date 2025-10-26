# Bounded Context: Agents and Tools

## 🎯 Purpose

This is a **legacy bounded context** that wraps `core/agents` (VLLMAgent) and `core/tools` (FileTool, GitTool, etc.).

**Status**: Not fully hexagonal yet, but self-contained.

## 📐 Current Architecture

```
core/agents/
├── vllm_agent.py          # ⚠️ Directly imports tools from core/tools
├── domain/
│   └── ports/
│       └── llm_client.py  # ✅ Hexagonal: LLM communication
├── application/
│   └── usecases/
│       ├── generate_plan_usecase.py       # ✅ Hexagonal
│       └── generate_next_action_usecase.py # ✅ Hexagonal
└── infrastructure/
    └── adapters/
        └── vllm_client_adapter.py          # ✅ Hexagonal

core/tools/ (legacy, used by VLLMAgent)
├── file_tool.py           # Direct implementations
├── git_tool.py
├── test_tool.py
├── docker_tool.py
├── http_tool.py
├── db_tool.py
└── ...
```

## ⚠️ Current State: Violations

### 1. Direct Tool Imports in VLLMAgent
```python
# core/agents/vllm_agent.py
from core.tools import (  # ❌ Direct import
    DatabaseTool,
    DockerTool,
    FileTool,
    GitTool,
    HttpTool,
    TestTool,
)
```

### 2. Direct Tool Instantiation
```python
# core/agents/vllm_agent.py lines 295-308
self.tools = {
    "git": GitTool(workspace_path, audit_callback),      # ❌ Direct instantiation
    "files": FileTool(workspace_path, audit_callback),    # ❌ Direct instantiation
    "tests": TestTool(workspace_path, audit_callback),   # ❌ Direct instantiation
    "http": HttpTool(audit_callback=audit_callback),     # ❌ Direct instantiation
    "db": DatabaseTool(audit_callback=audit_callback),   # ❌ Direct instantiation
}
```

### 3. Direct Tool Execution
```python
# core/agents/vllm_agent.py lines 1056-1082
tool = self.tools.get(tool_name)  # ❌ Direct access
method = getattr(tool, operation, None)  # ❌ Reflection
result = method(**params)  # ❌ Direct call
```

## 🔍 Root Cause Analysis

**Why not decoupled?**
- `core/tools` are **concrete implementations** used by VLLMAgent
- They are **runtime dependencies**, not compile-time ports
- The tools are **stateful** (require workspace_path, audit_callback)
- Refactoring would require **significant changes** to VLLMAgent

**Current flow**:
```
VLLMAgent.__init__() → Instantiate tools → Store in self.tools → Execute via reflection
```

## ✅ What's Working (Hexagonal)

**Already decoupled**:
1. ✅ LLM Communication: `LLMClientPort` → `VLLMClientAdapter`
2. ✅ Planning Logic: `GeneratePlanUseCase` (uses LLM port)
3. ✅ Decision Logic: `GenerateNextActionUseCase` (uses LLM port)

**Not decoupled yet**:
- ❌ Tool Execution: Direct access to `core/tools`
- ❌ Tool Registry: No abstraction for available tools
- ❌ Tool Results: No standardized return types

## 🎯 Future Refactoring (Not Now)

If we wanted to fully decouple tools, we would need:

### Step 1: Create Tool Port
```python
# core/agents/domain/ports/tool_executor_port.py
class ToolExecutorPort(ABC):
    @abstractmethod
    async def execute_operation(
        self,
        tool_name: str,
        operation: str,
        params: dict[str, Any]
    ) -> ToolResult: pass
```

### Step 2: Create Adapter
```python
# core/agents/infrastructure/tools/tool_executor_adapter.py
class ToolExecutorAdapter(ToolExecutorPort):
    def __init__(self, workspace_path: str, audit_callback: Callable):
        self._tools = {
            "files": FileTool(workspace_path, audit_callback),
            "git": GitTool(workspace_path, audit_callback),
            ...
        }

    async def execute_operation(self, tool_name, operation, params):
        tool = self._tools.get(tool_name)
        method = getattr(tool, operation)
        return method(**params)
```

### Step 3: Inject into VLLMAgent
```python
# VLLMAgent.__init__() would receive ToolExecutorPort
def __init__(self, ..., tool_executor: ToolExecutorPort):
    self.tool_executor = tool_executor  # ✅ Injected, not created
```

## 📋 Current Bounded Context Boundaries

```
┌─────────────────────────────────────────────────┐
│  Bounded Context: Agents and Tools               │
│                                                  │
│  ✅ LLM Communication (decoupled)                 │
│     LLMClientPort → VLLMClientAdapter           │
│                                                  │
│  ⚠️ Tool Execution (coupled)                    │
│     VLLMAgent → core/tools directly             │
│                                                  │
│  ✅ Planning Logic (decoupled)                  │
│     GeneratePlanUseCase                         │
│                                                  │
│  ✅ Decision Logic (decoupled)                  │
│     GenerateNextActionUseCase                   │
└─────────────────────────────────────────────────┘

External Dependencies:
- core/tools (FileTool, GitTool, etc.)  ← Not decoupled
```

## 🚫 Why Not Decouple Now?

1. **Risk**: Tools are heavily used (1358 tests pass)
2. **Time**: Would require extensive refactoring
3. **Value**: Current coupling works well
4. **Priority**: LLM decoupling was the bottleneck (already done)

## ✅ Acceptance Criteria

This bounded context is **acceptable** if:
- ✅ LLM operations are decoupled (hexagonal)
- ✅ Business logic in use cases (GeneratePlan, GenerateNextAction)
- ⚠️ Tools remain coupled (acceptable for now)

## 🎯 Summary

**Current state**:
- Partially hexagonal (LLM decoupled, tools not)
- Self-contained bounded context
- 1358 tests passing

**Next steps** (if needed):
- Document tool execution as "pending decoupling"
- Create TODO for future refactoring
- Focus on higher-priority items first

