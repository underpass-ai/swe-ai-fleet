# Implementation Roadmap - Resolución de Gaps Arquitecturales

**Fecha**: 2 de noviembre, 2025  
**Arquitecto**: Tirso García Ibáñez  
**Contexto**: Implementación de decisiones arquitecturales post-auditoría  
**Branch base**: `audit/architecture-gaps-evaluation`

---

## 🎯 Objetivo

Implementar las **4 decisiones arquitecturales** tomadas para resolver los gaps críticos identificados en la auditoría, siguiendo los principios de **DDD + Hexagonal Architecture**.

---

## 📊 Decisiones a Implementar

| # | Decisión | Opción | Timeline | Prioridad |
|---|----------|--------|----------|-----------|
| **1** | Task Derivation | Temporal en Orchestrator | 1 sem | **P0-A** |
| **2** | PO UI | Rescatar del histórico + adaptaciones | 4 sem | **P0-B** |
| **3** | RBAC | Embedded en Agent domain | 1 sem | **P0-C** |
| **4** | Timeline | Incremental "rápido" | ⏸️ TBD | **P0-D** |

---

## 🚀 Roadmap por Sprints

### Sprint 1: RBAC + Task Derivation (Semana 1)

**Objetivo**: Implementar validación de capacidades de agentes y descomposición básica de tasks.

#### 1.1 RBAC Domain Model (3 días)

**Archivos a crear**:

```
core/orchestrator/domain/
├── value_objects/
│   ├── role.py              # Role Value Object
│   ├── action.py            # Action Value Object
│   └── agent_id.py          # AgentId Value Object (si no existe)
├── entities/
│   └── agent.py             # Agent Aggregate Root (extender existente)
└── factories/
    └── role_factory.py      # RoleFactory (predefined roles)
```

**Tests**:
```
tests/unit/orchestrator/domain/
├── value_objects/
│   ├── test_role.py
│   ├── test_action.py
│   └── test_agent_id.py
├── entities/
│   └── test_agent_rbac.py
└── factories/
    └── test_role_factory.py
```

**Acceptance Criteria**:
- [ ] Role Value Object con validación de roles válidos
- [ ] Action Value Object con acciones predefinidas
- [ ] Agent.can_execute() implementado
- [ ] RoleFactory con 5 roles (architect, qa, po, developer, devops)
- [ ] Scope compatibility validation (technical, business, quality, operations)
- [ ] 100% coverage en tests de dominio
- [ ] No reflection, no setattr, no dynamic mutation
- [ ] Frozen dataclasses con fail-fast validation

**Entregables**:
- ✅ Modelo DDD completo con tests
- ✅ Documentation en docstrings
- ✅ Self-check de DDD compliance

---

#### 1.2 Task Derivation en Orchestrator (4 días)

**Archivos a modificar**:

```
core/orchestrator/
├── application/
│   └── usecases/
│       └── derive_subtasks_usecase.py  # Implementar lógica
├── infrastructure/
│   └── adapters/
│       └── llm_task_derivation_adapter.py  # LLM prompt para derivar tasks
└── domain/
    └── entities/
        └── task.py  # Extender Task entity si es necesario
```

**Tests**:
```
tests/unit/orchestrator/usecases/
└── test_derive_subtasks_usecase.py

tests/integration/orchestrator/
└── test_task_derivation_e2e.py
```

**Acceptance Criteria**:
- [ ] `DeriveSubtasksUseCase` implementado (ya no retorna UNIMPLEMENTED)
- [ ] Story → Tasks decomposition funcional
- [ ] LLM adapter usa vLLM con prompt de descomposición
- [ ] Tasks generados tienen estructura válida (TaskSpec)
- [ ] Integration con Neo4j para persistir task graph
- [ ] Tests unitarios con mock del LLM
- [ ] Integration test E2E con vLLM real
- [ ] ⚠️ Documentar deuda técnica: "Refactor a Planner Service en P1"

**Entregables**:
- ✅ DeriveSubtasks funcional
- ✅ E2E test passing
- ⚠️ Deuda técnica documentada

---

### Sprint 2: API Gateway + Planning Service (Semanas 2-3)

**Objetivo**: Crear infraestructura para que el UI pueda comunicarse con los microservicios.

#### 2.1 Planning Service (Python gRPC) (1 semana)

**Estructura**:

```
services/planning/
├── planning/
│   ├── domain/
│   │   ├── entities/
│   │   │   └── story.py
│   │   └── value_objects/
│   │       ├── story_id.py
│   │       ├── story_state.py
│   │       └── dor_score.py
│   ├── application/
│   │   ├── ports/
│   │   │   ├── messaging_port.py
│   │   │   └── storage_port.py
│   │   └── usecases/
│   │       ├── create_story_usecase.py
│   │       ├── transition_story_usecase.py
│   │       ├── list_stories_usecase.py
│   │       ├── approve_decision_usecase.py
│   │       └── reject_decision_usecase.py
│   ├── infrastructure/
│   │   └── adapters/
│   │       ├── nats_messaging_adapter.py
│   │       ├── neo4j_storage_adapter.py
│   │       └── grpc_server_adapter.py
│   └── server.py
├── specs/
│   └── planning.proto  # gRPC API spec
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
├── pyproject.toml
└── README.md
```

**gRPC API (planning.proto)**:

```protobuf
syntax = "proto3";
package planning;

service PlanningService {
  rpc CreateStory(CreateStoryRequest) returns (CreateStoryResponse);
  rpc ListStories(ListStoriesRequest) returns (ListStoriesResponse);
  rpc TransitionStory(TransitionStoryRequest) returns (TransitionStoryResponse);
  rpc ApproveDecision(ApproveDecisionRequest) returns (ApproveDecisionResponse);
  rpc RejectDecision(RejectDecisionRequest) returns (RejectDecisionResponse);
}

message CreateStoryRequest {
  string title = 1;
  string brief = 2;
  string created_by = 3;  // PO user ID
}

message CreateStoryResponse {
  string story_id = 1;
  string state = 2;
  int32 dor_score = 3;
}

message ListStoriesRequest {
  optional string filter_state = 1;  // e.g., "DRAFT", "READY"
}

message ListStoriesResponse {
  repeated Story stories = 1;
}

message Story {
  string story_id = 1;
  string title = 2;
  string brief = 3;
  string state = 4;
  int32 dor_score = 5;
  string created_by = 6;
  int64 created_at = 7;  // Unix timestamp
}

message TransitionStoryRequest {
  string story_id = 1;
  string event = 2;  // e.g., "approve_scope", "start_design"
  string actor = 3;  // e.g., "po", "architect"
}

message TransitionStoryResponse {
  string new_state = 1;
  bool success = 2;
  string error_message = 3;
}

message ApproveDecisionRequest {
  string story_id = 1;
  string decision_id = 2;
  string approved_by = 3;  // PO user ID
  string comment = 4;
}

message ApproveDecisionResponse {
  bool success = 1;
  string message = 2;
}

message RejectDecisionRequest {
  string story_id = 1;
  string decision_id = 2;
  string rejected_by = 3;
  string reason = 4;
}

message RejectDecisionResponse {
  bool success = 1;
  string message = 2;
}
```

**Acceptance Criteria**:
- [ ] Planning Service implementado en Python con Hexagonal Architecture
- [ ] Domain entities: Story, StoryState, DORScore
- [ ] Use cases implementados con DI
- [ ] gRPC server funcional
- [ ] NATS adapter publica eventos (story.created, story.transitioned, decision.approved)
- [ ] Neo4j adapter persiste stories
- [ ] Tests unitarios >90% coverage
- [ ] Integration tests con NATS + Neo4j
- [ ] Dockerfile + deployment K8s
- [ ] Desplegado en namespace swe-ai-fleet

**Entregables**:
- ✅ Planning Service funcional en K8s
- ✅ gRPC APIs disponibles (internal-planning:50051)
- ✅ NATS events publishing

---

#### 2.2 API Gateway (Python FastAPI) (1.5 semanas)

**Estructura**:

```
services/api-gateway/
├── gateway/
│   ├── routers/
│   │   ├── planner_router.py      # /api/planner/* endpoints
│   │   ├── context_router.py      # /api/context/* endpoints
│   │   └── events_router.py       # /api/events/stream (SSE)
│   ├── adapters/
│   │   ├── planning_grpc_client.py
│   │   ├── context_grpc_client.py
│   │   └── nats_sse_bridge.py
│   ├── middleware/
│   │   ├── cors_middleware.py
│   │   └── auth_middleware.py  # Future: JWT validation
│   ├── models/
│   │   ├── story_dto.py
│   │   └── context_dto.py
│   └── server.py
├── specs/
│   └── openapi.yaml  # REST API documentation
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
├── pyproject.toml
└── README.md
```

**REST API Endpoints**:

```
GET    /api/planner/stories                  → Planning.ListStories
POST   /api/planner/stories                  → Planning.CreateStory
POST   /api/planner/stories/{id}/transition  → Planning.TransitionStory
POST   /api/planner/decisions/{id}/approve   → Planning.ApproveDecision
POST   /api/planner/decisions/{id}/reject    → Planning.RejectDecision

GET    /api/context/{storyId}/{role}/{phase} → Context.GetContext
GET    /api/events/stream?storyId={id}       → SSE bridge to NATS
```

**SSE Bridge Implementation**:

```python
# gateway/routers/events_router.py

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from gateway.adapters.nats_sse_bridge import NATSSSEBridge


router = APIRouter()


@router.get("/stream")
async def event_stream(request: Request, story_id: str):
    """
    Server-Sent Events endpoint.
    
    Subscribes to NATS topics:
    - story.events.{story_id}
    - agent.deliberations.{story_id}
    - context.updated.{story_id}
    
    Streams updates to UI in real-time.
    """
    bridge = NATSSSEBridge()
    
    async def event_generator():
        async for event in bridge.subscribe(story_id=story_id):
            if await request.is_disconnected():
                break
            
            yield {
                "event": event.type,
                "data": event.payload,
            }
    
    return EventSourceResponse(event_generator())
```

**Acceptance Criteria**:
- [ ] FastAPI server implementado
- [ ] REST → gRPC translation para Planning Service
- [ ] REST → gRPC translation para Context Service
- [ ] SSE bridge funcional (NATS subscriptions → Server-Sent Events)
- [ ] CORS configurado para localhost:5173 (Vite dev) + *.underpassai.com
- [ ] Error handling completo (gRPC errors → HTTP status codes)
- [ ] OpenAPI documentation auto-generada
- [ ] Tests unitarios para routers
- [ ] Integration tests con servicios reales
- [ ] Dockerfile + deployment K8s
- [ ] Ingress configurado en https://api.underpassai.com

**Entregables**:
- ✅ API Gateway funcional en K8s
- ✅ REST APIs disponibles en https://api.underpassai.com
- ✅ SSE streaming funcional

---

### Sprint 3: UI Adaptaciones + Integration (Semana 4)

**Objetivo**: Adaptar el UI rescatado a las nuevas APIs y completar flujo E2E.

#### 3.1 UI Adaptaciones (3 días)

**Archivos a modificar**:

```
ui/po-react/src/
├── components/
│   ├── PlannerBoard.tsx           # Modificar
│   ├── ContextViewer.tsx          # Modificar
│   ├── DeliberationViewer.tsx     # NUEVO
│   └── DecisionApproval.tsx       # NUEVO
├── hooks/
│   └── useSSE.ts                  # Modificar (nuevos eventos)
├── api/
│   └── client.ts                  # NUEVO (fetch wrapper)
└── App.tsx                        # Modificar layout
```

**PlannerBoard.tsx - Cambios**:

```typescript
// Añadir decision approval buttons
<div className="flex gap-2">
  <button
    className="px-3 py-1 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700"
    onClick={() => approveDecision(story.decision_id)}
  >
    Approve Decision
  </button>
  <button
    className="px-3 py-1 text-xs bg-red-600 text-white rounded-lg hover:bg-red-700"
    onClick={() => rejectDecision(story.decision_id)}
  >
    Reject
  </button>
</div>
```

**DeliberationViewer.tsx - Nuevo Componente**:

```typescript
export default function DeliberationViewer({ storyId }: { storyId: string }) {
  const [deliberations, setDeliberations] = useState<Deliberation[]>([])
  
  useSSE(`/api/events/stream?storyId=${storyId}`, (event) => {
    if (event.type === 'agent.deliberation.completed') {
      setDeliberations(prev => [...prev, event.data])
    }
  })
  
  return (
    <div className="space-y-4">
      <h3 className="font-medium">Agent Deliberations</h3>
      {deliberations.map(d => (
        <article key={d.deliberation_id} className="border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="font-medium">{d.agent_role}</span>
            <span className="text-xs text-gray-500">Round {d.round}</span>
          </div>
          <p className="text-sm">{d.proposal}</p>
          <div className="mt-2 flex items-center gap-2">
            <span className={`px-2 py-1 text-xs rounded-full ${getScoreColor(d.score)}`}>
              Score: {d.score}/100
            </span>
          </div>
        </article>
      ))}
    </div>
  )
}
```

**Acceptance Criteria**:
- [ ] PlannerBoard.tsx adaptado a nuevas APIs
- [ ] DeliberationViewer.tsx implementado
- [ ] DecisionApproval.tsx implementado (approve/reject workflow)
- [ ] SSE hook actualizado para nuevos event types
- [ ] API client wrapper implementado (error handling)
- [ ] UI funcional con API Gateway
- [ ] Tests E2E con Playwright/Cypress
- [ ] Dockerfile actualizado
- [ ] Deployment a K8s (https://po.underpassai.com)

**Entregables**:
- ✅ UI funcional desplegado en K8s
- ✅ Flujo E2E completo (PO crea story → agents deliberan → PO aprueba)

---

#### 3.2 Integration E2E Testing (2 días)

**Tests a crear**:

```
tests/e2e/
├── test_po_workflow_complete.py
├── test_decision_approval_flow.py
├── test_sse_live_updates.py
└── test_rbac_enforcement.py
```

**test_po_workflow_complete.py**:

```python
"""
E2E Test: Complete PO Workflow

Scenario:
1. PO creates story via UI
2. Story enters DRAFT state
3. Orchestrator triggers agent deliberation
4. Architect, Developer, QA propose solutions
5. Council ranks proposals
6. Winner proposal sent to PO for approval
7. PO approves decision via UI
8. Orchestrator executes winning proposal
9. Workspace validates results
10. Story transitions to DONE
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_po_creates_story_and_approves_decision(page: Page):
    # Step 1: Navigate to PO UI
    page.goto("https://po.underpassai.com")
    
    # Step 2: Create story
    page.fill('input[placeholder*="Story title"]', "As a user, I want authentication")
    page.fill('textarea[placeholder*="Brief"]', "Implement JWT-based authentication")
    page.click('button:has-text("Create Story")')
    
    # Step 3: Wait for story to appear
    expect(page.locator('article').first).to_contain_text("authentication")
    
    # Step 4: Get story ID
    story_card = page.locator('article').first
    story_id = story_card.get_attribute('data-story-id')
    
    # Step 5: Wait for deliberations (SSE updates)
    # This will take ~30-60 seconds for agents to deliberate
    page.wait_for_selector(
        f'[data-deliberation-story="{story_id}"]',
        timeout=90_000  # 90 seconds
    )
    
    # Step 6: Verify deliberations appeared
    deliberations = page.locator('[data-deliberation-story]').all()
    assert len(deliberations) >= 3  # Architect, Dev, QA minimum
    
    # Step 7: Approve winning proposal
    page.click('button:has-text("Approve Decision")')
    
    # Step 8: Confirm approval
    page.click('button:has-text("Confirm")')
    
    # Step 9: Wait for execution to complete
    page.wait_for_selector(
        f'[data-story-id="{story_id}"] .state:has-text("DONE")',
        timeout=120_000  # 2 minutes for execution
    )
    
    # Step 10: Verify final state
    expect(story_card).to_contain_text("DONE")
    expect(story_card).to_have_class("state-done")
```

**Acceptance Criteria**:
- [ ] E2E test covering complete PO workflow (create → deliberate → approve → execute)
- [ ] RBAC enforcement test (QA cannot approve design, Architect cannot approve business)
- [ ] SSE live updates test (UI receives events in real-time)
- [ ] Performance test (deliberation completes in <60s, execution in <120s)
- [ ] All tests pass in CI/CD pipeline
- [ ] Tests run against real K8s deployment (not mocks)

**Entregables**:
- ✅ E2E test suite completo
- ✅ CI/CD pipeline ejecuta tests E2E
- ✅ Performance benchmarks documentados

---

## 📊 Timeline Summary

### Opción A: Timeline Comprimido (Paralelización)

| Sprint | Semanas | Features | Paralelo | Total |
|--------|---------|----------|----------|-------|
| **Sprint 1** | 1 | RBAC + Task Derivation | No | **1 sem** |
| **Sprint 2** | 2 | Planning Service + API Gateway | **Sí** (2 devs) | **1.5 sem** |
| **Sprint 3** | 1 | UI Adaptaciones + E2E Tests | No | **1 sem** |

**TOTAL: 3.5-4 semanas** (vs 6 semanas)

**Requisitos**:
- 2 desarrolladores (uno en Planning, otro en API Gateway)
- Infraestructura K8s estable
- vLLM server operativo

---

### Opción B: Scope Reducido P0 (Mínimo Viable)

| Sprint | Semanas | Features (Mínimo) | Total |
|--------|---------|-------------------|-------|
| **Sprint 1** | 1 | RBAC + Task Derivation básico | **1 sem** |
| **Sprint 2** | 2 | Planning Service (solo CreateStory + ApproveDecision) + API Gateway básico | **1.5 sem** |
| **Sprint 3** | 1 | UI mínimo (solo decision approval, sin SSE) | **0.5 sem** |

**TOTAL: 3 semanas**

**Scope eliminado (movido a P1)**:
- SSE live updates (usar polling en su lugar)
- DeliberationViewer (solo mostrar propuesta final)
- TransitionStory completo (solo estados mínimos)
- E2E tests exhaustivos (solo happy path)

**⚠️ Trade-off**: UX degradada (no live updates), deuda técnica incrementada

---

### Opción C: Ambas (Compresión + Reducción)

| Sprint | Semanas | Features | Paralelo | Total |
|--------|---------|----------|----------|-------|
| **Sprint 1** | 0.5 | RBAC (sin tests exhaustivos) | No | **0.5 sem** |
| **Sprint 2** | 1.5 | Planning + API Gateway (scope mínimo) | **Sí** | **1 sem** |
| **Sprint 3** | 1 | UI mínimo + E2E básico | No | **0.5 sem** |

**TOTAL: 2 semanas**

**⚠️ Riesgos**:
- Coverage <80% (violates quality gate)
- Features incompletas
- Bugs en producción
- Deuda técnica significativa

---

## ⚠️ DECISIÓN PENDIENTE: Confirmar Timeline

**Arquitecto, por favor confirma cuál de estas opciones es "rápido"**:

- [ ] **Opción A**: 3.5-4 semanas (paralelización, scope completo)
- [ ] **Opción B**: 3 semanas (scope reducido, UX mínima)
- [ ] **Opción C**: 2 semanas (compresión + reducción, alto riesgo)

**Recomendación del asistente**: **Opción A** (mejor balance calidad/velocidad)

---

## 📝 Próximos Pasos Inmediatos

1. ✅ Confirmar Decision 4 (timeline approach)
2. Crear branches de feature:
   - `feature/rbac-domain-model`
   - `feature/task-derivation-orchestrator`
   - `feature/planning-service`
   - `feature/api-gateway`
   - `feature/ui-adaptations`
3. Asignar recursos (1-2 devs)
4. Iniciar Sprint 1 (RBAC + Task Derivation)

---

## 🎯 Definition of Done

**Para cada feature**:
- [ ] Código implementado siguiendo DDD + Hexagonal Architecture
- [ ] No reflection, no setattr, no dynamic mutation
- [ ] Frozen dataclasses con fail-fast validation
- [ ] Tests unitarios ≥90% coverage
- [ ] Integration tests passing
- [ ] Linter errors = 0 (Ruff)
- [ ] Documentation en docstrings
- [ ] Self-check section confirming rules compliance
- [ ] Deployed a K8s (for services)
- [ ] E2E tests passing

**Para el proyecto completo (P0)**:
- [ ] PO puede crear story vía UI
- [ ] Agents deliberan automáticamente
- [ ] PO recibe propuesta ganadora
- [ ] PO puede aprobar/rechazar decisión
- [ ] RBAC enforcement funciona (Architect no puede aprobar business)
- [ ] Execution se dispara tras aprobación
- [ ] Story transiciona a DONE
- [ ] E2E test completo passing
- [ ] Sistema desplegado en K8s con TLS
- [ ] Performance: deliberation <60s, execution <120s

---

**Roadmap listo para ejecución una vez confirmada la Decision 4.** 🚀

