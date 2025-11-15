# Auditoría: Cumplimiento de Planning Service con ARCHITECTURE.md

**Fecha:** 2025-11-14
**Auditor:** AI Assistant
**Documento de Referencia:** `ARCHITECTURE.md`
**Estado:** 🔴 CRÍTICO - Múltiples discrepancias encontradas

---

## 📋 Resumen Ejecutivo

Esta auditoría compara la implementación actual de Planning Service con la arquitectura documentada en `ARCHITECTURE.md`. Se han identificado **discrepancias críticas** especialmente en:

1. **Task Derivation** - Implementación no confiable según usuario
2. **Eventos NATS** - Eventos adicionales no documentados
3. **Responsabilidades** - Funcionalidades fuera del scope documentado
4. **Consumidores NATS** - Planning Service consume eventos (contradice documentación)

---

## ✅ Cumplimiento: Arquitectura Hexagonal

### Domain Layer

| Requisito ARCHITECTURE.md | Implementación Real | Estado |
|---------------------------|---------------------|--------|
| Entities: Story (Aggregate Root) | ✅ `planning/domain/entities/story.py` | ✅ CUMPLE |
| Value Objects: StoryId, StoryState, DORScore | ✅ Implementados | ✅ CUMPLE |
| Entities adicionales: Task, Plan, Epic, Project | ⚠️ Implementados pero NO documentados | ⚠️ DISCREPANCIA |

**Discrepancia:** ARCHITECTURE.md solo menciona `Story` como entidad, pero la implementación incluye:
- `Task` (`planning/domain/entities/task.py`)
- `Plan` (`planning/domain/entities/plan.py`)
- `Epic` (`planning/domain/entities/epic.py`)
- `Project` (`planning/domain/entities/project.py`)

**Impacto:** ARCHITECTURE.md está incompleto - no refleja la jerarquía completa Project → Epic → Story → Task.

---

### Application Layer

| Requisito ARCHITECTURE.md | Implementación Real | Estado |
|---------------------------|---------------------|--------|
| Ports: StoragePort, MessagingPort | ✅ Implementados | ✅ CUMPLE |
| Use Cases: CreateStory, TransitionStory, ListStories, ApproveDecision, RejectDecision | ✅ Implementados | ✅ CUMPLE |
| Use Cases adicionales: CreateTask, DeriveTasksFromPlan, etc. | ⚠️ Implementados pero NO documentados | ⚠️ DISCREPANCIA |

**Use Cases Implementados (no documentados en ARCHITECTURE.md):**
- `CreateTaskUseCase`
- `GetTaskUseCase`
- `ListTasksUseCase`
- `DeriveTasksFromPlanUseCase`
- `CreateEpicUseCase`
- `GetEpicUseCase`
- `ListEpicsUseCase`
- `CreateProjectUseCase`
- `GetProjectUseCase`
- `ListProjectsUseCase`

**Application Services (no documentados):**
- `TaskDerivationResultService` - ⚠️ CRÍTICO: Usuario dice que no es confiable

**Discrepancia:** ARCHITECTURE.md solo documenta 5 use cases, pero hay 15+ implementados.

---

### Infrastructure Layer

| Requisito ARCHITECTURE.md | Implementación Real | Estado |
|---------------------------|---------------------|--------|
| Neo4jAdapter - Graph structure | ✅ `neo4j_adapter.py` | ✅ CUMPLE |
| ValkeyAdapter - Permanent details | ✅ `valkey_adapter.py` | ✅ CUMPLE |
| StorageAdapter - Composite (Neo4j+Valkey) | ✅ `storage_adapter.py` (no `dual_storage_adapter.py`) | ✅ CUMPLE |
| NATSAdapter - Event publishing | ✅ `nats_messaging_adapter.py` | ✅ CUMPLE |
| gRPC Server - External API | ✅ `server.py` | ✅ CUMPLE |

**Adicionales (no documentados):**
- `RayExecutorAdapter` - ⚠️ Para task derivation
- `PlanApprovedConsumer` - ⚠️ Consume eventos (contradice documentación)
- `TaskDerivationResultConsumer` - ⚠️ Consume eventos (contradice documentación)

---

## ⚠️ DISCREPANCIA CRÍTICA: Consumidores NATS

### ARCHITECTURE.md dice:

```markdown
### Consumes (NATS Events)
**None** - Planning Service is a producer, not a consumer
```

### Implementación Real:

**Planning Service SÍ consume eventos:**

1. **`PlanApprovedConsumer`** (`planning/infrastructure/consumers/plan_approved_consumer.py`)
   - Consume: `planning.plan.approved`
   - Propósito: Trigger task derivation automática
   - Flujo: Evento → `DeriveTasksFromPlanUseCase`

2. **`TaskDerivationResultConsumer`** (`planning/infrastructure/consumers/task_derivation_result_consumer.py`)
   - Consume: `agent.response.completed`
   - Propósito: Procesar resultados de task derivation del LLM
   - Flujo: Evento → `TaskDerivationResultService`

**Impacto:** ARCHITECTURE.md está **INCORRECTO** - Planning Service SÍ es consumidor de eventos.

---

## ⚠️ DISCREPANCIA CRÍTICA: Eventos NATS Publicados

### ARCHITECTURE.md documenta:

| Event | Subject | Payload | Consumer |
|-------|---------|---------|----------|
| story.created | `planning.story.created` | {story_id, title, created_by} | Orchestrator, Context |
| story.transitioned | `planning.story.transitioned` | {story_id, from_state, to_state} | Orchestrator, Context |
| decision.approved | `planning.decision.approved` | {story_id, decision_id, approved_by} | Orchestrator |
| decision.rejected | `planning.decision.rejected` | {story_id, decision_id, reason} | Orchestrator |

### Eventos Adicionales Implementados (NO documentados):

1. **`planning.story.tasks_not_ready`**
   - Publicado por: `NatsMessagingAdapter.publish_story_tasks_not_ready()`
   - Propósito: Notificar PO cuando historias no tienen tareas con prioridades
   - Payload: `{story_id, reason, task_ids_without_priority, total_tasks, occurred_at}`

2. **`planning.task.created`**
   - Publicado por: `CreateTaskUseCase`
   - Propósito: Notificar creación de tarea
   - Payload: `{task_id, story_id, plan_id, ...}`

3. **`planning.tasks.derived`** (o similar)
   - Publicado por: `TaskDerivationResultService._publish_tasks_derived_event()`
   - Propósito: Notificar que tareas fueron derivadas exitosamente
   - Payload: `{plan_id, task_count, timestamp}`

4. **`planning.task.derivation.failed`**
   - Publicado por: `TaskDerivationResultService._notify_manual_review()`
   - Propósito: Notificar fallo en derivación (requiere revisión manual)
   - Payload: `{plan_id, reason, requires_manual_review, timestamp}`

**Impacto:** ARCHITECTURE.md está incompleto - faltan eventos críticos.

---

## 🔴 CRÍTICO: Task Derivation - No Confiable

### Usuario indica: "No me puedo fiar de la implementación de la task derivation"

### Componentes de Task Derivation:

1. **`DeriveTasksFromPlanUseCase`**
   - Ubicación: `planning/application/usecases/derive_tasks_from_plan_usecase.py`
   - Responsabilidad: Enviar prompt al LLM vía Ray Executor
   - Dependencias: `StoragePort`, `RayExecutorPort`, `TaskDerivationConfig`

2. **`TaskDerivationResultService`**
   - Ubicación: `planning/application/services/task_derivation_result_service.py`
   - Responsabilidad: Procesar resultados del LLM y crear tareas
   - Dependencias: `CreateTaskUseCase`, `StoragePort`, `MessagingPort`

3. **`LLMTaskDerivationMapper`**
   - Ubicación: `planning/infrastructure/mappers/llm_task_derivation_mapper.py`
   - Responsabilidad: Parsear output del LLM → `TaskNode` VOs
   - ⚠️ Problema conocido: LLM no es idempotente, parsing puede fallar

4. **`PlanApprovedConsumer`**
   - Ubicación: `planning/infrastructure/consumers/plan_approved_consumer.py`
   - Responsabilidad: Escuchar `planning.plan.approved` → trigger derivation

5. **`TaskDerivationResultConsumer`**
   - Ubicación: `planning/infrastructure/consumers/task_derivation_result_consumer.py`
   - Responsabilidad: Escuchar `agent.response.completed` → procesar resultados

### Problemas Identificados:

#### 1. ROLE viene del LLM (INCORRECTO según AUDIT_ROLE_RESPONSIBILITY.md)

**Problema:** `TaskDerivationResultService` usa `task_node.role` del LLM para assignment:
```python
assigned_role = task_node.role  # LLM role hint - Planning Service should validate with RBAC
```

**Correcto:** ROLE debe venir del evento `planning.plan.approved`, NO del LLM.

**Estado:** ⚠️ PENDIENTE según `AUDIT_ROLE_RESPONSIBILITY.md`

#### 2. Parsing del LLM no es confiable

**Problema:** `LLMTaskDerivationMapper` parsea output del LLM usando regex, pero el LLM no es idempotente.

**Evidencia:** Documentación en mapper dice:
```python
# CRITICAL: LLM output is NOT idempotent - regex must be robust
```

**Impacto:** Parsing puede fallar silenciosamente o capturar campos incorrectos.

#### 3. Task Derivation NO está documentada en ARCHITECTURE.md

**Problema:** ARCHITECTURE.md NO menciona task derivation en absoluto.

**Impacto:** Funcionalidad crítica no documentada.

#### 4. Dependencia de Ray Executor (no documentada)

**Problema:** Planning Service depende de Ray Executor para task derivation, pero esto NO está en ARCHITECTURE.md.

**Evidencia:**
- `RayExecutorPort` en application layer
- `RayExecutorAdapter` en infrastructure layer
- Configuración de vLLM en `server.py`

---

## ✅ Cumplimiento: Persistencia Dual (Neo4j + Valkey)

### ARCHITECTURE.md especifica:

**Neo4j:**
- Graph structure (nodes + relationships)
- Minimal properties (id, state)
- Relationships: CREATED_BY, HAS_TASK, etc.

**Valkey:**
- Full story details (Hash)
- Permanent storage (AOF + RDB)
- Indexing sets (by state, all stories)

### Implementación Real:

✅ **StorageAdapter** (`storage_adapter.py`) implementa patrón dual correctamente:
- `save_story()` → Guarda en Valkey primero, luego Neo4j
- `get_story()` → Lee de Valkey (tiene todos los detalles)
- Comentarios documentan el patrón correctamente

✅ **Neo4jAdapter** (`neo4j_adapter.py`):
- Solo guarda estructura (id, state, relationships)
- NO guarda detalles completos

✅ **ValkeyStorageAdapter** (`valkey_adapter.py`):
- Guarda Hash completo con todos los campos
- Sets para indexing
- Configuración de persistencia documentada

**Estado:** ✅ CUMPLE con ARCHITECTURE.md

---

## ✅ Cumplimiento: Modelo de Dominio (Story)

### ARCHITECTURE.md especifica:

```python
@dataclass(frozen=True)
class Story:
    story_id: StoryId
    title: str
    brief: str
    state: StoryState
    dor_score: DORScore
    created_by: str
    created_at: datetime
    updated_at: datetime
```

### Implementación Real:

✅ **Story** (`planning/domain/entities/story.py`):
- `@dataclass(frozen=True)` ✅
- Campos coinciden con documentación ✅
- Value Objects: `Title`, `Brief`, `StoryState`, `DORScore`, `UserName` ✅
- Métodos: `transition_to()`, `meets_dor_threshold()`, `can_be_planned()` ✅
- `__post_init__()` con validación fail-fast ✅

**Discrepancia Menor:** Implementación usa `Title`, `Brief`, `UserName` como VOs (mejor que primitivos), pero ARCHITECTURE.md muestra `str`.

**Estado:** ✅ CUMPLE (implementación es mejor que documentación)

---

## ✅ Cumplimiento: FSM (Finite State Machine)

### ARCHITECTURE.md especifica:

```
Normal Flow:
DRAFT → PO_REVIEW → READY_FOR_PLANNING → PLANNED → READY_FOR_EXECUTION →
IN_PROGRESS → CODE_REVIEW → TESTING → READY_TO_REVIEW → ACCEPTED → DONE → ARCHIVED
```

### Implementación Real:

✅ **StoryState** (`planning/domain/value_objects/statuses/story_state.py`):
- Enum con todos los estados documentados ✅
- Método `can_transition_to()` valida transiciones ✅
- `@dataclass(frozen=True)` ✅

**Estado:** ✅ CUMPLE con ARCHITECTURE.md

---

## ✅ Cumplimiento: DDD Compliance Checklist

| Requisito | Implementación | Estado |
|-----------|----------------|--------|
| No reflection (`setattr`, `object.__setattr__`, `__dict__`) | ✅ Verificado: No uso de reflection | ✅ CUMPLE |
| No dynamic mutation (all dataclasses frozen) | ✅ Verificado: Todos `frozen=True` | ✅ CUMPLE |
| Fail-fast validation (ValueError in `__post_init__`) | ✅ Verificado: Todos tienen `__post_init__` | ✅ CUMPLE |
| No to_dict/from_dict in domain | ✅ Verificado: Mappers en infrastructure | ✅ CUMPLE |
| Dependency injection (use cases receive ports) | ✅ Verificado: Constructors inyectan ports | ✅ CUMPLE |
| Immutability (builder methods return new instances) | ✅ Verificado: `transition_to()` retorna nuevo | ✅ CUMPLE |
| Type hints complete | ✅ Verificado: Todos tienen type hints | ✅ CUMPLE |
| Layer boundaries respected | ✅ Verificado: Domain no importa infra | ✅ CUMPLE |
| Bounded context isolation (no imports from core/*) | ⚠️ Verificar: Posibles imports de `core/shared` | ⚠️ REVISAR |

**Estado:** ✅ CUMPLE (mayormente)

---

## 🔴 CRÍTICO: Responsabilidades Fuera de Scope

### ARCHITECTURE.md especifica:

**Core Responsibilities:**
1. Create and manage user stories
2. FSM state transitions
3. Decision approval/rejection workflow (PO human-in-the-loop)
4. Publish domain events for orchestrator integration

### Implementación Real incluye ADICIONALMENTE:

1. **Task Management** ⚠️
   - `CreateTaskUseCase`, `GetTaskUseCase`, `ListTasksUseCase`
   - Task CRUD completo
   - Task derivation (LLM-based)

2. **Plan Management** ⚠️
   - `get_plan()`, `save_plan()` en StoragePort
   - Plan entities y VOs

3. **Epic Management** ⚠️
   - `CreateEpicUseCase`, `GetEpicUseCase`, `ListEpicsUseCase`
   - Epic CRUD completo

4. **Project Management** ⚠️
   - `CreateProjectUseCase`, `GetProjectUseCase`, `ListProjectsUseCase`
   - Project CRUD completo

5. **Task Derivation (LLM)** ⚠️ CRÍTICO
   - Integración con Ray Executor
   - Parsing de LLM output
   - Dependency graph calculation

**Pregunta Arquitectónica:** ¿Estas responsabilidades pertenecen a Planning Service o deberían estar en otros servicios?

**Según usuario:** "Planning service es para planificar, es crear historias de usuario. Planning service es la puerta de entrada a la visualizacion de las historias / epics/ tareas, planning service siver para realizar la planificacion con el humano."

**Interpretación:** Task/Epic/Project management SÍ pertenece a Planning Service (son parte de planificación), pero task derivation puede ser cuestionable.

---

## 📊 Resumen de Discrepancias

### 🔴 CRÍTICAS (Deben corregirse):

1. **ARCHITECTURE.md dice "Planning Service NO consume eventos"** → INCORRECTO
   - Consume: `planning.plan.approved`, `agent.response.completed`

2. **Task Derivation NO está documentada** → Funcionalidad crítica sin documentación

3. **Task Derivation no es confiable** → Usuario indica que no se puede fiar de ella

4. **Eventos NATS incompletos** → Faltan eventos críticos en documentación

5. **ROLE viene del LLM** → Debe venir del evento según auditoría previa

### ⚠️ IMPORTANTES (Deben documentarse):

1. **Jerarquía completa Project → Epic → Story → Task** → No documentada

2. **15+ use cases** → Solo 5 documentados

3. **Dependencia de Ray Executor** → No documentada

4. **Application Services** → `TaskDerivationResultService` no documentado

### ✅ CUMPLE:

1. Arquitectura Hexagonal ✅
2. Persistencia Dual (Neo4j + Valkey) ✅
3. Modelo de Dominio (Story) ✅
4. FSM ✅
5. DDD Compliance ✅

---

## 🎯 Recomendaciones

### 1. Actualizar ARCHITECTURE.md

**Secciones a agregar/actualizar:**

1. **Consumidores NATS:**
   ```markdown
   ### Consumes (NATS Events)

   | Event | Subject | Purpose | Handler |
   |-------|---------|---------|---------|
   | plan.approved | `planning.plan.approved` | Trigger task derivation | PlanApprovedConsumer |
   | agent.response.completed | `agent.response.completed` | Process derivation results | TaskDerivationResultConsumer |
   ```

2. **Eventos Publicados (completar):**
   ```markdown
   | story.tasks_not_ready | `planning.story.tasks_not_ready` | PO notification | PO-UI |
   | task.created | `planning.task.created` | Task created | Orchestrator, Context |
   | tasks.derived | `planning.tasks.derived` | Tasks derived successfully | Monitoring |
   | task.derivation.failed | `planning.task.derivation.failed` | Derivation failed | PO-UI |
   ```

3. **Jerarquía completa:**
   ```markdown
   ## Domain Model

   Hierarchy: Project → Epic → Story → Task

   ### Project (Root)
   ### Epic (Groups Stories)
   ### Story (Aggregate Root)
   ### Task (Belongs to Story)
   ```

4. **Task Derivation (nueva sección):**
   ```markdown
   ## Task Derivation

   Automatic task decomposition from approved plans using LLM.

   Flow:
   1. Plan approved → PlanApprovedConsumer
   2. DeriveTasksFromPlanUseCase → Ray Executor
   3. LLM generates tasks → TaskDerivationResultConsumer
   4. TaskDerivationResultService → Creates tasks

   ⚠️ WARNING: Current implementation has reliability issues.
   ```

### 2. Revisar Task Derivation

**Acciones requeridas:**

1. **Auditar `TaskDerivationResultService`** completamente
2. **Corregir ROLE** según `AUDIT_ROLE_RESPONSIBILITY.md`
3. **Mejorar parsing del LLM** (hacer más robusto)
4. **Agregar tests de integración** para task derivation
5. **Documentar fallos conocidos** y casos edge

### 3. Clarificar Responsabilidades

**Decisión requerida:**

- ¿Task derivation pertenece a Planning Service?
- ¿O debería estar en otro servicio (Orchestrator, Workflow)?

**Según usuario:** Planning Service es para planificación con humano. Task derivation puede ser parte de planificación, pero necesita ser confiable.

---

## ✅ Conclusión

**Planning Service cumple con ARCHITECTURE.md en:**
- Arquitectura Hexagonal ✅
- Persistencia Dual ✅
- Modelo de Dominio ✅
- FSM ✅
- DDD Compliance ✅

**Planning Service NO cumple con ARCHITECTURE.md en:**
- Consumidores NATS (documentación incorrecta) 🔴
- Eventos NATS (documentación incompleta) 🔴
- Task Derivation (no documentada, no confiable) 🔴
- Jerarquía completa (no documentada) ⚠️

**Prioridad:** Actualizar ARCHITECTURE.md para reflejar la implementación real, especialmente task derivation y consumidores NATS.

---

**Próximos Pasos:**
1. Actualizar ARCHITECTURE.md con todas las discrepancias
2. Auditar Task Derivation completamente
3. Corregir ROLE según auditoría previa
4. Agregar tests de integración para task derivation

