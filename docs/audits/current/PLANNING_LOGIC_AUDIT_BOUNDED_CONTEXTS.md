# Auditoría: Lógica de Planificación en Bounded Contexts

**Fecha**: 2 de noviembre, 2025
**Autor**: AI Assistant (Claude Sonnet 4.5)
**Solicitado por**: Tirso García Ibáñez (Software Architect)
**Objetivo**: Identificar toda la lógica de planificación existente en agents_and_tools y orchestrator

---

## 🎯 Resumen Ejecutivo

Se identificaron **DOS bounded contexts** con lógica de planificación distribuida sin un dueño claro:

1. **`core/agents_and_tools/agents`** - Generación de planes de ejecución para agentes individuales
2. **`core/orchestrator` + `services/orchestrator`** - Orquestación y derivación de subtasks (PENDIENTE)

**Hallazgo crítico**: Existe un **GAP de responsabilidad** en la derivación de subtasks desde historias de usuario. La lógica está TODO/UNIMPLEMENTED.

---

## 📊 Bounded Context 1: `agents_and_tools` - Plan Generation

### Ubicación
```
core/agents_and_tools/agents/
├── application/
│   ├── usecases/
│   │   └── generate_plan_usecase.py         ← CORE: Generación de plan LLM
│   └── dtos/
│       └── plan_dto.py                       ← DTO del plan
├── domain/
│   └── entities/
│       └── core/
│           ├── execution_plan.py             ← Entidad: Plan de ejecución
│           └── execution_step.py             ← Entidad: Paso de ejecución
└── infrastructure/
    ├── mappers/
    │   └── execution_step_mapper.py          ← Mapper: dict → ExecutionStep
    └── services/
        ├── prompt_loader.py                  ← Carga prompts desde YAML
        └── json_response_parser.py           ← Parse JSON del LLM
```

### Responsabilidad
**Generar planes de ejecución para un agente individual** dado:
- Task description
- Smart context (de Context Service)
- Role (DEV, QA, ARCHITECT)
- Available tools (capabilities)
- Constraints (optional)

### Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                   GeneratePlanUseCase                       │
│  Input: task, context, role, tools, constraints             │
│  Output: PlanDTO (steps + reasoning)                        │
└─────────────────────────────────────────────────────────────┘
                        │ uses
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                      Dependencies                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ LLMClientPort│  │ PromptLoader │  │ JSONParser   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                        │ produces
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    ExecutionPlan                            │
│  steps: list[ExecutionStep]                                 │
│    - tool: str       (e.g., "file", "git", "test")         │
│    - operation: str  (e.g., "read_file", "commit")         │
│    - params: dict    (tool-specific parameters)            │
│  reasoning: str      (why this plan)                        │
└─────────────────────────────────────────────────────────────┘
```

### Código Clave

**GeneratePlanUseCase.execute()** (`generate_plan_usecase.py:62-133`):
```python
async def execute(
    self,
    task: str,
    context: str,
    role: str,
    available_tools: AgentCapabilities,
    constraints: ExecutionConstraints | None = None,
) -> PlanDTO:
    # 1. Load role-specific prompt from YAML
    prompt_config = self.prompt_loader.load_prompt_config("plan_generation")
    role_prompt = roles.get(role, f"You are an expert {role} engineer.")

    # 2. Build system prompt with tools
    system_prompt = system_template.format(
        role_prompt=role_prompt,
        capabilities=tools_json,
        mode=available_tools.mode
    )

    # 3. Build user prompt with task + context
    user_prompt = user_template.format(
        task=task,
        context=context
    )

    # 4. Call LLM via port
    response = await self.llm_client.generate(system_prompt, user_prompt)

    # 5. Parse JSON response
    plan = self.json_parser.parse_json_response(response)

    # 6. Map to entities
    step_entities = self.step_mapper.to_entity_list(plan["steps"])

    return PlanDTO(steps=step_entities, reasoning=plan.get("reasoning"))
```

**ExecutionPlan** (`execution_plan.py:1-12`):
```python
@dataclass(frozen=True)
class ExecutionPlan:
    """Structured execution plan from LLM."""
    steps: list[dict]
    reasoning: str | None = None
```

**ExecutionStep** (`execution_step.py:8-26`):
```python
@dataclass(frozen=True)
class ExecutionStep:
    """Single step in an execution plan."""
    tool: str
    operation: str
    params: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.tool:
            raise ValueError("tool cannot be empty")
        if not self.operation:
            raise ValueError("operation cannot be empty")
```

### Prompts
Los prompts se cargan desde:
```
core/agents_and_tools/resources/prompts/plan_generation.yaml
```

### Consumo
Este use case es usado por:
- **VLLMAgent** (`core/agents_and_tools/agents/vllm_agent.py`) - Agente individual con LLM

### Características
✅ **Arquitectura Hexagonal completa**
✅ **DTOs inmutables** (`@dataclass(frozen=True)`)
✅ **Fail-fast validation**
✅ **Dependency Injection** (ports)
✅ **Strong typing**
✅ **Role-specific prompts** (DEV, QA, ARCHITECT)
✅ **Tool-aware planning** (genera pasos basados en herramientas disponibles)

### Limitaciones Identificadas
❌ **Scope limitado**: Solo genera plan para UN agente
❌ **Sin multi-agent coordination**: No orquesta múltiples agentes
❌ **Sin task derivation**: No descompone historias en subtasks
❌ **Sin dependency tracking**: Los pasos son secuenciales, no hay grafo de dependencias

---

## 📊 Bounded Context 2: `orchestrator` - Multi-Agent Orchestration

### Ubicación
```
core/orchestrator/
├── usecases/
│   ├── orchestrate_usecase.py               ← Orquestación completa
│   └── peer_deliberation_usecase.py         ← Deliberación multi-agente
└── handler/
    └── agent_job_worker.py                  ← Worker Ray

services/orchestrator/
├── server.py                                 ← gRPC Server
│   └── DeriveSubtasks()                     ← ❌ UNIMPLEMENTED
├── application/
│   └── services/
│       └── auto_dispatch_service.py         ← Auto-dispatch deliberations
└── infrastructure/
    └── handlers/
        └── planning_consumer.py             ← ❌ TODO: derivar subtasks
```

### Responsabilidad
**Orquestar la deliberación multi-agente** y coordinar la ejecución distribuida de tasks.

**⚠️ RESPONSABILIDAD PENDIENTE**: Derivar subtasks desde una historia de usuario.

### Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│              OrchestratorPlanningConsumer                   │
│  Consume: planning.story.transitioned                       │
│  Consume: planning.plan.approved                            │
└─────────────────────────────────────────────────────────────┘
                        │ calls
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                AutoDispatchService                          │
│  dispatch_deliberations_for_plan(event)                     │
│    ├─ Role 1: DEV     → Deliberate                         │
│    ├─ Role 2: QA      → Deliberate                         │
│    └─ Role 3: ARCHITECT → Deliberate                       │
└─────────────────────────────────────────────────────────────┘
                        │ uses
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  DeliberateUseCase                          │
│  execute(council, role, task_description, constraints)      │
│    └─ Multi-agent peer deliberation                        │
└─────────────────────────────────────────────────────────────┘
                        │ produces
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                DeliberationResult                           │
│  results: list[Proposal]  (ranked proposals)                │
│  winner: str                                                │
│  duration_ms: int                                           │
└─────────────────────────────────────────────────────────────┘
```

### Código Clave

**OrchestratorPlanningConsumer._handle_plan_approved()** (`planning_consumer.py:179-253`):
```python
async def _handle_plan_approved(self, msg):
    """
    Handle plan approval events.

    When a plan is approved, we should:
    - Derive initial subtasks for orchestration    ← ❌ TODO
    - Initialize councils for the roles needed     ← ✅ DONE
    - Start task queue for execution               ← ❌ TODO
    """
    event = PlanApprovedEvent.from_dict(event_data)

    # AUTO-DISPATCH: Delegate to AutoDispatchService
    if self._auto_dispatch_service and event.roles:
        dispatch_result = await self._auto_dispatch_service.dispatch_deliberations_for_plan(event)

        logger.info(
            f"✅ Auto-dispatch completed: {dispatch_result['successful']}/{dispatch_result['total_roles']} successful"
        )
```

**AutoDispatchService.dispatch_deliberations_for_plan()** (`auto_dispatch_service.py:54-118`):
```python
async def dispatch_deliberations_for_plan(
    self,
    event: PlanApprovedEvent,
) -> dict[str, Any]:
    """
    Dispatch deliberations for all roles in the plan.

    For each role:
    1. Verify council exists
    2. Build task description from plan
    3. Execute deliberation
    4. Collect results
    """
    results = []

    for role in event.roles:
        try:
            result = await self._dispatch_single_deliberation(
                role=role,
                plan_id=event.plan_id,
                story_id=event.story_id,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to dispatch deliberation for {role}: {e}")
            results.append({"role": role, "success": False, "error": str(e)})

    return {
        "total_roles": len(event.roles),
        "successful": sum(1 for r in results if r.get("success")),
        "results": results
    }
```

**DeriveSubtasks RPC** (`server.py:583-592`):
```python
async def DeriveSubtasks(self, request, context):
    """Derive atomic subtasks from a case/plan.

    TODO: Implement task derivation logic.
    Requires integration with Planning and Context services.
    """
    logger.info(f"Derive subtasks: case={request.case_id}, roles={request.roles}")
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details("Subtask derivation not yet implemented")
    return orchestrator_dto.DeriveSubtasksResponse(tasks=[], total_tasks=0)
```

### Flujo Actual (Implementado)

```
PO aprueba plan
    ↓
Planning Service publica: planning.plan.approved
    ↓
OrchestratorPlanningConsumer recibe evento
    ↓
AutoDispatchService.dispatch_deliberations_for_plan()
    ↓
Para cada role (DEV, QA, ARCHITECT):
    ├─ Verificar que council existe
    ├─ Crear task_description: "Implement plan {plan_id} for story {story_id}"
    ├─ Ejecutar DeliberateUseCase
    └─ Publicar deliberation.completed event
```

### Flujo Deseado (NO implementado)

```
PO aprueba plan
    ↓
Planning Service publica: planning.plan.approved
    ↓
OrchestratorPlanningConsumer recibe evento
    ↓
❌ TODO: DeriveSubtasks(story_id, plan_id)
    ├─ Leer historia de usuario
    ├─ Analizar acceptance criteria
    ├─ Generar subtasks atómicas con:
    │   ├─ Dependencies (grafo de tareas)
    │   ├─ Priorities (1 = highest)
    │   ├─ Estimated effort
    │   └─ Role assignment
    └─ Persistir subtasks en Neo4j + Valkey
        ↓
Para cada subtask:
    ├─ Asignar a council de role correspondiente
    ├─ Ejecutar DeliberateUseCase
    └─ Publicar task.completed event
```

### Características
✅ **Auto-dispatch de deliberaciones**
✅ **Multi-agent coordination**
✅ **Event-driven** (NATS JetStream)
✅ **Role-based councils**
✅ **Hexagonal architecture**

### Limitaciones Identificadas
❌ **DeriveSubtasks NO implementado** - RPC retorna UNIMPLEMENTED
❌ **Task description es genérico** - "Implement plan X for story Y" (no específico)
❌ **No lee Planning Service** - No consulta el plan aprobado
❌ **No dependency tracking** - No maneja grafo de dependencias
❌ **No task queue** - No hay cola de tareas priorizada

---

## 🔍 GAP CRÍTICO: Derivación de Subtasks

### El Problema

Actualmente hay un **GAP de responsabilidad** entre:

1. **Planning Service** (Go) - Gestiona FSM de historias, NO descompone en subtasks
2. **agents_and_tools** - Genera plan de ejecución para UN agente, NO orquesta
3. **orchestrator** - Coordina multi-agent deliberation, pero NO deriva subtasks

**Resultado**: Nadie tiene la responsabilidad de:
- Descomponer historia de usuario → subtasks atómicas
- Crear grafo de dependencias entre subtasks
- Priorizar subtasks
- Asignar subtasks a roles

### Dónde Debería Estar Esta Lógica

#### Opción 1: `orchestrator` bounded context ✅ (RECOMENDADO)
```python
# services/orchestrator/application/usecases/derive_subtasks_usecase.py

class DeriveSubtasksUseCase:
    """Derive atomic subtasks from a user story."""

    async def execute(
        self,
        story_id: str,
        plan_id: str,
        roles: list[str],
    ) -> list[SubtaskDTO]:
        # 1. Fetch story from Context Service
        story = await self.context_client.get_story(story_id)

        # 2. Analyze acceptance criteria
        # 3. Use LLM to generate subtasks (via GeneratePlanUseCase)
        # 4. Create dependency graph
        # 5. Assign priorities
        # 6. Persist to Neo4j + Valkey
        # 7. Return subtask list
```

**Justificación**:
- Orchestrator ya coordina multi-agent execution
- Ya tiene RPC `DeriveSubtasks` definido (solo falta implementar)
- Ya consume eventos de Planning Service

#### Opción 2: Nuevo bounded context `planner` ⚠️ (ALTERNATIVA)
Crear un bounded context dedicado exclusivamente a:
- Task derivation
- Dependency management
- Priority assignment
- Effort estimation

**Justificación**:
- Separación de responsabilidades clara
- Reutilizable por otros servicios
- Más fácil de escalar independientemente

---

## 📋 Interacciones Actuales

### 1. Planning Service → Orchestrator
```
Planning Service (Go)
    │ publica: planning.plan.approved
    ▼
OrchestratorPlanningConsumer
    │ auto-dispatch deliberations
    ▼
AutoDispatchService
    │ para cada role
    ▼
DeliberateUseCase
```

### 2. Context Service → agents_and_tools
```
Context Service (Python)
    │ GET /context
    │ returns: smart context (surgical, 200 tokens)
    ▼
VLLMAgent.execute_task()
    │ calls: GeneratePlanUseCase
    ▼
ExecutionPlan
    │ steps: [ExecutionStep, ...]
    ▼
StepExecutionUseCase
```

### 3. orchestrator → agents_and_tools (Indirecta)
```
DeliberateUseCase
    │ multi-agent deliberation
    ▼
Para cada agente:
    │ VLLMAgent.generate_proposal()
    │     ├─ GeneratePlanUseCase
    │     └─ ExecutePlanUseCase
    ▼
Ranked proposals
```

---

## 🚨 Hallazgos Críticos

### 1. **Lógica de planificación fragmentada**
- `agents_and_tools`: Plan de ejecución para agente individual
- `orchestrator`: Coordina multi-agent, pero NO deriva subtasks
- **Planning Service**: Solo FSM de historias, NO task decomposition

### 2. **DeriveSubtasks UNIMPLEMENTED**
```python
# services/orchestrator/server.py:583-592
async def DeriveSubtasks(self, request, context):
    """❌ TODO: Implement task derivation logic."""
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details("Subtask derivation not yet implemented")
    return orchestrator_dto.DeriveSubtasksResponse(tasks=[], total_tasks=0)
```

### 3. **Planning Consumer con TODO**
```python
# services/orchestrator/infrastructure/handlers/planning_consumer.py:148-158
# TODO: Implement orchestration triggering
# This would:
# 1. Query Planning for subtasks in this phase
# 2. Call DeriveSubtasks if needed            ← ❌ NO EXISTE
# 3. Trigger Orchestrate RPC for relevant tasks
```

### 4. **Task description genérico**
```python
# services/orchestrator/application/services/auto_dispatch_service.py:159
task_description = f"Implement plan {plan_id} for story {story_id}"
```

**Problema**: El task_description NO incluye:
- Detalles de la historia
- Acceptance criteria
- Contexto específico del role
- Dependencies con otras tasks

### 5. **No integración con Planning Service**
Orchestrator NO consulta Planning Service para:
- Obtener detalles del plan aprobado
- Leer subtasks (porque no existen)
- Obtener acceptance criteria
- Leer transition history

---

## 💡 Conclusiones

### Responsabilidades Actuales
| Bounded Context | Responsabilidad | Estado |
|----------------|-----------------|--------|
| `agents_and_tools` | Generar plan de ejecución para UN agente | ✅ IMPLEMENTADO |
| `orchestrator` | Coordinar multi-agent deliberation | ✅ IMPLEMENTADO |
| `orchestrator` | Derivar subtasks desde historia | ❌ PENDING |
| `Planning Service` (Go) | FSM de historias de usuario | ✅ IMPLEMENTADO |
| `Planning Service` (Go) | Descomponer historias en subtasks | ❌ NOT IN SCOPE |

### GAP Identificado
**Nadie tiene la responsabilidad de**:
1. Descomponer historia de usuario → subtasks atómicas
2. Crear grafo de dependencias entre subtasks
3. Asignar subtasks a roles
4. Priorizar y estimar esfuerzo

### Recomendaciones
1. **Implementar `DeriveSubtasks` en orchestrator** - Usar LLM para descomponer historias
2. **Integrar Planning Service** - Leer plan aprobado y acceptance criteria
3. **Crear grafo de dependencias** - Persistir en Neo4j con relaciones DEPENDS_ON
4. **Mejorar task_description** - Incluir contexto específico del role
5. **Considerar bounded context `planner`** - Si la lógica crece demasiado

---

**Siguiente documento**: `PLANNER_GIT_HISTORY_AUDIT.md`


