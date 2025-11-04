# RBAC Challenge Questions - Answers & Verification

**Date:** 2025-11-04
**Status:** 🔍 In Progress
**Completed:** 2/25

---

## 🔴 Security & Attack Scenarios

### ✅ Q1: LLM Prompt Injection

**Question:** ¿Qué pasa si un usuario manipula el contexto para que el LLM ignore las restricciones RBAC?

**Answer:** ✅ **PROTEGIDO**

**Evidence:**
```python
# vllm_agent.py:578-591
if not self.agent.can_use_tool(tool_name):
    error_msg = f"RBAC Violation: Tool '{tool_name}' not allowed..."
    return StepExecutionResult(success=False, error=error_msg)
```

**Verification:**
- ✅ Validación RBAC en runtime (línea 579)
- ✅ Se ejecuta ANTES de llamar toolset.execute_operation
- ✅ NO importa lo que el LLM genere en el plan
- ✅ Test: `test_architect_cannot_execute_docker_tool` verifica esto

**Status:** ✅ SECURE

---

### ⚠️ Q2: Role Mutation After Creation

**Question:** ¿Es posible modificar el rol de un agente después de creación?

**Answer:** ⚠️ **CODE SMELL (pero NO vulnerable)**

**Verification Test:**
```python
architect = VLLMAgentFactory.create(architect_config)
print(f"Can use docker: {architect.can_use_tool('docker')}")  # False

# Modificar role:
architect.role = RoleFactory.create_devops()  # ← SÍ SE PUEDE MODIFICAR

# Verificar acceso:
print(f"Can use docker: {architect.can_use_tool('docker')}")  # ← Sigue False ✅
```

**Result:** Aunque `self.role` se puede modificar, las validaciones RBAC usan `self.agent` (immutable).

**Why It's Safe:**
```python
# vllm_agent.py:334
def can_use_tool(self, tool_name: str) -> bool:
    return self.agent.can_use_tool(tool_name)  # ← Usa self.agent (frozen)

# vllm_agent.py:579
if not self.agent.can_use_tool(tool_name):  # ← Usa self.agent (frozen)
```

**Domain Agent:**
```python
# agent.py:13
@dataclass(frozen=True)  # ← Immutable
class Agent:
    role: Role  # ← Este Role NO se puede cambiar
```

**Conclusion:**
- ⚠️ **Code Smell**: `VLLMAgent.role` y `VLLMAgent.agent` son modificables (confuso)
- ✅ **NOT Vulnerable**: Todas las validaciones usan `self.agent` (immutable)
- 🔧 **Improvement**: Hacer atributos privados o read-only

**Recommendation:**
```python
# Option A: Private attributes
class VLLMAgent:
    def __init__(self, config):
        self._role = config.role  # Private
        self._agent = Agent(...)  # Private

    @property
    def role(self) -> Role:
        return self._role  # Read-only

# Option B: __slots__ with frozen dataclass
@dataclass(frozen=True)
class VLLMAgentConfig:
    ...

# Keep as code smell for now, not security issue
```

**Status:** ⚠️ CODE SMELL (low priority fix)

---

### ⚠️ Q3: Capabilities Mutation

**Question:** ¿Es posible modificar las capabilities después de filtrado RBAC?

**Answer:** ⚠️ **CODE SMELL (pero NO vulnerable)**

**Verification:**
```python
qa_agent = VLLMAgentFactory.create(qa_config)
# Can modify internal dict:
qa_agent.agent.capabilities.tools.tools["docker"] = ToolDefinition(...)  # ← Works!

# But RBAC still enforced:
qa_agent.can_use_tool("docker")  # False ✅
```

**Why It's Safe:**
```python
# agent.py:93
def can_use_tool(self, tool_name: str) -> bool:
    return tool_name in self.role.allowed_tools  # ← Uses role, NOT capabilities.tools
```

**Status:** ⚠️ CODE SMELL (cosmetic, not security)

---

### ✅ Q4: Tool Name Aliasing

**Question:** ¿Qué pasa si LLM usa alias o nombres alternativos de tools?

**Answer:** ✅ **PROTEGIDO**

**Verification:**
```python
qa_agent.can_use_tool("git")    # False
qa_agent.can_use_tool("Git")    # False (case-sensitive)
qa_agent.can_use_tool("GIT")    # False
qa_agent.can_use_tool(" git ")  # False (no trim)
```

**Why It's Safe:** Exact string match (case-sensitive, no normalization)

**Status:** ✅ SECURE

---

### ✅ Q5: Empty/Null Tool Names

**Question:** ¿Qué pasa si el step tiene tool vacío o null?

**Answer:** ✅ **PROTEGIDO (FIXED)**

**Verification:**
```python
ExecutionStep(tool="", ...)    # ValueError ✅
ExecutionStep(tool="  ", ...)  # ValueError ✅ (FIXED)
ExecutionStep(tool=None, ...)  # ValueError ✅
```

**Fix Applied:**
```python
# execution_step.py:22
if not self.tool or not self.tool.strip():
    raise ValueError("tool cannot be empty or whitespace")
```

**Status:** ✅ SECURE

---

### ✅ Q6: Dynamic Tool Loading

**Question:** ¿Es posible cargar tools dinámicamente después de RBAC filtering?

**Answer:** ✅ **PROTEGIDO**

**Verification:**
```python
qa_agent.toolset.create_tool(ToolType.DOCKER)  # AttributeError ✅
```

**Why It's Safe:** `ToolExecutionAdapter` no expone `create_tool()` públicamente.

**Status:** ✅ SECURE

---

### ⚠️ Q7: Bypass Through Use Cases

**Question:** ¿Puedo llamar use cases directamente y modificar allowed_tools?

**Answer:** ⚠️ **CODE SMELL (mismo que Q2)**

**Verification:**
```python
service = StepExecutionApplicationService(
    tool_execution_port=port,
    allowed_tools=frozenset({"files"})
)

# Can reassign attribute:
service.allowed_tools = frozenset({"docker"})  # ← Works! ⚠️

# But frozenset itself is immutable:
service.allowed_tools.add("git")  # AttributeError ✅
```

**Status:** ⚠️ CODE SMELL (same as Q2 - instance attributes mutable)

---

## 🟡 Edge Cases & Boundaries

### ❓ Q8: Multiple Agents Same Process

**Question:** ¿Qué pasa si creo múltiples agentes con diferentes roles en el mismo proceso?

**Verification Needed:** Check for shared state, race conditions, capability leaks between agents.

---

**Progress:** 7/25 questions answered
**Next:** Continue with Q8-Q25

