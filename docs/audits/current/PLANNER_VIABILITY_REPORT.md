# Informe de Viabilidad: Bounded Context `planner`

**Fecha**: 2 de noviembre, 2025
**Autor**: AI Assistant (Claude Sonnet 4.5)
**Solicitado por**: Tirso García Ibáñez (Software Architect)
**Objetivo**: Evaluar viabilidad de crear/revivir bounded context `planner` y proponer soluciones

---

## 🎯 Resumen Ejecutivo

Basado en las auditorías de:
1. **Lógica de planificación en bounded contexts actuales** (`PLANNING_LOGIC_AUDIT_BOUNDED_CONTEXTS.md`)
2. **Planner histórico en git** (`PLANNER_GIT_HISTORY_AUDIT.md`)

**Conclusión**: ⚠️ **NO es viable revivir el planner completo**, pero **SÍ es viable crear un bounded context específico para Task Derivation**.

**Recomendación**: **Solución 3 (Hybrid)** - Implementar `DeriveSubtasks` en orchestrator + extraer features útiles del planner histórico.

---

## 📊 Estado Actual del Sistema

### Componentes Relacionados con Planning

| Componente | Responsabilidad | Estado | Gap |
|------------|-----------------|--------|-----|
| **Planning Service** (Go) | FSM de historias de usuario | ✅ Producción | Context provider, Guard eval, Event store |
| **agents_and_tools** | Plan de ejecución para UN agente | ✅ Implementado | Multi-agent coordination, Task derivation |
| **orchestrator** | Multi-agent deliberation | ✅ Implementado | Task derivation, Dependency tracking |
| **Planner** (Python histórico) | Cases + FSM + Context + Events + Graph | ❌ Abandonado (WIP) | Tests, Deployment, Integración |

### GAP Crítico Identificado

**Nadie tiene la responsabilidad de**:
1. ✅ Descomponer historia de usuario → subtasks atómicas
2. ✅ Crear grafo de dependencias entre subtasks
3. ✅ Asignar subtasks a roles
4. ✅ Priorizar y estimar esfuerzo

---

## 🎯 Análisis de Viabilidad

### ¿Es Viable Revivir el Planner Histórico Completo?

#### ❌ NO VIABLE por las siguientes razones:

1. **Overlap con Planning Service (Go)**
   - Planning Service ya gestiona FSM de historias
   - Duplicaría responsabilidades
   - Conflicto de ownership

2. **Scope Demasiado Amplio**
   - FSM engine
   - Case management
   - Context provider
   - Event store
   - Graph store
   - Guard evaluation
   - Human gates

   **Resultado**: Bounded context "God Object"

3. **Tecnología Mixta Sin Justificación**
   - Planning Service en Go (alto rendimiento)
   - Planner en Python (sin ventaja clara)
   - Aumenta complejidad del stack

4. **Falta de Tests**
   - 1,612 líneas sin tests
   - Alto riesgo de bugs
   - Imposible mantener con confianza

5. **Código WIP Abandonado**
   - Solo 1 commit
   - Nunca fue completado
   - Implementaciones mock

6. **Falta de Integración**
   - No integra con servicios actuales
   - Requeriría refactor masivo
   - ROI negativo

### ¿Es Viable Crear un Bounded Context Específico?

#### ✅ VIABLE con SCOPE LIMITADO:

**Bounded Context**: `task-derivation` (o `planner` con scope reducido)

**Responsabilidad ÚNICA**:
- Descomponer historia de usuario → subtasks atómicas
- Crear grafo de dependencias (Neo4j)
- Asignar subtasks a roles
- Priorizar y estimar esfuerzo

**Justificación**:
1. **GAP real** - Nadie hace task derivation actualmente
2. **Scope delimitado** - Una responsabilidad específica
3. **Reutilizable** - Otros servicios pueden consumirlo
4. **Testeable** - Scope pequeño, fácil de probar
5. **Escalable** - Puede evolucionar independientemente

---

## 💡 Soluciones Propuestas

### Solución 1: Implementar DeriveSubtasks en Orchestrator (SIMPLE)

**Descripción**: Implementar la funcionalidad de derivación de subtasks directamente en el servicio Orchestrator actual.

#### Arquitectura

```
services/orchestrator/
├── application/
│   └── usecases/
│       └── derive_subtasks_usecase.py        ← NUEVO
├── domain/
│   └── entities/
│       └── subtask.py                        ← NUEVO
└── server.py
    └── DeriveSubtasks()                      ← IMPLEMENTAR
```

#### Flujo

```
PO aprueba plan
    ↓
Planning Service publica: planning.plan.approved
    ↓
OrchestratorPlanningConsumer
    ↓
DeriveSubtasksUseCase.execute(story_id, plan_id)
    ├─ 1. Fetch story from Context Service
    ├─ 2. Fetch plan from Planning Service
    ├─ 3. Use LLM to generate subtasks (via GeneratePlanUseCase)
    ├─ 4. Create dependency graph
    ├─ 5. Assign roles
    ├─ 6. Persist to Neo4j + Valkey
    └─ 7. Return subtasks
        ↓
Para cada subtask:
    └─ AutoDispatchService → Deliberate
```

#### Implementación Mínima

**DeriveSubtasksUseCase**:
```python
from core.agents_and_tools.agents.application.usecases import GeneratePlanUseCase
from core.orchestrator.domain.tasks.subtask import Subtask
from services.orchestrator.domain.ports import ContextServicePort, GraphCommandPort

class DeriveSubtasksUseCase:
    """Derive atomic subtasks from a user story."""

    def __init__(
        self,
        context_client: ContextServicePort,
        graph_command: GraphCommandPort,
        plan_generator: GeneratePlanUseCase,
    ):
        self.context_client = context_client
        self.graph_command = graph_command
        self.plan_generator = plan_generator

    async def execute(
        self,
        story_id: str,
        plan_id: str,
        roles: list[str],
    ) -> list[Subtask]:
        # 1. Fetch story from Context Service
        story = await self.context_client.get_story(story_id)

        # 2. Build task description for LLM
        task_description = f"""
        Analyze the following user story and break it down into atomic subtasks.

        Story: {story.title}
        Description: {story.description}
        Acceptance Criteria: {story.acceptance_criteria}

        For each subtask, provide:
        - task_id: unique identifier
        - title: short title
        - description: detailed description
        - role: DEV, QA, or ARCHITECT
        - dependencies: list of task_ids that must complete first
        - priority: 1-10 (1 = highest)
        - estimated_hours: effort estimate
        """

        # 3. Use GeneratePlanUseCase to generate subtasks via LLM
        plan = await self.plan_generator.execute(
            task=task_description,
            context="",  # No additional context needed
            role="ARCHITECT",  # Architect decomposes stories
            available_tools={},
            constraints=None
        )

        # 4. Parse LLM response into Subtask entities
        subtasks = []
        for step in plan.steps:
            subtask = Subtask(
                task_id=step.params["task_id"],
                story_id=story_id,
                title=step.params["title"],
                description=step.params["description"],
                role=step.params["role"],
                dependencies=step.params.get("dependencies", []),
                priority=step.params.get("priority", 5),
                estimated_hours=step.params.get("estimated_hours", 4),
                status="PENDING"
            )
            subtasks.append(subtask)

        # 5. Persist to Neo4j
        for subtask in subtasks:
            # Create Task node
            await self.graph_command.upsert_entity(
                "Task",
                subtask.task_id,
                {
                    "task_id": subtask.task_id,
                    "story_id": subtask.story_id,
                    "title": subtask.title,
                    "description": subtask.description,
                    "role": subtask.role,
                    "priority": subtask.priority,
                    "estimated_hours": subtask.estimated_hours,
                    "status": subtask.status
                }
            )

            # Create BELONGS_TO relationship (Task → ProjectCase)
            await self.graph_command.relate(
                subtask.task_id,
                "BELONGS_TO",
                story_id,
                {}
            )

            # Create DEPENDS_ON relationships
            for dep_id in subtask.dependencies:
                await self.graph_command.relate(
                    subtask.task_id,
                    "DEPENDS_ON",
                    dep_id,
                    {}
                )

        # 6. Persist to Valkey (cache)
        # (similar to CreateTask in Context Service)

        return subtasks
```

#### Ventajas ✅
- **Mínima complejidad** - Un solo use case nuevo
- **Reutiliza código existente** - `GeneratePlanUseCase`
- **No requiere nuevo servicio** - Se queda en orchestrator
- **Rápido de implementar** - 1-2 días de desarrollo
- **Fácil de testear** - Mock LLM, mock Context Service

#### Desventajas ❌
- **Orchestrator crece en scope** - Ya coordina deliberations + deriva subtasks
- **Acoplamiento con LLM** - Depende de calidad de respuesta LLM
- **No reutilizable** - Otros servicios no pueden consumirlo fácilmente

#### Estimación
- **Desarrollo**: 2 días
- **Tests**: 1 día
- **Deployment**: 0 días (ya desplegado)
- **Total**: 3 días

---

### Solución 2: Crear Bounded Context Dedicado `task-derivation` (IDEAL)

**Descripción**: Crear un bounded context y microservicio independiente exclusivamente para task derivation.

#### Arquitectura

```
services/task-derivation/
├── domain/
│   ├── entities/
│   │   ├── subtask.py
│   │   └── dependency_graph.py
│   └── ports/
│       ├── context_service_port.py
│       ├── planning_service_port.py
│       └── graph_command_port.py
├── application/
│   └── usecases/
│       ├── derive_subtasks_usecase.py
│       └── analyze_dependencies_usecase.py
├── infrastructure/
│   ├── adapters/
│   │   ├── grpc_context_adapter.py
│   │   ├── grpc_planning_adapter.py
│   │   └── neo4j_command_adapter.py
│   └── mappers/
│       └── subtask_mapper.py
├── server.py                                  ← gRPC Server
├── Dockerfile
└── requirements.txt
```

#### API (gRPC)

```protobuf
syntax = "proto3";
package fleet.task_derivation.v1;

service TaskDerivationService {
  rpc DeriveSubtasks (DeriveSubtasksRequest) returns (DeriveSubtasksResponse);
  rpc GetDependencyGraph (GetDependencyGraphRequest) returns (GetDependencyGraphResponse);
  rpc ValidateDerivation (ValidateDerivationRequest) returns (ValidateDerivationResponse);
}

message DeriveSubtasksRequest {
  string story_id = 1;
  string plan_id = 2;
  repeated string roles = 3;
}

message Subtask {
  string task_id = 1;
  string story_id = 2;
  string title = 3;
  string description = 4;
  string role = 5;
  repeated string dependencies = 6;
  int32 priority = 7;
  int32 estimated_hours = 8;
}

message DeriveSubtasksResponse {
  repeated Subtask subtasks = 1;
  int32 total_tasks = 2;
  string derivation_id = 3;
}

message GetDependencyGraphRequest {
  string story_id = 1;
}

message DependencyGraphResponse {
  repeated DependencyEdge edges = 1;
  repeated string roots = 2;  // Tasks with no dependencies
  repeated string leaves = 3; // Tasks with no dependents
}

message DependencyEdge {
  string from_task = 1;
  string to_task = 2;
}
```

#### Deployment (Kubernetes)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: task-derivation
  namespace: swe-ai-fleet
spec:
  replicas: 2
  selector:
    matchLabels:
      app: task-derivation
  template:
    metadata:
      labels:
        app: task-derivation
    spec:
      containers:
      - name: task-derivation
        image: registry.underpassai.com/swe-ai-fleet/task-derivation:v1.0.0
        ports:
        - containerPort: 50060  # gRPC
        env:
        - name: CONTEXT_SERVICE_URL
          value: "context:50054"
        - name: PLANNING_SERVICE_URL
          value: "planning:50051"
        - name: NEO4J_URI
          valueFrom:
            secretKeyRef:
              name: neo4j-auth
              key: NEO4J_URI
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

#### Ventajas ✅
- **Separación de responsabilidades** - Un bounded context, una responsabilidad
- **Reutilizable** - Cualquier servicio puede consumirlo
- **Escalable independientemente** - Deploy y escala separado
- **Testeable** - Tests unitarios + integración + E2E
- **Evolvable** - Puede crecer sin afectar orchestrator
- **Clean Architecture** - Hexagonal + DDD completo

#### Desventajas ❌
- **Más complejidad inicial** - Nuevo servicio, nuevo deployment
- **Overhead de comunicación** - gRPC calls entre servicios
- **Más recursos** - CPU, memoria, pods adicionales
- **Mayor tiempo de desarrollo** - 1-2 semanas

#### Estimación
- **Desarrollo**: 1 semana
- **Tests**: 3 días
- **Deployment**: 2 días
- **Total**: 10-12 días

---

### Solución 3: Hybrid - DeriveSubtasks en Orchestrator + Extract Features del Planner (RECOMENDADO)

**Descripción**: Implementar `DeriveSubtasks` en orchestrator (Solución 1) PERO extraer y reutilizar features útiles del planner histórico.

#### Qué Extraer del Planner Histórico

1. **Context Provider Interface**
   ```python
   # De: src/swe_ai_fleet/planner/domain/interfaces.py
   # A: core/orchestrator/domain/ports/context_provider_port.py

   class ContextProviderPort(Protocol):
       async def get_role_context(
           self,
           story_id: str,
           role: str,
           phase: str,
       ) -> str:
           """Get surgical context for a specific role."""
   ```

2. **Guard Evaluator Interface**
   ```python
   # De: src/swe_ai_fleet/planner/domain/interfaces.py
   # A: services/orchestrator/domain/ports/guard_evaluator_port.py

   class GuardEvaluatorPort(Protocol):
       async def evaluate_guards(
           self,
           story_id: str,
           actor: str,
           event: str,
       ) -> dict[str, bool]:
           """Evaluate transition guards."""
   ```

3. **Dependency Graph Logic**
   ```python
   # De: src/swe_ai_fleet/planner/domain/interfaces.py (GraphStore)
   # A: services/orchestrator/application/services/dependency_graph_service.py

   class DependencyGraphService:
       async def create_dependency_graph(
           self,
           subtasks: list[Subtask],
       ) -> DependencyGraph:
           """Create graph of task dependencies."""

       async def get_execution_order(
           self,
           graph: DependencyGraph,
       ) -> list[list[str]]:
           """Get topological sort of tasks (execution order)."""

       async def detect_cycles(
           self,
           graph: DependencyGraph,
       ) -> list[list[str]]:
           """Detect circular dependencies."""
   ```

4. **Human Gates (for future)**
   ```python
   # De: src/swe_ai_fleet/planner/fsm.py
   # A: services/orchestrator/domain/entities/human_gate.py

   @dataclass(frozen=True)
   class HumanGate:
       name: str
       description: str
       required_actor: str | None
       approved_at: str | None
       approved_by: str | None
   ```

#### Arquitectura Hybrid

```
services/orchestrator/
├── application/
│   ├── usecases/
│   │   └── derive_subtasks_usecase.py        ← NUEVO (Solución 1)
│   └── services/
│       ├── dependency_graph_service.py       ← EXTRAÍDO del planner
│       └── auto_dispatch_service.py          ← YA EXISTE
├── domain/
│   ├── entities/
│   │   ├── subtask.py                        ← NUEVO
│   │   ├── dependency_graph.py               ← EXTRAÍDO del planner
│   │   └── human_gate.py                     ← EXTRAÍDO del planner
│   └── ports/
│       ├── context_provider_port.py          ← EXTRAÍDO del planner
│       └── guard_evaluator_port.py           ← EXTRAÍDO del planner
└── server.py
    └── DeriveSubtasks()                      ← IMPLEMENTAR
```

#### Flujo Completo

```
PO aprueba plan
    ↓
Planning Service publica: planning.plan.approved
    ↓
OrchestratorPlanningConsumer
    ↓
DeriveSubtasksUseCase.execute(story_id, plan_id)
    ├─ 1. Fetch story (Context Service)
    ├─ 2. Fetch plan (Planning Service)
    ├─ 3. Generate subtasks (LLM via GeneratePlanUseCase)
    ├─ 4. DependencyGraphService.create_dependency_graph()   ← EXTRAÍDO
    ├─ 5. DependencyGraphService.detect_cycles()             ← EXTRAÍDO
    ├─ 6. Assign roles
    ├─ 7. Persist to Neo4j + Valkey
    └─ 8. Return subtasks
        ↓
DependencyGraphService.get_execution_order()
    ↓
Para cada batch en execution order:
    └─ AutoDispatchService → Deliberate (en paralelo dentro del batch)
```

#### Ventajas ✅
- **Reutiliza código existente** - Planner histórico + Orchestrator
- **Complejidad media** - Más que Solución 1, menos que Solución 2
- **Separación de responsabilidades** - Interfaces bien definidas
- **Testeable** - Mock interfaces, tests unitarios
- **Escalable** - Puede evolucionar a Solución 2 si es necesario
- **ROI alto** - Aprovecha trabajo ya hecho (planner histórico)

#### Desventajas ❌
- **Refactor necesario** - Extraer código del planner histórico
- **Testing del código extraído** - Código sin tests originales
- **Orchestrator crece** - Más scope que Solución 1

#### Estimación
- **Desarrollo**: 4 días (implementar + extraer + integrar)
- **Tests**: 2 días (tests unitarios + integración)
- **Deployment**: 0 días (ya desplegado)
- **Total**: 6 días

---

## 📊 Comparación de Soluciones

| Aspecto | Solución 1 (Simple) | Solución 2 (Ideal) | Solución 3 (Hybrid) |
|---------|---------------------|-------------------|---------------------|
| **Complejidad** | Baja | Alta | Media |
| **Tiempo de desarrollo** | 3 días | 10-12 días | 6 días |
| **Reutilización de código** | Alta (GeneratePlanUseCase) | Media | Muy Alta (planner + orchestrator) |
| **Separación de responsabilidades** | ❌ Orchestrator crece | ✅ Bounded context dedicado | ⚠️ Orchestrator crece algo |
| **Escalabilidad** | ❌ Acoplado a orchestrator | ✅ Independiente | ⚠️ Puede migrar a Solución 2 |
| **Testabilidad** | ✅ Fácil | ✅ Muy fácil | ✅ Fácil |
| **Deployment** | ✅ No necesario | ❌ Nuevo servicio | ✅ No necesario |
| **Recursos (CPU/RAM)** | ✅ Sin overhead | ❌ Pods adicionales | ✅ Sin overhead |
| **gRPC Overhead** | ✅ No | ❌ Sí | ✅ No |
| **Dependency Graph** | ❌ Básico | ✅ Completo | ✅ Extraído del planner |
| **Guard Evaluation** | ❌ No | ✅ Sí | ✅ Interfaz del planner |
| **Human Gates** | ❌ No | ✅ Sí | ✅ Entidad del planner |
| **Event Store** | ❌ No | ✅ Sí | ⚠️ Puede agregar después |

---

## 🎯 Recomendación Final

### ✅ **Solución 3: Hybrid** (RECOMENDADO)

**Justificación**:

1. **Balance óptimo entre complejidad y valor**
   - No requiere crear nuevo microservicio (ahorra tiempo/recursos)
   - Reutiliza código ya existente (planner histórico)
   - Aprovecha arquitectura hexagonal del planner

2. **ROI alto**
   - 6 días de desarrollo vs 10-12 días de Solución 2
   - Aprovecha 1,612 líneas del planner histórico
   - Evita escribir código desde cero

3. **Escalabilidad futura**
   - Si task derivation crece mucho, fácil migrar a Solución 2
   - Interfaces bien definidas facilitan refactor
   - Bounded context puede extraerse después

4. **Testeable y mantenible**
   - Código extraído del planner tiene buena arquitectura
   - Interfaces permiten mocking fácil
   - Tests unitarios + integración factibles

5. **Resuelve el GAP crítico**
   - Deriva subtasks desde historias ✅
   - Crea grafo de dependencias ✅
   - Asigna roles ✅
   - Prioriza tasks ✅
   - Detecta dependencias circulares ✅

### Implementación Sugerida (Fase 1)

**Semana 1**: Extracción y Setup
1. Extraer interfaces del planner histórico
2. Crear `DeriveSubtasksUseCase`
3. Crear `DependencyGraphService`
4. Crear entidad `Subtask`

**Semana 2**: Implementación y Tests
5. Implementar `DeriveSubtasks` RPC
6. Integrar con `GeneratePlanUseCase`
7. Integrar con Context Service
8. Tests unitarios (20+ tests)

**Semana 3**: Integración y E2E
9. Integrar con `OrchestratorPlanningConsumer`
10. Integrar con `AutoDispatchService`
11. Tests de integración
12. Tests E2E completos

**Semana 4**: Deployment y Validación
13. Deploy a staging
14. Validación con PO
15. Deploy a producción
16. Monitoring y observabilidad

### Migración Futura a Solución 2 (Opcional)

Si en 3-6 meses:
- Task derivation se vuelve muy complejo
- Se necesita escalar independientemente
- Se requieren features avanzadas (ML-based derivation, etc.)

**Entonces**:
- Extraer bounded context dedicado
- Mover código a `services/task-derivation/`
- Crear gRPC API
- Deploy independiente

**Ventaja de Solución 3**: Las interfaces ya están definidas, migración es simple refactor.

---

## 🚨 Riesgos y Mitigaciones

### Riesgo 1: Calidad de Derivación LLM

**Problema**: LLM puede generar subtasks de baja calidad.

**Mitigación**:
- Prompt engineering específico
- Validación de outputs (schema validation)
- Human-in-the-loop review (PO aprueba derivación)
- Fallback a derivación manual

### Riesgo 2: Dependencias Circulares

**Problema**: LLM puede generar dependencias circulares.

**Mitigación**:
- `DependencyGraphService.detect_cycles()` implementado
- Fail-fast si se detectan ciclos
- Notificar a PO para corrección manual

### Riesgo 3: Complejidad de Orchestrator

**Problema**: Orchestrator crece en scope (deliberation + task derivation).

**Mitigación**:
- Interfaces bien definidas
- Separation of concerns clara
- Migración a Solución 2 si crece demasiado

### Riesgo 4: Código del Planner Sin Tests

**Problema**: Código extraído del planner no tiene tests.

**Mitigación**:
- Escribir tests ANTES de integrar
- Code review exhaustivo
- Tests unitarios + integración
- Coverage > 90%

---

## 📋 Criterios de Decisión

| Criterio | Solución 1 | Solución 2 | Solución 3 |
|----------|-----------|-----------|-----------|
| **Tiempo de implementación** | ✅ 3 días | ❌ 10-12 días | ⚠️ 6 días |
| **Complejidad** | ✅ Baja | ❌ Alta | ⚠️ Media |
| **Reutilización de código** | ⚠️ Media | ⚠️ Media | ✅ Alta |
| **Separación de responsabilidades** | ❌ Baja | ✅ Alta | ⚠️ Media |
| **Escalabilidad futura** | ❌ Limitada | ✅ Alta | ✅ Media-Alta |
| **Overhead de infraestructura** | ✅ Ninguno | ❌ Alto | ✅ Ninguno |
| **ROI** | ⚠️ Medio | ❌ Bajo (inicial) | ✅ Alto |
| **Riesgo técnico** | ⚠️ Medio | ✅ Bajo | ⚠️ Medio |

### Matriz de Decisión (Weighted Scoring)

| Criterio | Peso | Sol 1 | Sol 2 | Sol 3 |
|----------|------|-------|-------|-------|
| Tiempo de implementación | 20% | 5 | 2 | 4 |
| ROI | 25% | 3 | 2 | 5 |
| Escalabilidad | 15% | 2 | 5 | 4 |
| Complejidad (menor es mejor) | 15% | 5 | 2 | 4 |
| Separación de responsabilidades | 15% | 2 | 5 | 3 |
| Overhead infraestructura (menor es mejor) | 10% | 5 | 1 | 5 |
| **TOTAL WEIGHTED** | 100% | **3.55** | **3.05** | **4.15** |

**Ganador**: ✅ **Solución 3 (Hybrid)** - 4.15/5.0

---

## 💡 Conclusiones

### Principales Hallazgos

1. **GAP crítico existe**: Task derivation no está implementado en ningún bounded context
2. **Planner histórico tiene valor**: 1,612 líneas de código con buena arquitectura (sin tests)
3. **No revivir planner completo**: Demasiado overlap con Planning Service
4. **Solución 3 es óptima**: Balance perfecto entre tiempo, ROI y escalabilidad

### Recomendaciones para el Arquitecto

1. **Implementar Solución 3 (Hybrid)**:
   - Extraer interfaces del planner histórico
   - Implementar `DeriveSubtasksUseCase` en orchestrator
   - Integrar con `AutoDispatchService`

2. **Timeline Sugerido**:
   - Sprint 1 (2 semanas): Implementación + Tests
   - Sprint 2 (1 semana): Integración E2E
   - Sprint 3 (1 semana): Deployment + Validación

3. **Criterios de Éxito**:
   - ✅ PO puede aprobar plan → Orchestrator deriva subtasks automáticamente
   - ✅ Subtasks tienen dependencias correctas (grafo sin ciclos)
   - ✅ Subtasks se asignan a roles automáticamente
   - ✅ Tests > 90% coverage
   - ✅ E2E tests pass (test_002 actualizado)

4. **Migración Futura**:
   - Si task derivation crece, evaluar Solución 2 en 6 meses
   - Interfaces ya definidas facilitan migración

---

## 📝 Próximos Pasos

### Inmediato (Esta Semana)
1. ✅ Review este informe con el equipo
2. ⏳ Decisión final: Solución 1, 2 o 3
3. ⏳ Crear epic en backlog
4. ⏳ Estimar esfuerzo detallado

### Corto Plazo (Próximas 2 Semanas)
5. ⏳ Extraer código del planner histórico (branch `feature/planner-po-facing`)
6. ⏳ Implementar `DeriveSubtasksUseCase`
7. ⏳ Implementar `DependencyGraphService`
8. ⏳ Tests unitarios (>90% coverage)

### Medio Plazo (Próximo Sprint)
9. ⏳ Integrar con `OrchestratorPlanningConsumer`
10. ⏳ Actualizar `test_002_multi_agent_planning.py`
11. ⏳ Deploy a staging
12. ⏳ Validación con PO

### Largo Plazo (3-6 Meses)
13. ⏳ Evaluar migración a Solución 2 (si task derivation crece)
14. ⏳ Implementar Human Gates (aprobación manual de derivación)
15. ⏳ Implementar Event Store (auditoría de derivaciones)

---

**Documentos relacionados**:
- `PLANNING_LOGIC_AUDIT_BOUNDED_CONTEXTS.md` - Auditoría de bounded contexts actuales
- `PLANNER_GIT_HISTORY_AUDIT.md` - Auditoría del planner histórico

**Decisión final**: Pendiente de aprobación del Software Architect (Tirso García Ibáñez)


