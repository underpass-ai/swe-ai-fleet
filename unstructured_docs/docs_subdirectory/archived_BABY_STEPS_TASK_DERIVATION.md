# Baby Steps - Task Derivation Implementation

**Fecha:** 11 de noviembre, 2025
**Branch:** `feature/task-derivation-use-cases`
**Objetivo:** Implementar task derivation en Planning Service (GAP 4 - P0)

---

## 🎯 Estrategia: Baby Steps con DDD Estricto

Cada baby step:
- ✅ Se commitea independientemente
- ✅ Sigue DDD estricto (NO primitivos)
- ✅ Tell, Don't Ask
- ✅ Un archivo por clase
- ✅ VOs organizados por afinidad

---

## 📋 Baby Steps Plan

### ✅ Baby Step 1: Domain Layer - Value Objects (COMPLETADO)

**Commit:** `da6372d` + `8946f32` + `cdefe2d`

**Implementado:**

```
domain/value_objects/
├── identifiers/
│   └── deliberation_id.py        ← Ray Executor tracking
├── content/
│   └── dependency_reason.py      ← Por qué existe dependencia
├── actors/
│   └── role.py                   ← Agent role (DEV, QA, etc)
└── task_derivation/
    ├── keyword.py                ← Concepto técnico (con matches_in)
    ├── llm_prompt.py            ← Prompt LLM (con token_count_estimate)
    ├── task_node.py             ← Task en grafo (TaskId, Title, Role, Keywords)
    ├── dependency_edge.py       ← Relación dependencia (TaskId, TaskId, Reason)
    └── dependency_graph.py      ← Grafo completo con factory method
```

**DDD:**
- ✅ NO primitivos (str, int, dict)
- ✅ Inmutabilidad (`frozen=True`)
- ✅ Fail-fast validation
- ✅ Tell, Don't Ask: `DependencyGraph.from_tasks()` construye sí mismo
- ✅ Rich behavior: `has_circular_dependency()`, `get_execution_levels()`

**Líneas de código:** ~500 LOC

---

### ✅ Baby Step 2: Application Layer - Port (COMPLETADO)

**Commit:** `da6372d`

**Implementado:**

```
application/ports/
└── ray_executor_port.py         ← Interface para Ray Executor
```

**Interfaz:**
```python
class RayExecutorPort(ABC):
    async def submit_task_derivation(
        plan_id: PlanId,
        prompt: LLMPrompt,
        role: Role,
    ) -> DeliberationId:
        """Fire-and-forget: retorna deliberation_id inmediato"""
```

**Patrón:** Event-Driven (no polling)

**Líneas de código:** ~80 LOC

---

### ✅ Baby Step 3: Application Layer - Use Case (COMPLETADO)

**Commit:** `8946f32`

**Implementado:**

```
application/usecases/
└── derive_tasks_from_plan_usecase.py
```

**Use Case:**
```python
@dataclass
class DeriveTasksFromPlanUseCase:
    storage: StoragePort
    ray_executor: RayExecutorPort

    async def execute(self, plan_id: PlanId) -> DeliberationId:
        # 1. Fetch plan
        # 2. Build LLM prompt
        # 3. Submit to Ray (fire-and-forget)
        # 4. Return deliberation_id
```

**Características:**
- ✅ Event-driven (no espera resultado)
- ✅ Usa SOLO ports (Hexagonal)
- ✅ SOLO Value Objects
- ✅ Structured prompt con instrucciones claras

**Líneas de código:** ~120 LOC

---

### ⏳ Baby Step 4: Infrastructure - Adapter Ray Executor (PENDIENTE)

**Ubicación:**
```
infrastructure/adapters/
└── ray_executor_adapter.py      ← Cliente gRPC a Ray Executor
```

**Implementación:**
```python
class RayExecutorAdapter(RayExecutorPort):
    """Adapter que implementa RayExecutorPort usando gRPC."""

    def __init__(self, grpc_address: str):
        self.channel = grpc.aio.insecure_channel(grpc_address)
        self.stub = RayExecutorServiceStub(self.channel)

    async def submit_task_derivation(
        self,
        plan_id: PlanId,
        prompt: LLMPrompt,
        role: Role,
    ) -> DeliberationId:
        # Build gRPC request
        request = ExecuteDeliberationRequest(
            task_id=f"derive-{plan_id.value}",
            task_description=prompt.value,
            role=role.value,
            agents=[{"id": "task-deriver", "role": "SYSTEM"}],
            vllm_url=self.config.vllm_url,
            vllm_model=self.config.vllm_model,
        )

        # Call Ray Executor (returns immediately)
        response = await self.stub.ExecuteDeliberation(request)

        return DeliberationId(response.deliberation_id)
```

**Estimación:** ~150 LOC

---

### ⏳ Baby Step 5: Infrastructure - Consumer Plan Approved (PENDIENTE)

**Ubicación:**
```
infrastructure/consumers/
└── plan_approved_consumer.py    ← Escucha planning.plan.approved
```

**Flow:**
```python
class PlanApprovedConsumer:
    """
    Escucha: planning.plan.approved
    Acción: Llama DeriveTasksFromPlanUseCase
    """

    def __init__(
        self,
        nats_client,
        derive_tasks_usecase: DeriveTasksFromPlanUseCase,
    ):
        self.nats = nats_client
        self.use_case = derive_tasks_usecase

    async def start(self):
        await self.nats.subscribe(
            "planning.plan.approved",
            callback=self._handle_plan_approved
        )

    async def _handle_plan_approved(self, msg):
        # 1. Parse evento (DTO → VO via mapper)
        payload = json.loads(msg.data)
        plan_id = PlanId(payload["plan_id"])

        # 2. Llamar use case
        deliberation_id = await self.use_case.execute(plan_id)

        # 3. Store tracking (para consumer de resultados)
        await self.storage.save_derivation_tracking(
            deliberation_id=deliberation_id,
            plan_id=plan_id,
            status="pending"
        )

        # 4. ACK
        await msg.ack()
```

**Mapper necesario:**
```python
# infrastructure/mappers/plan_approved_event_mapper.py
class PlanApprovedEventMapper:
    @staticmethod
    def payload_to_plan_id(payload: dict) -> PlanId:
        """DTO infra → VO domain"""
        return PlanId(payload["plan_id"])
```

**Estimación:** ~100 LOC (consumer) + ~50 LOC (mapper)

---

### ⏳ Baby Step 6: Infrastructure - Consumer Task Derivation Result (PENDIENTE)

**Ubicación:**
```
infrastructure/consumers/
└── task_derivation_result_consumer.py  ← Escucha agent.response.completed
```

**Flow:**
```python
class TaskDerivationResultConsumer:
    """
    Escucha: agent.response.completed
    Filtra: Solo task_id.startswith("derive-")
    Acción: Parse tasks → Persistir → Publicar eventos
    """

    def __init__(
        self,
        nats_client,
        create_task_usecase: CreateTaskUseCase,
        storage: StoragePort,
        messaging: MessagingPort,
    ):
        self.nats = nats_client
        self.create_task = create_task_usecase
        self.storage = storage
        self.messaging = messaging

    async def start(self):
        await self.nats.subscribe(
            "agent.response.completed",
            callback=self._handle_agent_response
        )

    async def _handle_agent_response(self, msg):
        payload = json.loads(msg.data)
        task_id = payload["task_id"]

        # 1. Filtrar: solo task derivation
        if not task_id.startswith("derive-"):
            return  # Not our event

        # 2. Extract plan_id
        plan_id = PlanId(task_id.replace("derive-", ""))

        # 3. Parse LLM result → TaskNodes
        generated_text = payload["result"]["proposal"]
        task_nodes = self._parse_tasks_from_llm(generated_text)

        # 4. Build dependency graph (Tell, Don't Ask)
        graph = DependencyGraph.from_tasks(task_nodes)

        # 5. Validar grafo (strategy: retry on circular)
        retry_count = await self._get_retry_count(plan_id)

        if graph.has_circular_dependency():
            if retry_count < MAX_RETRIES:
                # Retry con prompt mejorado
                await self._retry_derivation(plan_id, retry_count + 1)
                await msg.ack()
                return
            else:
                # Human-in-the-loop
                await self._notify_manual_review(plan_id)
                await msg.ack()
                return

        # 6. Persistir tasks (usar CreateTaskUseCase N veces)
        story_id = await self.storage.get_story_id_for_plan(plan_id)

        for task_node in graph.tasks:
            await self.create_task.execute(
                plan_id=plan_id,
                story_id=story_id,
                title=str(task_node.title),
                description="",  # LLM puede incluir description
                type=TaskType.DEVELOPMENT,
                assigned_to=str(task_node.role),
                priority=1,  # LLM puede indicar priority
            )
            # CreateTaskUseCase ya publica planning.task.created

        # 7. Persistir dependencies en Neo4j
        await self._persist_dependencies(graph.dependencies)

        # 8. Publicar evento final
        await self.messaging.publish_event(
            "planning.tasks.derived",
            {
                "plan_id": plan_id.value,
                "task_count": len(graph.tasks),
                "dependency_count": len(graph.dependencies)
            }
        )

        # 9. ACK
        await msg.ack()
```

**Parser LLM:**
```python
def _parse_tasks_from_llm(self, text: str) -> tuple[TaskNode, ...]:
    """Parse formato estructurado del LLM."""
    # Parse blocks:
    # TASK_ID: TASK-001
    # TITLE: Setup project
    # ROLE: DEV
    # KEYWORDS: setup, project, init
    ...
```

**Estimación:** ~250 LOC (consumer) + ~100 LOC (parser) + ~50 LOC (mapper)

---

### ⏳ Baby Step 7: Integration - Planning Server (PENDIENTE)

**Modificar:** `services/planning/server.py`

**Cambios:**
```python
async def main():
    # Existing setup...

    # NEW: Initialize Ray Executor adapter
    ray_executor_adapter = RayExecutorAdapter(
        grpc_address=os.getenv(
            'RAY_EXECUTOR_ADDR',
            'ray-executor-service.swe-ai-fleet.svc.cluster.local:50056'
        )
    )

    # NEW: Initialize DeriveTasksFromPlanUseCase
    derive_tasks_usecase = DeriveTasksFromPlanUseCase(
        storage=storage_adapter,
        ray_executor=ray_executor_adapter,
    )

    # NEW: Initialize consumers
    plan_approved_consumer = PlanApprovedConsumer(
        nats_client=nc,
        derive_tasks_usecase=derive_tasks_usecase,
        storage=storage_adapter,
    )

    task_derivation_result_consumer = TaskDerivationResultConsumer(
        nats_client=nc,
        create_task_usecase=create_task_uc,
        storage=storage_adapter,
        messaging=messaging_adapter,
    )

    # Start consumers
    await plan_approved_consumer.start()
    await task_derivation_result_consumer.start()

    logger.info("✅ Task derivation consumers started")
```

**Estimación:** ~50 LOC modificación

---

### ⏳ Baby Step 8: Tests - Unit Tests (PENDIENTE)

**Ubicación:**
```
tests/unit/
├── domain/
│   └── value_objects/
│       └── test_dependency_graph.py     ← Tests VOs
└── application/
    └── usecases/
        └── test_derive_tasks_from_plan_usecase.py
```

**Tests necesarios:**

1. **test_dependency_graph.py** (~300 LOC)
   - test_create_valid_dependency_graph
   - test_from_tasks_factory_method
   - test_detects_circular_dependencies
   - test_no_circular_in_acyclic_graph
   - test_get_root_tasks
   - test_get_execution_levels
   - test_validation_errors

2. **test_task_node.py** (~150 LOC)
   - test_create_valid_task_node
   - test_has_keyword_matching
   - test_validation_errors

3. **test_derive_tasks_from_plan_usecase.py** (~200 LOC)
   - test_execute_happy_path
   - test_plan_not_found
   - test_ray_executor_error
   - test_builds_correct_prompt
   - Usar mocks para ports

**Estimación:** ~650 LOC tests

---

### ⏳ Baby Step 9: Tests - Integration Tests (PENDIENTE)

**Ubicación:**
```
tests/integration/
└── test_task_derivation_integration.py
```

**Scenarios:**

1. **test_plan_approved_triggers_derivation**
   - Publicar planning.plan.approved
   - Verificar consumer llama use case
   - Verificar job submitido a Ray

2. **test_agent_result_creates_tasks**
   - Publicar agent.response.completed (mock result)
   - Verificar tasks creados
   - Verificar planning.task.created publicado

3. **test_circular_dependency_retry**
   - Mock LLM genera circular deps
   - Verificar retry automático
   - Max retries → human-in-the-loop

**Estimación:** ~300 LOC

---

### ⏳ Baby Step 10: Validation - E2E Test (PENDIENTE)

**Ubicación:**
```
tests/e2e/
└── test_task_derivation_e2e.py
```

**Scenario completo:**
```python
async def test_complete_task_derivation_flow():
    # 1. PO aprueba plan
    response = await planning_client.ApproveDecision(
        plan_id="PLAN-001"
    )

    # 2. Esperar evento planning.plan.approved
    event = await nats_wait_for("planning.plan.approved", timeout=5)
    assert event["plan_id"] == "PLAN-001"

    # 3. Verificar job submitido a Ray
    # (mock Ray Executor o usar real con stub)

    # 4. Simular resultado LLM
    await nats_publish("agent.response.completed", {
        "task_id": "derive-PLAN-001",
        "result": {
            "proposal": """
            TASK_ID: TASK-001
            TITLE: Setup authentication
            ...
            """
        }
    })

    # 5. Esperar tasks creados
    tasks = []
    for _ in range(5):  # 5 tasks esperados
        event = await nats_wait_for("planning.task.created", timeout=10)
        tasks.append(event)

    assert len(tasks) == 5

    # 6. Verificar dependencies en Neo4j
    deps = await neo4j_query("MATCH ()-[r:DEPENDS_ON]->() RETURN r")
    assert len(deps) > 0

    # 7. Verificar evento final
    event = await nats_wait_for("planning.tasks.derived", timeout=5)
    assert event["task_count"] == 5
```

**Estimación:** ~200 LOC

---

## 📊 Resumen de Progreso

| Baby Step | Estado | LOC | Commits |
|-----------|--------|-----|---------|
| 1. Domain VOs | ✅ DONE | ~500 | 3 commits |
| 2. Port | ✅ DONE | ~80 | (incluido) |
| 3. Use Case | ✅ DONE | ~120 | (incluido) |
| 4. Adapter | ⏳ TODO | ~150 | - |
| 5. Consumer Plan Approved | ⏳ TODO | ~150 | - |
| 6. Consumer Result | ⏳ TODO | ~400 | - |
| 7. Integration | ⏳ TODO | ~50 | - |
| 8. Unit Tests | ⏳ TODO | ~650 | - |
| 9. Integration Tests | ⏳ TODO | ~300 | - |
| 10. E2E Validation | ⏳ TODO | ~200 | - |
| **TOTAL** | **30% DONE** | **~2,600** | **3/10** |

---

## 🎯 Próximos Pasos

### Inmediato: Baby Step 4 (Adapter)

Crear `RayExecutorAdapter`:
- Cliente gRPC a Ray Executor (:50056)
- Implementa `RayExecutorPort`
- Mapea VOs → protobuf → gRPC call
- Mapea gRPC response → VOs

**Dependencias:**
- Necesita `ray_executor_pb2` y `ray_executor_pb2_grpc`
- Planning Service debe generar protobufs en build
- O importar desde `services/ray_executor/gen/`

---

## 🔧 Decisiones Técnicas Tomadas

### 1. Event-Driven (NO Polling)
- ✅ Submit job → retorna deliberation_id
- ✅ Resultado vía NATS (agent.response.completed)
- ❌ NO polling GetDeliberationStatus

### 2. Retry Strategy (Circular Dependencies)
- ✅ Retry automático (MAX_RETRIES=3)
- ✅ Human-in-the-loop después de max retries
- ✅ DependencyGraph valida sí mismo

### 3. DDD Estricto
- ✅ NO primitivos (str, int, dict)
- ✅ Tell, Don't Ask
- ✅ Factory methods
- ✅ Rich value objects

### 4. Arquitectura Hexagonal
- ✅ Ports en application layer
- ✅ Adapters en infrastructure layer
- ✅ Domain no conoce infraestructura

---

## 🚀 Estimación Total

**Tiempo restante:** 2-3 días

**Breakdown:**
- Baby Steps 4-7 (código): 1.5 días
- Baby Steps 8-9 (tests): 1 día
- Baby Step 10 (E2E + validación): 0.5 días

**Crítico para GAP 4:**
- Baby Steps 4-7 son suficientes para funcionalidad básica
- Baby Steps 8-10 para calidad productiva

---

**Status:** Baby Steps 1-3 completados (30%)
**Next:** Baby Step 4 (RayExecutorAdapter)

