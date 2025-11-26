# Arquitectura de Eventos - Planning Service

## Resumen

El **Planning Service** es el servicio backend que:
1. **PUBLICA** eventos a NATS cuando ocurren cambios (crear proyecto, story, etc.)
2. **CONSUME** eventos de otros servicios (para workflows reactivos)

**planning-ui** NO publica eventos - solo hace llamadas gRPC al Planning Service.

---

## Eventos Publicados por Planning Service

El Planning Service publica eventos a NATS cuando ocurren cambios en el dominio:

### Proyectos
- `planning.project.created` - Cuando se crea un proyecto nuevo
  - **Publicado por:** `CreateProjectUseCase`
  - **Consumidores potenciales:** Otros servicios que necesitan saber de nuevos proyectos

### Epics
- `planning.epic.created` - Cuando se crea un epic
  - **Publicado por:** `CreateEpicUseCase`

### Stories
- `planning.story.created` - Cuando se crea una story
  - **Publicado por:** `CreateStoryUseCase`
- `planning.story.transitioned` - Cuando una story cambia de estado (FSM)
  - **Publicado por:** `TransitionStoryUseCase`
- `planning.story.tasks_not_ready` - Cuando las tasks no están listas para transición
  - **Publicado por:** `TransitionStoryUseCase` (cuando falla validación)

### Tasks
- `planning.task.created` - Cuando se crea una task
  - **Publicado por:** `CreateTaskUseCase`

### Decisions
- `planning.decision.approved` - Cuando se aprueba una decisión
  - **Publicado por:** `ApproveDecisionUseCase`
- `planning.decision.rejected` - Cuando se rechaza una decisión
  - **Publicado por:** `RejectDecisionUseCase`

### Task Derivation
- `task.derivation.requested` - Solicita derivación de tasks a otro servicio
  - **Publicado por:** `DeriveTasksFromPlanUseCase`
- `planning.tasks.derived` - Notifica que se derivaron tasks
  - **Publicado por:** `TaskDerivationResultService`
- `planning.task.derivation.failed` - Notifica fallo en derivación
  - **Publicado por:** `TaskDerivationResultService`

---

## Eventos Consumidos por Planning Service

El Planning Service también consume eventos de otros servicios para workflows reactivos:

### Plan Approval
- **Evento:** `planning.plan.approved`
- **Consumer:** `PlanApprovedConsumer`
- **Acción:** Triggers `DeriveTasksFromPlanUseCase` para derivar tasks automáticamente

### Task Derivation Results
- **Eventos:** `agent.response.completed`, `agent.response.failed`
- **Consumer:** `TaskDerivationResultConsumer`
- **Acción:** Procesa resultados de derivación de tasks y crea tasks en el Planning Service

---

## Flujo de Comunicación

```
planning-ui (Frontend)
    │
    │ HTTP/gRPC
    ▼
Planning Service (Backend)
    │
    │ ┌─────────────────────────┐
    │ │ Publica eventos (NATS)  │
    │ └─────────────────────────┘
    │           │
    │           ▼
    │    NATS JetStream
    │           │
    │           ├──► Otros servicios (consumen eventos)
    │
    │ ┌─────────────────────────┐
    │ │ Consume eventos (NATS)  │
    │ └─────────────────────────┘
    │           ▲
    │           │
    │    NATS JetStream
    │           │
    │           └──► Otros servicios (publican eventos)
```

---

## Implementación Técnica

### Publicación de Eventos

Todos los use cases que necesitan publicar eventos usan el `MessagingPort`:

```python
await self.messaging.publish_event(
    subject="planning.project.created",  # NATS subject (NO "topic")
    payload=payload,  # dict JSON-serializable
)
```

**Importante:** El parámetro es `subject=`, NO `topic=`.

### Adapter

El `NATSMessagingAdapter` implementa el `MessagingPort` y publica a NATS JetStream:

```python
class NATSMessagingAdapter(MessagingPort):
    async def publish_event(
        self,
        subject: str,  # NATS subject
        payload: dict[str, Any],  # Event payload
    ) -> None:
        message = json.dumps(payload).encode("utf-8")
        ack = await self.js.publish(subject, message)
```

---

## Términos: "Topic" vs "Subject"

En NATS:
- **Subject** = Término correcto para NATS (usado en código)
- **Topic** = Término de otros sistemas de mensajería (Kafka, RabbitMQ, etc.)

**En este proyecto:**
- ✅ Usamos `subject` en código y puertos
- ✅ Los eventos se publican a NATS subjects
- ❌ NO usar "topic" - es confuso con otros sistemas

---

## Referencias

- [NATS Documentation - Subjects](https://docs.nats.io/nats-concepts/subjects)
- `services/planning/application/ports/messaging_port.py` - Definición del puerto
- `services/planning/infrastructure/adapters/nats_messaging_adapter.py` - Implementación
- `services/planning/infrastructure/consumers/` - Consumers de eventos

