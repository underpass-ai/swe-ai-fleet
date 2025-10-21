# 🔍 Análisis Riguroso: Casos de Uso de Deliberación

**Fecha**: 20 de Octubre de 2025  
**Objetivo**: Entender la arquitectura de deliberación y resolver duplicación

---

## 📋 Casos de Uso Encontrados

### Ubicaciones:

1. **`src/swe_ai_fleet/orchestrator/usecases/peer_deliberation_usecase.py`**
   - Clase: `Deliberate`
   - Líneas: 88
   - Última modificación: Hoy (async fix aplicado)

2. **`src/swe_ai_fleet/orchestrator/usecases/deliberate_async_usecase.py`**
   - Clase: `DeliberateAsync`
   - Líneas: 253
   - Función: Deliberación async via Ray Executor

3. **`services/orchestrator/application/usecases/deliberate_usecase.py`**
   - Clase: `DeliberateUseCase`
   - Líneas: 137
   - Función: Wrapper hexagonal que llama a `Deliberate` (peer_deliberation)

---

## 🎯 Análisis Caso por Caso

### 1. `Deliberate` (peer_deliberation_usecase.py)

**Ubicación**: `src/swe_ai_fleet/orchestrator/usecases/peer_deliberation_usecase.py`

**Propósito**: **Deliberación SÍNCRONA in-process** (dentro del mismo pod)

**Características**:
```python
class Deliberate:
    def __init__(self, agents: list[Agent], tooling: Scoring, rounds: int = 1)
    async def execute(task: str, constraints: TaskConstraints) -> list[DeliberationResult]
```

**Qué hace**:
1. Recibe **lista de agentes YA CREADOS**
2. Ejecuta deliberación **localmente** (mismo proceso)
3. Llama a agentes **síncronamente** (o async, detecta automáticamente)
4. Hace peer review en **N rounds**
5. Scoring y ranking **local**
6. Retorna **resultados inmediatamente**

**Cuándo se usa**:
- RPC `Deliberate` (gRPC call síncrono que espera respuesta)
- Tests unitarios
- Cuando ya tienes agentes creados en memoria

**Dependencias**:
- `Agent` (domain entity)
- `Scoring` (domain service)
- `TaskConstraints` (domain entity)

**Ventajas**:
- ✅ Respuesta inmediata
- ✅ Sin overhead de Ray
- ✅ Fácil de testear
- ✅ Sync y async compatible

**Desventajas**:
- ❌ Limitado a recursos del pod
- ❌ No escala horizontalmente
- ❌ Blocking (aunque async)

---

### 2. `DeliberateAsync` (deliberate_async_usecase.py)

**Ubicación**: `src/swe_ai_fleet/orchestrator/usecases/deliberate_async_usecase.py`

**Propósito**: **Deliberación ASÍNCRONA distribuida** (via Ray cluster)

**Características**:
```python
class DeliberateAsync:
    def __init__(self, ray_executor_stub, vllm_url, model, nats_url)
    async def execute(task_id, task_description, role, num_agents) -> dict
    async def get_deliberation_status(deliberation_id) -> dict
```

**Qué hace**:
1. **NO crea agentes** - los crea Ray Executor
2. Llama a **Ray Executor via gRPC**
3. Ray Executor crea jobs en Ray cluster
4. **Retorna INMEDIATAMENTE** con deliberation_id
5. Resultados se publican a **NATS asíncronamente**
6. Cliente debe **polling** para obtener resultado

**Cuándo se usa**:
- Deliberaciones **long-running**
- Cuando necesitas **escalabilidad horizontal**
- Fire-and-forget pattern
- **ACTUALMENTE**: NO ESTÁ SIENDO USADO ⚠️

**Dependencias**:
- Ray Executor gRPC service
- Ray cluster
- NATS JetStream
- vLLM server

**Ventajas**:
- ✅ Non-blocking
- ✅ Escala horizontalmente (Ray)
- ✅ Puede manejar miles de deliberaciones
- ✅ Fault-tolerant (Ray)

**Desventajas**:
- ❌ Más complejo
- ❌ Requiere polling para resultados
- ❌ Overhead de Ray + gRPC

---

### 3. `DeliberateUseCase` (Hexagonal)

**Ubicación**: `services/orchestrator/application/usecases/deliberate_usecase.py`

**Propósito**: **WRAPPER hexagonal** sobre `Deliberate` (peer_deliberation)

**Características**:
```python
class DeliberateUseCase:
    def __init__(self, stats: OrchestratorStatistics, messaging: MessagingPort)
    async def execute(council, role, task_description, constraints) -> DeliberationResult
```

**Qué hace**:
1. Recibe **council ya creado** (instancia de `Deliberate`)
2. **Valida inputs** (fail-fast)
3. Llama a **council.execute()** (await)
4. **Actualiza estadísticas**
5. **Publica evento** DeliberationCompletedEvent
6. Retorna **NamedTuple tipado**

**Relación con `Deliberate`**:
```python
# DeliberateUseCase es un WRAPPER:
results = await council.execute(task, constraints)
# ↑ council ES una instancia de Deliberate (peer_deliberation_usecase)
```

**Cuándo se usa**:
- RPC `Deliberate` en `server.py` (línea 188)
- Cuando necesitas orchestration logic adicional:
  - Stats tracking
  - Event publishing
  - Domain event handling

**Ventajas**:
- ✅ Hexagonal Architecture
- ✅ Separation of Concerns
- ✅ Stats y events centralizados
- ✅ Testeable sin infraestructura

**Desventajas**:
- Ninguna, es buen diseño ✅

---

## 🏗️ Arquitectura - Cómo se Relacionan

```
┌─────────────────────────────────────────────────────────────┐
│                      gRPC Server                            │
│                     (server.py)                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌────────────────────┐    ┌──────────────────────┐
│ RPC: Deliberate    │    │ RPC: StreamDelib...  │
│ (sync, blocking)   │    │ (UNIMPLEMENTED)      │
└────────┬───────────┘    └──────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ DeliberateUseCase (Hexagonal Wrapper)   │
│ services/orchestrator/application/      │
│                                         │
│ - Validates inputs                      │
│ - Updates statistics                    │
│ - Publishes events                      │
│ - Calls council.execute()               │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ Deliberate (Peer Deliberation)          │
│ src/swe_ai_fleet/.../peer_deliberation  │
│                                         │
│ - Manages agent collaboration           │
│ - Peer review rounds                    │
│ - Proposal generation/critique/revise   │
│ - Scoring and ranking                   │
└────────┬────────────────────────────────┘
         │
         ▼
    ┌───┴────┐
    │ Agents │
    └────────┘
```

**RELACIÓN**:
- `DeliberateUseCase` **WRAPPER de** `Deliberate`
- `Deliberate` **EJECUTA** la deliberación real
- `DeliberateAsync` **ALTERNATIVA** distribuida (NO se usa actualmente)

---

## 📊 Comparación Rigurosa

| Característica | Deliberate<br/>(peer_deliberation) | DeliberateAsync<br/>(async via Ray) | DeliberateUseCase<br/>(Hexagonal) |
|----------------|-----------------------------------|-------------------------------------|-----------------------------------|
| **Ubicación** | `src/.../peer_deliberation_usecase.py` | `src/.../deliberate_async_usecase.py` | `services/.../deliberate_usecase.py` |
| **Tipo** | Core logic | Async alternative | Hexagonal wrapper |
| **Patrón** | Strategy | Fire-and-forget | Application Service |
| **Execution** | In-process | Distributed (Ray) | Delegates to Deliberate |
| **Retorna** | Results immediately | deliberation_id | NamedTuple result |
| **Agentes** | Pre-created in memory | Created by Ray Executor | From council parameter |
| **Estadísticas** | ❌ No | ❌ No | ✅ Sí |
| **Eventos** | ❌ No | ❌ No | ✅ Sí (via MessagingPort) |
| **Tests** | 32 tests | 0 tests (deprecated?) | 4 tests |
| **Usado en** | server.py (via wrapper) | ❌ Nowhere | server.py Deliberate RPC |
| **Async Fix** | ✅ Aplicado | N/A | ✅ Aplicado (llama con await) |

---

## 🔄 Flujo Real en Código

### Cuando llamas `Deliberate` RPC:

```python
# 1. server.py línea 165
async def Deliberate(self, request, context):
    council = self.council_registry.get_council(request.role)
    
    # 2. Llama al wrapper hexagonal
    deliberate_uc = DeliberateUseCase(
        stats=self.stats,
        messaging=self.messaging
    )
    
    # 3. Wrapper ejecuta el council
    deliberation_result = await deliberate_uc.execute(
        council=council,  # ← Este council ES Deliberate (peer_deliberation)
        role=request.role,
        task_description=request.task_description,
        constraints=constraints,
    )
    
    # 4. Wrapper internamente hace:
    # services/orchestrator/application/usecases/deliberate_usecase.py línea 101:
    results = await council.execute(task_description, constraints)
    #                ↑
    #                └─ council = Deliberate instance (peer_deliberation_usecase)
    
    # 5. Deliberate ejecuta agents:
    # src/swe_ai_fleet/orchestrator/usecases/peer_deliberation_usecase.py línea 33:
    async def execute(self, task, constraints):
        # Generate proposals
        # Peer review
        # Score and rank
        return sorted_results
```

---

## ❓ Por Qué Existen Ambos

### `Deliberate` (peer_deliberation_usecase.py)
**Razón de existir**: Core deliberation logic

- Es el **algoritmo real** de deliberación
- Implementa peer review multi-round
- **Reutilizable** en diferentes contextos
- **Domain logic puro**

### `DeliberateAsync` (deliberate_async_usecase.py)
**Razón de existir**: Escalabilidad horizontal

- Para **carga alta** (miles de deliberaciones)
- Distribución en Ray cluster
- **Fire-and-forget** pattern
- **Actualmente NO usado** ⚠️

### `DeliberateUseCase` (Hexagonal)
**Razón de existir**: Application orchestration

- **Wrapper hexagonal** sobre `Deliberate`
- Agrega **cross-cutting concerns**:
  - Statistics tracking
  - Event publishing
  - Validation
  - Error handling
- **Separation of Concerns**

---

## 🚨 Problema Actual

### El Issue:

El `server.py` llama correctamente:

```python
# server.py línea 188:
deliberation_result = await deliberate_uc.execute(
    council=council,
    ...
)
```

Y `DeliberateUseCase` hace:

```python
# deliberate_usecase.py línea 101:
results = await council.execute(task_description, constraints)
```

Y `Deliberate` (peer_deliberation) es:

```python
# peer_deliberation_usecase.py línea 33:
async def execute(self, task, constraints):
    # ✅ ASYNC CORRECTO
```

**ENTONCES, ¿POR QUÉ SIGUE FALLANDO?**

---

## 🔍 Investigación del Error

El error dice:
```
asyncio.run() cannot be called from a running event loop
```

Esto significa que **EN ALGÚN LUGAR** se está llamando `asyncio.run()`.

### Posibles Lugares:

#### 1. ¿En los agentes?

Vamos a verificar si `VLLMAgent` usa `asyncio.run()`:

**Archivo a revisar**: `src/swe_ai_fleet/agents/vllm_agent.py`

---

## 💡 Hipótesis

**El código que fixeamos en `peer_deliberation_usecase.py` NO es el que está causando el error.**

**Posibilidades**:

1. **VLLMAgent.generate/critique/revise** usan `asyncio.run()` internamente
2. **Scoring service** usa `asyncio.run()` 
3. El código en el container **NO tiene el fix** (cache de Docker)

---

## 🎯 Siguiente Paso: Verificar VLLMAgent

Necesitamos leer `VLLMAgent` para ver si tiene `asyncio.run()`:

```bash
grep -n "asyncio.run" src/swe_ai_fleet/agents/vllm_agent.py
```

Si `VLLMAgent` usa `asyncio.run()`, ese es el verdadero problema.

---

## 📊 Resumen Arquitectura

### Diseño Correcto:

```
DeliberateUseCase (Hexagonal)
    ↓ delega a
Deliberate (Peer Deliberation) ← CORE LOGIC
    ↓ usa
VLLMAgent ← PUEDE TENER EL BUG
```

### Alternativa (No Usada):

```
DeliberateAsync
    ↓ llama vía gRPC
Ray Executor
    ↓ crea jobs en
Ray Cluster
    ↓ ejecuta
VLLMAgentJob
```

---

## ✅ Conclusiones Rigurosas

### 1. NO hay duplicación innecesaria

Los 3 casos de uso tienen **propósitos diferentes**:
- **Deliberate**: Core algorithm
- **DeliberateAsync**: Scalability alternative (not used)
- **DeliberateUseCase**: Hexagonal wrapper

### 2. La arquitectura es correcta

Es **buen diseño** tener:
- Core logic (`Deliberate`)
- Application wrapper (`DeliberateUseCase`)
- Alternative implementation (`DeliberateAsync`)

### 3. El bug NO está donde pensamos

El async fix en `Deliberate.execute()` está **correcto**, pero:
- ⚠️ **VLLMAgent probablemente usa `asyncio.run()`**
- ⚠️ O el container no tiene el código actualizado

### 4. Necesitamos verificar VLLMAgent

**Archivo crítico**: `src/swe_ai_fleet/agents/vllm_agent.py`

**Buscar**:
```python
def generate(...):
    asyncio.run(...)  # ← BUG REAL
```

**Fix**:
```python
async def generate(...):
    await ...  # ← CORRECTO
```

---

## 🔧 Plan de Acción

1. ✅ **Verificar VLLMAgent** tiene asyncio.run()
2. ✅ **Fixear VLLMAgent** si es necesario
3. ✅ **Rebuild** sin cache
4. ✅ **Redeploy** y testear
5. ✅ **Eliminar `DeliberateAsync`** si no se usa

---

## 📝 Recomendaciones

### Mantener:
- ✅ `Deliberate` (peer_deliberation) - Core logic
- ✅ `DeliberateUseCase` (Hexagonal) - Application wrapper

### Eliminar:
- ⚠️ `DeliberateAsync` - No se usa, agrega confusión

### Documentar:
- 📝 README explicando diferencia entre Deliberate y DeliberateUseCase
- 📝 Cuándo usar cada uno
- 📝 Diagramas de secuencia actualizados


