# RBAC - New Vulnerabilities Found During Q&A

**Date:** 2025-11-04
**Status:** 🔴 2 NEW ISSUES FOUND

---

## 🟡 ISSUE #1: VLLMAgent Attributes Mutable (Code Smell)

**Severity:** 🟡 **LOW** (Code smell, not security vulnerability)
**Type:** Inconsistent Immutability

### Problem

`VLLMAgent.role` and `VLLMAgent.agent` are mutable instance attributes:

```python
class VLLMAgent:
    def __init__(self, config):
        self.role = config.role  # ← Mutable attribute
        self.agent = Agent(...)  # ← Mutable attribute
```

### Proof of Concept

```python
architect = VLLMAgentFactory.create(architect_config)
architect.role = RoleFactory.create_devops()  # ← Works! (mutation)
```

### Why It's NOT Currently Vulnerable

All RBAC validations use `self.agent` (which is frozen dataclass), not `self.role`:

```python
def can_use_tool(self, tool_name: str) -> bool:
    return self.agent.can_use_tool(tool_name)  # Uses self.agent (immutable)
```

Even if `self.role` is modified, `self.agent.role` cannot be modified (frozen).

### Recommended Fix

**Option A: Private attributes with properties**
```python
class VLLMAgent:
    def __init__(self, config):
        self._role = config.role
        self._agent = Agent(...)

    @property
    def role(self) -> Role:
        return self._role

    @property
    def agent(self) -> Agent:
        return self._agent
```

**Option B: Use __slots__**
```python
class VLLMAgent:
    __slots__ = ('_role', '_agent', ...)
```

**Priority:** LOW (cosmetic fix for consistency)

---

## 🟡 ISSUE #2: ToolRegistry.tools Dict Is Mutable

**Severity:** 🟡 **LOW** (Immutability violation, but mitigated)
**Type:** Broken Encapsulation

### Problem

`ToolRegistry.tools` uses `dict[str, ToolDefinition]` which is mutable:

```python
@dataclass(frozen=True)
class ToolRegistry:
    tools: dict[str, ToolDefinition]  # ← dict is mutable even in frozen dataclass
```

### Proof of Concept

```python
qa_agent = VLLMAgentFactory.create(qa_config)
print(qa_agent.agent.capabilities.tools.get_tool_names())  # ['files', 'http', 'tests']

# Mutate internal dict:
qa_agent.agent.capabilities.tools.tools["docker"] = ToolDefinition(name="docker", operations={})

print(qa_agent.agent.capabilities.tools.get_tool_names())  # ['docker', 'files', 'http', 'tests']
# ❌ Docker was added!
```

### Why It's NOT Currently Vulnerable

RBAC validation uses `role.allowed_tools`, not `capabilities.tools`:

```python
# agent.py:93
def can_use_tool(self, tool_name: str) -> bool:
    return tool_name in self.role.allowed_tools  # ← Uses role, NOT capabilities
```

So even though capabilities.tools can be modified, RBAC still works:

```python
qa_agent.can_use_tool("docker")  # False (uses role.allowed_tools)
```

### Recommended Fix

Use `MappingProxyType` to make dict immutable:

```python
from types import MappingProxyType
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ToolRegistry:
    _tools_internal: dict[str, ToolDefinition] = field(repr=False)

    def __post_init__(self):
        # Wrap dict in MappingProxyType for true immutability
        object.__setattr__(
            self,
            'tools',
            MappingProxyType(self._tools_internal)
        )

    @property
    def tools(self) -> MappingProxyType[str, ToolDefinition]:
        """Immutable view of tools dict."""
        return self._tools
```

Or simpler: Use `tuple` instead of `dict`:

```python
@dataclass(frozen=True)
class ToolRegistry:
    _tools: tuple[ToolDefinition, ...]  # Immutable

    def get_tool(self, name: str) -> ToolDefinition:
        for tool in self._tools:
            if tool.name == name:
                return tool
        raise KeyError(f"Tool '{name}' not found")
```

**Priority:** LOW (architectural consistency, not security)

---

## 📊 Summary

| Question | Status | Severity | Notes |
|----------|--------|----------|-------|
| Q1 | ✅ SECURE | - | RBAC validated at runtime |
| Q2 | ⚠️ CODE SMELL | LOW | self.role mutable but validations use self.agent |
| Q3 | ⚠️ CODE SMELL | LOW | tools dict mutable but RBAC uses role.allowed_tools |
| Q4-Q25 | ⏳ PENDING | - | Not yet reviewed |

**Findings:**
- ✅ Core RBAC logic is sound
- ⚠️ Immutability could be stronger (cosmetic issues)
- ✅ Current mitigations prevent exploits

---

**Next:** Continue with Q4-Q25

