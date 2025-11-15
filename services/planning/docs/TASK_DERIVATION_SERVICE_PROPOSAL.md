# Propuesta: Extraer Task Derivation a Servicio Dedicado

**Fecha:** 2025-11-14
**Autor:** AI Assistant
**Estado:** 🟡 Propuesta Arquitectónica
**Prioridad:** 🔴 ALTA - Mejora separación de concerns

---

## 📋 Resumen Ejecutivo

### Propuesta

**Mover la derivación de tareas (Task Derivation) de Planning Service a un servicio dedicado**, dejando a Planning Service solo con la responsabilidad de **indicar que se debe iniciar la derivación**.

### Justificación

**Principio de Responsabilidad Única (SRP):**
- Planning Service debería ser responsable solo de **planificación** (crear historias, gestionar ciclo de vida)
- Task Derivation es una **responsabilidad diferente** (generación automática de tasks usando LLM)
- Separar concerns mejora mantenibilidad y escalabilidad

**Ventajas:**
- ✅ **Separación clara de responsabilidades**
- ✅ **Planning Service más simple** (solo planificación)
- ✅ **Task Derivation Service puede escalar independientemente**
- ✅ **Mejor testabilidad** (servicios más pequeños)
- ✅ **Mejor alineación con arquitectura de microservicios**

---

## 🎯 Responsabilidades Actuales vs. Propuestas

### Planning Service (Actual)

**Responsabilidades Actuales:**
1. ✅ Crear y persistir entidades (Project → Epic → Story → Task)
2. ✅ Gestionar ciclo de vida de historias (FSM)
3. ✅ Aprobar/rechazar decisiones
4. ✅ **Task Derivation** (completo):
   - Escuchar `planning.plan.approved`
   - Obtener contexto de Context Service
   - Construir prompt LLM
   - Enviar a Ray Executor
   - Procesar resultados del LLM
   - Crear tasks
   - Persistir tasks
   - Validar tasks

**Problema:** Planning Service tiene demasiadas responsabilidades relacionadas con Task Derivation.

### Planning Service (Propuesto)

**Responsabilidades Propuestas:**
1. ✅ Crear y persistir entidades (Project → Epic → Story → Task)
2. ✅ Gestionar ciclo de vida de historias (FSM)
3. ✅ Aprobar/rechazar decisiones
4. ✅ **Solo indicar inicio de Task Derivation**:
   - Escuchar `planning.plan.approved`
   - Publicar evento `task.derivation.requested` (nuevo evento)
   - **FIN** - Task Derivation Service se encarga del resto

**Ventaja:** Planning Service se enfoca solo en planificación.

### Task Derivation Service (Nuevo)

**Responsabilidades Propuestas:**
1. ✅ Escuchar `task.derivation.requested`
2. ✅ Obtener contexto de Context Service
3. ✅ Construir prompt LLM
4. ✅ Enviar a Ray Executor
5. ✅ Procesar resultados del LLM
6. ✅ Crear tasks (llamando a Planning Service vía gRPC)
7. ✅ Validar tasks
8. ✅ Publicar eventos de resultado

**Ventaja:** Servicio dedicado con responsabilidad única.

---

## 🏗 Arquitectura Propuesta

### Diagrama de Flujo Actual

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJO ACTUAL                              │
└─────────────────────────────────────────────────────────────┘

1. planning.plan.approved event
   ↓
2. PlanApprovedConsumer (Planning Service)
   ↓
3. DeriveTasksFromPlanUseCase (Planning Service)
   - Fetch Plan
   - Get Context from Context Service
   - Build Prompt
   - Submit to Ray Executor
   ↓
4. Ray Executor → vLLM
   ↓
5. agent.response.completed event
   ↓
6. TaskDerivationResultConsumer (Planning Service)
   ↓
7. TaskDerivationResultService (Planning Service)
   - Parse LLM output
   - Build dependency graph
   - Create tasks
   - Persist tasks
   ↓
8. Tasks stored in Planning Service
```

**Problema:** Todo está en Planning Service.

### Diagrama de Flujo Propuesto

```
┌─────────────────────────────────────────────────────────────┐
│                  FLUJO PROPUESTO                             │
└─────────────────────────────────────────────────────────────┘

1. planning.plan.approved event
   ↓
2. PlanApprovedConsumer (Planning Service)
   ↓
3. RequestTaskDerivationUseCase (Planning Service)
   - Solo publica evento task.derivation.requested
   ↓
4. task.derivation.requested event
   ↓
5. TaskDerivationRequestConsumer (Task Derivation Service)
   ↓
6. DeriveTasksUseCase (Task Derivation Service)
   - Fetch Plan from Planning Service (gRPC)
   - Get Context from Context Service (gRPC)
   - Build Prompt
   - Submit to Ray Executor
   ↓
7. Ray Executor → vLLM
   ↓
8. agent.response.completed event
   ↓
9. TaskDerivationResultConsumer (Task Derivation Service)
   ↓
10. ProcessTaskDerivationResultUseCase (Task Derivation Service)
    - Parse LLM output
    - Build dependency graph
    - Create tasks via Planning Service (gRPC)
    ↓
11. CreateTaskUseCase (Planning Service)
    - Persist tasks
    ↓
12. Tasks stored in Planning Service
    ↓
13. task.derivation.completed event (Task Derivation Service)
    - Notifica que derivación completó
```

**Ventaja:** Separación clara de responsabilidades.

---

## 📦 Componentes a Mover

### Componentes que se Mueven a Task Derivation Service

**Application Layer:**
- ✅ `DeriveTasksFromPlanUseCase` → `DeriveTasksUseCase`
- ✅ `TaskDerivationResultService` → `ProcessTaskDerivationResultUseCase`

**Infrastructure Layer:**
- ✅ `TaskDerivationResultConsumer` → Mover completo
- ✅ `RayExecutorAdapter` → Mover completo
- ✅ `ContextServiceAdapter` → Mover completo
- ✅ `LLMTaskDerivationMapper` → Mover completo
- ✅ `DependencyGraph` (domain VO) → Mover completo
- ✅ `TaskNode` (domain VO) → Mover completo
- ✅ `LLMPrompt` (domain VO) → Mover completo
- ✅ `TaskDerivationConfig` (domain VO) → Mover completo

**Configuration:**
- ✅ `config/task_derivation.yaml` → Mover completo

**Tests:**
- ✅ Todos los tests relacionados con Task Derivation

### Componentes que se Quedan en Planning Service

**Application Layer:**
- ✅ `CreateTaskUseCase` → Se queda (crear tasks es responsabilidad de Planning)
- ✅ `GetTaskUseCase` → Se queda
- ✅ `ListTasksUseCase` → Se queda
- ✅ `TransitionStoryUseCase` → Se queda (validación de tasks)

**Infrastructure Layer:**
- ✅ `PlanApprovedConsumer` → Se queda (pero simplificado)
- ✅ `StorageAdapter` → Se queda (persistencia de tasks)
- ✅ `NATSMessagingAdapter` → Se queda (publicar eventos)

**Domain Layer:**
- ✅ `Task` entity → Se queda (Planning Service persiste tasks)
- ✅ `Story` entity → Se queda
- ✅ `Plan` entity → Se queda (pero solo como referencia)

### Componentes Nuevos en Planning Service

**Application Layer:**
- 🆕 `RequestTaskDerivationUseCase` → Nuevo (solo publica evento)

**Infrastructure Layer:**
- 🆕 Simplificación de `PlanApprovedConsumer` → Solo publica evento

---

## 🔌 Integración entre Servicios

### Comunicación: Planning Service → Task Derivation Service

**Event-Driven (NATS):**
```
Planning Service publica:
  Event: task.derivation.requested
  Payload: {
    plan_id: "plan-001",
    story_id: "story-001",
    roles: ["DEVELOPER", "QA"],
    requested_by: "po-001",
    timestamp: "2025-11-14T10:00:00Z"
  }
```

**Ventaja:** Desacoplado, asíncrono, escalable.

### Comunicación: Task Derivation Service → Planning Service

**Síncrono (gRPC):**
```
Task Derivation Service llama:
  - GetPlan(plan_id) → Obtener Plan details
  - CreateTask(request) → Crear tasks
  - ListTasks(story_id) → Validar tasks existentes
```

**Ventaja:** Síncrono para operaciones críticas, Planning Service mantiene control de datos.

### Comunicación: Task Derivation Service → Context Service

**Síncrono (gRPC):**
```
Task Derivation Service llama:
  - GetContext(story_id, role, phase) → Obtener contexto rehidratado
```

**Ventaja:** Ya existe, solo se mueve la llamada.

### Comunicación: Task Derivation Service → Ray Executor

**Síncrono (gRPC):**
```
Task Derivation Service llama:
  - SubmitTaskDerivation(prompt, role) → Enviar a vLLM
```

**Ventaja:** Ya existe, solo se mueve la llamada.

---

## 📋 Eventos Propuestos

### Nuevos Eventos

**1. `task.derivation.requested`**
- **Publicado por:** Planning Service
- **Consumido por:** Task Derivation Service
- **Payload:**
  ```json
  {
    "event_type": "task.derivation.requested",
    "plan_id": "plan-001",
    "story_id": "story-001",
    "roles": ["DEVELOPER", "QA"],
    "requested_by": "po-001",
    "timestamp": "2025-11-14T10:00:00Z"
  }
  ```

**2. `task.derivation.completed`**
- **Publicado por:** Task Derivation Service
- **Consumido por:** Planning Service, Monitoring
- **Payload:**
  ```json
  {
    "event_type": "task.derivation.completed",
    "plan_id": "plan-001",
    "story_id": "story-001",
    "task_count": 5,
    "status": "success",
    "timestamp": "2025-11-14T10:05:00Z"
  }
  ```

**3. `task.derivation.failed`**
- **Publicado por:** Task Derivation Service
- **Consumido por:** Planning Service, PO-UI
- **Payload:**
  ```json
  {
    "event_type": "task.derivation.failed",
    "plan_id": "plan-001",
    "story_id": "story-001",
    "reason": "LLM parsing failed",
    "requires_manual_review": true,
    "timestamp": "2025-11-14T10:05:00Z"
  }
  ```

### Eventos que se Mantienen

- ✅ `planning.plan.approved` → Se mantiene (otro servicio lo publica)
- ✅ `agent.response.completed` → Se mantiene (Ray Executor lo publica)
- ✅ `planning.task.created` → Se mantiene (Planning Service lo publica)
- ✅ `planning.story.tasks_not_ready` → Se mantiene (Planning Service lo publica)

---

## 🔧 Cambios en Planning Service

### Cambios en `PlanApprovedConsumer`

**Antes:**
```python
async def _handle_message(self, msg) -> None:
    payload = json.loads(msg.data.decode())
    plan_id = PlanId(payload["plan_id"])

    # Llama directamente a DeriveTasksFromPlanUseCase
    deliberation_id = await self._derive_tasks.execute(plan_id)

    await msg.ack()
```

**Después:**
```python
async def _handle_message(self, msg) -> None:
    payload = json.loads(msg.data.decode())
    plan_id = PlanId(payload["plan_id"])
    story_id = StoryId(payload["story_id"])
    roles = payload.get("roles", [])

    # Solo publica evento para Task Derivation Service
    await self._request_derivation.execute(
        plan_id=plan_id,
        story_id=story_id,
        roles=roles,
    )

    await msg.ack()
```

**Ventaja:** Mucho más simple, solo publica evento.

### Nuevo Use Case: `RequestTaskDerivationUseCase`

```python
@dataclass
class RequestTaskDerivationUseCase:
    """Use case for requesting task derivation.

    Planning Service solo indica que se debe iniciar derivación.
    Task Derivation Service se encarga del resto.
    """
    messaging: MessagingPort

    async def execute(
        self,
        plan_id: PlanId,
        story_id: StoryId,
        roles: tuple[str, ...],
        requested_by: str = "planning-service",
    ) -> None:
        """Request task derivation for a story.

        Args:
            plan_id: Plan identifier
            story_id: Story identifier
            roles: Roles for task derivation
            requested_by: Who requested derivation
        """
        payload = {
            "event_type": "task.derivation.requested",
            "plan_id": plan_id.value,
            "story_id": story_id.value,
            "roles": list(roles),
            "requested_by": requested_by,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        await self.messaging.publish_event(
            topic="task.derivation.requested",
            payload=payload,
        )
```

**Ventaja:** Responsabilidad única, simple.

### Cambios en `TransitionStoryUseCase`

**Sin cambios:** `TransitionStoryUseCase` sigue validando que tasks existan y tengan prioridades válidas. No necesita cambios porque las tasks se crean vía gRPC desde Task Derivation Service.

---

## 🆕 Task Derivation Service (Nuevo)

### Estructura Propuesta

```
services/task-derivation/
├── task_derivation/
│   ├── domain/
│   │   ├── value_objects/
│   │   │   ├── task_node.py
│   │   │   ├── dependency_graph.py
│   │   │   ├── llm_prompt.py
│   │   │   └── task_derivation_config.py
│   │   └── events/
│   │       └── task_derivation_completed_event.py
│   ├── application/
│   │   ├── ports/
│   │   │   ├── planning_port.py  # gRPC client para Planning Service
│   │   │   ├── context_port.py
│   │   │   ├── ray_executor_port.py
│   │   │   └── messaging_port.py
│   │   ├── usecases/
│   │   │   ├── derive_tasks_usecase.py
│   │   │   └── process_task_derivation_result_usecase.py
│   │   └── services/
│   │       └── task_derivation_service.py
│   └── infrastructure/
│       ├── adapters/
│       │   ├── planning_service_adapter.py  # gRPC client
│       │   ├── context_service_adapter.py
│       │   ├── ray_executor_adapter.py
│       │   └── nats_messaging_adapter.py
│       ├── consumers/
│       │   ├── task_derivation_request_consumer.py
│       │   └── task_derivation_result_consumer.py
│       └── mappers/
│           └── llm_task_derivation_mapper.py
├── config/
│   └── task_derivation.yaml
├── tests/
│   ├── unit/
│   └── integration/
└── server.py
```

### Ports Necesarios

**1. PlanningPort (gRPC Client):**
```python
class PlanningPort(Protocol):
    """Port for Planning Service gRPC integration."""

    async def get_plan(self, plan_id: str) -> dict[str, Any]:
        """Get plan details from Planning Service."""
        ...

    async def create_task(self, request: dict[str, Any]) -> dict[str, Any]:
        """Create task in Planning Service."""
        ...

    async def list_tasks(self, story_id: str) -> list[dict[str, Any]]:
        """List tasks for a story from Planning Service."""
        ...
```

**2. ContextPort:**
```python
class ContextPort(Protocol):
    """Port for Context Service gRPC integration."""

    async def get_context(
        self,
        story_id: str,
        role: str,
        phase: str = "plan",
    ) -> str:
        """Get rehydrated context from Context Service."""
        ...
```

**3. RayExecutorPort:**
```python
class RayExecutorPort(Protocol):
    """Port for Ray Executor gRPC integration."""

    async def submit_task_derivation(
        self,
        plan_id: str,
        prompt: str,
        role: str,
    ) -> str:
        """Submit task derivation to Ray Executor."""
        ...
```

**4. MessagingPort:**
```python
class MessagingPort(Protocol):
    """Port for NATS messaging."""

    async def publish_event(
        self,
        topic: str,
        payload: dict[str, Any],
    ) -> None:
        """Publish event to NATS."""
        ...
```

### Use Cases Propuestos

**1. DeriveTasksUseCase:**
```python
@dataclass
class DeriveTasksUseCase:
    """Use case for deriving tasks from a plan.

    Responsibilities:
    - Get plan from Planning Service
    - Get context from Context Service
    - Build LLM prompt
    - Submit to Ray Executor
    """
    planning_service: PlanningPort
    context_service: ContextPort
    ray_executor: RayExecutorPort
    config: TaskDerivationConfig

    async def execute(
        self,
        plan_id: str,
        story_id: str,
        roles: tuple[str, ...],
    ) -> str:
        """Derive tasks for a story.

        Returns:
            DeliberationId for tracking
        """
        # 1. Get plan from Planning Service
        plan = await self.planning_service.get_plan(plan_id)

        # 2. Get context from Context Service
        role_for_context = roles[0] if roles else "developer"
        context = await self.context_service.get_context(
            story_id=story_id,
            role=role_for_context,
            phase="plan",
        )

        # 3. Build prompt
        prompt = self.config.build_prompt(
            description=plan["description"],
            acceptance_criteria=plan["acceptance_criteria"],
            technical_notes=plan["technical_notes"],
            rehydrated_context=context,
        )

        # 4. Submit to Ray Executor
        deliberation_id = await self.ray_executor.submit_task_derivation(
            plan_id=plan_id,
            prompt=prompt,
            role=role_for_context,
        )

        return deliberation_id
```

**2. ProcessTaskDerivationResultUseCase:**
```python
@dataclass
class ProcessTaskDerivationResultUseCase:
    """Use case for processing task derivation results.

    Responsibilities:
    - Parse LLM output
    - Build dependency graph
    - Create tasks via Planning Service
    - Publish events
    """
    planning_service: PlanningPort
    messaging: MessagingPort

    async def execute(
        self,
        plan_id: str,
        story_id: str,
        role: str,
        llm_output: str,
    ) -> None:
        """Process task derivation result.

        Args:
            plan_id: Plan identifier
            story_id: Story identifier
            role: Role from context
            llm_output: LLM output text
        """
        # 1. Parse LLM output
        task_nodes = LLMTaskDerivationMapper.from_llm_text(llm_output)

        # 2. Build dependency graph
        graph = DependencyGraph.from_tasks(task_nodes)

        # 3. Validate circular dependencies
        if graph.has_circular_dependency():
            await self._publish_failure_event(
                plan_id=plan_id,
                story_id=story_id,
                reason="Circular dependencies detected",
            )
            raise ValueError("Circular dependencies")

        # 4. Create tasks via Planning Service
        ordered_tasks = graph.get_ordered_tasks()
        for task_node in ordered_tasks:
            task_request = {
                "plan_id": plan_id,
                "story_id": story_id,
                "title": task_node.title.value,
                "description": task_node.description.value,
                "estimated_hours": task_node.estimated_hours.to_hours(),
                "priority": task_node.priority.to_int(),
                "assigned_to": role,
            }
            await self.planning_service.create_task(task_request)

        # 5. Publish success event
        await self._publish_success_event(
            plan_id=plan_id,
            story_id=story_id,
            task_count=len(task_nodes),
        )
```

---

## 📊 Comparación: Antes vs. Después

### Planning Service

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Responsabilidades** | Planificación + Task Derivation | Solo Planificación |
| **Use Cases** | 15+ | 13 (sin Task Derivation) |
| **Consumers** | 2 | 1 (simplificado) |
| **Dependencias** | Ray Executor, Context Service | Ninguna (solo eventos) |
| **Complejidad** | Alta | Media |
| **Acoplamiento** | Alto (con Ray, Context) | Bajo (solo eventos) |

### Task Derivation Service (Nuevo)

| Aspecto | Valor |
|---------|-------|
| **Responsabilidades** | Solo Task Derivation |
| **Use Cases** | 2 |
| **Consumers** | 2 |
| **Dependencias** | Planning Service (gRPC), Context Service (gRPC), Ray Executor (gRPC) |
| **Complejidad** | Media |
| **Acoplamiento** | Medio (gRPC calls) |

---

## ✅ Ventajas de la Separación

### 1. Separación de Concerns

**Planning Service:**
- ✅ Se enfoca solo en planificación
- ✅ No necesita conocer detalles de LLM
- ✅ No necesita conocer detalles de Ray Executor
- ✅ No necesita conocer detalles de Context Service

**Task Derivation Service:**
- ✅ Se enfoca solo en derivación de tasks
- ✅ Puede evolucionar independientemente
- ✅ Puede escalar independientemente
- ✅ Puede tener su propia lógica de retry/error handling

### 2. Escalabilidad

**Planning Service:**
- ✅ Puede escalar independientemente de Task Derivation
- ✅ No necesita recursos GPU (Ray Executor)
- ✅ Puede ser más ligero

**Task Derivation Service:**
- ✅ Puede escalar según demanda de derivaciones
- ✅ Puede tener recursos dedicados para LLM
- ✅ Puede tener su propia estrategia de caching

### 3. Testabilidad

**Planning Service:**
- ✅ Tests más simples (menos dependencias)
- ✅ No necesita mocks de Ray Executor
- ✅ No necesita mocks de Context Service

**Task Derivation Service:**
- ✅ Tests enfocados en derivación
- ✅ Puede testear flujo completo de derivación
- ✅ Tests más aislados

### 4. Mantenibilidad

**Planning Service:**
- ✅ Código más simple
- ✅ Menos archivos
- ✅ Menos complejidad

**Task Derivation Service:**
- ✅ Código enfocado en una responsabilidad
- ✅ Más fácil de entender
- ✅ Más fácil de modificar

### 5. Despliegue Independiente

**Planning Service:**
- ✅ Puede desplegarse sin Task Derivation
- ✅ Puede actualizarse sin afectar Task Derivation

**Task Derivation Service:**
- ✅ Puede desplegarse independientemente
- ✅ Puede actualizarse sin afectar Planning Service

---

## ⚠️ Consideraciones y Desafíos

### 1. Comunicación entre Servicios

**Desafío:** Task Derivation Service necesita obtener Plan de Planning Service.

**Solución:**
- ✅ gRPC síncrono para operaciones críticas (GetPlan, CreateTask)
- ✅ Eventos asíncronos para coordinación (task.derivation.requested)

### 2. Consistencia de Datos

**Desafío:** Tasks se crean en Planning Service pero se derivan en Task Derivation Service.

**Solución:**
- ✅ Planning Service mantiene control de datos (CreateTask vía gRPC)
- ✅ Task Derivation Service solo solicita creación
- ✅ Planning Service valida antes de crear

### 3. Manejo de Errores

**Desafío:** Errores pueden ocurrir en múltiples servicios.

**Solución:**
- ✅ Eventos de error (`task.derivation.failed`)
- ✅ Retry logic en Task Derivation Service
- ✅ Notificación al PO cuando falla

### 4. Testing End-to-End

**Desafío:** Tests E2E requieren múltiples servicios.

**Solución:**
- ✅ Tests de integración por servicio
- ✅ Tests E2E con servicios mockeados
- ✅ Tests E2E con servicios reales en ambiente de desarrollo

### 5. Observabilidad

**Desafío:** Trazabilidad a través de múltiples servicios.

**Solución:**
- ✅ Correlation IDs en eventos
- ✅ Distributed tracing (OpenTelemetry)
- ✅ Logging estructurado

---

## 🗺 Plan de Migración

### Fase 1: Preparación (1-2 días)

1. ✅ Crear estructura de Task Derivation Service
2. ✅ Crear ports e interfaces
3. ✅ Documentar APIs y eventos

### Fase 2: Implementación (3-5 días)

1. ✅ Mover componentes de Planning Service a Task Derivation Service
2. ✅ Implementar PlanningPort adapter (gRPC client)
3. ✅ Implementar use cases en Task Derivation Service
4. ✅ Implementar consumers en Task Derivation Service

### Fase 3: Integración (2-3 días)

1. ✅ Actualizar Planning Service (simplificar PlanApprovedConsumer)
2. ✅ Implementar RequestTaskDerivationUseCase
3. ✅ Configurar eventos NATS
4. ✅ Configurar gRPC clients

### Fase 4: Testing (2-3 días)

1. ✅ Tests unitarios en Task Derivation Service
2. ✅ Tests de integración
3. ✅ Tests E2E
4. ✅ Validar flujo completo

### Fase 5: Despliegue (1-2 días)

1. ✅ Desplegar Task Derivation Service
2. ✅ Actualizar Planning Service
3. ✅ Validar en producción
4. ✅ Monitorear errores

**Total Estimado:** 9-15 días

---

## 📝 Checklist de Migración

### Planning Service

- [ ] Crear `RequestTaskDerivationUseCase`
- [ ] Simplificar `PlanApprovedConsumer` (solo publicar evento)
- [ ] Remover `DeriveTasksFromPlanUseCase`
- [ ] Remover `TaskDerivationResultService`
- [ ] Remover `TaskDerivationResultConsumer`
- [ ] Remover `RayExecutorAdapter`
- [ ] Remover `ContextServiceAdapter`
- [ ] Remover `LLMTaskDerivationMapper`
- [ ] Remover domain VOs relacionados (TaskNode, DependencyGraph, etc.)
- [ ] Remover `config/task_derivation.yaml`
- [ ] Actualizar tests (remover tests de Task Derivation)
- [ ] Actualizar documentación

### Task Derivation Service (Nuevo)

- [ ] Crear estructura del servicio
- [ ] Crear domain VOs (TaskNode, DependencyGraph, etc.)
- [ ] Crear ports (PlanningPort, ContextPort, RayExecutorPort, MessagingPort)
- [ ] Crear adapters (PlanningServiceAdapter, ContextServiceAdapter, etc.)
- [ ] Crear use cases (DeriveTasksUseCase, ProcessTaskDerivationResultUseCase)
- [ ] Crear consumers (TaskDerivationRequestConsumer, TaskDerivationResultConsumer)
- [ ] Crear mappers (LLMTaskDerivationMapper)
- [ ] Mover `config/task_derivation.yaml`
- [ ] Crear tests unitarios
- [ ] Crear tests de integración
- [ ] Crear Dockerfile
- [ ] Crear deployment K8s
- [ ] Crear documentación

### Infraestructura

- [ ] Configurar eventos NATS (`task.derivation.requested`, `task.derivation.completed`, `task.derivation.failed`)
- [ ] Configurar gRPC endpoints en Planning Service (GetPlan, CreateTask)
- [ ] Configurar gRPC client en Task Derivation Service
- [ ] Configurar monitoring y logging
- [ ] Configurar distributed tracing

---

## 🎯 Conclusión

### Recomendación

**✅ RECOMENDADO:** Extraer Task Derivation a un servicio dedicado.

**Razones:**
1. ✅ Mejora separación de concerns
2. ✅ Planning Service se vuelve más simple
3. ✅ Task Derivation Service puede escalar independientemente
4. ✅ Mejor testabilidad y mantenibilidad
5. ✅ Alineado con arquitectura de microservicios

### Próximos Pasos

1. **Revisar propuesta** con equipo
2. **Aprobar arquitectura** propuesta
3. **Crear tareas** de migración
4. **Iniciar Fase 1** (Preparación)

---

## 📚 Referencias

- `ARCHITECTURE.md` - Arquitectura actual de Planning Service
- `PLANNING_SERVICE_STATE.md` - Estado actual detallado
- `PENDING_TASKS.md` - Tareas pendientes
- `.cursorrules` - Reglas arquitectónicas

---

**Documento generado:** 2025-11-14
**Última actualización:** 2025-11-14
**Versión:** 1.0

