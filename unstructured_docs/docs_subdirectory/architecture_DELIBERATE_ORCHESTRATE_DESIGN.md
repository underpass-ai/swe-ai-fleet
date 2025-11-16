# Diseño de Integración: Deliberate & Orchestrate

## 🎯 Objetivo

Integrar los casos de uso **Deliberate** y **Orchestrate** en los consumers del Orchestrator Service para crear un flujo completo de ejecución de tareas con multi-agent deliberation.

---

## 📐 Arquitectura Actual de Use Cases

### 1. **Deliberate** - Deliberación Entre Pares

```python
class Deliberate:
    def __init__(
        self, 
        agents: list[Agent],      # Agentes que participan
        tooling: Scoring,         # Sistema de scoring
        rounds: int = 1           # Rondas de peer review
    ):
        pass
    
    def execute(
        self, 
        task: str,                # Descripción de la tarea
        constraints: TaskConstraints  # Rubric y restricciones
    ) -> list[DeliberationResult]:  # Ordenados por score (alto → bajo)
        """
        Proceso:
        1. Cada agente genera propuesta inicial
        2. Peer review: cada agente critica la propuesta del siguiente
        3. Revisión: cada agente mejora su propuesta con feedback
        4. Scoring: evalúa todas las propuestas
        5. Retorna lista ordenada por score
        """
```

**Entrada**:
- `task`: Descripción textual de lo que hay que hacer
- `constraints`: Rubric para evaluación, requirements, timeouts

**Salida**:
```python
DeliberationResult:
  - proposal: Proposal (author: Agent, content: str)
  - checks: CheckSuite (policy, lint, dryrun)
  - score: float
  - rank: int
```

---

### 2. **Orchestrate** - Workflow Completo

```python
class Orchestrate:
    def __init__(
        self,
        config: SystemConfig,
        councils: dict[str, Deliberate],  # role → Deliberate instance
        architect: ArchitectSelectorService  # Selector final
    ):
        pass
    
    def execute(
        self,
        role: Role,               # Rol que maneja la tarea
        task: Task,               # Objeto Task del dominio
        constraints: TaskConstraints
    ) -> dict[str, Any]:
        """
        Proceso:
        1. Selecciona council basado en role
        2. Ejecuta deliberación (llama Deliberate.execute)
        3. Architect selecciona el mejor de los mejores
        4. Retorna {winner: DeliberationResult, candidates: list}
        """
```

**Entrada**:
- `role`: Role enum (DEV, QA, ARCHITECT, etc.)
- `task`: Task object con descripción, constraints, metadata
- `constraints`: TaskConstraints con rubrics

**Salida**:
```python
{
    "winner": DeliberationResult,      # El elegido por architect
    "candidates": list[DeliberationResult]  # Otros top-k
}
```

---

## 🔄 Flujo de Datos Completo: De Planning a Execution

### Fase 1: Plan Approved → Task Derivation

```
Planning Service
    ↓
  publishes: planning.plan.approved
    {story_id, plan_id, roles: [DEV, QA], ...}
    ↓
OrchestratorPlanningConsumer
    ↓
  derive_subtasks()  # ← FALTA IMPLEMENTAR
    ↓
  list[Task]
    {
      id: "TASK-001",
      description: "Implement login endpoint",
      role: DEV,
      constraints: {...},
      dependencies: [...]
    }
    ↓
  TaskQueue.enqueue(task)  # ← FALTA IMPLEMENTAR
```

### Fase 2: Task Dispatch → Orchestration

```
TaskQueue.dequeue()
    ↓
  next_task: Task
    ↓
Orchestrate.execute(role=DEV, task=next_task, constraints)
    ↓
  council = councils["DEV"]  # Deliberate instance para DEV
    ↓
  Deliberate.execute(task.description, constraints)
    ↓
    [Agent1.generate(), Agent2.generate(), Agent3.generate()]
      ↓ peer review rounds
    [Proposal1, Proposal2, Proposal3]
      ↓ scoring
    [Result1(score=0.95), Result2(score=0.87), Result3(score=0.82)]
    ↓
  Architect.choose([Result1, Result2, Result3])
    ↓
  {winner: Result1, candidates: [Result2, Result3]}
    ↓
  Publicar: orchestration.task.dispatched
    {
      story_id,
      task_id: "TASK-001",
      agent_id: "agent-dev-001",
      role: "DEV"
    }
```

### Fase 3: Agent Execution → Response Processing

```
Agent ejecuta task en workspace
    ↓
  publishes: agent.response.completed
    {
      task_id: "TASK-001",
      agent_id: "agent-dev-001",
      output: {...},
      checks_passed: true
    }
    ↓
OrchestratorAgentResponseConsumer
    ↓
  if requires_deliberation:
    # Caso: múltiples agentes trabajaron en paralelo
    ↓
    Deliberate.execute(...)  # ← Comparar resultados
    ↓
    winner = results[0]
    ↓
    Publicar: orchestration.deliberation.completed
      {
        story_id,
        task_id,
        decisions: [{id, type, rationale, ...}]
      }
  ↓
  TaskQueue.mark_completed(task_id)
  ↓
  next_task = TaskQueue.dequeue()
  ↓
  if next_task:
    Orchestrate.execute(...)  # Siguiente tarea
```

---

## 🏗️ Componentes Necesarios

### 1. ❌ **TaskQueue** (Redis/Valkey)

```python
class TaskQueue:
    """Cola de tareas con prioridades y dependencias."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.queue_key = "orchestrator:task_queue"
        self.status_key = "orchestrator:task_status"
    
    async def enqueue(self, task: Task, priority: int = 0):
        """Agregar tarea a la cola con prioridad."""
        task_data = {
            "id": task.id,
            "story_id": task.story_id,
            "description": task.description,
            "role": task.role.name,
            "constraints": task.constraints.to_dict(),
            "dependencies": task.dependencies,
            "priority": priority,
            "created_at": time.time(),
        }
        
        # Usar sorted set para prioridades
        await self.redis.zadd(
            self.queue_key,
            {json.dumps(task_data): priority}
        )
        
        # Set status
        await self.redis.hset(
            self.status_key,
            task.id,
            "QUEUED"
        )
    
    async def dequeue(self) -> Task | None:
        """Obtener siguiente tarea (mayor prioridad)."""
        # ZPOPMAX obtiene el de mayor score (prioridad)
        result = await self.redis.zpopmax(self.queue_key, count=1)
        if not result:
            return None
        
        task_json, priority = result[0]
        task_data = json.loads(task_json)
        
        # Update status
        await self.redis.hset(
            self.status_key,
            task_data["id"],
            "IN_PROGRESS"
        )
        
        return Task.from_dict(task_data)
    
    async def mark_completed(self, task_id: str):
        """Marcar tarea como completada."""
        await self.redis.hset(
            self.status_key,
            task_id,
            "COMPLETED"
        )
    
    async def mark_failed(self, task_id: str, error: str):
        """Marcar tarea como fallida."""
        await self.redis.hset(
            self.status_key,
            task_id,
            f"FAILED:{error}"
        )
    
    async def get_status(self, task_id: str) -> str:
        """Obtener status de una tarea."""
        status = await self.redis.hget(self.status_key, task_id)
        return status.decode() if status else "UNKNOWN"
```

---

### 2. ❌ **derive_subtasks()** - Derivación de Tareas

```python
async def derive_subtasks(
    plan_id: str,
    plan_content: str,  # Contenido del plan (markdown/structured)
    roles: list[str]
) -> list[Task]:
    """
    Analiza un plan y extrae subtasks atómicas ejecutables.
    
    Proceso:
    1. Parsear plan (markdown sections, YAML, o JSON)
    2. Identificar tasks por role
    3. Extraer dependencias entre tasks
    4. Crear objetos Task con constraints
    5. Asignar prioridades
    
    Returns:
        Lista de Tasks ordenadas por dependencias
    """
    
    # Opción A: Plan es markdown con estructura
    # ## DEV Tasks
    # - [ ] TASK-001: Implement login endpoint
    #   - Depends on: TASK-000
    #   - Priority: HIGH
    
    # Opción B: Plan es JSON/YAML estructurado
    # tasks:
    #   - id: TASK-001
    #     role: DEV
    #     description: "Implement login endpoint"
    #     dependencies: [TASK-000]
    
    tasks = []
    
    # Parse plan (ejemplo simplificado)
    plan_data = yaml.safe_load(plan_content)  # o markdown parser
    
    for task_def in plan_data.get("tasks", []):
        task = Task(
            id=task_def["id"],
            story_id=task_def["story_id"],
            plan_id=plan_id,
            description=task_def["description"],
            role=Role[task_def["role"]],
            constraints=TaskConstraints.from_dict(task_def.get("constraints", {})),
            dependencies=task_def.get("dependencies", []),
            priority=task_def.get("priority", 0),
        )
        tasks.append(task)
    
    # Ordenar topológicamente por dependencias
    sorted_tasks = topological_sort(tasks)
    
    return sorted_tasks
```

**Alternativa**: El Planning Service ya podría generar las subtasks y publicarlas como eventos separados.

---

### 3. ✅ **Councils Initialization** - Ya parcialmente implementado

El servidor ya tiene la estructura pero con councils vacíos:

```python
# En server.py
class OrchestratorServiceServicer:
    def __init__(self, config: SystemConfig):
        self.councils = {}  # ← Actualmente vacío
        self.orchestrator = None  # ← No inicializado
```

**Necesitamos**:

```python
def _initialize_councils(self, config: SystemConfig) -> dict[str, Deliberate]:
    """
    Inicializa councils para cada role con sus agentes.
    
    PROBLEMA: ¿De dónde vienen los agentes?
    
    Opciones:
    A) Mock agents para desarrollo
    B) Agentes remotos (Ray, Kubernetes pods)
    C) Agent registry service
    """
    councils = {}
    scoring = Scoring()
    
    for role_config in config.roles:
        # OPCIÓN A: Crear mock agents
        agents = [
            MockAgent(agent_id=f"agent-{role_config.name.lower()}-{i}", 
                     role=Role[role_config.name])
            for i in range(role_config.replicas)
        ]
        
        # OPCIÓN B: Registrar agentes remotos (Ray actors)
        # agents = await self._get_agents_from_ray(role_config.name)
        
        # OPCIÓN C: Obtener de registry
        # agents = await self.agent_registry.get_agents(role_config.name)
        
        councils[role_config.name] = Deliberate(
            agents=agents,
            tooling=scoring,
            rounds=1  # Configurable
        )
    
    return councils
```

---

## 🤔 Decisiones de Diseño Críticas

### Decisión 1: ¿Dónde se crean las subtasks?

**Opción A**: Planning Service genera subtasks
- ✅ Planning tiene el contexto completo del plan
- ✅ Puede usar LLM para derivar tasks inteligentemente
- ✅ Orchestrator solo consume tasks ya definidas
- ❌ Acoplamiento: Planning debe conocer formato de Task

**Opción B**: Orchestrator deriva subtasks del plan
- ✅ Orchestrator tiene control total sobre task decomposition
- ✅ Planning solo publica plan aprobado
- ❌ Orchestrator necesita entender formato de planes
- ❌ Más complejo

**Recomendación**: **Opción A** - Planning genera subtasks y las publica como eventos individuales.

---

### Decisión 2: ¿Cuándo se ejecuta Deliberate?

**Opción A**: Siempre delibera antes de dispatch
- ✅ Consistente, todas las tasks pasan por deliberación
- ❌ Lento, incluso para tasks triviales
- ❌ Desperdicia recursos

**Opción B**: Delibera solo después de ejecución (post-hoc)
- ✅ Rápido para tasks simples
- ✅ Deliberación solo cuando hay múltiples propuestas
- ❌ Más complejo, requiere colectar resultados

**Opción C**: Configurable por task
- ✅ Flexible
- ✅ Tasks críticas siempre deliberan
- ✅ Tasks simples skip deliberation
- ❌ Requiere metadata adicional

**Recomendación**: **Opción C** - Metadata en Task: `requires_pre_deliberation: bool`

---

### Decisión 3: ¿Dónde viven los Agents?

**Opción A**: Mock agents en memoria
- ✅ Fácil para desarrollo y testing
- ❌ No escalable
- ❌ No realistic

**Opción B**: Ray remote actors
- ✅ Distribuido, escalable
- ✅ Ya tenemos Ray en el stack
- ❌ Requiere Ray cluster operacional
- ❌ Complejidad de networking

**Opción C**: Kubernetes pods (agent runners)
- ✅ Ya tenemos workspace runners
- ✅ Isolation, security
- ❌ Startup time
- ❌ Resource overhead

**Opción D**: Agent registry service + dynamic dispatch
- ✅ Flexible, puede usar Ray o K8s
- ✅ Abstracción limpia
- ❌ Componente adicional

**Recomendación**: **Fase 1: A (mocks)**, **Fase 2: D (registry) + C (K8s runners)**

---

### Decisión 4: ¿Cómo manejar dependencias entre tasks?

**Opción A**: TaskQueue respeta dependencias
- ✅ Centralizado en un lugar
- ✅ Fácil de entender
- ❌ TaskQueue se vuelve complejo

**Opción B**: Orchestrator verifica dependencias antes de dispatch
- ✅ Lógica de dominio en Orchestrator
- ✅ TaskQueue se mantiene simple
- ❌ Requiere consultar estado de otras tasks

**Recomendación**: **Opción B** - Orchestrator verifica, TaskQueue solo almacena

---

## 🎯 Plan de Implementación por Fases

### 🟢 **Fase 1: Mock Implementation** (Para Testing)

**Objetivo**: Probar el flujo sin agentes reales

```python
# 1. MockAgent simple
class MockAgent(Agent):
    def generate(self, task, constraints, diversity=False):
        return {"content": f"Mock solution for {task}"}
    
    def critique(self, content, rubric):
        return "Mock feedback"
    
    def revise(self, content, feedback):
        return content  # Sin cambios

# 2. Inicializar councils con mocks
councils = {
    "DEV": Deliberate(
        agents=[MockAgent(f"dev-{i}") for i in range(3)],
        tooling=Scoring(),
        rounds=1
    )
}

# 3. TaskQueue simple (en memoria, sin Redis)
class InMemoryTaskQueue:
    def __init__(self):
        self.queue = []
    
    async def enqueue(self, task):
        self.queue.append(task)
    
    async def dequeue(self):
        return self.queue.pop(0) if self.queue else None
```

**Beneficio**: Podemos testear el flujo completo end-to-end sin infraestructura compleja.

---

### 🟡 **Fase 2: Redis TaskQueue** (Producción)

**Objetivo**: Queue persistente y distribuido

```python
# Implementar TaskQueue con Redis como mostrado arriba
# - Prioridades
# - Estado persistente
# - Failover
```

---

### 🟡 **Fase 3: Real Agents** (Integración con Runners)

**Objetivo**: Conectar con workspace runners reales

```python
# AgentProxy que comunica con workspace runner via gRPC
class WorkspaceAgentProxy(Agent):
    def __init__(self, workspace_service_url):
        self.workspace = WorkspaceServiceStub(
            grpc.insecure_channel(workspace_service_url)
        )
    
    def generate(self, task, constraints, diversity=False):
        response = self.workspace.ExecuteTask(
            ExecuteTaskRequest(
                task=task,
                constraints=constraints
            )
        )
        return {"content": response.output}
```

---

### 🔴 **Fase 4: Full Event Sourcing** (Futuro)

**Objetivo**: Todas las decisiones como eventos inmutables

- Cada deliberation result → evento
- Cada task state change → evento
- Replay para debugging
- Time travel queries

---

## 📝 Próximos Pasos Inmediatos

### 1. **Implementar Fase 1 (Mocks)** ✅ RECOMENDADO AHORA

```bash
# Archivos a crear/modificar:
1. src/swe_ai_fleet/orchestrator/domain/agents/mock_agent.py
2. src/swe_ai_fleet/orchestrator/adapters/in_memory_task_queue.py
3. services/orchestrator/server.py (inicializar councils con mocks)
4. services/orchestrator/consumers/planning_consumer.py (usar Orchestrate)
5. services/orchestrator/consumers/agent_response_consumer.py (usar Deliberate)
```

### 2. **Tests de Integración**

```bash
# Testear flujo completo:
1. Planning publica plan.approved
2. Orchestrator deriva tasks (mock)
3. Orchestrator ejecuta Orchestrate
4. Verifica que winner es seleccionado
5. Verifica que task.dispatched es publicado
```

### 3. **Implementar TaskQueue con Redis** (Fase 2)

Después de que funcione con mocks.

---

## 🎨 Diagrama de Secuencia Completo

```
Planning     Orchestrator     TaskQueue     Deliberate     Agents     Context
   │               │              │             │           │          │
   │──plan.approved──>│              │             │           │          │
   │               │──enqueue───>│             │           │          │
   │               │<──ok────────│             │           │          │
   │               │──dequeue──>│             │           │          │
   │               │<─task──────│             │           │          │
   │               │                          │           │          │
   │               │──execute(task)────────>│           │          │
   │               │                          │──generate()──>│          │
   │               │                          │<─proposal─────│          │
   │               │                          │ (x3 agents)   │          │
   │               │                          │──score()──────│          │
   │               │<─ranked results─────────│           │          │
   │               │                          │           │          │
   │               │──publish: task.dispatched─────────────────────>│
   │               │                                                 │
   │               │                          Agent Workspace        │
   │               │                          executes task          │
   │               │                                │                │
   │               │<──agent.response.completed─────│                │
   │               │                                                 │
   │               │──deliberate(results)───>│           │          │
   │               │<─winner─────────────────│           │          │
   │               │                                                 │
   │               │──publish: deliberation.completed──────────────>│
   │               │                                                 │
   │               │<──context.updated───────────────────────────────│
```

---

¿Empezamos con la **Fase 1 (Mock Implementation)** para tener el flujo funcionando end-to-end?

