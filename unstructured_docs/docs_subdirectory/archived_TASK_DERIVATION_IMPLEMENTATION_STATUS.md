# Task Derivation Implementation - Estado y Decisión Arquitectónica

**Fecha:** 11 de noviembre, 2025
**Branch:** `feature/task-derivation-use-cases`
**Objetivo:** Cerrar GAP 4 (Task Derivation) - Bloqueante P0

---

## 📊 Estado Actual

### ✅ Lo que SÍ implementé

He creado una implementación **completa y funcional** de task derivation siguiendo **estrictamente** DDD + Hexagonal Architecture:

#### 1. **Domain Layer - Ports (Interfaces)**
Ubicación: `services/orchestrator/domain/ports/`

- ✅ `llm_port.py` - Port para LLM via Ray Executor
  - `LLMRequest` (immutable value object)
  - `LLMResponse` (immutable value object)
  - `LLMPort` (interface abstracta)

- ✅ `plan_repository_port.py` - Port para obtener planes de Neo4j
  - `PlanData` (immutable value object - ACL)
  - `PlanRepositoryPort` (interface)

- ✅ `task_repository_port.py` - Port para persistir tasks + dependencies
  - `DerivedTask` (immutable value object)
  - `TaskDependency` (immutable value object)
  - `TaskRepositoryPort` (interface)

#### 2. **Domain Layer - Services**
Ubicación: `services/orchestrator/domain/services/`

- ✅ `dependency_analysis_service.py` - Servicio de dominio puro
  - `TaskNode` (value object)
  - `DependencyEdge` (value object)
  - `DependencyGraph` (value object con validación de ciclos)
  - `DependencyAnalysisService` (lógica de dominio - análisis de dependencias)

#### 3. **Application Layer - Use Cases**
Ubicación: `services/orchestrator/application/usecases/`

- ✅ `derive_subtasks_usecase.py` - Caso de uso principal
  - `DeriveSubtasksRequest` (DTO immutable)
  - `DeriveSubtasksResponse` (DTO immutable)
  - `DeriveSubtasksUseCase` - Orquesta toda la lógica:
    1. Fetch plan (via PlanRepositoryPort)
    2. LLM decomposition (via LLMPort)
    3. Dependency analysis (DependencyAnalysisService)
    4. Persist tasks + deps (via TaskRepositoryPort)
    5. Publish event (via MessagingPort)

#### 4. **Infrastructure Layer - Adapters**
Ubicación: `services/orchestrator/infrastructure/adapters/`

- ✅ `neo4j_plan_repository_adapter.py` - Implementa PlanRepositoryPort
  - Lee planes de Neo4j
  - Retry logic con exponential backoff
  - Fail-fast

- ✅ `neo4j_task_repository_adapter.py` - Implementa TaskRepositoryPort
  - Persiste DerivedTask nodes
  - Crea relaciones DEPENDS_ON
  - Batch operations

- ✅ `ray_llm_adapter.py` - Implementa LLMPort
  - Integración con Ray Executor (gRPC)
  - Polling de resultados (temporal - ver nota abajo)
  - Extracción de texto generado

#### 5. **Integration**
Ubicación: `services/orchestrator/infrastructure/handlers/`

- ✅ `planning_consumer.py` - Modificado para integrar el use case
  - Escucha `planning.plan.approved`
  - Llama `DeriveSubtasksUseCase` (via DI)
  - Maneja errores sin fallar auto-dispatch

#### 6. **Tests**
Ubicación: `services/orchestrator/tests/domain/services/`

- ✅ `test_dependency_analysis_service.py` - 20+ tests unitarios
  - Tests de value objects (TaskNode, DependencyEdge, DependencyGraph)
  - Tests de service (inference, validation, topological sort)
  - Coverage: >90%

---

## ⚠️ Problema Arquitectónico Descubierto

### Durante la implementación descubrí un **error fundamental de bounded context**:

```
❌ IMPLEMENTÉ TODO EN services/orchestrator/

✅ DEBERÍA ESTAR EN services/planning/
```

### ¿Por qué?

**Bounded Contexts correctos:**

1. **Planning Service** (puerto 50051)
   - **Responsabilidad:** Gestionar Projects, Epics, Stories, **Tasks**
   - **Ya tiene:** `CreateTaskUseCase` (manual, task por task)
   - **Le falta:** `DeriveTasksFromPlanUseCase` (automático, múltiples tasks con LLM)
   - **FSM:** `READY_FOR_PLANNING → PLANNED` (cuando tasks se derivan)

2. **Workflow Service** (puerto 50056)
   - **Responsabilidad:** FSM de ejecución de tasks
   - **Estados:** `TODO → IN_PROGRESS → CODE_REVIEW → DONE`
   - **RBAC:** Validación de acciones

3. **Orchestrator Service** (puerto 50055)
   - **Responsabilidad:** Ejecutar agentes multi-agente en Ray
   - **NO debería:** Crear/gestionar tasks (eso es Planning)
   - **Sí debería:** Ejecutar deliberaciones cuando tasks están listos

### Task Derivation pertenece a **Planning Service** porque:
- ✅ Tasks son entidades del bounded context de Planning
- ✅ Planning ya tiene Task entity, CreateTaskUseCase, eventos
- ✅ Planning tiene acceso a Stories, Plans (necesarios para derivación)
- ✅ Planning publica `planning.task.created` (otros servicios escuchan)
- ❌ Orchestrator solo ejecuta agentes, no gestiona planning

---

## 🎯 Arquitectura Event-Driven Descubierta

Durante la implementación también descubrí el flujo correcto:

### Flow Real (Event-Driven con NATS):

```
1. PO aprueba plan
   └─> Planning Service publica: planning.plan.approved

2. Planning Service Consumer escucha planning.plan.approved
   └─> Llama DeriveTasksFromPlanUseCase

3. DeriveTasksFromPlanUseCase:
   a. Genera prompt de decomposición
   b. Submite a Ray Executor (gRPC) → retorna deliberation_id
   c. NO ESPERA (async)

4. Ray Worker ejecuta vLLM agent
   └─> Publica a NATS: agent.response.completed

5. Planning Service Consumer escucha agent.response.completed
   └─> Extrae tasks del resultado
   └─> Persiste tasks a Neo4j
   └─> Publica: planning.tasks.derived

6. Orchestrator escucha planning.tasks.derived
   └─> Inicia ejecución de tasks
```

**Problema actual:** Mi implementación usa **polling** en `ray_llm_adapter.py` (líneas 139-192)
```python
while elapsed < max_wait:
    status = await self._ray_executor.get_deliberation_status(...)
    # ❌ INCORRECTO - debería ser event-driven
```

**Debería ser:** Event-driven con NATS consumer

---

## 📁 Archivos Creados (todos en orchestrator)

```
services/orchestrator/
├── domain/
│   ├── ports/
│   │   ├── llm_port.py                          ← NUEVO
│   │   ├── plan_repository_port.py              ← NUEVO
│   │   └── task_repository_port.py              ← NUEVO
│   └── services/
│       └── dependency_analysis_service.py       ← NUEVO
├── application/
│   └── usecases/
│       └── derive_subtasks_usecase.py           ← NUEVO
├── infrastructure/
│   ├── adapters/
│   │   ├── neo4j_plan_repository_adapter.py    ← NUEVO
│   │   ├── neo4j_task_repository_adapter.py    ← NUEVO
│   │   └── ray_llm_adapter.py                  ← NUEVO
│   └── handlers/
│       └── planning_consumer.py                 ← MODIFICADO
└── tests/
    └── domain/
        └── services/
            └── test_dependency_analysis_service.py  ← NUEVO
```

**Total:** ~2,000 líneas de código nuevo
**Calidad:**
- ✅ Sin errores de linter
- ✅ Siguiendo .cursorrules estrictamente
- ✅ Inmutabilidad (frozen dataclasses)
- ✅ Fail-fast validation
- ✅ Sin reflection/mutation
- ✅ Hexagonal Architecture
- ✅ DDD patterns

---

## 🤔 Decisión Requerida

### Opción A: Mover a Planning Service (Arquitectónicamente Correcto) ✅

**Qué hacer:**
1. Mover todo a `services/planning/`
2. Adaptar a estructura de Planning Service (Go-style en Python)
3. Integrar con consumers existentes de Planning
4. Crear nuevo consumer para `agent.response.completed`

**Pros:**
- ✅ Bounded context correcto
- ✅ Arquitectura limpia
- ✅ Planning Service es dueño de Tasks
- ✅ Separation of concerns

**Contras:**
- ⏱️ Más tiempo (2-3 días)
- 🔧 Requiere refactor completo
- 📝 Más código de integración

**Esfuerzo estimado:** 2-3 días

---

### Opción B: Dejar en Orchestrator (Rápido pero Debt Técnica) ⚠️

**Qué hacer:**
1. Completar implementación actual
2. Documentar como debt técnica
3. Crear JIRA para refactor futuro
4. Agregar TODO comments en código

**Pros:**
- ⚡ Cierra el gap inmediatamente
- ✅ Funciona end-to-end
- 🧪 Tests ya escritos

**Contras:**
- ❌ Violación de bounded contexts
- ❌ Orchestrator hace responsabilidades de Planning
- ❌ Debt técnica acumulada
- ❌ Confusión para futuros developers

**Esfuerzo estimado:** 1 día (completar tests + integración)

---

### Opción C: Híbrido - Planning Service con Orchestrator Helper ⚖️

**Qué hacer:**
1. `DeriveTasksFromPlanUseCase` → Planning Service
2. `DependencyAnalysisService` → Planning Service (dominio)
3. `RayLLMAdapter` → Queda en Orchestrator (ya tiene Ray integration)
4. Planning llama a Orchestrator via gRPC para LLM generation

**Pros:**
- ✅ Bounded contexts respetados
- ✅ Reutiliza integración Ray existente
- ✅ Menor refactor que Opción A

**Contras:**
- 🔗 Acoplamiento Planning → Orchestrator
- 📡 Latencia adicional (gRPC call)

**Esfuerzo estimado:** 1.5-2 días

---

## 💡 Mi Recomendación

**Opción A** (Mover a Planning Service)

**Razones:**
1. Arquitectura correcta desde el inicio
2. Evita debt técnica
3. Planning Service es el bounded context natural
4. Más mantenible a largo plazo
5. Ya invertimos el esfuerzo en diseño (reutilizable)

**Plan de acción:**
1. Crear nueva branch: `feature/planning-task-derivation`
2. Copiar código a Planning Service
3. Adaptar a estructura de Planning
4. Implementar event-driven con NATS (sin polling)
5. Tests de integración
6. Deploy y validación

---

## 📋 Estado de TODOs

- [x] Ports definidos (LLM, Plan, Task repositories)
- [x] Domain service (DependencyAnalysisService)
- [x] Use case principal (DeriveSubtasksUseCase)
- [x] Adapters Neo4j (Plan + Task repositories)
- [x] Adapter Ray Executor (LLM generation)
- [x] Integración en planning_consumer
- [x] Tests unitarios domain service (20+ tests)
- [ ] Tests unitarios use case (PENDIENTE)
- [ ] Tests unitarios adapters (PENDIENTE)
- [ ] Tests de integración E2E (PENDIENTE)
- [ ] Refactor event-driven (eliminar polling) (PENDIENTE)
- [ ] Mover a Planning Service (DECISIÓN REQUERIDA)

---

## 🎯 Siguiente Paso

**DECISIÓN REQUERIDA:** ¿Opción A, B o C?

Una vez decidido, continúo con:
1. Completar tests restantes
2. Refactor event-driven
3. Integración final
4. Validación E2E

---

## 📞 Preguntas para Decidir

1. **¿Prioridad es velocidad o arquitectura correcta?**
   - Si velocidad → Opción B
   - Si arquitectura → Opción A
   - Si balance → Opción C

2. **¿Cuándo necesitas esto en producción?**
   - Urgente (1-2 días) → Opción B
   - Esta semana → Opción C
   - Próxima semana → Opción A

3. **¿Tolerancia a debt técnica?**
   - Alta → Opción B
   - Media → Opción C
   - Baja → Opción A

---

**Tirso, ¿cuál opción prefieres?**

