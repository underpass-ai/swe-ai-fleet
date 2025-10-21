# 🐛 BUG CRÍTICO: asyncio.run() en VLLMAgent (AsyncVLLMAgent)

**Fecha**: 20 de Octubre de 2025  
**Severidad**: 🔴 **CRÍTICA** - Bloquea deliberaciones automáticas  
**Estado**: 📝 DOCUMENTADO - Pendiente de Fix  

---

## 🎯 Resumen del Problema

El sistema de auto-dispatch está funcionando correctamente, pero falla al ejecutar deliberaciones debido a `asyncio.run()` siendo llamado desde un event loop ya corriendo.

---

## 🔍 Análisis del Error

### Error Completo

```
RuntimeError: asyncio.run() cannot be called from a running event loop

Traceback:
  File "services/orchestrator/application/services/auto_dispatch_service.py", line 162
    result = await deliberate_uc.execute(...)
  
  File "services/orchestrator/application/usecases/deliberate_usecase.py", line 101
    results = await council.execute(task_description, constraints)
  
  File "src/swe_ai_fleet/orchestrator/usecases/peer_deliberation_usecase.py", line 47
    result = a.generate(task, constraints, diversity=True)
  
  File "src/swe_ai_fleet/orchestrator/domain/agents/vllm_agent.py", line 342
    return asyncio.run(super().generate(task, constraints, diversity))
           ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

---

## 🔴 Root Cause: AsyncVLLMAgent Sync Wrappers

### Ubicación del Código Problemático

**Archivo**: `src/swe_ai_fleet/orchestrator/domain/agents/vllm_agent.py`  
**Líneas**: 332-351

```python
class AsyncVLLMAgent(VLLMAgent):
    """Async wrapper for VLLMAgent to maintain sync interface compatibility."""
    
    def generate(self, task: str, constraints: TaskConstraints, diversity: bool = False) -> dict[str, Any]:
        """Sync wrapper for async generate."""
        return asyncio.run(super().generate(task, constraints, diversity))  # ← ❌ LÍNEA 342
    
    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        """Sync wrapper for async critique."""
        return asyncio.run(super().critique(proposal, rubric))  # ← ❌ LÍNEA 346
    
    def revise(self, content: str, feedback: str) -> str:
        """Sync wrapper for async revise."""
        return asyncio.run(super().revise(content, feedback))  # ← ❌ LÍNEA 350
```

---

## 🎭 Contexto del Problema

### Flujo de Ejecución

```
1. gRPC Server (async event loop corriendo)
   ↓
2. PlanningConsumer.handle_plan_approved() [async]
   ↓
3. AutoDispatchService.dispatch_deliberations_for_plan() [async]
   ↓
4. DeliberateUseCase.execute() [async]
   ↓
5. Deliberate.execute() (peer_deliberation_usecase.py) [async]
   ↓
6. agent.generate() → AsyncVLLMAgent.generate() [SYNC wrapper]
   ↓
7. asyncio.run(super().generate(...))  ❌ BOOM!
   
   ERROR: Ya hay un event loop corriendo (del gRPC server)
```

---

## 🤔 ¿Por Qué Existe AsyncVLLMAgent?

### Historia

**Problema Original**: 
- `VLLMAgent` (base) tiene métodos async
- Algunos callers querían interface sync
- Se creó `AsyncVLLMAgent` con wrappers sync usando `asyncio.run()`

**Cuándo Funcionaba**:
- ✅ Cuando se llamaba desde código sync (sin event loop)
- ✅ En scripts CLI
- ✅ En notebooks

**Cuándo NO Funciona**:
- ❌ Desde gRPC server async (event loop corriendo)
- ❌ Desde FastAPI async endpoints
- ❌ Desde NATS consumers async

---

## ✅ Soluciones Propuestas

### Solución 1: Eliminar AsyncVLLMAgent (RECOMENDADA)

**Razón**: Ya no se necesita porque TODO el flujo es async

**Cambios Requeridos**:

1. **Eliminar clase** `AsyncVLLMAgent` (líneas 332-351)
   
2. **Actualizar** `agent_factory.py`:
```python
# ANTES:
from .vllm_agent import AsyncVLLMAgent
return AsyncVLLMAgent(...)

# DESPUÉS:
from .vllm_agent import VLLMAgent
return VLLMAgent(...)  # ← Usa la clase base async directamente
```

3. **Actualizar** `peer_deliberation_usecase.py` (ya está listo):
```python
# Ya detecta y awaitea correctamente:
result = a.generate(...)
if hasattr(result, '__await__'):
    result = await result  # ✅ Ya implementado
```

4. **Actualizar tests** que usen `AsyncVLLMAgent` → `VLLMAgent`

**Estimación**: 30 minutos

**Impacto**: 
- ✅ Elimina code smell (asyncio.run() en async context)
- ✅ Simplifica código (una clase menos)
- ✅ Desbloquea auto-dispatch
- ❌ Breaking change para callers sync (si existen)

---

### Solución 2: Detectar Event Loop y Usar Async

**Razón**: Mantener compatibilidad sync/async

**Cambios Requeridos**:

```python
class AsyncVLLMAgent(VLLMAgent):
    def generate(self, task: str, constraints: TaskConstraints, diversity: bool = False) -> dict[str, Any]:
        """Smart wrapper: async si hay event loop, sync si no."""
        try:
            # Check if event loop is running
            loop = asyncio.get_running_loop()
            # If we're here, loop is running → return coroutine
            return super().generate(task, constraints, diversity)  # Returns coroutine
        except RuntimeError:
            # No event loop → use asyncio.run
            return asyncio.run(super().generate(task, constraints, diversity))
```

**Estimación**: 15 minutos

**Impacto**:
- ✅ Mantiene compatibilidad sync
- ✅ Funciona en contextos async
- ⚠️ Más complejo
- ⚠️ Retorna tipos diferentes (dict vs coroutine)

---

### Solución 3: Crear Dos Interfaces Separadas

**Razón**: Separar completamente sync vs async

```python
class VLLMAgent(Agent):  # Async
    async def generate(...) -> dict:
        pass

class VLLMAgentSync:  # Sync (usa asyncio.run internamente)
    def generate(...) -> dict:
        return asyncio.run(VLLMAgent(...).generate(...))
```

**Estimación**: 45 minutos

**Impacto**:
- ✅ Claridad máxima (dos clases distintas)
- ✅ No confusión
- ⚠️ Duplicación de código
- ⚠️ Más mantenimiento

---

## 🎯 Recomendación: **Solución 1** (Eliminar AsyncVLLMAgent)

### Razones:

1. **TODO el flujo es async ahora**:
   - gRPC server → async
   - PlanningConsumer → async  
   - AutoDispatchService → async
   - DeliberateUseCase → async
   - Deliberate (peer_deliberation) → async
   
2. **peer_deliberation_usecase.py YA detecta y awaitea**:
```python
result = a.generate(task, constraints, diversity=True)
if hasattr(result, '__await__'):
    result = await result  # ✅ Ya implementado
```

3. **Simplifica el código**:
   - Una clase menos
   - Sin wrappers sync innecesarios
   - Sin asyncio.run() problemático

4. **Tests también son async**:
   - Ya usan `asyncio.run()` en pytest
   - No necesitan interface sync

---

## 📋 Plan de Implementación (Solución 1)

### Paso 1: Eliminar AsyncVLLMAgent

**Archivo**: `src/swe_ai_fleet/orchestrator/domain/agents/vllm_agent.py`

```python
# ELIMINAR líneas 332-351:
class AsyncVLLMAgent(VLLMAgent):
    """Async wrapper for VLLMAgent to maintain sync interface compatibility."""
    # ... todo esto se elimina
```

---

### Paso 2: Actualizar Agent Factory

**Archivo**: `src/swe_ai_fleet/orchestrator/domain/agents/agent_factory.py`

```python
# ANTES (línea 15):
from .vllm_agent import AsyncVLLMAgent

# DESPUÉS:
from .vllm_agent import VLLMAgent

# ANTES (línea 121):
return AsyncVLLMAgent(...)

# DESPUÉS:
return VLLMAgent(...)
```

---

### Paso 3: Actualizar Tests

**Archivo**: `tests/unit/test_vllm_agent_unit.py`

```python
# Find/replace:
AsyncVLLMAgent → VLLMAgent

# Verificar que tests usen await:
result = await agent.generate(...)  # ✅
```

---

### Paso 4: Verificar Peer Deliberation

**Archivo**: `src/swe_ai_fleet/orchestrator/usecases/peer_deliberation_usecase.py`

```python
# Ya está correcto (líneas 47-50):
result = a.generate(task, constraints, diversity=True)
if hasattr(result, '__await__'):
    result = await result  # ✅ Detecta y awaitea
```

**NO requiere cambios** ✅

---

### Paso 5: Testing

```bash
# 1. Unit tests
source .venv/bin/activate
pytest tests/unit/test_vllm_agent_unit.py -v

# 2. Orchestrator tests
pytest services/orchestrator/tests/ -v

# 3. Integration tests
pytest tests/unit/orchestrator/test_deliberate_integration.py -v
```

---

### Paso 6: Rebuild & Redeploy

```bash
# Build
podman build --no-cache -f services/orchestrator/Dockerfile \
  -t registry.underpassai.com/swe-fleet/orchestrator:v2.8.0-async-agents .

# Push
podman push registry.underpassai.com/swe-fleet/orchestrator:v2.8.0-async-agents

# Deploy
kubectl set image -n swe-ai-fleet deployment/orchestrator \
  orchestrator=registry.underpassai.com/swe-fleet/orchestrator:v2.8.0-async-agents

# Restart clean
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=0
sleep 5
kubectl scale deployment/orchestrator -n swe-ai-fleet --replicas=1
```

---

### Paso 7: E2E Test

```bash
# Run auto-dispatch test
kubectl delete job -n swe-ai-fleet test-auto-dispatch
kubectl apply -f deploy/k8s/98-test-auto-dispatch-job.yaml

# Watch orchestrator logs for deliberation
kubectl logs -n swe-ai-fleet -l app=orchestrator -f
```

**Buscar en logs**:
- ✅ `🚀 Auto-dispatching deliberations for 1 roles: DEV`
- ✅ `🎭 Starting deliberation for DEV`
- ✅ `✅ Deliberation completed for DEV: X proposals in Yms`

---

## 📊 Archivos Afectados

| Archivo | Tipo de Cambio | Líneas Afectadas |
|---------|----------------|------------------|
| `src/.../vllm_agent.py` | DELETE class | 332-351 (20 líneas) |
| `src/.../agent_factory.py` | REPLACE import/return | 15, 105, 119, 121 |
| `tests/unit/test_vllm_agent_unit.py` | FIND/REPLACE | ~10 referencias |

**Total**: 3 archivos, ~30 líneas de cambios

---

## 🎓 Lecciones Aprendidas

### 1. asyncio.run() es Peligroso en Async Context

**Regla**: NUNCA usar `asyncio.run()` dentro de código que puede ser llamado desde un event loop async.

**Detectar**: Si tu código puede ser llamado desde:
- gRPC server async
- FastAPI async endpoints
- NATS consumers async
- Cualquier `async def` function

→ **NO uses `asyncio.run()`**

---

### 2. Sync Wrappers Sobre Async Son Code Smell

Si tienes:
```python
class AsyncWrapper(BaseAsync):
    def sync_method(self):
        return asyncio.run(self.async_method())  # ← Code smell
```

**Mejor**:
- Eliminar wrapper
- Hacer TODO async
- Usar `await` directamente

---

### 3. Detection Pattern en Deliberate Está Correcto

```python
# peer_deliberation_usecase.py (líneas 47-50)
result = a.generate(task, constraints, diversity=True)
if hasattr(result, '__await__'):
    result = await result  # ✅ Detecta y awaitea
```

Este patrón **ES CORRECTO** y ya maneja ambos casos (sync/async).

El problema NO es el detector, es que el wrapper sync usa `asyncio.run()`.

---

## 🚨 Impacto del Bug

### ❌ Qué NO Funciona

1. **Auto-dispatch de deliberaciones** desde planning consumer
2. **Deliberaciones triggereadas por eventos** NATS
3. **Cualquier deliberación** iniciada desde async context

### ✅ Qué SÍ Funciona

1. **Deliberaciones vía gRPC `Deliberate` RPC** directamente (FALSO - también falla)
2. **Unit tests** (usan `asyncio.run()` en pytest, no en agent)
3. **Scripts sync** que llaman deliberaciones

---

## 🔧 Workaround Temporal

**NINGUNO** - Este bug bloquea completamente las deliberaciones automáticas.

La única forma de ejecutar deliberaciones sería:
1. Modificar agent factory para usar `VLLMAgent` directamente (no `AsyncVLLMAgent`)
2. Rebuild y redeploy

**No hay workaround sin código changes.**

---

## 📅 Próximo Fix (Estimación: 45 minutos)

### Timeline:

1. **Eliminar `AsyncVLLMAgent`** (5 min)
2. **Actualizar `agent_factory.py`** (2 min)
3. **Actualizar tests** (10 min)
4. **Run all tests** (5 min)
5. **Rebuild orchestrator** (5 min)
6. **Push & deploy** (3 min)
7. **E2E test auto-dispatch** (5 min)
8. **Verification** (10 min)

**Total**: ~45 minutos para fix completo

---

## 🎯 Success Criteria

Fix será exitoso cuando veamos en logs:

```
🚀 Auto-dispatching deliberations for 1 roles: DEV
🎭 Starting deliberation for DEV: Implement plan plan-test-clean-arch...
✅ Deliberation completed for DEV: 3 proposals in 2500ms
```

**Sin errores de asyncio.run()**

---

## 📖 Referencias

- **Python asyncio docs**: https://docs.python.org/3/library/asyncio-task.html#asyncio.run
- **Issue similar**: https://github.com/python/cpython/issues/90908
- **Best practices**: No anidar `asyncio.run()` calls

---

## ✍️ Notas del Arquitecto

Este bug demuestra la importancia de:

1. **Testing end-to-end** - Los unit tests no capturaron esto
2. **Event loop awareness** - Conocer el contexto de ejecución
3. **Async all the way** - Si el stack es async, TODO debe ser async
4. **Eliminar abstracciones innecesarias** - AsyncVLLMAgent es un wrapper innecesario

**Este fix es crítico para desbloquear el sistema completo.** 🎯

---

## 🔄 Estado Actual

- ✅ Auto-dispatch implementado (código perfecto)
- ✅ AutoDispatchService creado (arquitectura limpia)
- ✅ Planning consumer refactorizado (sin code smells)
- ✅ Tests pasando (6/6 planning consumer)
- ❌ **BLOQUEADO por AsyncVLLMAgent.asyncio.run()**

**Una vez arreglado este bug, el sistema completo funcionará end-to-end!** 🚀


