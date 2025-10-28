# Bounded Contexts Coupling Analysis — CRÍTICO

**Date**: October 28, 2025  
**Status**: ⚠️ ACOPLAMIENTO DETECTADO  
**Priority**: HIGH — Architectural Violation

---

## 🚨 Problema Detectado

El bounded context `orchestrator` (core) importa directamente de `context` (core), violando los principios de DDD:

```python
# ❌ VIOLACIÓN: orchestrator importa de context
from core.context.ports.graph_command_port import GraphCommandPort
from core.context.ports.graph_query_port import GraphQueryPort
from core.context.usecases.rehydrate_context import RehydrateContextUseCase
from core.context.usecases.update_subtask_status import UpdateSubtaskStatusUseCase
```

**Ubicación**: `core/orchestrator/handler/agent_job_worker.py`

---

## ✅ Estado Actual de Desacoplamiento

### Bounded Context: `agents_and_tools` ✅
- **Estado**: COMPLETAMENTE AISLADO
- **Importa de**:
  - ✅ Solo módulos propios (`core.agents_and_tools.*`)
- **NO importa**:
  - ❌ NO importa de `core.context/`
  - ❌ NO importa de `core.orchestrator/`
- **Comunicación**: Vía string serializable (`context: str`)

### Bounded Context: `context` ✅
- **Estado**: COMPLETAMENTE AISLADO
- **Importa de**:
  - ✅ Solo módulos propios (`core.context.*`)
- **NO importa**:
  - ❌ NO importa de `core.agents_and_tools/`
  - ❌ NO importa de `core.orchestrator/`

### Bounded Context: `orchestrator` ⚠️
- **Estado**: ACOPLADO a `context/`
- **Importa de**:
  - ✅ Propios (`core.orchestrator.*`)
  - ❌ **context/ports/** (violación)
  - ❌ **context/usecases/** (violación)
- **NO importa**:
  - ✅ NO importa de `core.agents_and_tools/`

---

## 📊 Matriz de Acoplamiento

```
                    agents_and_tools    context    orchestrator
agents_and_tools          ✅              ✅           ✅
context                    ✅              ✅           ✅
orchestrator               ✅              ❌           ✅
```

Leyenda:
- ✅ = Sin acoplamiento
- ❌ = Acoplamiento detectado (violación)

---

## 🎯 Solución Correcta

### Patrón Actual (Incorrecto)
```
orchestrator (core)  --imports-->  context (core)
```

**Problema**: Acoplamiento directo a nivel de `core/`, violando separación de bounded contexts.

### Patrón Correcto (Por Implementar)
```
orchestrator (services)  <--gRPC-->  context (services)
      |                                      |
      v                                      v
orchestrator (core)              context (core)
```

**Flujo correcto**:
1. **Microservicios se comunican**: `services/orchestrator/` ↔ `services/context/` vía gRPC/NATS
2. **Bounded contexts están aislados**: `core/orchestrator/` NO importa de `core/context/`

---

## 🔧 Arquitectura Correcta

### Comunicación Entre Microservicios

```
┌─────────────────────────┐         ┌─────────────────────────┐
│  Orchestrator Service  │  gRPC   │   Context Service       │
│  (services/orchestrator)│ ◄─────► │   (services/context)    │
└─────────────────────────┘         └─────────────────────────┘
         │                                      │
         │ Uses                                 │ Uses
         ▼                                      ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│  orchestrator (core)    │         │   context (core)       │
│  - Domain entities      │         │   - Domain entities    │
│  - Use cases            │         │   - Use cases          │
│  - Handlers             │         │   - Ports              │
└─────────────────────────┘         └─────────────────────────┘
```

**Regla**: Solo `services/*/` importan de `core/*/`. Los `services/*` se comunican entre sí.

---

## 🛠️ Refactoring Requerido

### 1. Aislar Core Bounded Contexts

**Acción**: Mover todas las importaciones de `core.context` fuera de `core/orchestrator/handler/`

**Archivo**: `core/orchestrator/handler/agent_job_worker.py`

**Antes (Actual)**:
```python
# ❌ En core/orchestrator/handler/agent_job_worker.py
from core.context.ports.graph_command_port import GraphCommandPort
from core.context.ports.graph_query_port import GraphQueryPort
from core.context.usecases.rehydrate_context import RehydrateContextUseCase
from core.context.usecases.update_subtask_status import UpdateSubtaskStatusUseCase
```

**Después (Correcto)**:
```python
# ✅ En core/orchestrator/handler/agent_job_worker.py
# NO importa de context directamente

# En su lugar, el worker recibe puertos como dependencias inyectadas
class AgentJobWorker:
    def __init__(
        self,
        context_service: Any,  # gRPC client stub
        # NO importa GraphQueryPort directamente
    ):
        self.context_service = context_service
```

### 2. Implementar Comunicación en Microservicio

**Archivo**: `services/orchestrator/server.py`

**Implementar**:
```python
# ✅ En services/orchestrator/server.py
import grpc
from gen import context_pb2_grpc  # Generated from specs/context.proto

class OrchestratorService:
    def __init__(self):
        # Connect to Context Service via gRPC
        context_channel = grpc.insecure_channel('context-service:50054')
        self.context_stub = context_pb2_grpc.ContextServiceStub(context_channel)
```

### 3. Definir Contrato gRPC

**Archivo**: `specs/context.proto`

**Agregar método**:
```protobuf
service ContextService {
  rpc GetContext(ContextRequest) returns (ContextResponse);
  rpc RehydrateContext(RehydrationRequest) returns (RehydrationResponse);
  rpc UpdateSubtaskStatus(UpdateRequest) returns (UpdateResponse);
}
```

---

## 📋 Plan de Refactoring

### Fase 1: Análisis (DONE)
- [x] Identificar acoplamientos
- [x] Mapear dependencias
- [x] Documentar arquitectura correcta

### Fase 2: Definir Contrato (TODO)
- [ ] Crear/actualizar `specs/context.proto`
- [ ] Definir mensajes: `RehydrationRequest`, `ContextResponse`
- [ ] Generar clientes/servidores con `make gen`

### Fase 3: Aislar Core (TODO)
- [ ] Refactorizar `core/orchestrator/handler/agent_job_worker.py`
- [ ] Eliminar imports de `core.context` desde `core/orchestrator`
- [ ] Definir puerto `ContextServicePort` en `core/orchestrator/domain/ports/`

### Fase 4: Implementar Adapter (TODO)
- [ ] Crear `services/orchestrator/infrastructure/adapters/context_grpc_adapter.py`
- [ ] Implementar puerto usando gRPC client
- [ ] Inyectar adapter en AgentJobWorker

### Fase 5: Actualizar Core/Context (TODO)
- [ ] Implementar `services/context/server.py` con métodos gRPC
- [ ] Registrar handlers en `ContextService`
- [ ] Probar flujo completo E2E

### Fase 6: Testing (TODO)
- [ ] Unit tests: Core aislado
- [ ] Integration tests: gRPC comunicación
- [ ] E2E tests: Flujo completo

---

## 📊 Verificación de Desacoplamiento

### Comando de Verificación
```bash
# Buscar imports cruzados en core/
grep -r "from core\.(context|orchestrator|agents_and_tools)\." core/
```

**Resultado esperado**: Solo matches en `core/X/X/` (imports internos)

### Criterios de Éxito
1. ✅ `core/orchestrator/` NO importa de `core/context/`
2. ✅ `core/context/` NO importa de `core/orchestrator/`
3. ✅ `core/agents_and_tools/` NO importa de otros bounded contexts
4. ✅ `services/orchestrator/` se comunica con `services/context/` vía gRPC

---

## 🔍 Impacto

### Riesgo Actual
- **Alto**: Cambios en `core/context/` afectan `core/orchestrator/`
- **Alto**: Imposible testear bounded contexts independientemente
- **Alto**: Difícil reutilizar `core/context/` en otros contextos

### Beneficios del Refactoring
- ✅ **Testeabilidad**: Bounded contexts testeados independientemente
- ✅ **Flexibilidad**: Cambiar implementación de Context sin afectar Orchestrator
- ✅ **Escalabilidad**: Microservicios escalan independientemente
- ✅ **Dependency Inversion**: Orchestrator depende de abstracciones, no concreciones

---

## 📝 Referencias

- [Hexagonal Architecture - Ports & Adapters](./HEXAGONAL_ARCHITECTURE_PRINCIPLES.md)
- [Microservices Architecture](./MICROSERVICES_ARCHITECTURE.md)
- [DDD - Bounded Contexts](https://www.domainlanguage.com/ddd/)

---

**Siguiente Acción**: Implementar gRPC contrato en `specs/context.proto` y refactorizar `agent_job_worker.py`

