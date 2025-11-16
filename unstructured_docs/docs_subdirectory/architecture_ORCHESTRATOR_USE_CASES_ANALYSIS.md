# Análisis Completo: Use Cases del Orchestrator

## 📊 Revisión de la Arquitectura Existente

### ✅ Componentes de Dominio Implementados

| Componente | Archivo | Estado | Descripción |
|-----------|---------|--------|-------------|
| **Agent** | `domain/agents/agent.py` | ✅ Interfaz | Base abstracta para agentes |
| **Role** | `domain/agents/role.py` | ✅ Completo | Dataclass con capabilities |
| **Task** | `domain/tasks/task.py` | ⚠️ Simplificado | Solo `{description, id, priority}` |
| **TaskConstraints** | `domain/tasks/task_constraints.py` | ✅ Completo | Rubrics y constraints |
| **DeliberationResult** | `domain/deliberation_result.py` | ✅ Completo | Proposal + checks + score |
| **Proposal** | `domain/deliberation_result.py` | ✅ Completo | Author + content |
| **CheckSuiteResult** | `domain/check_results/check_suite.py` | ✅ Completo | Lint, dryrun, policy |
| **Scoring** | `domain/check_results/services/scoring.py` | ✅ Completo | Evalúa proposals |
| **ArchitectSelector** | `domain/agents/services/architect_selector_service.py` | ✅ Completo | Selecciona winner |

---

## 🔍 Análisis Detallado de Componentes

### 1. **Agent Interface** (Abstracto)

```python
class Agent:
    def generate(self, task: str, constraints: TaskConstraints, diversity: bool) -> dict[str, Any]:
        raise NotImplementedError
    
    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        raise NotImplementedError
    
    def revise(self, content: str, feedback: str) -> str:
        raise NotImplementedError
```

**Métodos necesarios**:
- `generate()`: Genera propuesta inicial para una tarea
- `critique()`: Evalúa propuesta de otro agente
- `revise()`: Mejora propuesta basado en feedback

**Para implementar consumers necesitamos**: Crear implementación concreta (MockAgent o RealAgent)

---

### 2. **Task Domain Object** (⚠️ Simplificado)

```python
@dataclass(frozen=True)
class Task:
    description: str
    id: str | None = None
    priority: int = 0
```

**⚠️ PROBLEMA**: Muy simplificado para uso en consumers.

**Campos que FALTAN** (necesarios para consumers):
- `story_id: str` - ¿A qué story pertenece?
- `role: Role` - ¿Qué rol debe ejecutarla?
- `dependencies: list[str]` - ¿De qué otras tasks depende?
- `status: TaskStatus` - Estado actual
- `constraints: TaskConstraints` - Constraints específicos

**Solución**: Extender Task o crear TaskSpec más completo.

---

### 3. **TaskConstraints** (✅ Completo)

```python
@dataclass(frozen=True)
class TaskConstraints:
    rubric: dict[str, Any]              # Evaluación general
    architect_rubric: dict[str, Any]    # Criterios del architect
    cluster_spec: dict[str, Any] | None # Spec de ejecución
    additional_constraints: dict[str, Any] | None
```

**Métodos útiles**:
- `get_k_value()` → int para top-k selection
- `to_dict()` / `from_dict()` → Serialización

**✅ LISTO PARA USAR** en consumers

---

### 4. **DeliberationResult & Proposal** (✅ Completo)

```python
@dataclass(frozen=True)
class Proposal:
    author: Agent
    content: str

@dataclass(frozen=True)
class DeliberationResult:
    proposal: Proposal
    checks: CheckSuiteResult
    score: float
```

**Métodos útiles**:
- `to_dict()` / `from_dict()` → Para serializar en NATS events

**✅ LISTO PARA USAR** en consumers

---

### 5. **Use Cases Implementados**

#### **Deliberate Use Case** ✅

```python
class Deliberate:
    def __init__(
        self, 
        agents: list[Agent],      # Lista de agentes
        tooling: Scoring,         # Sistema de scoring
        rounds: int = 1           # Rondas de peer review
    ):
        self._agents = agents
        self._tooling = tooling
        self._rounds = rounds
    
    def execute(
        self, 
        task: str,                # Descripción de la tarea
        constraints: TaskConstraints
    ) -> list[DeliberationResult]:
        # 1. Generate initial proposals
        proposals = [
            Proposal(
                author=agent,
                content=agent.generate(task, constraints, diversity=True)["content"]
            )
            for agent in self._agents
        ]
        
        # 2. Peer review rounds
        for _ in range(self._rounds):
            for i, agent in enumerate(self._agents):
                peer_idx = (i + 1) % len(proposals)
                feedback = agent.critique(proposals[peer_idx].content, constraints.get_rubric())
                revised = agent.revise(proposals[peer_idx].content, feedback)
                proposals[peer_idx] = Proposal(
                    author=proposals[peer_idx].author,
                    content=revised
                )
        
        # 3. Score and rank
        results = []
        for proposal in proposals:
            check_suite = self._tooling.run_check_suite(proposal.content)
            score = self._tooling.score_checks(check_suite)
            results.append(DeliberationResult(
                proposal=proposal,
                checks=check_suite,
                score=score
            ))
        
        return sorted(results, key=lambda x: x.score, reverse=True)
```

**Input**: 
- `task: str` - Descripción textual
- `constraints: TaskConstraints` - Rubric y constraints

**Output**:
- `list[DeliberationResult]` - Ordenados por score (mayor primero)

**✅ COMPLETO Y LISTO**

---

#### **Orchestrate Use Case** ✅

```python
class Orchestrate:
    def __init__(
        self,
        config: SystemConfig,
        councils: dict[str, Deliberate],  # role.name → Deliberate instance
        architect: ArchitectSelectorService
    ):
        self._config = config
        self._councils = councils
        self._architect = architect
    
    def execute(
        self,
        role: Role,        # Objeto Role (no string)
        task: Task,        # Objeto Task (no string)
        constraints: TaskConstraints
    ) -> dict[str, Any]:
        # 1. Get council for role
        council = self._councils[role.name]
        
        # 2. Execute deliberation
        ranked = council.execute(task.description, constraints)
        
        # 3. Architect selects winner
        return self._architect.choose(ranked, constraints)
```

**Input**:
- `role: Role` - Objeto Role (tiene `.name`)
- `task: Task` - Objeto Task (tiene `.description`)
- `constraints: TaskConstraints`

**Output**:
```python
{
    "winner": DeliberationResult,
    "candidates": list[DeliberationResult]  # Top-k minus winner
}
```

**✅ COMPLETO Y LISTO**

---

## 🚧 Componentes que FALTAN para Consumers

### 1. ❌ **Mock Agent Implementation**

```python
# src/swe_ai_fleet/orchestrator/domain/agents/mock_agent.py

from typing import Any
from .agent import Agent
from ..tasks.task_constraints import TaskConstraints


class MockAgent(Agent):
    """Simple mock agent for testing deliberation flow."""
    
    def __init__(self, agent_id: str, role: str):
        self.agent_id = agent_id
        self.role = role
    
    def generate(
        self, 
        task: str, 
        constraints: TaskConstraints, 
        diversity: bool
    ) -> dict[str, Any]:
        """Generate a mock proposal."""
        return {
            "content": f"Mock solution for '{task}' by {self.agent_id}\n"
                      f"Role: {self.role}\n"
                      f"Diversity: {diversity}\n"
                      f"Rubric requirements: {list(constraints.rubric.keys())}"
        }
    
    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        """Generate mock feedback."""
        return f"Mock feedback from {self.agent_id}: Consider improving based on {list(rubric.keys())}"
    
    def revise(self, content: str, feedback: str) -> str:
        """Apply mock revision."""
        return f"{content}\n\n[REVISED based on: {feedback}]"
    
    def __repr__(self):
        return f"MockAgent(id={self.agent_id}, role={self.role})"
```

---

### 2. ❌ **InMemoryTaskQueue** (Para Fase 1)

```python
# src/swe_ai_fleet/orchestrator/adapters/in_memory_task_queue.py

import asyncio
from typing import Optional
from ..domain.tasks.task import Task


class InMemoryTaskQueue:
    """Simple in-memory task queue for development/testing."""
    
    def __init__(self):
        self._queue: list[tuple[int, Task]] = []  # (priority, task)
        self._status: dict[str, str] = {}
        self._lock = asyncio.Lock()
    
    async def enqueue(self, task: Task, priority: int = 0):
        """Add task to queue with priority (higher = more important)."""
        async with self._lock:
            self._queue.append((priority, task))
            # Sort by priority (higher first), then by order added
            self._queue.sort(key=lambda x: (-x[0], len(self._queue)))
            
            if task.id:
                self._status[task.id] = "QUEUED"
    
    async def dequeue(self) -> Optional[Task]:
        """Get next highest-priority task."""
        async with self._lock:
            if not self._queue:
                return None
            
            priority, task = self._queue.pop(0)
            
            if task.id:
                self._status[task.id] = "IN_PROGRESS"
            
            return task
    
    async def mark_completed(self, task_id: str):
        """Mark task as completed."""
        async with self._lock:
            self._status[task_id] = "COMPLETED"
    
    async def mark_failed(self, task_id: str, error: str):
        """Mark task as failed."""
        async with self._lock:
            self._status[task_id] = f"FAILED: {error}"
    
    async def get_status(self, task_id: str) -> str:
        """Get status of a task."""
        async with self._lock:
            return self._status.get(task_id, "UNKNOWN")
    
    async def size(self) -> int:
        """Get queue size."""
        async with self._lock:
            return len(self._queue)
```

---

### 3. ❌ **Extended Task for Consumers**

El Task actual es demasiado simple. Necesitamos extenderlo:

```python
# Opción A: Extender Task existente
@dataclass(frozen=True)
class Task:
    description: str
    id: str | None = None
    priority: int = 0
    
    # NUEVOS CAMPOS NECESARIOS:
    story_id: str | None = None
    role: str | None = None  # Role name
    dependencies: tuple[str, ...] = ()  # Task IDs que deben completarse primero
    metadata: dict[str, Any] | None = None
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        return cls(
            description=data["description"],
            id=data.get("id"),
            priority=data.get("priority", 0),
            story_id=data.get("story_id"),
            role=data.get("role"),
            dependencies=tuple(data.get("dependencies", [])),
            metadata=data.get("metadata"),
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "id": self.id,
            "priority": self.priority,
            "story_id": self.story_id,
            "role": self.role,
            "dependencies": list(self.dependencies),
            "metadata": self.metadata,
        }
```

---

## 🎯 Plan de Implementación Corregido

### **Fase 1: Mock Implementation** (COMENZAR AQUÍ)

#### Paso 1: Crear MockAgent ✅

```bash
# Crear archivo
src/swe_ai_fleet/orchestrator/domain/agents/mock_agent.py
```

#### Paso 2: Crear InMemoryTaskQueue ✅

```bash
# Crear archivo
src/swe_ai_fleet/orchestrator/adapters/in_memory_task_queue.py
```

#### Paso 3: Extender Task (si es necesario) ⚠️

**Opción A**: Modificar `domain/tasks/task.py` (breaking change)
**Opción B**: Crear `TaskRequest` DTO separado para consumers
**Opción C**: Usar metadata dict para campos adicionales

**Recomendación**: **Opción C** por ahora (no breaking)

#### Paso 4: Inicializar Councils en server.py ✅

```python
# En server.py
from swe_ai_fleet.orchestrator.domain.agents.mock_agent import MockAgent
from swe_ai_fleet.orchestrator.usecases import Deliberate, Orchestrate

def _initialize_councils(config: SystemConfig) -> dict[str, Deliberate]:
    """Initialize councils with mock agents."""
    councils = {}
    scoring = Scoring()
    
    for role_config in config.roles:
        # Create mock agents for this role
        agents = [
            MockAgent(
                agent_id=f"agent-{role_config.name.lower()}-{i}",
                role=role_config.name
            )
            for i in range(role_config.replicas)
        ]
        
        # Create Deliberate use case for this role
        councils[role_config.name] = Deliberate(
            agents=agents,
            tooling=scoring,
            rounds=1  # Single round for now
        )
    
    return councils
```

#### Paso 5: Integrar en Consumers ✅

**OrchestratorPlanningConsumer**:
```python
# En __init__
self.orchestrate_usecase = orchestrate  # Inyectado
self.task_queue = task_queue  # Inyectado

# En _handle_plan_approved
async def _handle_plan_approved(self, msg):
    event = json.loads(msg.data.decode())
    
    # Mock: crear una task de ejemplo
    task = Task(
        description=f"Implement features for plan {event.get('plan_id')}",
        id=f"TASK-{event.get('plan_id')}-001",
        priority=1
    )
    
    # Enqueue
    await self.task_queue.enqueue(task, priority=1)
    
    # Dequeue immediately for demo
    next_task = await self.task_queue.dequeue()
    if next_task:
        # Execute orchestration
        role = Role.from_string("DEV")
        constraints = TaskConstraints(
            rubric={"quality": "high", "tests": "required"},
            architect_rubric={"k": 3, "criteria": "best overall"}
        )
        
        result = await asyncio.to_thread(
            self.orchestrate_usecase.execute,
            role=role,
            task=next_task,
            constraints=constraints
        )
        
        # Publish task dispatched
        winner = result["winner"]
        await self.publisher.publish(
            "orchestration.task.dispatched",
            json.dumps({
                "story_id": event.get("story_id"),
                "task_id": next_task.id,
                "agent_id": winner.proposal.author.agent_id,
                "role": role.name,
            }).encode()
        )
    
    await msg.ack()
```

**OrchestratorAgentResponseConsumer**:
```python
# En __init__
self.deliberate_usecase = None  # Will be set per-role

# En _handle_agent_completed
async def _handle_agent_completed(self, msg):
    response = json.loads(msg.data.decode())
    
    if response.get("requires_deliberation"):
        # Get appropriate council
        role_name = response.get("role", "DEV")
        council = self.orchestrator.councils.get(role_name)
        
        if council:
            # Execute deliberation
            task_desc = response.get("task_description")
            constraints = TaskConstraints.from_dict(response.get("constraints", {}))
            
            results = await asyncio.to_thread(
                council.execute,
                task=task_desc,
                constraints=constraints
            )
            
            # Winner is first (highest score)
            winner = results[0]
            
            # Extract decisions (mock for now)
            decisions = [{
                "id": f"DEC-{response.get('task_id')}-001",
                "type": "TECHNICAL",
                "rationale": f"Selected proposal with score {winner.score}",
                "affected_subtask": response.get("task_id"),
            }]
            
            # Publish deliberation completed
            await self.publisher.publish(
                "orchestration.deliberation.completed",
                json.dumps({
                    "story_id": response.get("story_id"),
                    "task_id": response.get("task_id"),
                    "decisions": decisions,
                    "timestamp": time.time(),
                }).encode()
            )
    
    await msg.ack()
```

---

## 📊 Resumen de Estado

| Componente | Estado | Acción Necesaria |
|-----------|--------|------------------|
| **Deliberate Use Case** | ✅ Completo | Ninguna - usar as-is |
| **Orchestrate Use Case** | ✅ Completo | Ninguna - usar as-is |
| **Agent Interface** | ✅ Completo | Implementar MockAgent |
| **Task** | ⚠️ Simplificado | Usar metadata dict |
| **TaskConstraints** | ✅ Completo | Ninguna |
| **DeliberationResult** | ✅ Completo | Ninguna |
| **MockAgent** | ❌ No existe | ✅ CREAR |
| **InMemoryTaskQueue** | ❌ No existe | ✅ CREAR |
| **Councils Initialization** | ❌ Vacío | ✅ IMPLEMENTAR en server.py |
| **Consumer Integration** | ❌ Solo logging | ✅ INTEGRAR use cases |

---

## 🎯 Siguiente Paso INMEDIATO

1. ✅ Crear `MockAgent`
2. ✅ Crear `InMemoryTaskQueue`  
3. ✅ Inicializar councils en `server.py`
4. ✅ Integrar en `planning_consumer.py`
5. ✅ Integrar en `agent_response_consumer.py`

¿Empezamos con la implementación?

