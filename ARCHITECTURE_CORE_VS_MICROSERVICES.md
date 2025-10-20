# 🏗️ Arquitectura: Core vs Microservicios - SIN CONFUSIONES

**Fecha**: 20 de Octubre de 2025  
**Objetivo**: Aclarar de una vez por todas qué es qué en el proyecto

---

## 🎯 LA VERDAD ABSOLUTA

### HAY DOS CAPAS DE CÓDIGO COMPLETAMENTE DIFERENTES:

```
swe-ai-fleet/
├── src/swe_ai_fleet/              ← 🔵 CORE (Lógica de Negocio Reutilizable)
│   ├── orchestrator/              ← Core orchestration logic
│   ├── agents/                    ← Core agent implementations
│   ├── context/                   ← Core context logic
│   └── ray_jobs/                  ← Core Ray job logic
│
└── services/                      ← 🟢 MICROSERVICIOS (gRPC/HTTP Servers)
    ├── orchestrator/              ← Orchestrator Microservice (Hexagonal)
    ├── context/                   ← Context Microservice
    ├── ray-executor/              ← Ray Executor Microservice
    └── monitoring/                ← Monitoring Dashboard
```

---

## 🔵 CORE (`src/swe_ai_fleet/`)

### Propósito:
**Lógica de negocio pura, reutilizable, sin infraestructura**

### Qué contiene:
- **Domain logic** (algoritmos, reglas de negocio)
- **Agents** (VLLMAgent, ToolEnabledAgent, etc.)
- **Use cases ORIGINALES** (peer_deliberation, dispatch, etc.)
- **Domain entities** (Task, Agent, Role, etc.)

### Características:
- ✅ **Reutilizable** entre microservicios
- ✅ **Sin gRPC** (no sabe que existen microservicios)
- ✅ **Sin NATS** (no sabe que existe messaging)
- ✅ **Testeable** sin infraestructura
- ✅ **Python puro** (solo lógica)

### Ejemplos de archivos CORE:
```
src/swe_ai_fleet/orchestrator/usecases/
├── peer_deliberation_usecase.py   ← CORE: Algoritmo de deliberación
├── dispatch_usecase.py            ← CORE: Algoritmo de dispatch
└── deliberate_async_usecase.py    ← CORE: Variant async (via Ray)

src/swe_ai_fleet/agents/
├── vllm_agent.py                  ← CORE: Implementación de agente vLLM
├── profile_loader.py              ← CORE: Carga de perfiles
└── mock_agent.py                  ← CORE: Agente para testing
```

---

## 🟢 MICROSERVICIOS (`services/`)

### Propósito:
**Servers gRPC/HTTP que USAN el core, con arquitectura hexagonal**

### Qué contiene:
- **Entry points** (server.py)
- **Hexagonal Architecture** (Domain/Application/Infrastructure)
- **Adapters** (NATS, gRPC, Redis, Neo4j)
- **Handlers** (Event consumers)
- **Mappers** (DTO ↔ Domain)

### Características:
- ✅ **Usa código de `src/`** como librería
- ✅ **Hexagonal Architecture** (Ports & Adapters)
- ✅ **gRPC servers** (expone APIs)
- ✅ **Event consumers** (NATS)
- ✅ **Infrastructure** (databases, messaging)

### Ejemplos de archivos MICROSERVICIO:
```
services/orchestrator/
├── server.py                          ← gRPC Server (entry point)
├── domain/                            ← Domain Layer (HEXAGONAL)
│   ├── entities/                      ← Entities específicas del MS
│   ├── ports/                         ← Interfaces (contracts)
│   └── value_objects/                 ← VOs específicos del MS
├── application/                       ← Application Layer (HEXAGONAL)
│   └── usecases/
│       └── deliberate_usecase.py      ← WRAPPER sobre core/peer_deliberation
└── infrastructure/                    ← Infrastructure Layer (HEXAGONAL)
    ├── adapters/                      ← Implementaciones de ports
    ├── handlers/                      ← NATS event handlers
    └── mappers/                       ← DTO ↔ Domain mappers
```

---

## 🔗 CÓMO SE RELACIONAN

### Relación: **MICROSERVICIO USA CORE**

```python
# services/orchestrator/server.py (MICROSERVICIO)
# ↓ USA ↓
from swe_ai_fleet.orchestrator.usecases.peer_deliberation_usecase import Deliberate  # CORE
from swe_ai_fleet.orchestrator.domain.agents.agent_factory import AgentFactory  # CORE
from swe_ai_fleet.orchestrator.domain.tasks.task_constraints import TaskConstraints  # CORE

# El microservicio ENVUELVE el core con hexagonal:
from services.orchestrator.application.usecases import DeliberateUseCase  # WRAPPER

# Luego:
council = Deliberate(agents, scoring, rounds)  # ← CORE
deliberate_uc = DeliberateUseCase(stats, messaging)  # ← WRAPPER HEXAGONAL
result = await deliberate_uc.execute(council, ...)  # ← Wrapper llama core
```

---

## 📊 Casos de Uso de Deliberación - ACLARACIÓN DEFINITIVA

### HAY 3 CLASES CON NOMBRES SIMILARES:

| Clase | Ubicación | Tipo | Propósito | Quién la Usa |
|-------|-----------|------|-----------|--------------|
| **`Deliberate`** | `src/.../peer_deliberation_usecase.py` | 🔵 **CORE** | **ALGORITMO** de deliberación peer-to-peer | Council, Tests, Microservicio |
| **`DeliberateAsync`** | `src/.../deliberate_async_usecase.py` | 🔵 **CORE** | **ALTERNATIVA** async via Ray Executor | ❌ Nadie (deprecated) |
| **`DeliberateUseCase`** | `services/.../deliberate_usecase.py` | 🟢 **MICROSERVICIO** | **WRAPPER hexagonal** sobre `Deliberate` | server.py (gRPC) |

---

## 🎭 LA JERARQUÍA REAL

```
┌─────────────────────────────────────────────────────────┐
│           MICROSERVICIO: Orchestrator                   │
│           services/orchestrator/server.py               │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │  HEXAGONAL LAYER: Application                     │ │
│  │  services/orchestrator/application/usecases/      │ │
│  │                                                    │ │
│  │  DeliberateUseCase (WRAPPER)                      │ │
│  │  - Agrega: Stats, Events, Validation             │ │
│  │  - Llama a: Deliberate (CORE)                    │ │
│  └──────────────────┬────────────────────────────────┘ │
│                     │                                   │
│                     ▼                                   │
│  ┌───────────────────────────────────────────────────┐ │
│  │  CORE LOGIC (Imported from src/)                 │ │
│  │  src/swe_ai_fleet/orchestrator/usecases/         │ │
│  │                                                    │ │
│  │  Deliberate (ALGORITMO REAL)                      │ │
│  │  - Peer review                                    │ │
│  │  - Agent coordination                             │ │
│  │  - Scoring and ranking                            │ │
│  └──────────────────┬────────────────────────────────┘ │
│                     │                                   │
└─────────────────────┼───────────────────────────────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │  CORE: Agents         │
          │  src/swe_ai_fleet/    │
          │  agents/              │
          │                       │
          │  - VLLMAgent          │
          │  - MockAgent          │
          │  - AgentFactory       │
          └───────────────────────┘
```

---

## 💡 REGLA DE ORO

### 🔵 `src/` = CORE (Business Logic)
**Características**:
- ✅ Lógica de negocio pura
- ✅ Reutilizable
- ✅ Sin infraestructura (no gRPC, no NATS, no Redis)
- ✅ Testeable en isolation
- ✅ Compartida entre microservicios

**Ejemplos**:
- `Deliberate` - Algoritmo de deliberación
- `VLLMAgent` - Implementación de agente
- `TaskConstraints` - Entidad de dominio
- `Scoring` - Servicio de scoring

---

### 🟢 `services/` = MICROSERVICIOS (Infrastructure)
**Características**:
- ✅ gRPC servers (entry points)
- ✅ Hexagonal Architecture
- ✅ Adapters (NATS, Redis, Neo4j)
- ✅ **IMPORTA código de `src/`**
- ✅ **ENVUELVE** core con cross-cutting concerns

**Ejemplos**:
- `DeliberateUseCase` - Wrapper que agrega stats y events
- `NATSMessagingAdapter` - Adapter para NATS
- `GRPCRayExecutorAdapter` - Adapter para Ray Executor
- `PlanningConsumer` - Event handler

---

## 🔄 FLUJO COMPLETO (CLARÍSIMO)

### Cuando llamas RPC `Deliberate`:

```
1. CLIENT
   ↓
   gRPC call Deliberate(task, role)
   ↓
2. MICROSERVICIO (services/orchestrator/server.py)
   ↓
   async def Deliberate(request, context):
   ↓
3. HEXAGONAL WRAPPER (services/orchestrator/application/usecases/)
   ↓
   DeliberateUseCase(stats, messaging)
   await deliberate_uc.execute(council, role, task, ...)
   ↓
4. CORE ALGORITHM (src/swe_ai_fleet/orchestrator/usecases/)
   ↓
   Deliberate instance (council)
   await council.execute(task, constraints)
   ↓
5. CORE AGENTS (src/swe_ai_fleet/agents/)
   ↓
   VLLMAgent.generate()
   VLLMAgent.critique()
   VLLMAgent.revise()
   ↓
6. RESULTS
   ↓
   Deliberate returns sorted results
   ↓
   DeliberateUseCase updates stats + publishes events
   ↓
   server.py maps to protobuf
   ↓
   CLIENT receives DeliberateResponse
```

---

## 📝 POR QUÉ ESTA SEPARACIÓN

### Razón 1: **Reutilización**

El **CORE** (`src/`) puede ser usado por:
- ✅ Microservicio Orchestrator
- ✅ Microservicio Ray Executor
- ✅ Scripts de CLI
- ✅ Tests
- ✅ Jupyter notebooks

### Razón 2: **Separation of Concerns**

| Responsabilidad | Dónde | Quién |
|-----------------|-------|-------|
| **Algoritmo de deliberación** | `src/` CORE | `Deliberate` |
| **Stats tracking** | `services/` MS | `DeliberateUseCase` |
| **Event publishing** | `services/` MS | `DeliberateUseCase` |
| **gRPC marshalling** | `services/` MS | `server.py` + mappers |
| **NATS connection** | `services/` MS | `NATSMessagingAdapter` |

### Razón 3: **Testabilidad**

```python
# Test del CORE (sin infraestructura):
deliberate = Deliberate(mock_agents, mock_scoring, rounds=1)
results = await deliberate.execute(task, constraints)
# ✅ Simple, rápido, sin dependencias

# Test del MICROSERVICIO (con mocks de ports):
deliberate_uc = DeliberateUseCase(mock_stats, mock_messaging)
result = await deliberate_uc.execute(mock_council, role, task, ...)
# ✅ Testa stats, events, sin NATS real
```

---

## ⚠️ CONFUSIÓN COMÚN (Y CÓMO EVITARLA)

### ❌ **ERROR COMÚN**:
"Hay 3 clases de deliberación, ¿cuál uso?"

### ✅ **RESPUESTA CLARA**:

#### Si estás en `src/` (CORE):
→ Usa `Deliberate` (peer_deliberation_usecase.py)

#### Si estás en `services/` (MICROSERVICIO):
→ Usa `DeliberateUseCase` (wrapper hexagonal)

#### Si necesitas escalabilidad horizontal:
→ Considera `DeliberateAsync` (pero actualmente no se usa)

---

## 📐 DIAGRAMA DEFINITIVO

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🔵 CORE (src/swe_ai_fleet/)                       ┃
┃                                                    ┃
┃  ┌──────────────────────────────────────────────┐ ┃
┃  │  Deliberate (peer_deliberation_usecase.py)   │ ┃
┃  │  ==========================================  │ ┃
┃  │  • ALGORITMO de peer review                  │ ┃
┃  │  • Coordina agentes                          │ ┃  
┃  │  • Genera/Critica/Revisa proposals           │ ┃
┃  │  • Scoring y ranking                         │ ┃
┃  │  • NO stats, NO events, NO infra             │ ┃
┃  │                                              │ ┃
┃  │  async def execute(task, constraints)        │ ┃
┃  │      → list[DeliberationResult]              │ ┃
┃  └──────────────────────────────────────────────┘ ┃
┃                                                    ┃
┃  ┌──────────────────────────────────────────────┐ ┃
┃  │  VLLMAgent (vllm_agent.py)                   │ ┃
┃  │  • generate(), critique(), revise()          │ ┃
┃  └──────────────────────────────────────────────┘ ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                       ▲
                       │ IMPORTS
                       │
┏━━━━━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🟢 MICROSERVICIO (services/orchestrator/)       ┃
┃                                                  ┃
┃  ┌────────────────────────────────────────────┐ ┃
┃  │  server.py (gRPC Server)                   │ ┃
┃  │  async def Deliberate(request, context):   │ ┃
┃  └──────────────────┬─────────────────────────┘ ┃
┃                     │                            ┃
┃                     ▼                            ┃
┃  ┌────────────────────────────────────────────┐ ┃
┃  │  DeliberateUseCase (Hexagonal Wrapper)     │ ┃
┃  │  application/usecases/deliberate_usecase   │ ┃
┃  │  =========================================  │ ┃
┃  │  • ENVUELVE Deliberate (core)              │ ┃
┃  │  • AGREGA: Stats tracking                  │ ┃
┃  │  • AGREGA: Event publishing                │ ┃
┃  │  • AGREGA: Validation                      │ ┃
┃  │  • DELEGA a council.execute()              │ ┃
┃  │                                            │ ┃
┃  │  async def execute(council, role, task...) │ ┃
┃  │      results = await council.execute(...)  │ ┃
┃  │                      ↑                      │ ┃
┃  │                      └─ council = Deliberate (CORE) ┃
┃  └────────────────────────────────────────────┘ ┃
┃                                                  ┃
┃  ┌────────────────────────────────────────────┐ ┃
┃  │  Infrastructure Adapters                   │ ┃
┃  │  • NATSMessagingAdapter                    │ ┃
┃  │  • GRPCRayExecutorAdapter                  │ ┃
┃  │  • EnvironmentConfigurationAdapter         │ ┃
┃  └────────────────────────────────────────────┘ ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

---

## 🎯 EJEMPLO CONCRETO: Peer Deliberation

### 🔵 CORE: `Deliberate`

**Archivo**: `src/swe_ai_fleet/orchestrator/usecases/peer_deliberation_usecase.py`

**Responsabilidad**: **SOLO el algoritmo de peer review**

```python
class Deliberate:
    def __init__(self, agents, tooling, rounds):
        self._agents = agents
        self._tooling = tooling
        self._rounds = rounds
    
    async def execute(self, task, constraints):
        # 1. Generate proposals
        proposals = [await a.generate(task) for a in self._agents]
        
        # 2. Peer review rounds
        for _ in range(self._rounds):
            for agent, proposal in zip(self._agents, proposals):
                feedback = await agent.critique(proposal)
                revised = await agent.revise(proposal, feedback)
        
        # 3. Score and rank
        results = [score(p) for p in proposals]
        return sorted(results, key=lambda x: x.score, reverse=True)
```

**NO sabe nada de**:
- ❌ gRPC
- ❌ NATS
- ❌ Estadísticas del microservicio
- ❌ Eventos de dominio del MS

---

### 🟢 MICROSERVICIO: `DeliberateUseCase`

**Archivo**: `services/orchestrator/application/usecases/deliberate_usecase.py`

**Responsabilidad**: **Orchestrar** la deliberación + cross-cutting concerns

```python
class DeliberateUseCase:
    def __init__(self, stats, messaging):
        self._stats = stats          # ← MS concern
        self._messaging = messaging  # ← MS concern
    
    async def execute(self, council, role, task, constraints, story_id, task_id):
        # VALIDACIÓN (MS concern)
        if not task: raise ValueError()
        
        # DELEGACIÓN AL CORE
        results = await council.execute(task, constraints)
        #               ↑
        #               └─ council ES Deliberate (CORE)
        
        # STATS (MS concern)
        self._stats.increment_deliberation(role, duration_ms)
        
        # EVENTOS (MS concern)
        if self._messaging:
            await self._messaging.publish(DeliberationCompletedEvent(...))
        
        # RETORNO TIPADO (MS concern)
        return DeliberationResult(results, duration_ms, stats)
```

**Sabe de**:
- ✅ OrchestratorStatistics (MS entity)
- ✅ MessagingPort (MS port)
- ✅ DeliberationCompletedEvent (MS event)
- ✅ NATS (via port)

**NO duplica**:
- ✅ Peer review logic (está en `Deliberate` CORE)
- ✅ Agent coordination (está en `Deliberate` CORE)

---

## ✅ CONCLUSIÓN SIN CONFUSIONES

### La Verdad:

1. **`Deliberate` (CORE)** = El algoritmo de deliberación
2. **`DeliberateUseCase` (MS)** = Wrapper hexagonal que agrega stats/events
3. **NO hay duplicación** - Es un patrón correcto
4. **`DeliberateUseCase` DELEGA a `Deliberate`** - Wrapper pattern

### Analogía:

```
CORE (src/)          = Motor de un carro
MICROSERVICIO        = El carro completo (con dashboard, radio, AC)

Deliberate           = Motor (hace el trabajo)
DeliberateUseCase    = Dashboard (monitorea el motor, agrega métricas)
```

---

## 🚨 EL VERDADERO PROBLEMA

### NO es duplicación de código

El problema **NO** es que tengamos 2-3 clases similares.

### El problema ES:

**`planning_consumer.py` NO llama a NINGUNO de los casos de uso de deliberación**

```python
# planning_consumer.py línea 220 (ACTUAL):
logger.info("TODO: Auto-dispatch deliberations using DeliberateUseCase")
# ↑
# └─ Solo loggea, NO ejecuta nada

# planning_consumer.py línea 220 (DEBERÍA SER):
council = self.council_registry.get_council(role)
deliberate_uc = DeliberateUseCase(self.stats, self.messaging)
result = await deliberate_uc.execute(council, role, task, ...)
# ↑
# └─ Ejecuta deliberación REAL
```

---

## 📊 Estadísticas de Uso

| Clase | Usado Por | Frecuencia | Estado |
|-------|-----------|------------|--------|
| **`Deliberate` (CORE)** | server.py (via wrapper)<br/>32 tests<br/>Orchestrate usecase | **ALTO** | ✅ Activo |
| **`DeliberateAsync` (CORE)** | ❌ Nadie | **ZERO** | ⚠️ Deprecated |
| **`DeliberateUseCase` (MS)** | server.py<br/>4 tests | **MEDIO** | ✅ Activo |

---

## 🎯 Recomendaciones

### Mantener:
1. ✅ **`Deliberate` (CORE)** - Es el core algorithm, crítico
2. ✅ **`DeliberateUseCase` (MS)** - Wrapper hexagonal correcto

### Eliminar o Documentar:
3. ⚠️ **`DeliberateAsync` (CORE)** - Decidir:
   - Opción A: Eliminar si no se usará
   - Opción B: Documentar como "Future scalability option"
   - Opción C: Usarlo para long-running deliberations

### Documentar Claramente:
4. 📝 Crear `README.md` en `src/swe_ai_fleet/orchestrator/` explicando:
   - Qué es CORE vs MICROSERVICIO
   - Cuándo usar cada clase
   - Relación entre ellas

5. 📝 Agregar comentarios en `DeliberateUseCase`:
```python
class DeliberateUseCase:
    """Hexagonal wrapper over Deliberate (core algorithm).
    
    This use case DELEGATES to Deliberate (peer_deliberation_usecase.py)
    and adds microservice concerns:
    - Statistics tracking
    - Event publishing
    - Validation
    
    The actual deliberation algorithm is in src/swe_ai_fleet/orchestrator/
    usecases/peer_deliberation_usecase.py (Deliberate class).
    """
```

---

## 🎊 RESUMEN ULTRA-CLARO

### La Arquitectura:

```
src/               = Librería de lógica de negocio (CORE)
services/          = Microservicios que USAN el core

Deliberate         = Algoritmo (CORE)
DeliberateUseCase  = Wrapper con stats/events (MICROSERVICIO)

Relación           = MICROSERVICIO IMPORTA Y USA CORE
```

### El Problema Actual:

**NO es arquitectura. La arquitectura es CORRECTA.**

**El problema ES**: `planning_consumer.py` no llama a deliberaciones.

### El Fix:

**3 líneas** en `planning_consumer.py` para llamar a `DeliberateUseCase`.

**¡Eso es TODO!** 🎯


