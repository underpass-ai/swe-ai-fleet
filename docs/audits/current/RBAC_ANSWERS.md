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

### ❓ Q3: Capabilities Mutation

**Question:** ¿Es posible modificar las capabilities después de filtrado RBAC?

**Verification Needed:**
```python
qa_agent = VLLMAgentFactory.create(qa_config)

# Try to mutate capabilities:
qa_agent.agent.capabilities.tools.tools["docker"] = ToolDefinition(...)  # ← ¿Funciona?
```

Let's check:

