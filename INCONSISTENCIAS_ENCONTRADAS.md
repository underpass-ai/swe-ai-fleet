# Inconsistencias Encontradas en Casos de Uso

## Resumen
Se encontraron inconsistencias donde se usan `dict[str, Any]` en lugar de entidades de dominio existentes.

## 1. ✅ CRÍTICO: NextActionDTO y PlanDTO

### Ubicación: `core/agents_and_tools/agents/application/dtos/`

**Problema:**
- `NextActionDTO.step` es `dict[str, Any] | None`
- `PlanDTO.steps` es `list[dict[str, Any]]`

**Debería ser:**
- `NextActionDTO.step` debería ser `ExecutionStep | None`
- `PlanDTO.steps` debería ser `list[ExecutionStep]`

**Impacto:**
- Causa acceso dinámico a dicts en `vllm_agent.py` (líneas 395, 407, 434-435)
- Violación de Rule #4: NO REFLECTION / NO DYNAMIC MUTATION

**Archivos afectados:**
- `core/agents_and_tools/agents/application/dtos/next_action_dto.py`
- `core/agents_and_tools/agents/application/dtos/plan_dto.py`
- `core/agents_and_tools/agents/vllm_agent.py` (líneas 395, 407, 434-435, 724)

**Ejemplo de violación:**
```python
# ❌ MALO - Acceso dinámico a dict
related_operations=[f"{s['tool']}.{s['operation']}" for s in plan.steps]
content=f"Executing: {step['tool']}.{step['operation']}({self._get_step_params(step)})"
tool_name=step["tool"]
operation=step["operation"]
```

```python
# ✅ BUENO - Acceso a atributos de entidad
related_operations=[f"{s.tool}.{s.operation}" for s in plan.steps]
content=f"Executing: {step.tool}.{step.operation}({self._get_step_params(step)})"
tool_name=step.tool
operation=step.operation
```

---

## 2. ✅ IMPORTANTE: vllm_agent.get_available_tools()

### Ubicación: `core/agents_and_tools/agents/vllm_agent.py:263`

**Problema:**
```python
def get_available_tools(self) -> dict[str, Any]:
    """Returns Dictionary with: tools, mode, capabilities, summary"""
    return self.toolset.get_available_tools_description(...)
```

**Debería ser:**
```python
def get_available_tools(self) -> AgentCapabilities:
    """Returns AgentCapabilities entity"""
    return self.toolset.get_available_tools_description(...)
```

**Impacto:**
- `self.toolset.get_available_tools_description()` ahora retorna `AgentCapabilities` (ya actualizado)
- Pero `vllm_agent.get_available_tools()` todavía dice que retorna `dict[str, Any]`
- Esto causa inconsistencia de tipos

**Archivo afectado:**
- `core/agents_and_tools/agents/vllm_agent.py:263`

---

## 3. ⚠️ DEBATIBLE: Parámetros genéricos

### Ubicación: Múltiples entidades de dominio

**Observación:**
- Varias entidades tienen campos `dict[str, Any]` para metadatos o parámetros genéricos
- Ejemplos: `ExecutionStep.params`, `Operation.params`, `ExecutionResult.metadata`, etc.

**Análisis:**
- Estos son legítimos porque son datos genéricos/metadatos
- NO son inconsistencias según `.cursorrules`
- Son específicamente para datos flexibles que vienen del exterior

**Archivos (legítimos, no cambiar):**
- `core/agents_and_tools/agents/domain/entities/execution_step.py`
- `core/agents_and_tools/agents/domain/entities/operation.py`
- `core/agents_and_tools/agents/domain/entities/*_execution_result.py`
- `core/agents_and_tools/agents/domain/ports/tool_execution_port.py`

---

## Prioridades de Refactor

### P1 - CRÍTICO
1. Cambiar `NextActionDTO.step` a `ExecutionStep | None`
2. Cambiar `PlanDTO.steps` a `list[ExecutionStep]`
3. Actualizar `vllm_agent.py` para usar atributos de `ExecutionStep` en lugar de acceso a dict

### P2 - IMPORTANTE
4. Cambiar `vllm_agent.get_available_tools()` retorno a `AgentCapabilities`
5. Actualizar usos de `get_available_tools()` si hay algún acceso a `.tools` o `.capabilities` como dict

---

## Archivos a Modificar

1. `core/agents_and_tools/agents/application/dtos/next_action_dto.py`
2. `core/agents_and_tools/agents/application/dtos/plan_dto.py`
3. `core/agents_and_tools/agents/vllm_agent.py`
4. `core/agents_and_tools/agents/application/usecases/generate_plan_usecase.py`
5. `core/agents_and_tools/agents/application/usecases/generate_next_action_usecase.py`
6. Tests asociados

