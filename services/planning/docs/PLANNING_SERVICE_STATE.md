# Planning Service - Estado Actual e Implementación Detallada

**Fecha:** 2025-11-14
**Versión:** v0.1.0
**Estado:** 🟡 Funcional pero con gaps críticos en Task Derivation
**Autor:** AI Assistant (Documentación Técnica)

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura Actual](#arquitectura-actual)
3. [Implementación Detallada](#implementación-detallada)
4. [Task Derivation: Flujo Completo](#task-derivation-flujo-completo)
5. [Integración con Context Service](#integración-con-context-service)
6. [Gaps Críticos Identificados](#gaps-críticos-identificados)
7. [Relación con Contexto](#relación-con-contexto)
8. [Roadmap de Correcciones](#roadmap-de-correcciones)

---

## 🎯 Resumen Ejecutivo

### Estado General

**Planning Service** es un microservicio Python que gestiona el ciclo de vida de historias de usuario siguiendo principios de **Domain-Driven Design (DDD)** y **Arquitectura Hexagonal**.

**Estado Funcional:**
- ✅ **Arquitectura completa**: DDD + Hexagonal implementada correctamente
- ✅ **Domain Layer**: Entidades inmutables, Value Objects, invariantes de dominio
- ✅ **Application Layer**: 15+ use cases, ports/interfaces, dependency injection
- ✅ **Infrastructure Layer**: Adapters, consumers, mappers, dual persistence (Neo4j + Valkey)
- ✅ **Tests**: >90% cobertura, tests unitarios completos
- ✅ **Event-Driven**: NATS JetStream para eventos de dominio

**Estado de Task Derivation:**
- 🟡 **Implementado pero no confiable**: Usuario indica que no se puede confiar en la implementación
- 🟡 **Gaps críticos identificados**: ROLE, parsing LLM, dependencias
- 🟡 **Integración Context Service**: Estructura creada pero protobuf pendiente

### Métricas Clave

| Métrica | Valor | Estado |
|---------|-------|--------|
| **Cobertura de Tests** | >90% | ✅ |
| **Use Cases Implementados** | 15+ | ✅ |
| **Entidades de Dominio** | 4 (Project, Epic, Story, Task) | ✅ |
| **Consumidores NATS** | 2 | ✅ |
| **Eventos Publicados** | 8 | ✅ |
| **Task Derivation** | Implementado | 🟡 No confiable |
| **Context Service Integration** | Estructura lista | 🟡 Protobuf pendiente |

---

## 🏗 Arquitectura Actual

### Diagrama de Capas (Hexagonal Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Entities (frozen=True)                              │   │
│  │    • Project (root)                                  │   │
│  │    • Epic (groups Stories)                          │   │
│  │    • Story (aggregate root)                          │   │
│  │    • Task (atomic work unit)                         │   │
│  │                                                       │   │
│  │  Value Objects                                       │   │
│  │    • Identifiers: ProjectId, EpicId, StoryId, TaskId │   │
│  │    • Content: Title, Brief, TaskDescription         │   │
│  │    • Status: StoryState, TaskStatus, TaskType       │   │
│  │    • Task Derivation: TaskNode, DependencyGraph     │   │
│  │    • Actors: Role, RoleMapper                        │   │
│  │                                                       │   │
│  │  Domain Events                                       │   │
│  │    • StoryTasksNotReadyEvent                        │   │
│  │    • TaskCreatedEvent                                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         ↓                       ↑
┌─────────────────────────────────────────────────────────────┐
│              Application Layer                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Ports (Interfaces)                                  │   │
│  │    • StoragePort (Neo4j + Valkey)                   │   │
│  │    • MessagingPort (NATS)                            │   │
│  │    • RayExecutorPort (vLLM)                         │   │
│  │    • ContextPort (Context Service)                   │   │
│  │    • ConfigurationPort                               │   │
│  │                                                       │   │
│  │  Use Cases                                           │   │
│  │    • Project: CreateProject, GetProject, ListProjects│   │
│  │    • Epic: CreateEpic, GetEpic, ListEpics            │   │
│  │    • Story: CreateStory, GetStory, ListStories,      │   │
│  │            TransitionStory                           │   │
│  │    • Task: CreateTask, GetTask, ListTasks           │   │
│  │    • Task Derivation: DeriveTasksFromPlan           │   │
│  │    • Decision: ApproveDecision, RejectDecision      │   │
│  │                                                       │   │
│  │  Application Services                                │   │
│  │    • TaskDerivationResultService                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         ↓                       ↑
┌─────────────────────────────────────────────────────────────┐
│           Infrastructure Layer                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Adapters (Outbound)                                 │   │
│  │    • Neo4jAdapter (graph structure)                  │   │
│  │    • ValkeyAdapter (permanent details)               │   │
│  │    • StorageAdapter (composite)                      │   │
│  │    • NATSMessagingAdapter (events)                   │   │
│  │    • RayExecutorAdapter (vLLM)                       │   │
│  │    • ContextServiceAdapter (gRPC)                    │   │
│  │    • EnvironmentConfigurationAdapter                 │   │
│  │                                                       │   │
│  │  Consumers (Inbound)                                 │   │
│  │    • PlanApprovedConsumer                            │   │
│  │    • TaskDerivationResultConsumer                    │   │
│  │                                                       │   │
│  │  Mappers                                             │   │
│  │    • StoryValkeyMapper                               │   │
│  │    • TaskEventMapper                                 │   │
│  │    • LLMTaskDerivationMapper                         │   │
│  │    • StoryEventMapper                                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Dual Persistence Pattern

**Neo4j (Graph Database):**
- **Propósito**: Estructura de grafo para relaciones y navegación
- **Almacena**: Nodes (id, state) + Relationships (HAS_TASK, CREATED_BY, etc.)
- **Uso**: Rehydratación de contexto, navegación de alternativas, observabilidad

**Valkey (In-Memory Database):**
- **Propósito**: Almacenamiento permanente de detalles completos
- **Almacena**: Hash completo con todos los campos de entidades
- **Uso**: CRUD operations, FSM state lookups, fast key-value access

**Ventajas del Patrón Dual:**
- ✅ Neo4j: Navegación eficiente de relaciones complejas
- ✅ Valkey: Acceso rápido a detalles completos
- ✅ Separación de concerns: Estructura vs. Contenido
- ✅ Escalabilidad: Cada base de datos optimizada para su propósito

---

## 🔧 Implementación Detallada

### Domain Layer

#### Entidades Principales

**1. Project (Root Entity)**
```python
@dataclass(frozen=True)
class Project:
    project_id: ProjectId
    name: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    owner: str = ""
    created_at: datetime  # REQUIRED
    updated_at: datetime  # REQUIRED
```

**Invariantes de Dominio:**
- ✅ Name no puede estar vacío
- ✅ Project es root (no tiene parent)
- ✅ Immutable (frozen=True)

**2. Epic (Groups Stories)**
```python
@dataclass(frozen=True)
class Epic:
    epic_id: EpicId
    project_id: ProjectId  # REQUIRED - domain invariant
    title: str
    description: str = ""
    status: EpicStatus = EpicStatus.ACTIVE
    created_at: datetime  # REQUIRED
    updated_at: datetime  # REQUIRED
```

**Invariantes de Dominio:**
- ✅ Title no puede estar vacío
- ✅ **MUST belong to a Project** (`project_id` is REQUIRED)
- ✅ Immutable (frozen=True)

**3. Story (Aggregate Root)**
```python
@dataclass(frozen=True)
class Story:
    story_id: StoryId
    epic_id: EpicId  # REQUIRED - domain invariant
    title: Title
    brief: Brief
    state: StoryState  # FSM state
    dor_score: DORScore  # Definition of Ready (0-100)
    created_by: UserName
    created_at: datetime
    updated_at: datetime
```

**Invariantes de Dominio:**
- ✅ Title y brief no pueden estar vacíos
- ✅ **MUST belong to an Epic** (`epic_id` is REQUIRED)
- ✅ State transitions deben seguir FSM rules
- ✅ DoR score debe ser 0-100
- ✅ Immutable (frozen=True)

**4. Task (Atomic Work Unit)**
```python
@dataclass(frozen=True)
class Task:
    # REQUIRED fields FIRST
    task_id: TaskId  # Planning Service generates
    story_id: StoryId  # REQUIRED - domain invariant
    plan_id: PlanId  # Optional - reference to Plan (Sprint/Iteration)
    title: str  # From vLLM
    created_at: datetime  # REQUIRED
    updated_at: datetime  # REQUIRED

    # Optional fields LAST
    description: str = ""  # From vLLM
    estimated_hours: int = 0  # From vLLM
    assigned_to: str = ""  # Planning Service assigns (RBAC)
    type: TaskType = TaskType.DEVELOPMENT
    status: TaskStatus = TaskStatus.TODO
    priority: int = 1  # From vLLM
```

**Invariantes de Dominio:**
- ✅ Title no puede estar vacío
- ✅ **MUST belong to a Story** (`story_id` is REQUIRED)
- ✅ `plan_id` es referencia opcional a Plan (Sprint/Iteration) - Plan NO es persistido
- ✅ estimated_hours no puede ser negativo
- ✅ priority debe ser >= 1
- ✅ Immutable (frozen=True)

**Jerarquía de Dominio:**
```
Project (root)
  └── Epic (belongs to Project)
      └── Story (belongs to Epic)
          └── Task (belongs to Story)
```

**Nota sobre Plan:**
- ⚠️ **Plan NO es una entidad persistida** en Planning Service
- **Plan = Decisión del PO** sobre qué Stories trabajar en la siguiente iteración
- **Plan = Sprint/Iteration** seleccionado por PO
- Plan viene del evento `planning.plan.approved` (de otro servicio)
- Planning Service solo referencia Plan via `plan_id` desde eventos

### Application Layer

#### Use Cases Implementados

**Project Use Cases:**
- ✅ `CreateProjectUseCase` - Crear nuevo proyecto
- ✅ `GetProjectUseCase` - Obtener proyecto por ID
- ✅ `ListProjectsUseCase` - Listar todos los proyectos

**Epic Use Cases:**
- ✅ `CreateEpicUseCase` - Crear nueva épica
- ✅ `GetEpicUseCase` - Obtener épica por ID
- ✅ `ListEpicsUseCase` - Listar épicas (por proyecto)

**Story Use Cases:**
- ✅ `CreateStoryUseCase` - Crear nueva historia de usuario
- ✅ `GetStoryUseCase` - Obtener historia por ID
- ✅ `ListStoriesUseCase` - Listar historias (por épica)
- ✅ `TransitionStoryUseCase` - Transición de estado FSM (con validación de tasks)

**Task Use Cases:**
- ✅ `CreateTaskUseCase` - Crear nueva tarea
- ✅ `GetTaskUseCase` - Obtener tarea por ID
- ✅ `ListTasksUseCase` - Listar tareas (por historia)

**Task Derivation Use Cases:**
- ✅ `DeriveTasksFromPlanUseCase` - Derivar tareas automáticamente usando LLM

**Decision Use Cases:**
- ✅ `ApproveDecisionUseCase` - Aprobar decisión (publica evento)
- ✅ `RejectDecisionUseCase` - Rechazar decisión (publica evento)

#### Application Services

**TaskDerivationResultService:**
- **Responsabilidad**: Procesar resultados de vLLM y crear tareas
- **Dependencias**: `CreateTaskUseCase`, `StoragePort`, `MessagingPort`
- **Flujo**:
  1. Recibe `TaskNode` VOs parseados del LLM
  2. Construye grafo de dependencias (desde keywords)
  3. Valida dependencias circulares
  4. Genera TaskIds reales (Planning Service, NO del LLM)
  5. Crea tareas en orden de dependencias
  6. Persiste relaciones de dependencias en Neo4j
  7. Publica eventos (success/failure)

### Infrastructure Layer

#### Adapters

**StorageAdapter (Composite):**
- Combina `Neo4jAdapter` + `ValkeyAdapter`
- **Neo4j**: Graph structure (nodes + relationships)
- **Valkey**: Permanent details (Hash completo)

**NATSMessagingAdapter:**
- Implementa `MessagingPort`
- Publica eventos de dominio a NATS JetStream
- Eventos: `story.created`, `story.transitioned`, `task.created`, `tasks.derived`, etc.

**RayExecutorAdapter:**
- Implementa `RayExecutorPort`
- Llama a Ray Executor Service vía gRPC
- Envía prompts a vLLM para task derivation
- Fire-and-forget (async)

**ContextServiceAdapter:**
- Implementa `ContextPort`
- Llama a Context Service vía gRPC
- Obtiene contexto rehidratado por rol
- ⚠️ **Estado**: Estructura creada, protobuf pendiente (raise NotImplementedError)

#### Consumers

**PlanApprovedConsumer:**
- **Evento**: `planning.plan.approved`
- **Responsabilidad**: Trigger task derivation cuando Plan es aprobado
- **Flujo**:
  1. Escucha evento `planning.plan.approved`
  2. Extrae `plan_id` del payload
  3. Llama a `DeriveTasksFromPlanUseCase.execute(plan_id)`
  4. ACK/NAK según resultado

**TaskDerivationResultConsumer:**
- **Evento**: `agent.response.completed`
- **Responsabilidad**: Procesar resultados de task derivation del vLLM
- **Flujo**:
  1. Escucha evento `agent.response.completed`
  2. Filtra tasks con `task_id.startswith("derive-")`
  3. Extrae `plan_id`, `story_id`, `role` del payload
  4. Parsea LLM output → `TaskNode` VOs
  5. Delega a `TaskDerivationResultService.process()`
  6. ACK/NAK según resultado

#### Mappers

**LLMTaskDerivationMapper:**
- **Responsabilidad**: Parsear output del LLM → `TaskNode` VOs
- **Formato esperado**:
  ```
  TITLE: Setup project structure
  DESCRIPTION: Create initial project folders
  ESTIMATED_HOURS: 8
  PRIORITY: 1
  KEYWORDS: setup, project
  ---
  ```
- ⚠️ **Problema conocido**: LLM no es idempotente, parsing puede fallar

**StoryValkeyMapper:**
- Convierte `Story` entity ↔ Valkey Hash
- Domain → Infrastructure (serialization)

**TaskEventMapper:**
- Convierte `TaskCreatedEvent` → NATS payload
- Domain → Infrastructure (event serialization)

---

## 🔄 Task Derivation: Flujo Completo

### Overview

**Task Derivation** es el proceso donde:
1. **vLLM crea tareas** desde un Plan aprobado
2. **Planning Service almacena tareas** generadas por vLLM
3. **Planning Service valida tareas** (prioridades, completitud)
4. **PO decide si tareas son correctas** (human-in-the-loop)
5. **Story solo puede avanzar** a READY_FOR_EXECUTION si todas las tareas son válidas

### Flujo Detallado (Paso a Paso)

```
┌─────────────────────────────────────────────────────────────┐
│              TASK DERIVATION FLOW (DETALLADO)               │
└─────────────────────────────────────────────────────────────┘

1. PO (Product Owner) decide qué Stories trabajar en siguiente iteración
   ↓
2. Plan Approved (Decisión del PO para Sprint)
   ↓
3. Event: planning.plan.approved
   Payload: {
     plan_id: "plan-001",
     story_id: "story-001",  // Plan puede tener múltiples Stories
     roles: ["DEVELOPER", "QA"],  // Roles del evento
     approved_by: "po-001",
     timestamp: "2025-11-14T10:00:00Z"
   }
   ↓
4. PlanApprovedConsumer._handle_message()
   - Parsea payload JSON
   - Extrae plan_id → PlanId VO
   - Llama a DeriveTasksFromPlanUseCase.execute(plan_id)
   ↓
5. DeriveTasksFromPlanUseCase.execute(plan_id)
   a) Fetch Plan from storage (via StoragePort)
      - Plan contiene: plan_id, story_id, title, description,
        acceptance_criteria, technical_notes, roles

   b) Get rehydrated context by role from Context Service
      - Llama a ContextServiceAdapter.get_context(
          story_id=plan.story_id,
          role=plan.roles[0],  // Primer rol del Plan
          phase="plan"
        )
      - Context Service retorna contexto rehidratado:
        * Story header (qué estamos construyendo)
        * Plan header (cómo lo estamos construyendo)
        * Role tasks (tareas existentes para el rol)
        * Relevant decisions (decisiones relevantes)
        * Decision dependencies (dependencias entre decisiones)
        * Impacted tasks (tareas impactadas)
        * Recent milestones (hitos recientes)
        * Last summary (último resumen)
      - ⚠️ Si Context Service falla → fallback a Plan-only prompt

   c) Build LLM prompt
      - Usa TaskDerivationConfig.build_prompt()
      - Template: config/task_derivation.yaml
      - Incluye:
        * Rehydrated context (si disponible)
        * Plan description
        * Acceptance criteria
        * Technical notes

   d) Submit to Ray Executor (async, fire-and-forget)
      - Llama a RayExecutorAdapter.submit_task_derivation()
      - Retorna DeliberationId para tracking
   ↓
6. Ray Executor → vLLM (GPU worker)
   - Ejecuta prompt en GPU worker
   - Genera tasks en formato estructurado
   ↓
7. vLLM generates tasks (structured output):
   TITLE: Setup project structure
   DESCRIPTION: Create initial project folders and files
   ESTIMATED_HOURS: 8
   PRIORITY: 1
   KEYWORDS: setup, project, structure
   ---
   TITLE: Create database schema
   DESCRIPTION: Design and implement database tables
   ESTIMATED_HOURS: 16
   PRIORITY: 2
   KEYWORDS: database, schema, tables
   ---
   (más tasks...)
   ↓
8. Event: agent.response.completed
   Payload: {
     task_id: "derive-plan-001",
     story_id: "story-001",  // Context from event
     role: "DEVELOPER",  // Context from event
     result: {
       proposal: "TITLE: Setup project structure\n..."
     }
   }
   ↓
9. TaskDerivationResultConsumer._handle_message()
   - Filtra: solo tasks con task_id.startswith("derive-")
   - Extrae plan_id, story_id, role del payload
   - Parsea LLM output → TaskNode VOs (via LLMTaskDerivationMapper)
   - Delega a TaskDerivationResultService.process()
   ↓
10. TaskDerivationResultService.process()
    a) Validación de input
       - Verifica que task_nodes no esté vacío
       - Verifica que role no esté vacío

    b) Build dependency graph
       - DependencyGraph.from_tasks(task_nodes)
       - Calcula dependencias desde keywords matching
       - Ejemplo: Si Task B menciona keywords de Task A → B depende de A

    c) Validar dependencias circulares
       - Si hay dependencias circulares:
         * Publica evento task.derivation.failed
         * Raise ValueError (fail-fast)

    d) Map role from context
       - RoleMapper.from_string(role)  // role viene del evento
       - Convierte string → Role VO

    e) Persist tasks in dependency order
       - graph.get_ordered_tasks()  // Ordena por dependencias
       - Para cada TaskNode:
         * Genera TaskId real: TaskId(f"T-{uuid4()}")
         * Crea CreateTaskRequest VO:
           - plan_id: del contexto (Plan/Sprint)
           - story_id: del contexto (Story)
           - task_id: generado por Planning Service
           - title, description: del LLM
           - assigned_to: RoleMapper.from_string(role)
           - estimated_hours: del LLM
           - priority: del LLM
         * Llama a CreateTaskUseCase.execute(request)

    f) Persist dependency relationships
       - storage.save_task_dependencies(graph.dependencies)
       - Guarda relaciones en Neo4j para navegación

    g) Publish success event
       - messaging.publish_event("planning.tasks.derived", payload)
   ↓
11. Tasks almacenadas en Planning Service
    - Neo4j: Nodes + Relationships (dependencias)
    - Valkey: Hash completo con detalles
   ↓
12. PO valida tasks (via UI):
    - Revisa si tasks son correctas
    - Puede reformular story si es necesario
    - Puede solicitar re-derivación
   ↓
13. Story transition to READY_FOR_EXECUTION:
    - TransitionStoryUseCase valida:
      * Story debe tener al menos una task
      * Todas las tasks deben tener priority >= 1
    - Si inválido:
      * Publica StoryTasksNotReadyEvent
      * PO recibe notificación en UI
      * Story NO puede transicionar
    - Si válido:
      * Story transiciona → READY_FOR_EXECUTION
```

### Componentes Clave

**DeriveTasksFromPlanUseCase:**
- **Responsabilidad**: Enviar Plan a Ray Executor para task generation
- **Dependencias**: `StoragePort`, `RayExecutorPort`, `ContextPort`, `TaskDerivationConfig`
- **Flujo**: Fetch Plan → Get Context → Build Prompt → Submit to Ray

**TaskDerivationResultService:**
- **Responsabilidad**: Procesar resultados de vLLM y crear tareas
- **Dependencias**: `CreateTaskUseCase`, `StoragePort`, `MessagingPort`
- **Flujo**: Parse → Build Graph → Validate → Create Tasks → Persist Dependencies

**LLMTaskDerivationMapper:**
- **Responsabilidad**: Parsear output del LLM → `TaskNode` VOs
- **Problema**: LLM no es idempotente, parsing puede fallar

**DependencyGraph:**
- **Responsabilidad**: Calcular dependencias desde keywords
- **Algoritmo**: Keyword matching (si Task B menciona keywords de Task A → B depende de A)

---

## 🔗 Integración con Context Service

### Propósito

**Context Service** proporciona contexto rehidratado por rol para enriquecer el prompt del LLM durante task derivation.

### Arquitectura de Integración

**ContextPort (Application Layer):**
```python
class ContextPort(Protocol):
    async def get_context(
        self,
        story_id: StoryId,
        role: str,
        phase: str = "plan",
    ) -> str:
        """Get rehydrated context for a Story and role."""
        ...
```

**ContextServiceAdapter (Infrastructure Layer):**
```python
class ContextServiceAdapter(ContextPort):
    def __init__(self, grpc_address: str):
        self.grpc_address = grpc_address
        self._stub = None  # TODO: Initialize when protobuf available

    async def get_context(...) -> str:
        # TODO: Implement gRPC call when protobuf files are available
        raise NotImplementedError("Protobuf generation pending")
```

### Flujo de Integración

```
DeriveTasksFromPlanUseCase.execute(plan_id)
  ↓
1. Fetch Plan from storage
   plan = await storage.get_plan(plan_id)
   ↓
2. Get rehydrated context by role
   role_for_context = plan.roles[0]  // Primer rol del Plan
   rehydrated_context = await context_service.get_context(
       story_id=plan.story_id,
       role=role_for_context,
       phase="plan"
   )
   ↓
3. Build LLM prompt with context
   prompt = config.build_prompt(
       description=plan.description,
       acceptance_criteria=plan.acceptance_criteria,
       technical_notes=plan.technical_notes,
       rehydrated_context=rehydrated_context  // Contexto enriquecido
   )
   ↓
4. Submit to Ray Executor
   deliberation_id = await ray_executor.submit_task_derivation(...)
```

### Contexto Rehidratado (Qué Proporciona Context Service)

**Context Service** retorna contexto estructurado que incluye:

1. **Story Header**:
   - Título de la historia
   - Descripción breve
   - Estado actual
   - DoR score

2. **Plan Header**:
   - Título del plan
   - Descripción del plan
   - Acceptance criteria
   - Technical notes

3. **Role Tasks**:
   - Tareas existentes para el rol específico
   - Estado de cada tarea
   - Prioridades y estimaciones

4. **Relevant Decisions**:
   - Decisiones relevantes para el rol
   - Decisiones que afectan las tareas del rol
   - Alternativas consideradas

5. **Decision Dependencies**:
   - Relaciones entre decisiones
   - Dependencias entre decisiones y tareas

6. **Impacted Tasks**:
   - Tareas impactadas por decisiones
   - Tareas que dependen de otras tareas

7. **Recent Milestones**:
   - Hitos recientes del proyecto
   - Eventos importantes

8. **Last Summary**:
   - Último resumen del contexto
   - Estado general del proyecto

### Estado Actual de la Integración

**✅ Completado:**
- ✅ `ContextPort` creado (interface)
- ✅ `ContextServiceAdapter` creado (estructura)
- ✅ `DeriveTasksFromPlanUseCase` integrado con Context Service
- ✅ `TaskDerivationConfig` actualizado para aceptar `rehydrated_context`
- ✅ Template YAML actualizado con placeholder `{rehydrated_context}`
- ✅ Fallback implementado (si Context Service falla → Plan-only prompt)

**🟡 Pendiente:**
- 🟡 Generar protobuf files (`context_pb2`, `context_pb2_grpc`)
- 🟡 Implementar llamada gRPC real en `ContextServiceAdapter.get_context()`
- 🟡 Configurar gRPC client stub
- 🟡 Manejar errores gRPC (timeouts, retries)

**⚠️ Problema Actual:**
- `ContextServiceAdapter.get_context()` actualmente raise `NotImplementedError`
- El use case captura la excepción y hace fallback a Plan-only prompt
- Funcional pero sin contexto enriquecido hasta que protobuf esté disponible

---

## 🚨 Gaps Críticos Identificados

### Gap 1: ROLE debe venir del evento, NO del LLM

**Problema:**
- Actualmente `TaskDerivationResultService` recibe `role` del evento `agent.response.completed`
- Pero el flujo completo requiere que `role` venga del evento `planning.plan.approved`
- **Estado**: Parcialmente corregido (role viene del evento, pero falta validación RBAC)

**Impacto:**
- ⚠️ Sin validación RBAC antes de asignar tasks
- ⚠️ Role puede no ser el correcto para la Story

**Tareas Pendientes:**
- [ ] Extraer `roles` del evento `planning.plan.approved` en `PlanApprovedConsumer`
- [ ] Pasar `roles` a `DeriveTasksFromPlanUseCase` (para Context Service)
- [ ] Validar `roles` con RBAC antes de asignar tasks
- [ ] Asegurar que `role` en `agent.response.completed` coincida con `roles` del Plan

**Archivos Afectados:**
- `planning/infrastructure/consumers/plan_approved_consumer.py`
- `planning/application/usecases/derive_tasks_from_plan_usecase.py`
- `planning/application/services/task_derivation_result_service.py`

### Gap 2: Parsing del LLM no es confiable

**Problema:**
- `LLMTaskDerivationMapper` parsea output del LLM usando regex
- LLM no es idempotente → parsing puede fallar silenciosamente
- No hay validación exhaustiva de campos parseados

**Impacto:**
- 🔴 Tasks pueden crearse con datos inválidos
- 🔴 Parsing puede fallar sin notificar al PO
- 🔴 Campos faltantes pueden causar errores downstream

**Tareas Pendientes:**
- [ ] Mejorar robustez del parsing (regex más flexible)
- [ ] Agregar validación exhaustiva de campos parseados
- [ ] Validar rangos (priority 1-10, estimated_hours 1-40)
- [ ] Agregar logging detallado cuando parsing falla
- [ ] Publicar evento `task.derivation.failed` con detalles del error
- [ ] Notificar al PO cuando parsing falla

**Archivos Afectados:**
- `planning/infrastructure/mappers/llm_task_derivation_mapper.py`
- `planning/application/services/task_derivation_result_service.py`

### Gap 3: Dependencias basadas en keywords pueden ser incorrectas

**Problema:**
- `DependencyGraph` calcula dependencias desde keyword matching
- Algoritmo: Si Task B menciona keywords de Task A → B depende de A
- Puede generar dependencias incorrectas o falsas positivas

**Impacto:**
- ⚠️ Tasks pueden tener dependencias incorrectas
- ⚠️ Orden de ejecución puede ser incorrecto
- ⚠️ Dependencias circulares pueden no detectarse correctamente

**Tareas Pendientes:**
- [ ] Revisar algoritmo de keyword matching
- [ ] Agregar tests para casos edge
- [ ] Mejorar logging de cómo se calculan dependencias
- [ ] Considerar si LLM debería generar dependencias explícitas
- [ ] O mejorar keyword matching para ser más inteligente

**Archivos Afectados:**
- `planning/domain/value_objects/task_derivation/dependency_graph.py`

### Gap 4: Integración RBAC incompleta

**Problema:**
- `TaskDerivationResultService` tiene TODO: "Validate with RBAC before assignment"
- Actualmente solo mapea role string → Role VO
- No valida permisos RBAC antes de asignar tasks

**Impacto:**
- ⚠️ Tasks pueden asignarse a roles sin permisos
- ⚠️ No hay validación de permisos RBAC

**Tareas Pendientes:**
- [ ] Definir cómo Planning Service integra con RBAC
- [ ] Revisar `RBAC_REVIEW.md` para entender niveles de RBAC
- [ ] Determinar si Planning Service necesita port para RBAC
- [ ] O si RBAC se valida en otro servicio (Workflow Service)
- [ ] Implementar validación RBAC antes de asignar tasks

**Archivos Afectados:**
- `planning/application/services/task_derivation_result_service.py`
- `planning/application/ports/` (nuevo port si es necesario)

### Gap 5: Context Service Integration incompleta

**Problema:**
- `ContextServiceAdapter` tiene `NotImplementedError`
- Protobuf files no están generados
- Llamada gRPC real no está implementada

**Impacto:**
- 🟡 Task derivation funciona pero sin contexto enriquecido
- 🟡 Fallback a Plan-only prompt (menos contexto para LLM)

**Tareas Pendientes:**
- [ ] Generar protobuf files (`context_pb2`, `context_pb2_grpc`)
- [ ] Implementar llamada gRPC real en `ContextServiceAdapter.get_context()`
- [ ] Configurar gRPC client stub
- [ ] Manejar errores gRPC (timeouts, retries)
- [ ] Agregar tests de integración con Context Service

**Archivos Afectados:**
- `planning/infrastructure/adapters/context_service_adapter.py`
- `services/context/gen/` (protobuf files)

### Gap 6: Tests de integración faltantes

**Problema:**
- Task Derivation necesita tests de integración para validar flujo completo
- No hay tests E2E para workflow completo

**Impacto:**
- ⚠️ No se puede validar flujo completo end-to-end
- ⚠️ Edge cases no están cubiertos

**Tareas Pendientes:**
- [ ] Tests de integración: Plan approved → Tasks derived → Tasks stored
- [ ] Tests de integración: LLM output parsing → TaskNode VOs → Tasks created
- [ ] Tests de integración: Dependency graph calculation → Tasks ordered correctly
- [ ] Tests E2E: Create Story → Approve Plan → Derive Tasks → Transition Story
- [ ] Tests de edge cases: LLM output inválido, campos faltantes, etc.

**Archivos Afectados:**
- `tests/integration/test_task_derivation_integration.py` (nuevo)
- `tests/e2e/test_planning_workflow_e2e.py` (nuevo)

---

## 🌐 Relación con Contexto

### ¿Qué es el Contexto?

**Contexto** en SWE AI Fleet se refiere a la información rehidratada que un agente necesita para entender el estado actual del trabajo y tomar decisiones informadas.

### Contexto en Task Derivation

**Task Derivation** usa contexto rehidratado por rol para enriquecer el prompt del LLM. El contexto proporciona:

1. **Story Context** (Qué estamos construyendo):
   - Título y descripción de la historia
   - Estado actual de la historia
   - DoR score
   - Acceptance criteria

2. **Plan Context** (Cómo lo estamos construyendo):
   - Título y descripción del plan
   - Technical notes
   - Approach y decisiones técnicas

3. **Role Context** (Qué tareas tiene el rol):
   - Tareas existentes para el rol específico
   - Estado de cada tarea
   - Prioridades y estimaciones

4. **Decision Context** (Qué decisiones se han tomado):
   - Decisiones relevantes para el rol
   - Decisiones que afectan las tareas del rol
   - Alternativas consideradas

5. **Dependency Context** (Cómo se relacionan las cosas):
   - Dependencias entre decisiones
   - Dependencias entre tareas
   - Impactos de decisiones en tareas

6. **Milestone Context** (Qué ha pasado):
   - Hitos recientes del proyecto
   - Eventos importantes
   - Resúmenes del estado general

### Por qué el Contexto es Crítico

**Sin Contexto (Plan-only prompt):**
- LLM solo ve: Plan description, Acceptance criteria, Technical notes
- **Limitación**: No sabe qué tareas ya existen, qué decisiones se tomaron, qué dependencias hay
- **Resultado**: Puede generar tareas duplicadas, ignorar decisiones previas, crear dependencias incorrectas

**Con Contexto Rehidratado:**
- LLM ve: Todo lo anterior + Story context + Role tasks + Decisions + Dependencies + Milestones
- **Ventaja**: Puede generar tareas que respetan decisiones previas, evitan duplicados, respetan dependencias
- **Resultado**: Tasks más precisas, mejor alineadas con el contexto del proyecto

### Flujo de Contexto en Task Derivation

```
1. Plan Approved Event
   ↓
2. DeriveTasksFromPlanUseCase
   - Fetch Plan from storage
   - Get Story from Plan
   ↓
3. Context Service GetContext(story_id, role, phase="plan")
   - Rehydrates context from Neo4j graph
   - Rehydrates context from Valkey details
   - Assembles RoleContextFields:
     * Story header
     * Plan header
     * Role tasks
     * Relevant decisions
     * Decision dependencies
     * Impacted tasks
     * Recent milestones
     * Last summary
   ↓
4. Context string (formatted prompt blocks)
   ↓
5. LLM Prompt (enriched with context)
   - Context (rehydrated)
   - Plan description
   - Acceptance criteria
   - Technical notes
   ↓
6. vLLM generates tasks (with context awareness)
   ↓
7. Tasks stored in Planning Service
   ↓
8. Context updated (new tasks added to context)
```

### Contexto y Dependencias

**Dependencias entre Tasks** se calculan desde:
1. **Keywords matching** (actual):
   - Si Task B menciona keywords de Task A → B depende de A
   - Problema: Puede generar dependencias incorrectas

2. **Contexto de decisiones** (futuro):
   - Si Decision X afecta Task A y Task B → B puede depender de A
   - Ventaja: Dependencias más precisas basadas en decisiones

3. **Contexto de tareas existentes** (futuro):
   - Si Task A ya existe y Task B menciona conceptos de Task A → B depende de A
   - Ventaja: Respeta tareas existentes

### Contexto y RBAC

**RBAC (Role-Based Access Control)** determina:
- Qué roles pueden ver qué contexto
- Qué roles pueden crear qué tipos de tasks
- Qué roles pueden asignarse a qué tasks

**Contexto por Rol:**
- **Developer**: Ve tasks de desarrollo, decisiones técnicas, dependencias técnicas
- **QA**: Ve tasks de testing, decisiones de calidad, dependencias de testing
- **Architect**: Ve todas las tasks, todas las decisiones, todas las dependencias
- **PO**: Ve story context, plan context, milestones (vista de negocio)

**Task Derivation usa contexto del rol** para generar tasks apropiadas para ese rol.

---

## 🗺 Roadmap de Correcciones

### Prioridad 🔴 CRÍTICA (Bloquea confiabilidad)

**1. Completar integración Context Service**
- **Tarea**: Generar protobuf files e implementar llamada gRPC real
- **Impacto**: Task derivation tendrá contexto enriquecido
- **Esfuerzo**: Medio (2-3 días)
- **Dependencias**: Context Service protobuf files

**2. Corregir flujo de ROLE**
- **Tarea**: Extraer roles del evento `planning.plan.approved` y validar con RBAC
- **Impacto**: Tasks asignadas correctamente según RBAC
- **Esfuerzo**: Medio (2-3 días)
- **Dependencias**: Definir integración RBAC

**3. Mejorar parsing del LLM**
- **Tarea**: Hacer parsing más robusto y agregar validación exhaustiva
- **Impacto**: Tasks creadas con datos válidos
- **Esfuerzo**: Alto (3-5 días)
- **Dependencias**: Entender variaciones del LLM output

### Prioridad ⚠️ IMPORTANTE (Mejora funcionalidad)

**4. Revisar algoritmo de dependencias**
- **Tarea**: Mejorar keyword matching o considerar dependencias explícitas del LLM
- **Impacto**: Dependencias más precisas entre tasks
- **Esfuerzo**: Medio (2-3 días)
- **Dependencias**: Tests de casos edge

**5. Implementar validación RBAC**
- **Tarea**: Validar permisos RBAC antes de asignar tasks
- **Impacto**: Tasks asignadas según permisos
- **Esfuerzo**: Medio (2-3 días)
- **Dependencias**: Definir integración RBAC

**6. Agregar tests de integración**
- **Tarea**: Tests de integración y E2E para task derivation
- **Impacto**: Validación de flujo completo
- **Esfuerzo**: Alto (3-5 días)
- **Dependencias**: Infraestructura de testing

### Prioridad 📝 MEJORAS (Documentación y validación)

**7. Actualizar documentación**
- **Tarea**: Actualizar README.md y summaries con task derivation
- **Impacto**: Documentación completa y actualizada
- **Esfuerzo**: Bajo (1 día)
- **Dependencias**: Ninguna

**8. Verificar bounded context**
- **Tarea**: Auditar imports y verificar que no hay imports de `core/*`
- **Impacto**: Bounded context isolation
- **Esfuerzo**: Bajo (1 día)
- **Dependencias**: Ninguna

---

## 📊 Resumen Final

### Estado Actual

**Planning Service** está **funcionalmente completo** pero necesita **correcciones críticas en Task Derivation** para ser confiable en producción.

**Fortalezas:**
- ✅ Arquitectura sólida (DDD + Hexagonal)
- ✅ Domain layer bien diseñado
- ✅ Application layer completa
- ✅ Infrastructure layer robusta
- ✅ Tests unitarios completos (>90% coverage)
- ✅ Event-driven architecture implementada

**Debilidades:**
- 🟡 Task Derivation no es confiable (parsing LLM, dependencias)
- 🟡 Integración Context Service incompleta (protobuf pendiente)
- 🟡 RBAC integration incompleta
- 🟡 Tests de integración faltantes

### Gaps Críticos para Crear Tasks de una Historia

**Para crear el conjunto de tareas de una historia de usuario, faltan:**

1. **Contexto Rehidratado Completo**:
   - ⚠️ Context Service integration incompleta (protobuf pendiente)
   - ⚠️ Sin contexto enriquecido, LLM puede generar tasks incorrectas

2. **Parsing Robusto del LLM**:
   - ⚠️ Parsing actual puede fallar silenciosamente
   - ⚠️ Sin validación exhaustiva de campos

3. **Dependencias Precisas**:
   - ⚠️ Keyword matching puede generar dependencias incorrectas
   - ⚠️ Sin dependencias explícitas del LLM

4. **RBAC Validation**:
   - ⚠️ Sin validación RBAC antes de asignar tasks
   - ⚠️ Tasks pueden asignarse incorrectamente

5. **Validación End-to-End**:
   - ⚠️ Sin tests de integración para validar flujo completo
   - ⚠️ Edge cases no están cubiertos

### Relación con Contexto

**El contexto es crítico para Task Derivation** porque:

1. **Proporciona información rica** sobre el estado actual del proyecto
2. **Evita duplicados** al mostrar tareas existentes
3. **Respeta decisiones previas** al mostrar decisiones relevantes
4. **Mejora dependencias** al mostrar relaciones existentes
5. **Alinea con el rol** al filtrar contexto por rol específico

**Sin contexto**, Task Derivation funciona pero genera tasks menos precisas y puede ignorar decisiones previas o crear duplicados.

**Con contexto**, Task Derivation genera tasks más precisas, respeta decisiones previas, evita duplicados, y respeta dependencias existentes.

---

## 📚 Referencias

- `ARCHITECTURE.md` - Arquitectura completa de Planning Service
- `PENDING_TASKS.md` - Tareas pendientes identificadas
- `AUDIT_ARCHITECTURE_COMPLIANCE_V2.md` - Auditoría de cumplimiento
- `AUDIT_ROLE_RESPONSIBILITY.md` - Auditoría de responsabilidad de ROLE
- `RBAC_REVIEW.md` - Revisión de RBAC integration
- `config/task_derivation.yaml` - Configuración de task derivation

---

**Documento generado:** 2025-11-14
**Última actualización:** 2025-11-14
**Versión:** 1.0

