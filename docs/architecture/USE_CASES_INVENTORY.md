# Inventario de Casos de Uso Implementados

## 📊 Context Service Use Cases

### ✅ Implementados y Listos

| Use Case | Archivo | Propósito | Payload | Uso en Consumers |
|----------|---------|-----------|---------|------------------|
| **ProjectCaseUseCase** | `project_case.py` | Crear/actualizar casos | `{case_id, name?}` | ✅ Usar en `planning_consumer` para story transitions |
| **ProjectDecisionUseCase** | `project_decision.py` | Registrar decisiones | `{node_id, kind?, summary?, sub_id?}` | ✅ **YA USADO** en `orchestration_consumer` |
| **ProjectSubtaskUseCase** | `project_subtask.py` | Crear subtasks con relación a plan | `{plan_id, sub_id, title?, type?}` | ⚠️ Usar cuando Planning cree subtasks |
| **ProjectPlanVersionUseCase** | `project_plan_version.py` | Versionar planes | `{case_id, plan_id, version}` | ⚠️ Usar cuando Planning apruebe plan |
| **UpdateSubtaskStatusUseCase** | `update_subtask_status.py` | Actualizar status de subtask | `{sub_id, status}` | ✅ **YA USADO** en `orchestration_consumer` |
| **ProjectorCoordinator** | `projector_coordinator.py` | Coordina todos los use cases | Event dispatcher | ✅ Podríamos usarlo como facade |

### 🎯 ProjectorCoordinator - Event Router

Este es un **coordinador central** que ya mapea event types a use cases:

```python
handlers = {
    "case.created": ProjectCaseUseCase.execute,
    "plan.versioned": ProjectPlanVersionUseCase.execute,
    "subtask.created": ProjectSubtaskUseCase.execute,
    "subtask.status_changed": UpdateSubtaskStatusUseCase.execute,
    "decision.made": ProjectDecisionUseCase.execute,
}
```

**💡 Podríamos usar este coordinator en los consumers** en lugar de llamar use cases individuales.

---

## 📊 Orchestrator Service Use Cases

### ✅ Implementados y Listos

| Use Case | Archivo | Propósito | Parámetros | Uso en Consumers |
|----------|---------|-----------|------------|------------------|
| **Deliberate** | `peer_deliberation_usecase.py` | Deliberación entre agentes | `(task, constraints)` | ⚠️ Debería usarse en `agent_response_consumer` |
| **Orchestrate** | `orchestrate_usecase.py` | Workflow completo de orchestración | `(role, task, constraints)` | ⚠️ Debería usarse en `planning_consumer` |

### 📋 Detalles de Use Cases

#### **Deliberate Use Case**
```python
class Deliberate:
    def __init__(self, agents: list[Agent], tooling: Scoring, rounds: int = 1):
        """
        Args:
            agents: Lista de agentes que participan
            tooling: Scoring para evaluar propuestas
            rounds: Número de rondas de peer review
        """
    
    def execute(self, task: str, constraints: TaskConstraints) -> list[DeliberationResult]:
        """
        Returns: Lista ordenada por score (highest first)
        """
```

**Proceso**:
1. Cada agente genera propuesta inicial
2. Peer review rounds: cada agente critica la propuesta del siguiente
3. Cada agente revisa su propuesta basado en feedback
4. Scoring evalúa todas las propuestas
5. Retorna lista ordenada por score

#### **Orchestrate Use Case**
```python
class Orchestrate:
    def __init__(self, config: SystemConfig, councils: dict[str, Deliberate], architect: ArchitectSelectorService):
        """
        Args:
            config: System configuration
            councils: Mapa de role -> Deliberate use case
            architect: Selector del mejor resultado
        """
    
    def execute(self, role: Role, task: Task, constraints: TaskConstraints) -> dict[str, Any]:
        """
        Returns: {winner: DeliberationResult, candidates: list[DeliberationResult]}
        """
```

**Proceso**:
1. Selecciona council basado en role
2. Ejecuta deliberación (llama a `Deliberate.execute`)
3. Architect selecciona el mejor resultado
4. Retorna winner + candidates

---

## 🔄 Cómo los Consumers Deberían Usar los Use Cases

### Context Service Consumers

#### 1. **PlanningEventsConsumer** → ProjectCaseUseCase

```python
# ❌ ANTES (directo a persistencia)
await self.graph.upsert_entity("PhaseTransition", id, props)

# ✅ AHORA (usar use case)
from swe_ai_fleet.context.usecases.projector_coordinator import ProjectorCoordinator

self.coordinator = ProjectorCoordinator(writer=graph_command)

# En el handler
event_type = "case.phase_transitioned"  # Nuevo tipo
payload = {
    "case_id": story_id,
    "from_phase": from_phase,
    "to_phase": to_phase,
}
self.coordinator.handle(event_type, payload)
```

**Alternativa**: Extender `ProjectCaseUseCase` con método `handle_phase_transition()`.

#### 2. **OrchestrationEventsConsumer** → ProjectDecisionUseCase ✅

**YA IMPLEMENTADO** en la refactorización actual:

```python
# ✅ CORRECTO - Ya lo hicimos
self.project_decision = ProjectDecisionUseCase(writer=graph_command)

payload = {
    "node_id": decision_id,
    "kind": decision.get("type"),
    "summary": decision.get("rationale"),
    "sub_id": decision.get("affected_subtask"),
}

await asyncio.to_thread(
    self.project_decision.execute,
    payload
)
```

---

### Orchestrator Service Consumers

#### 1. **OrchestratorAgentResponseConsumer** → Deliberate

```python
# ❌ ANTES (solo logging)
logger.info(f"Agent completed: {task_id}")

# ✅ AHORA (trigger deliberation si es necesario)
from swe_ai_fleet.orchestrator.usecases.peer_deliberation_usecase import Deliberate

# En __init__
self.deliberation_usecase = deliberate_instance  # Inyectado por server

# En _handle_agent_completed
if response.get("requires_deliberation"):
    # Recopilar propuestas de múltiples agentes
    proposals = await self._collect_proposals(task_id, role)
    
    # Ejecutar deliberación
    results = await asyncio.to_thread(
        self.deliberation_usecase.execute,
        task=response.get("task_description"),
        constraints=response.get("constraints"),
    )
    
    # Publicar resultado
    winner = results[0]  # El primero es el de mayor score
    decisions = self._extract_decisions(winner)
    
    await self.publisher.publish_deliberation_completed(
        story_id=response.get("story_id"),
        task_id=task_id,
        decisions=decisions,
    )
```

#### 2. **OrchestratorPlanningConsumer** → Orchestrate

```python
# ❌ ANTES (solo logging)
logger.info(f"Plan approved: {plan_id}")

# ✅ AHORA (derivar subtasks y orchestrate)
from swe_ai_fleet.orchestrator.usecases.orchestrate_usecase import Orchestrate

# En __init__
self.orchestrate_usecase = orchestrate_instance  # Inyectado por server

# En _handle_plan_approved
# 1. Derivar subtasks (aún no implementado)
subtasks = await self._derive_subtasks(plan_id, roles)

# 2. Para cada subtask, trigger orchestration
for subtask in subtasks:
    result = await asyncio.to_thread(
        self.orchestrate_usecase.execute,
        role=subtask.role,
        task=subtask.description,
        constraints=subtask.constraints,
    )
    
    # 3. Publish task dispatched
    await self.publisher.publish_task_dispatched(
        story_id=story_id,
        task_id=subtask.id,
        agent_id=result["winner"].proposal.author.agent_id,
        role=subtask.role,
    )
```

---

## 🚧 Componentes Faltantes

### Context Service
- ❌ **`ProjectCaseUseCase.handle_phase_transition()`** - Método específico para transiciones
  - O alternativamente: nuevo event type en `ProjectorCoordinator`
  
### Orchestrator Service
- ❌ **`derive_subtasks()`** - Analizar plan y extraer subtasks atómicos
  - Entrada: `{story_id, plan_id, roles}`
  - Salida: `list[Task]`
  - Lógica: Parsear plan, identificar tareas, asignar roles, crear dependencias

- ❌ **TaskQueue** - Cola de tareas con Redis/Valkey
  - `enqueue(task)` - Agregar tarea
  - `dequeue()` - Obtener siguiente tarea
  - `mark_completed(task_id)` - Marcar como completada
  - `get_status(task_id)` - Status de tarea

---

## 📐 Patrón de Uso Recomendado

### ✅ Arquitectura Limpia

```
Event (NATS) 
  ↓
Consumer (async handler)
  - Parsea evento
  - Valida schema
  - Convierte a payload del dominio
  ↓
Use Case (domain logic)
  - Valida reglas de negocio
  - Coordina entities/services
  - Persiste cambios
  ↓
Domain Entity
  - Valida invariantes
  - Aplica lógica de dominio
  ↓
Port/Adapter
  - Traduce a modelo de persistencia
  - Ejecuta queries/commands
  ↓
Infraestructura (Neo4j, Valkey, NATS)
```

### ✅ Inyección de Dependencias

```python
# En server.py
graph_command = Neo4jCommandStore(cfg=...)
project_decision = ProjectDecisionUseCase(writer=graph_command)

# Pasar a consumer
orchestration_consumer = OrchestrationEventsConsumer(
    nc=nats_handler.nc,
    js=nats_handler.js,
    project_decision_usecase=project_decision,  # ← Inyectado
    nats_publisher=nats_handler,
)
```

---

## 🎯 Próximos Pasos

### Fase 2A: Refactorizar Consumers Existentes ✅ EN PROGRESO
- [x] Context - OrchestrationEventsConsumer → Usa ProjectDecisionUseCase
- [x] Context - OrchestrationEventsConsumer → Usa UpdateSubtaskStatusUseCase
- [x] Context - PlanningEventsConsumer → Mejora cache invalidation
- [ ] Context - Considerar usar ProjectorCoordinator como facade

### Fase 2B: Integrar Orchestrator Consumers
- [ ] Orchestrator - AgentResponseConsumer → Llamar Deliberate
- [ ] Orchestrator - PlanningConsumer → Llamar Orchestrate
- [ ] Orchestrator - Implementar derive_subtasks()

### Fase 3: Componentes Nuevos
- [ ] TaskQueue con Redis/Valkey
- [ ] Context - handle_phase_transition() en ProjectCaseUseCase

---

## 📊 Matriz de Cobertura

| Consumer | Evento | Use Case Actual | Use Case Ideal | Estado |
|----------|--------|----------------|----------------|--------|
| Context - Planning | story.transitioned | Ninguno | ProjectCaseUseCase | 🔴 TODO |
| Context - Planning | plan.approved | Ninguno | ProjectPlanVersionUseCase | 🔴 TODO |
| Context - Orchestration | deliberation.completed | ✅ ProjectDecisionUseCase | ✅ ProjectDecisionUseCase | 🟢 DONE |
| Context - Orchestration | task.dispatched | ✅ UpdateSubtaskStatusUseCase | ✅ UpdateSubtaskStatusUseCase | 🟢 DONE |
| Orchestrator - Planning | story.transitioned | Ninguno | N/A (monitoring) | 🟢 OK |
| Orchestrator - Planning | plan.approved | Ninguno | Orchestrate | 🔴 TODO |
| Orchestrator - Context | context.updated | Ninguno | N/A (monitoring) | 🟢 OK |
| Orchestrator - Agents | agent.completed | Ninguno | Deliberate | 🔴 TODO |
| Orchestrator - Agents | agent.failed | Ninguno | N/A (error handling) | 🟢 OK |

**Leyenda**:
- 🟢 DONE/OK - Completado o no requiere acción
- 🟡 PARTIAL - Parcialmente implementado
- 🔴 TODO - Pendiente de implementar

