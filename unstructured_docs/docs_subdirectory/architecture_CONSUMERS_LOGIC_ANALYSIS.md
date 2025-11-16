# Análisis de Lógica de Consumers NATS

## 🎯 Estado Actual vs Estado Ideal

Los consumers implementados actualmente están **funcionando pero incompletos**. Están escuchando eventos correctamente, pero **no están llamando a los casos de uso del dominio**, sino haciendo operaciones directas de persistencia.

---

## 📊 Context Service Consumers

### 1. **PlanningEventsConsumer** (`services/context/consumers/planning_consumer.py`)

#### ✅ **Lo que hace actualmente**:

```python
async def _handle_story_transitioned(msg):
    """Cuando Planning Service publica planning.story.transitioned"""
    # ✅ Parsea el evento
    story_id = event.get("story_id")
    from_phase = event.get("from_phase")
    to_phase = event.get("to_phase")
    
    # ⚠️ PROBLEMA: Llamada directa a persistencia
    await asyncio.to_thread(
        self.graph.upsert_entity,
        entity_type="PhaseTransition",
        entity_id=f"{story_id}:{timestamp}",
        properties={...}
    )
```

#### ❌ **Lo que DEBERÍA hacer**:

```python
async def _handle_story_transitioned(msg):
    """Cuando Planning Service publica planning.story.transitioned"""
    event = json.loads(msg.data.decode())
    
    # ✅ CORRECTO: Llamar al caso de uso del dominio
    payload = {
        "case_id": event.get("story_id"),
        "from_phase": event.get("from_phase"),
        "to_phase": event.get("to_phase"),
        "timestamp": event.get("timestamp"),
    }
    
    # Usar ProjectCaseUseCase para registrar transición
    await asyncio.to_thread(
        self.project_case_usecase.handle_phase_transition,
        payload
    )
    
    # Invalidar cache de contexto para forzar regeneración
    await self.cache.delete_pattern(f"context:{story_id}:*")
```

#### 📋 **Casos de Uso que debería llamar**:

1. **`ProjectCaseUseCase`** (aún no existe método `handle_phase_transition`)
   - Para registrar transiciones de fase
   - Actualizar estado del caso en Neo4j
   
2. **Cache invalidation** (ya lo hace parcialmente)
   - Invalidar contexto en Valkey
   - Forzar regeneración en próximo `GetContext`

---

### 2. **OrchestrationEventsConsumer** (`services/context/consumers/orchestration_consumer.py`)

#### ✅ **Lo que hace actualmente**:

```python
async def _handle_deliberation_completed(msg):
    """Cuando Orchestrator publica orchestration.deliberation.completed"""
    decisions = event.get("decisions", [])
    
    # ⚠️ PROBLEMA: Loop manual + llamadas directas
    for decision in decisions:
        await asyncio.to_thread(
            self.graph.upsert_entity,
            entity_type="Decision",
            entity_id=decision_id,
            properties={...}
        )
```

#### ✅ **Lo que DEBERÍA hacer**:

```python
async def _handle_deliberation_completed(msg):
    """Cuando Orchestrator publica orchestration.deliberation.completed"""
    event = json.loads(msg.data.decode())
    decisions = event.get("decisions", [])
    
    # ✅ CORRECTO: Usar ProjectDecisionUseCase
    for decision in decisions:
        payload = {
            "node_id": decision.get("id"),
            "kind": decision.get("type"),
            "summary": decision.get("rationale"),
            "sub_id": decision.get("affected_subtask"),  # si aplica
        }
        
        # Usar caso de uso del dominio
        await asyncio.to_thread(
            self.project_decision_usecase.execute,
            payload
        )
    
    # Publicar context.updated event
    await self.publisher.publish_context_updated(
        story_id=event.get("story_id"),
        version=event.get("timestamp"),
    )
```

#### 📋 **Casos de Uso que debería llamar**:

1. **`ProjectDecisionUseCase.execute(payload)`** ✅ Ya existe
   - Persiste decisión en Neo4j
   - Crea relación AFFECTS con subtask si aplica
   
2. **`ContextNATSHandler.publish_context_updated()`** ✅ Ya existe
   - Notifica a otros servicios del cambio

---

## 📊 Orchestrator Service Consumers

### 3. **OrchestratorPlanningConsumer** (`services/orchestrator/consumers/planning_consumer.py`)

#### ⚠️ **Lo que hace actualmente**:

```python
async def _handle_plan_approved(msg):
    """Cuando Planning publica planning.plan.approved"""
    # ❌ PROBLEMA: Solo logging, no hace nada
    logger.info(f"Plan approved: {plan_id}")
    # TODO: Implement task derivation
```

#### ✅ **Lo que DEBERÍA hacer**:

```python
async def _handle_plan_approved(msg):
    """Cuando Planning publica planning.plan.approved"""
    event = json.loads(msg.data.decode())
    
    # ✅ CORRECTO: Llamar DeriveSubtasks
    # Esto debería existir como método en OrchestrationUseCase
    subtasks = await self.orchestration_usecase.derive_subtasks(
        story_id=event.get("story_id"),
        plan_id=event.get("plan_id"),
        roles=event.get("roles"),
    )
    
    # Inicializar task queue
    for subtask in subtasks:
        await self.task_queue.enqueue(subtask)
    
    # Publicar evento
    await self.publisher.publish(
        "orchestration.plan.approved",
        json.dumps({
            "plan_id": plan_id,
            "subtasks_count": len(subtasks),
        }).encode()
    )
```

#### 📋 **Casos de Uso que debería llamar**:

1. **`OrchestrationUseCase.derive_subtasks()`** ❌ No existe aún
   - Analizar plan y extraer subtasks
   - Asignar roles y dependencias
   - Inicializar cola de tareas

2. **`TaskQueue.enqueue()`** ❌ No existe aún
   - Agregar tareas a la cola de ejecución

---

### 4. **OrchestratorAgentResponseConsumer** (`services/orchestrator/consumers/agent_response_consumer.py`)

#### ⚠️ **Lo que hace actualmente**:

```python
async def _handle_agent_completed(msg):
    """Cuando un agente completa una tarea"""
    # ❌ PROBLEMA: Solo logging
    logger.info(f"Agent completed: {task_id}")
    # TODO: Implement completion handling
```

#### ✅ **Lo que DEBERÍA hacer**:

```python
async def _handle_agent_completed(msg):
    """Cuando un agente completa una tarea"""
    response = json.loads(msg.data.decode())
    
    # ✅ Si el task requiere deliberación, trigger it
    if response.get("requires_deliberation"):
        # Llamar PeerDeliberationUseCase
        result = await self.deliberation_usecase.execute(
            task_id=response.get("task_id"),
            role=response.get("role"),
            proposals=[response.get("output")],
        )
        
        # Publicar resultado de deliberación
        await self.publisher.publish_deliberation_completed(
            story_id=response.get("story_id"),
            task_id=response.get("task_id"),
            decisions=result.get("decisions"),
        )
    
    # Marcar task como completado
    await self.task_queue.mark_completed(response.get("task_id"))
    
    # Dispatch next task
    next_task = await self.task_queue.get_next()
    if next_task:
        await self.dispatch_usecase.execute(next_task)
```

#### 📋 **Casos de Uso que debería llamar**:

1. **`PeerDeliberationUseCase.execute()`** ✅ Ya existe
   - Coordinar revisión entre múltiples agentes
   - Scoring y selección del mejor resultado

2. **`DispatchUseCase.execute()`** ✅ Ya existe
   - Asignar tarea al siguiente agente disponible

3. **`TaskQueue` operations** ❌ No existe aún
   - `mark_completed()`, `get_next()`

---

## 🏗️ **Componentes Faltantes**

### Context Service:
1. ✅ **`ProjectDecisionUseCase`** - Ya existe
2. ✅ **`UpdateSubtaskStatusUseCase`** - Ya existe
3. ❌ **`ProjectCaseUseCase.handle_phase_transition()`** - Falta método
4. ⚠️ **Cache invalidation logic** - Parcialmente implementado

### Orchestrator Service:
1. ✅ **`PeerDeliberationUseCase`** - Ya existe
2. ✅ **`DispatchUseCase`** - Ya existe  
3. ❌ **`OrchestrationUseCase.derive_subtasks()`** - No existe
4. ❌ **`TaskQueue`** - No existe (necesita Redis/Valkey backend)
5. ❌ **Task state management** - No existe

---

## 🚀 **Plan de Acción**

### Fase 1: Refactorizar Consumers Existentes ✅ AHORA
1. **Context Service**: 
   - Integrar `ProjectDecisionUseCase` en `OrchestrationEventsConsumer`
   - Implementar cache invalidation completa en `PlanningEventsConsumer`

2. **Orchestrator Service**:
   - Mantener logging por ahora (sin casos de uso listos)
   - Documentar qué casos de uso necesitamos

### Fase 2: Implementar Componentes Faltantes
1. **TaskQueue** (Redis/Valkey backend)
2. **OrchestrationUseCase.derive_subtasks()**
3. **ProjectCaseUseCase.handle_phase_transition()**

### Fase 3: Integración Completa
1. Conectar todos los consumers con sus casos de uso
2. Tests de integración end-to-end
3. Monitoreo de event lag

---

## 📐 **Arquitectura Correcta: Event → Consumer → UseCase → Domain**

```
┌─────────────────┐
│  NATS Event     │
│  (JSON payload) │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Consumer       │ ← Parsea evento, valida schema
│  (async handler)│
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Use Case       │ ← Lógica de negocio, orquestación
│  (domain logic) │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Domain Entity  │ ← Validaciones, reglas de negocio
│  + Port/Adapter │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Persistence    │ ← Neo4j, Valkey, etc.
│  (Adapter)      │
└─────────────────┘
```

### ❌ **Mal** (actual):
```python
# Consumer llama directamente a persistencia
await self.graph.upsert_entity("Decision", id, props)
```

### ✅ **Bien** (debería ser):
```python
# Consumer llama a Use Case, que usa Domain Entity
await self.project_decision_usecase.execute(payload)
```

---

## 💡 **Beneficios de la Arquitectura Correcta**

1. **Testeable**: Los use cases se pueden testear sin NATS
2. **Reutilizable**: Los use cases se pueden llamar desde gRPC, CLI, consumers
3. **Validaciones**: El dominio valida antes de persistir
4. **Transacciones**: Los use cases manejan atomicidad
5. **Eventos**: Los use cases pueden emitir eventos de dominio
6. **Auditabilidad**: Los use cases son el punto de instrumentación

---

## 🎯 **Resumen Ejecutivo**

| Consumer | Estado | Casos de Uso Llamados | Casos de Uso Necesarios |
|----------|--------|----------------------|-------------------------|
| Context - Planning | 🟡 Parcial | Ninguno (persistencia directa) | `ProjectCaseUseCase` |
| Context - Orchestration | 🟡 Parcial | Ninguno (persistencia directa) | `ProjectDecisionUseCase` ✅ |
| Orchestrator - Planning | 🔴 TODO | Ninguno (solo logging) | `derive_subtasks()` ❌ |
| Orchestrator - Context | 🔴 TODO | Ninguno (solo logging) | N/A (solo monitoring) |
| Orchestrator - Agents | 🔴 TODO | Ninguno (solo logging) | `Deliberate`, `Dispatch` ✅ |

**Leyenda**:
- ✅ Ya existe y está listo
- ❌ No existe, hay que implementarlo
- 🟢 Completo
- 🟡 Funciona pero incompleto
- 🔴 Solo estructura, sin lógica


