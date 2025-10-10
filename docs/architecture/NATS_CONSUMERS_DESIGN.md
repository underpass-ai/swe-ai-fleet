# NATS Consumers Design - Comunicación Asíncrona entre Servicios

## 🎯 Objetivo

Diseñar los **consumers, streams y subjects** de NATS JetStream necesarios para la comunicación asíncrona entre microservicios del sistema SWE AI Fleet.

---

## 🏗️ Arquitectura de Servicios

### Microservicios del Sistema

| Servicio | Tecnología | Puerto | Rol |
|----------|-----------|--------|-----|
| **Gateway** | Go | 8080 | API REST + SSE para frontend |
| **Planning** | Go | 50051 | FSM de historias (Agile) |
| **StoryCoach** | Go | 50052 | Scoring INVEST + sugerencias |
| **Context** | Python | 50054 | Orquestador de contexto |
| **Orchestrator** | Python | 50055 | Coordinación multi-agente |
| **Workspace** | Go | 50053 | Gestión de workspaces |
| **Agents** | Python | Jobs | Ejecución aislada en K8s |

---

## 📡 Streams de NATS JetStream

### **Stream 1: PLANNING_EVENTS**

**Propósito**: Eventos del ciclo de vida de historias y planes

**Configuración**:
```yaml
name: PLANNING_EVENTS
subjects:
  - planning.story.>
  - planning.plan.>
  - planning.task.>
retention: limits
max_age: 30d
max_msgs: 1000000
storage: file
```

**Subjects**:
```
planning.story.created          # Historia creada
planning.story.updated          # Historia actualizada
planning.story.transitioned     # Cambio de fase (DRAFT → BUILD)
planning.plan.created           # Plan generado
planning.plan.approved          # Plan aprobado por PO
planning.task.created           # Subtarea creada
planning.task.assigned          # Tarea asignada a rol
planning.task.completed         # Tarea completada
```

---

### **Stream 2: CONTEXT_EVENTS**

**Propósito**: Eventos de cambios en el contexto de ejecución

**Configuración**:
```yaml
name: CONTEXT_EVENTS
subjects:
  - context.>
retention: limits
max_age: 7d
max_msgs: 100000
storage: file
```

**Subjects**:
```
context.updated                 # Contexto actualizado (decisiones, etc)
context.decision.added          # Nueva decisión registrada
context.milestone.reached       # Milestone alcanzado
context.snapshot.created        # Snapshot de estado creado
```

---

### **Stream 3: ORCHESTRATOR_EVENTS**

**Propósito**: Eventos de deliberación y orquestación

**Configuración**:
```yaml
name: ORCHESTRATOR_EVENTS
subjects:
  - orchestration.>
retention: limits
max_age: 7d
max_msgs: 50000
storage: file
```

**Subjects**:
```
orchestration.deliberation.started    # Deliberación iniciada
orchestration.deliberation.completed  # Deliberación completada
orchestration.agent.registered        # Agente registrado
orchestration.council.formed          # Consejo formado
orchestration.task.dispatched         # Tarea enviada a agente
orchestration.task.completed          # Tarea completada por agente
```

---

### **Stream 4: AGENT_COMMANDS**

**Propósito**: Comandos para agentes (request/response asíncrono)

**Configuración**:
```yaml
name: AGENT_COMMANDS
subjects:
  - agent.cmd.>
retention: limits
max_age: 1h
max_msgs: 10000
storage: file
```

**Subjects**:
```
agent.cmd.execute               # Ejecutar tarea
agent.cmd.stop                  # Detener ejecución
agent.cmd.report                # Solicitar reporte de progreso
```

---

### **Stream 5: AGENT_RESPONSES**

**Propósito**: Respuestas de agentes

**Configuración**:
```yaml
name: AGENT_RESPONSES
subjects:
  - agent.response.>
retention: limits
max_age: 1h
max_msgs: 10000
storage: file
```

**Subjects**:
```
agent.response.started          # Agente comenzó tarea
agent.response.progress         # Progreso intermedio
agent.response.completed        # Tarea completada
agent.response.failed           # Tarea falló
```

---

## 🔄 Consumers por Servicio

### **1. Context Service Consumers**

#### Consumer: `context-planning-events`
**Stream**: PLANNING_EVENTS  
**Subjects**: `planning.story.transitioned`, `planning.plan.approved`  
**Queue Group**: `context-workers`  
**Durability**: Ephemeral (por ahora)

**Propósito**: Reaccionar a cambios en planning para invalidar cache

```python
# services/context/nats_handler.py
await js.subscribe(
    "planning.story.transitioned",
    queue="context-workers",
    cb=self._handle_story_transition
)

async def _handle_story_transition(self, msg):
    event = json.loads(msg.data.decode())
    story_id = event["story_id"]
    new_phase = event["to_phase"]
    
    # Invalidar cache de contexto
    await self.cache.delete(f"context:{story_id}")
    
    # Log para auditoría
    logger.info(f"Context invalidated for {story_id} → {new_phase}")
    
    await msg.ack()
```

---

#### Consumer: `context-orchestration-events`
**Stream**: ORCHESTRATOR_EVENTS  
**Subjects**: `orchestration.deliberation.completed`  
**Queue Group**: `context-workers`

**Propósito**: Recibir resultados de deliberación para actualizar contexto

```python
await js.subscribe(
    "orchestration.deliberation.completed",
    queue="context-workers",
    cb=self._handle_deliberation_completed
)

async def _handle_deliberation_completed(self, msg):
    event = json.loads(msg.data.decode())
    story_id = event["story_id"]
    decisions = event["decisions"]
    
    # Actualizar contexto con nuevas decisiones
    for decision in decisions:
        await self.graph_command.upsert_entity(
            entity_type="Decision",
            entity_id=decision["id"],
            properties=decision
        )
    
    # Publicar evento de actualización
    await self.js.publish(
        "context.updated",
        json.dumps({
            "story_id": story_id,
            "version": int(time.time()),
            "changes": ["decisions"]
        }).encode()
    )
    
    await msg.ack()
```

---

### **2. Orchestrator Service Consumers**

#### Consumer: `orchestrator-planning-events`
**Stream**: PLANNING_EVENTS  
**Subjects**: `planning.task.created`, `planning.task.assigned`  
**Queue Group**: `orchestrator-workers`

**Propósito**: Detectar nuevas tareas para orquestar agentes

```python
await js.subscribe(
    "planning.task.created",
    queue="orchestrator-workers",
    cb=self._handle_task_created
)

async def _handle_task_created(self, msg):
    event = json.loads(msg.data.decode())
    task_id = event["task_id"]
    role = event["assigned_role"]
    story_id = event["story_id"]
    
    # Obtener contexto
    context = await self.context_client.GetContext(
        story_id=story_id,
        role=role,
        phase=event["phase"]
    )
    
    # Crear deliberación
    result = await self.deliberate(
        task_id=task_id,
        context=context.context,
        role=role
    )
    
    # Publicar resultado
    await self.js.publish(
        "orchestration.deliberation.completed",
        json.dumps({
            "story_id": story_id,
            "task_id": task_id,
            "decisions": result.decisions
        }).encode()
    )
    
    await msg.ack()
```

---

#### Consumer: `orchestrator-context-updates`
**Stream**: CONTEXT_EVENTS  
**Subjects**: `context.updated`  
**Queue Group**: `orchestrator-workers`

**Propósito**: Reaccionar a cambios de contexto para re-evaluar planes

```python
await js.subscribe(
    "context.updated",
    queue="orchestrator-workers",
    cb=self._handle_context_updated
)

async def _handle_context_updated(self, msg):
    event = json.loads(msg.data.decode())
    story_id = event["story_id"]
    changes = event["changes"]
    
    # Verificar si hay tareas en curso que necesiten actualización
    if "decisions" in changes:
        # Notificar agentes activos
        await self._notify_active_agents(story_id)
    
    await msg.ack()
```

---

#### Consumer: `orchestrator-agent-responses`
**Stream**: AGENT_RESPONSES  
**Subjects**: `agent.response.>`  
**Queue Group**: `orchestrator-workers`

**Propósito**: Recibir respuestas de agentes y actualizar estado

```python
await js.subscribe(
    "agent.response.>",
    queue="orchestrator-workers",
    cb=self._handle_agent_response
)

async def _handle_agent_response(self, msg):
    event = json.loads(msg.data.decode())
    task_id = event["task_id"]
    status = event["status"]
    result = event.get("result")
    
    # Actualizar estado de tarea
    await self._update_task_status(task_id, status)
    
    if status == "completed":
        # Actualizar contexto con resultado
        await self.context_client.UpdateContext(
            story_id=event["story_id"],
            task_id=task_id,
            changes=result["changes"]
        )
    
    await msg.ack()
```

---

### **3. Planning Service Consumers**

#### Consumer: `planning-context-events`
**Stream**: CONTEXT_EVENTS  
**Subjects**: `context.milestone.reached`  
**Queue Group**: `planning-workers`

**Propósito**: Detectar milestones para actualizar FSM

```go
// services/planning/nats_handler.go
js.Subscribe("context.milestone.reached", func(msg *nats.Msg) {
    var event MilestoneEvent
    json.Unmarshal(msg.Data, &event)
    
    // Verificar si milestone permite transición FSM
    if canTransition(event.StoryID, event.Milestone) {
        // Trigger transición automática
        err := fsm.Transition(event.StoryID, event.Milestone)
        if err == nil {
            // Publicar evento de transición
            publishEvent("planning.story.transitioned", event.StoryID)
        }
    }
    
    msg.Ack()
}, nats.Durable("planning-milestones"), nats.DeliverGroup("planning-workers"))
```

---

#### Consumer: `planning-orchestration-events`
**Stream**: ORCHESTRATOR_EVENTS  
**Subjects**: `orchestration.task.completed`  
**Queue Group**: `planning-workers`

**Propósito**: Actualizar estado de tareas cuando se completan

```go
js.Subscribe("orchestration.task.completed", func(msg *nats.Msg) {
    var event TaskCompletedEvent
    json.Unmarshal(msg.Data, &event)
    
    // Actualizar tarea en base de datos
    err := db.UpdateTask(event.TaskID, "COMPLETED")
    
    // Verificar si todas las tareas de la fase están completas
    if allTasksComplete(event.StoryID, event.Phase) {
        // Publicar evento de fase completada
        publishEvent("planning.phase.completed", event.StoryID, event.Phase)
    }
    
    msg.Ack()
}, nats.Durable("planning-tasks"), nats.DeliverGroup("planning-workers"))
```

---

### **4. Gateway Service Consumers**

#### Consumer: `gateway-all-events`
**Stream**: ALL (wildcard)  
**Subjects**: `>` (todos)  
**Queue Group**: None (cada instancia recibe todos)

**Propósito**: Enviar SSE (Server-Sent Events) al frontend

```go
// services/gateway/sse_handler.go
js.Subscribe(">", func(msg *nats.Msg) {
    subject := msg.Subject
    data := msg.Data
    
    // Enviar a todos los clientes SSE suscritos
    sseHub.BroadcastToSubscribers(subject, data)
    
    msg.Ack()
}, nats.DeliverGroup("gateway-sse-1"))  // Cada pod tiene su propio grupo
```

**Ejemplo SSE en Frontend**:
```javascript
const eventSource = new EventSource('/api/events');

eventSource.addEventListener('planning.story.transitioned', (e) => {
  const event = JSON.parse(e.data);
  updateStoryCard(event.story_id, event.to_phase);
});

eventSource.addEventListener('context.updated', (e) => {
  const event = JSON.parse(e.data);
  refreshContextViewer(event.story_id);
});
```

---

### **5. Workspace Service Consumers**

#### Consumer: `workspace-agent-commands`
**Stream**: AGENT_COMMANDS  
**Subjects**: `agent.cmd.execute`  
**Queue Group**: `workspace-workers`

**Propósito**: Ejecutar comandos de agentes en workspaces aislados

```go
js.Subscribe("agent.cmd.execute", func(msg *nats.Msg) {
    var cmd AgentCommand
    json.Unmarshal(msg.Data, &cmd)
    
    // Crear workspace aislado
    workspace := createWorkspace(cmd.TaskID)
    
    // Ejecutar agente en K8s Job
    job := k8s.CreateJob(cmd.AgentType, workspace)
    
    // Publicar respuesta de inicio
    publishEvent("agent.response.started", cmd.TaskID, job.Name)
    
    msg.Ack()
}, nats.Durable("workspace-executor"), nats.DeliverGroup("workspace-workers"))
```

---

## 📊 Tabla Resumen de Consumers

| Servicio | Consumer Name | Stream | Subjects | Queue Group | Durability |
|----------|--------------|--------|----------|-------------|------------|
| **Context** | context-planning-events | PLANNING_EVENTS | `planning.story.transitioned` | context-workers | Ephemeral |
| **Context** | context-orchestration-events | ORCHESTRATOR_EVENTS | `orchestration.deliberation.completed` | context-workers | Ephemeral |
| **Orchestrator** | orchestrator-planning-events | PLANNING_EVENTS | `planning.task.created` | orchestrator-workers | Ephemeral |
| **Orchestrator** | orchestrator-context-updates | CONTEXT_EVENTS | `context.updated` | orchestrator-workers | Ephemeral |
| **Orchestrator** | orchestrator-agent-responses | AGENT_RESPONSES | `agent.response.>` | orchestrator-workers | Ephemeral |
| **Planning** | planning-context-events | CONTEXT_EVENTS | `context.milestone.reached` | planning-workers | Durable |
| **Planning** | planning-orchestration-events | ORCHESTRATOR_EVENTS | `orchestration.task.completed` | planning-workers | Durable |
| **Gateway** | gateway-all-events | ALL | `>` | gateway-sse-{pod} | Ephemeral |
| **Workspace** | workspace-agent-commands | AGENT_COMMANDS | `agent.cmd.execute` | workspace-workers | Durable |

---

## 🚀 Implementación por Fases

### **Phase 1: Core Event Bus** (Sprint N+1) ✅
- [x] NATS JetStream desplegado
- [x] Stream CONTEXT_EVENTS creado
- [x] Context Service consumers (ephemeral)
- [x] Orchestrator Service consumers (básicos)

### **Phase 2: Planning Integration** (Sprint N+2)
- [ ] Stream PLANNING_EVENTS
- [ ] Planning → Context events
- [ ] Context → Planning events
- [ ] FSM automation triggers

### **Phase 3: Agent Orchestration** (Sprint N+3)
- [ ] Stream AGENT_COMMANDS
- [ ] Stream AGENT_RESPONSES
- [ ] Orchestrator → Workspace commands
- [ ] Workspace → Agent Job creation
- [ ] Agent → Orchestrator responses

### **Phase 4: Real-time UI** (Sprint N+4)
- [ ] Gateway SSE endpoint
- [ ] Frontend EventSource integration
- [ ] Real-time story status updates
- [ ] Real-time context viewer

### **Phase 5: Event Sourcing** (Sprint N+5+)
- [ ] Durable consumers per pod
- [ ] Event replay capability
- [ ] Temporal queries
- [ ] Complete audit trail

---

## 🔧 Configuración NATS JetStream

### Crear Streams (CLI)

```bash
# Stream para Planning
nats stream add PLANNING_EVENTS \
  --subjects "planning.>" \
  --retention limits \
  --max-age 30d \
  --max-msgs 1000000 \
  --storage file

# Stream para Context
nats stream add CONTEXT_EVENTS \
  --subjects "context.>" \
  --retention limits \
  --max-age 7d \
  --max-msgs 100000 \
  --storage file

# Stream para Orchestrator
nats stream add ORCHESTRATOR_EVENTS \
  --subjects "orchestration.>" \
  --retention limits \
  --max-age 7d \
  --max-msgs 50000 \
  --storage file

# Stream para Agent Commands
nats stream add AGENT_COMMANDS \
  --subjects "agent.cmd.>" \
  --retention limits \
  --max-age 1h \
  --max-msgs 10000 \
  --storage file

# Stream para Agent Responses
nats stream add AGENT_RESPONSES \
  --subjects "agent.response.>" \
  --retention limits \
  --max-age 1h \
  --max-msgs 10000 \
  --storage file
```

---

## 📈 Monitoring & Observability

### Métricas Clave por Consumer

```prometheus
# Mensajes procesados
nats_consumer_delivered_total{consumer="context-planning-events"}

# Mensajes pendientes
nats_consumer_num_pending{consumer="context-planning-events"}

# Mensajes reentregados (indica problemas)
nats_consumer_num_redelivered{consumer="context-planning-events"}

# Lag del consumer
nats_consumer_lag{consumer="context-planning-events"}
```

### Alertas Recomendadas

```yaml
# Alertmanager rules
- alert: NATSConsumerLagHigh
  expr: nats_consumer_lag > 1000
  for: 5m
  annotations:
    summary: "Consumer {{ $labels.consumer }} tiene lag alto"
    
- alert: NATSConsumerRedeliveryHigh
  expr: rate(nats_consumer_num_redelivered[5m]) > 10
  for: 5m
  annotations:
    summary: "Consumer {{ $labels.consumer }} tiene reentregas altas"
```

---

## 🔐 Seguridad

### Autenticación NATS

```yaml
# nats-server.conf
authorization {
  users = [
    {
      user: "context-service"
      password: $CONTEXT_NATS_PASSWORD
      permissions: {
        publish: ["context.>"]
        subscribe: ["planning.>", "orchestration.>"]
      }
    },
    {
      user: "orchestrator-service"
      password: $ORCHESTRATOR_NATS_PASSWORD
      permissions: {
        publish: ["orchestration.>", "agent.cmd.>"]
        subscribe: ["planning.>", "context.>", "agent.response.>"]
      }
    }
  ]
}
```

---

## 📚 Referencias

- [NATS JetStream Documentation](https://docs.nats.io/nats-concepts/jetstream)
- [Event Sourcing Plan](./EVENT_SOURCING_PLAN.md)
- [Context Service Interactions](../../services/context/INTERACTIONS_ANALYSIS.md)
- [Orchestrator Service](../../services/orchestrator/README.md)

---

**Last Updated**: 2025-10-10  
**Owner**: Architecture Team  
**Status**: 📝 Design Document → Ready for Implementation

