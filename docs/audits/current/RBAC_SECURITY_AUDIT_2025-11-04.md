# RBAC Security Audit - VLLMAgent Implementation

**Date:** 2025-11-04
**Auditor:** AI Assistant + Tirso García
**Scope:** RBAC enforcement in VLLMAgent and use cases
**Status:** 🔴 **3 CRITICAL VULNERABILITIES FOUND**

---

## 🔴 CRITICAL VULNERABILITIES

### VULNERABILITY #1: VLLMAgent._execute_step() - RBAC Bypass

**Severity:** 🔴 **CRITICAL**
**File:** `core/agents_and_tools/agents/vllm_agent.py:558-584`
**Type:** Missing Authorization Check

#### Problem

`_execute_step()` executes tool operations **WITHOUT validating RBAC permissions**:

```python
async def _execute_step(self, step: dict | ExecutionStep) -> StepExecutionResult:
    step_entity = self._ensure_execution_step(step)

    tool_name = step_entity.tool  # ← Could be ANY tool name
    operation = step_entity.operation
    params = step_entity.params or {}

    # ❌ VULNERABILITY: No RBAC validation before execution
    result = self.toolset.execute_operation(
        tool_name,      # ← Executes ANY tool
        operation,
        params,
        enable_write=self.enable_tools,  # Only validates read/write, NOT RBAC
    )
```

#### Attack Scenario

1. **Architect agent** is created (allowed_tools={"files", "git", "db", "http"})
2. **Malicious input** or **LLM hallucination** generates plan:
   ```json
   {
     "steps": [
       {"tool": "docker", "operation": "build", "params": {"dockerfile": "..."}}
     ]
   }
   ```
3. **`_execute_step()` executes `docker.build()`** ❌ WITHOUT checking RBAC
4. **COMPLETE RBAC BYPASS** - Architect gains docker access

#### Impact

- **High**: Complete bypass of RBAC system
- **Privilege escalation**: Any role can execute any tool
- **LLM manipulation**: Malicious prompts can grant unauthorized access
- **Defense-in-depth violation**: No enforcement at execution layer

#### Root Cause

RBAC is only enforced at:
- ✅ **Initialization**: Capabilities filtered by role
- ✅ **LLM Prompt**: Only allowed tools shown to LLM
- ❌ **Execution**: NO validation before executing tool

**Missing enforcement point:** Runtime execution validation

#### Recommended Fix

Add RBAC validation in `_execute_step()` BEFORE executing:

```python
async def _execute_step(self, step: dict | ExecutionStep) -> StepExecutionResult:
    step_entity = self._ensure_execution_step(step)

    tool_name = step_entity.tool
    operation = step_entity.operation
    params = step_entity.params or {}

    # ✅ FIX: Validate RBAC before execution (fail-fast)
    if not self.agent.can_use_tool(tool_name):
        raise ValueError(
            f"RBAC Violation: Tool '{tool_name}' not allowed for role '{self.role.get_name()}'. "
            f"Allowed tools: {sorted(self.role.allowed_tools)}"
        )

    # Now safe to execute
    result = self.toolset.execute_operation(
        tool_name,
        operation,
        params,
        enable_write=self.enable_tools,
    )
```

---

### VULNERABILITY #2: StepExecutionApplicationService - RBAC Bypass

**Severity:** 🔴 **CRITICAL**
**File:** `core/agents_and_tools/agents/application/services/step_execution_service.py:39-65`
**Type:** Missing Authorization Check

#### Problem

`StepExecutionApplicationService.execute()` has the **same vulnerability** as VLLMAgent._execute_step():

```python
async def execute(
    self,
    step: ExecutionStep,
    enable_write: bool = True,
) -> StepExecutionDTO:
    tool_name = step.tool
    operation = step.operation
    params = step.params or {}

    # ❌ VULNERABILITY: No RBAC validation
    result = self.tool_execution_port.execute_operation(
        tool_name=tool_name,  # ← Executes ANY tool
        operation=operation,
        params=params,
        enable_write=enable_write,
    )
```

#### Additional Challenge

This service is in **Application Layer**, but it **doesn't have access to Agent or Role**:

```python
def __init__(self, tool_execution_port: ToolExecutionPort):
    # ❌ No Agent, no Role - cannot validate RBAC
    self.tool_execution_port = tool_execution_port
```

#### Impact

- **High**: Same as Vulnerability #1
- **Architectural issue**: Service can't enforce RBAC without Agent/Role

#### Recommended Fix

**Option A**: Pass Agent to service constructor:

```python
def __init__(
    self,
    tool_execution_port: ToolExecutionPort,
    agent: Agent,  # ← Add Agent dependency
):
    self.tool_execution_port = tool_execution_port
    self.agent = agent

async def execute(self, step: ExecutionStep, enable_write: bool = True) -> StepExecutionDTO:
    tool_name = step.tool

    # ✅ Validate RBAC
    if not self.agent.can_use_tool(tool_name):
        raise ValueError(f"RBAC Violation: Tool '{tool_name}' not allowed")

    # Execute
    result = self.tool_execution_port.execute_operation(...)
```

**Option B**: Pass allowed_tools instead of Agent:

```python
def __init__(
    self,
    tool_execution_port: ToolExecutionPort,
    allowed_tools: frozenset[str],  # ← Add allowed_tools
):
    self.tool_execution_port = tool_execution_port
    self.allowed_tools = allowed_tools

async def execute(self, step: ExecutionStep, enable_write: bool = True) -> StepExecutionDTO:
    tool_name = step.tool

    # ✅ Validate RBAC
    if tool_name not in self.allowed_tools:
        raise ValueError(f"RBAC Violation: Tool '{tool_name}' not allowed")

    # Execute
    result = self.tool_execution_port.execute_operation(...)
```

---

### 🟡 VULNERABILITY #3: Prompt Template Role Mismatch

**Severity:** 🟡 **MEDIUM** (Functionality Issue, not Security)
**File:** `core/agents_and_tools/resources/prompts/plan_generation.yaml:38-43`
**Type:** Configuration Mismatch

#### Problem

Prompt template keys don't match RoleEnum values:

```yaml
# plan_generation.yaml
roles:
  DEV: "You are an expert software developer..."       # ❌ Key is "DEV"
  QA: "You are an expert QA engineer..."               # ✅ Key is "QA" (matches)
  ARCHITECT: "You are a senior software architect..."  # ✅ Key is "ARCHITECT" (matches)
  DEVOPS: "You are a DevOps engineer..."               # ✅ Key is "DEVOPS" (matches)
  DATA: "You are a data engineer..."                   # ✅ Key is "DATA" (matches)
```

```python
# role.py
class RoleEnum(str, Enum):
    ARCHITECT = "architect"
    QA = "qa"
    DEVELOPER = "developer"  # ❌ Enum name is DEVELOPER, not DEV
    PO = "po"
    DEVOPS = "devops"
    DATA = "data"

def get_prompt_key(self) -> str:
    return self.value.value.upper()  # Returns "DEVELOPER", not "DEV"
```

#### Impact

- **Medium**: Developer role uses **fallback prompt** instead of specific prompt
- Falls back to: `f"You are an expert {role.get_name()} engineer."`
- Not a security issue, but degrades LLM context quality

#### Current Behavior

```python
# Developer agent
role_prompt = roles.get(
    "DEVELOPER",  # ← Looking for "DEVELOPER"
    f"You are an expert developer engineer."  # ← Uses fallback
)
# YAML has "DEV", not "DEVELOPER" → fallback is used
```

#### Recommended Fix

Update `plan_generation.yaml` to match RoleEnum names:

```yaml
roles:
  DEVELOPER: "You are an expert software developer focused on writing clean, maintainable code."  # ✅ Fix
  QA: "You are an expert QA engineer focused on testing and quality validation."
  ARCHITECT: "You are a senior software architect focused on design and analysis."
  DEVOPS: "You are a DevOps engineer focused on deployment and infrastructure."
  DATA: "You are a data engineer focused on databases and data pipelines."
  PO: "You are a product owner focused on business value and requirements."  # ✅ Add missing
```

---

## 🟢 VERIFIED SECURE COMPONENTS

### ✅ Agent Aggregate Root

**File:** `core/agents_and_tools/agents/domain/entities/core/agent.py`

**Secure:**
- ✅ Immutable (`@dataclass(frozen=True)`)
- ✅ `can_execute()` validates action against role
- ✅ `can_use_tool()` validates tool against allowed_tools
- ✅ `capabilities` are pre-filtered at creation
- ✅ No way to modify role or capabilities after creation

### ✅ Role Value Object

**File:** `core/agents_and_tools/agents/domain/entities/rbac/role.py`

**Secure:**
- ✅ Immutable (`@dataclass(frozen=True)`)
- ✅ `allowed_tools: frozenset[str]` (immutable)
- ✅ `allowed_actions: frozenset[ActionEnum]` (immutable)
- ✅ Validation in `__post_init__` (fail-fast)

### ✅ AgentCapabilities Filtering

**File:** `core/agents_and_tools/common/domain/entities/agent_capabilities.py`

**Secure:**
- ✅ `filter_by_allowed_tools()` creates NEW instance (immutable)
- ✅ Original capabilities never modified
- ✅ Filtered capabilities validated (cannot be empty)

---

## 🎯 Summary

| Issue | Severity | Location | Status |
|-------|----------|----------|--------|
| VLLMAgent._execute_step() RBAC bypass | 🔴 CRITICAL | vllm_agent.py:558 | ❌ VULNERABLE |
| StepExecutionService RBAC bypass | 🔴 CRITICAL | step_execution_service.py:39 | ❌ VULNERABLE |
| Prompt template mismatch | 🟡 MEDIUM | plan_generation.yaml:38 | ⚠️ DEGRADED |

---

## 📋 Recommended Actions

### Priority 1 (CRITICAL - Security)

1. **Add RBAC validation in VLLMAgent._execute_step()**
   - Validate `self.agent.can_use_tool(tool_name)` before execution
   - Raise `ValueError` with clear message if violated
   - Add test for RBAC bypass attempt

2. **Add RBAC validation in StepExecutionApplicationService**
   - Pass `Agent` or `allowed_tools` to constructor
   - Validate tool access before execution
   - Add test for RBAC enforcement

### Priority 2 (MEDIUM - Functionality)

3. **Fix prompt template keys**
   - Change "DEV" → "DEVELOPER" in plan_generation.yaml
   - Add "PO" role prompt (currently missing)
   - Verify all role keys match RoleEnum names

### Priority 3 (ENHANCEMENT - Defense in Depth)

4. **Add RBAC validation in ToolFactory.execute_operation()**
   - Optional: Add allowed_tools parameter
   - Validate before tool execution
   - Additional security layer

5. **Add integration tests**
   - Test RBAC bypass attempts
   - Verify exceptions are raised
   - Test all roles with disallowed tools

---

## 🔒 Security Checklist

- [ ] VLLMAgent._execute_step() validates RBAC
- [ ] StepExecutionService validates RBAC
- [ ] Prompt templates match RoleEnum exactly
- [ ] All roles have prompts defined
- [ ] Integration tests for RBAC bypass attempts
- [ ] Audit trail logs RBAC violations
- [ ] Documentation updated with security model

---

**Conclusion:** RBAC domain model is **architecturally sound**, but **runtime enforcement is incomplete**.
**Recommendation:** Fix critical vulnerabilities #1 and #2 **BEFORE merge to main**.

---

**Auditor:** AI Assistant
**Date:** 2025-11-04
**Next Review:** After fixes applied

