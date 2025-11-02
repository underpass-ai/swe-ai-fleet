# Decisiones Arquitecturales Finales - 2 Noviembre 2025

**Arquitecto**: Tirso García Ibáñez (Software Architect & Founder)
**Asistente**: AI Assistant (Claude Sonnet 4.5)
**Estado**: ✅ **TODAS LAS DECISIONES CONFIRMADAS**
**Branch**: `audit/architecture-gaps-evaluation`

---

## 🎯 Resumen Ejecutivo

Tras la auditoría arquitectural completa que identificó 6 gaps críticos post-cleanup (PR #86), se tomaron **4 decisiones arquitecturales estratégicas** para resolver los blockers P0 y restaurar la funcionalidad del sistema como "equipo ágil virtual con human-in-the-loop".

**Timeline total**: 10 semanas (6 sem P0 + 4 sem P1)
**Enfoque**: MVP-first con arquitectura limpia (sin deuda técnica)

---

## ✅ Decisión 1: Planning Service

### Pregunta
¿Cómo gestionamos el FSM (Finite State Machine) de stories?

### Opciones Evaluadas
- **A. Nuevo Planning en Python** ← ✅ **ELEGIDA**
- B. FSM en Context Service
- C. Migrar del planner histórico

### Decisión Final
**Opción A - Nuevo Planning Service en Python**

### Justificación
1. **Arquitectura limpia**: DDD + Hexagonal desde cero
2. **Evita deuda técnica**: El planner histórico está WIP (1,612 líneas sin tests)
3. **Separación de responsabilidades**: Planning es un bounded context propio
4. **Mantenibilidad**: Código nuevo, documentado, con tests >90%

### Especificación Técnica

**Estructura del servicio**:
```
services/planning/
├── planning/
│   ├── domain/
│   │   ├── entities/
│   │   │   └── story.py               # Story aggregate root
│   │   └── value_objects/
│   │       ├── story_id.py
│   │       ├── story_state.py          # FSM states
│   │       └── dor_score.py            # Definition of Ready score
│   ├── application/
│   │   ├── ports/
│   │   │   ├── messaging_port.py       # NATS publishing
│   │   │   └── storage_port.py         # Neo4j persistence
│   │   └── usecases/
│   │       ├── create_story_usecase.py
│   │       ├── transition_story_usecase.py
│   │       ├── approve_decision_usecase.py
│   │       └── reject_decision_usecase.py
│   └── infrastructure/
│       └── adapters/
│           ├── nats_messaging_adapter.py
│           ├── neo4j_storage_adapter.py
│           └── grpc_server_adapter.py
├── specs/
│   └── planning.proto                  # gRPC API
├── tests/
│   ├── unit/
│   └── integration/
└── Dockerfile
```

**gRPC API** (planning.proto):
```protobuf
service PlanningService {
  rpc CreateStory(CreateStoryRequest) returns (CreateStoryResponse);
  rpc ListStories(ListStoriesRequest) returns (ListStoriesResponse);
  rpc TransitionStory(TransitionStoryRequest) returns (TransitionStoryResponse);
  rpc ApproveDecision(ApproveDecisionRequest) returns (ApproveDecisionResponse);
  rpc RejectDecision(RejectDecisionRequest) returns (RejectDecisionResponse);
}
```

**FSM States**:
```python
DRAFT → PO_REVIEW → READY_FOR_PLANNING → IN_PROGRESS → CODE_REVIEW → TESTING → DONE
```

### Timeline
- **Semanas 1-2**: Implementación completa
- **Coverage**: >90% tests unitarios + integration tests

### Deployment
- Namespace: `swe-ai-fleet`
- Service: `internal-planning:50051` (gRPC)
- Replicas: 2
- Resources: 500m CPU, 1Gi RAM

---

## ✅ Decisión 2: PO UI

### Pregunta
¿Qué stack usamos para la interfaz del Product Owner?

### Opciones Evaluadas
- A. React + API Gateway (desde cero)
- B. React + gRPC-Web
- **C. Revivir UI legacy** ← ✅ **ELEGIDA**

### Decisión Final
**Opción C - Revivir UI legacy del histórico de GitHub**

### Justificación
1. **Ahorro de tiempo**: 3-4 semanas vs desarrollo desde cero
2. **Stack moderno**: React 18.2 + TypeScript + Vite + Tailwind CSS
3. **Features ya implementadas**:
   - Crear stories
   - Ver estados FSM
   - Aprobar scope
   - Context viewer por role/phase
   - SSE (Server-Sent Events) para live updates
4. **Código recuperado**: Commit `c4fc4b5~` (anterior al cleanup PR #86)

### UI Recuperado

**Stack tecnológico**:
- React 18.2
- TypeScript 5.2
- Vite 7.1 (build tool)
- Tailwind CSS 3.4
- SSE (Server-Sent Events)

**Componentes existentes**:
```
ui/po-react/src/
├── App.tsx                      # Layout principal
├── components/
│   ├── PlannerBoard.tsx         # Gestión de stories ✅
│   ├── ContextViewer.tsx        # Visualización de contexto ✅
│   └── useSSE.ts                # Hook para Server-Sent Events ✅
├── main.tsx
└── index.css
```

### Gaps Identificados y Soluciones

| Gap | Estado | Solución |
|-----|--------|----------|
| **API Gateway no existe** | 🔴 Blocker | Crear nuevo servicio (FastAPI) |
| **Planning Service eliminado** | 🔴 Blocker | Ya resuelto (Decision 1) |
| **SSE bridge NATS→SSE** | 🔴 Blocker | Implementar en API Gateway |
| **Decision approval APIs** | 🔴 Missing | Añadir endpoints approve/reject |
| **Deliberation viewer** | 🟡 Enhancement | Crear componente nuevo |

### Adaptaciones Necesarias

**1. Crear componentes nuevos**:
```typescript
// DeliberationViewer.tsx - Ver propuestas de agentes
// DecisionApproval.tsx - Workflow approve/reject con comentarios
```

**2. Extender PlannerBoard.tsx**:
```typescript
// Añadir botones approve/reject para decisiones
<button onClick={() => approveDecision(story.decision_id)}>
  Approve Decision
</button>
```

**3. API Gateway (nuevo servicio)**:
```
services/api-gateway/
├── gateway/
│   ├── routers/
│   │   ├── planner_router.py      # REST → Planning Service gRPC
│   │   ├── context_router.py      # REST → Context Service gRPC
│   │   └── events_router.py       # SSE endpoint (NATS → SSE bridge)
│   ├── adapters/
│   │   ├── planning_grpc_client.py
│   │   ├── context_grpc_client.py
│   │   └── nats_sse_bridge.py
│   └── server.py                  # FastAPI app
└── Dockerfile
```

**REST API Endpoints**:
```
GET    /api/planner/stories
POST   /api/planner/stories
POST   /api/planner/stories/{id}/transition
POST   /api/planner/decisions/{id}/approve
POST   /api/planner/decisions/{id}/reject
GET    /api/context/{storyId}/{role}/{phase}
GET    /api/events/stream?storyId={id}          # SSE
```

**SSE Bridge (NATS → Server-Sent Events)**:
```python
@router.get("/stream")
async def event_stream(request: Request, story_id: str):
    """
    Subscribe to NATS topics:
    - story.events.{story_id}
    - agent.deliberations.{story_id}

    Stream updates to UI in real-time via SSE.
    """
    bridge = NATSSSEBridge()
    async def event_generator():
        async for event in bridge.subscribe(story_id=story_id):
            yield {"event": event.type, "data": event.payload}

    return EventSourceResponse(event_generator())
```

### Timeline
- **Semanas 1-2**: API Gateway (FastAPI + SSE bridge)
- **Semanas 3-4**: UI adaptaciones (nuevos componentes + integración)
- **Total**: 4 semanas

### Deployment
- **API Gateway**: https://api.underpassai.com
- **PO UI**: https://po.underpassai.com
- Namespace: `swe-ai-fleet`
- Ingress: cert-manager + Route53 (TLS automático)

---

## ✅ Decisión 3: RBAC (Role-Based Access Control)

### Pregunta
¿Cómo implementamos control de acceso basado en roles?

### Opciones Evaluadas
- A. Centralizado (Adapter + Port)
- **B. Distribuido con lógica DDD centralizada** ← ✅ **ELEGIDA**
- C. Middleware en API Gateway

### Decisión Final
**Opción B - Distribuido con lógica DDD centralizada en Agent domain**

### Justificación
1. **RBAC es dominio, no infraestructura**: Las capacidades de un agente son parte de su identidad
2. **Self-contained**: Cada agent valida sus propias acciones sin dependencias externas
3. **DDD compliant**: Agent es Aggregate Root, Role y Action son Value Objects
4. **Performance**: Validación local, sin llamadas de red
5. **Type-safe**: Frozen dataclasses + type hints completos
6. **Testable**: Pure functions, fácil de mockear

### Modelo DDD

**Agent (Aggregate Root)**:
```python
@dataclass(frozen=True)
class Agent:
    agent_id: AgentId
    role: Role                    # Value Object
    name: str
    current_task_id: str | None = None

    def can_execute(self, action: Action) -> bool:
        """
        Self-validation: Agent asks itself if it can execute an action.

        Business Rule:
        - Action MUST be in role's allowed_actions
        - Action scope MUST match role scope
        """
        return self.role.can_perform(action)
```

**Role (Value Object)**:
```python
@dataclass(frozen=True)
class Role:
    name: str                     # "architect" | "qa" | "developer" | "po" | "devops"
    allowed_actions: frozenset[str]
    scope: str                    # "technical" | "business" | "quality" | "operations"

    def can_perform(self, action: Action) -> bool:
        return (
            action.name in self.allowed_actions
            and action.scope == self.scope
        )
```

**Action (Value Object)**:
```python
@dataclass(frozen=True)
class Action:
    name: str
    scope: str
    description: str

    # Predefined actions
    APPROVE_DESIGN = "approve_design"          # Architect (technical)
    REJECT_DESIGN = "reject_design"            # Architect (technical)
    APPROVE_PROPOSAL = "approve_proposal"      # PO (business)
    REJECT_PROPOSAL = "reject_proposal"        # PO (business)
    APPROVE_TESTS = "approve_tests"            # QA (quality)
    VALIDATE_COMPLIANCE = "validate_compliance" # QA (quality)
    EXECUTE_TASK = "execute_task"              # Developer (technical)
    DEPLOY_SERVICE = "deploy_service"          # DevOps (operations)
```

### Roles Predefinidos (RoleFactory)

```python
class RoleFactory:
    @staticmethod
    def create_architect() -> Role:
        return Role(
            name="architect",
            allowed_actions=frozenset([
                "approve_design",
                "reject_design",
                "review_architecture",
            ]),
            scope="technical",
        )

    @staticmethod
    def create_po() -> Role:
        return Role(
            name="po",
            allowed_actions=frozenset([
                "approve_proposal",
                "reject_proposal",
                "request_refinement",
                "approve_scope",
            ]),
            scope="business",
        )

    @staticmethod
    def create_qa() -> Role:
        return Role(
            name="qa",
            allowed_actions=frozenset([
                "approve_tests",
                "reject_tests",
                "validate_compliance",
            ]),
            scope="quality",
        )
```

### Enforcement en Use Cases

```python
class ExecuteActionUseCase:
    async def execute(self, agent: Agent, action: Action) -> None:
        # RBAC enforcement: Agent validates itself
        if not agent.can_execute(action):
            raise PermissionDeniedError(
                f"Agent {agent.agent_id.value} with role {agent.role.name} "
                f"cannot execute action {action.name} (scope: {action.scope})"
            )

        # Execute action...
        await self._messaging_port.publish_event(
            topic="agent.action.executed",
            payload={"agent_id": agent.agent_id.value, "action": action.name},
        )
```

### Ejemplos de Uso

**Ejemplo 1: Architect aprueba diseño** ✅
```python
architect = Agent(
    agent_id=AgentId("agent-arch-001"),
    role=RoleFactory.create_architect(),
    name="Senior Architect Agent",
)

approve_design = Action(
    name="approve_design",
    scope="technical",
    description="Approve architectural design",
)

assert architect.can_execute(approve_design) == True  # ✅ Allowed
```

**Ejemplo 2: QA intenta aprobar diseño** ❌
```python
qa = Agent(
    agent_id=AgentId("agent-qa-001"),
    role=RoleFactory.create_qa(),
    name="QA Agent",
)

approve_design = Action(
    name="approve_design",
    scope="technical",  # Wrong scope for QA
    description="Approve architectural design",
)

assert qa.can_execute(approve_design) == False  # ❌ Forbidden (wrong scope)
```

**Ejemplo 3: PO aprueba propuesta de negocio** ✅
```python
po = Agent(
    agent_id=AgentId("agent-po-001"),
    role=RoleFactory.create_po(),
    name="Product Owner Agent",
)

approve_proposal = Action(
    name="approve_proposal",
    scope="business",
    description="Approve business proposal",
)

assert po.can_execute(approve_proposal) == True  # ✅ Allowed
```

### Ventajas del Approach

| Aspecto | Beneficio |
|---------|-----------|
| **DDD Compliant** | Agent = Aggregate Root, Role/Action = Value Objects |
| **Hexagonal** | RBAC en dominio, no en infraestructura |
| **Self-contained** | Sin dependencias externas, validación local |
| **Performance** | Sin llamadas de red para validación |
| **Type-safe** | Frozen dataclasses + type hints completos |
| **Testable** | Pure functions, fácil de mockear |
| **Immutable** | Fail-fast validation, sin mutación |
| **Explicit** | Sin reflection, sin magic, sin dynamic routing |

### Timeline
- **Semana 1**: Implementación completa + tests
- **Coverage**: 100% en domain layer

---

## ✅ Decisión 4: Timeline de Implementación

### Pregunta
¿Cuál es la estrategia temporal para implementar los gaps P0?

### Opciones Evaluadas
- A. MVP Rápido (4 semanas, deuda técnica)
- **B. Incremental ajustado con vista al MVP** ← ✅ **ELEGIDA**
- C. Completo P0 (10 semanas, sin compromisos)

### Decisión Final
**Opción B - Incremental (6 sem P0 + 4 sem P1) ajustado con vista al MVP**

### Justificación
1. **Balance calidad/velocidad**: P0 completo en 6 semanas sin deuda técnica
2. **MVP-first**: Priorizar features críticas para validar flujo E2E
3. **Arquitectura limpia**: Tests >90%, DDD + Hexagonal desde el inicio
4. **Scope optimizado**: P0 tiene features completas, P1 tiene enhancements
5. **Riesgo controlado**: Sin compromisos en quality gate

### Roadmap Detallado

#### **Sprint 1: Foundation (Semanas 1-2)**

**Objetivo**: Implementar base arquitectural con Planning Service y RBAC

**Planning Service**:
- ✅ Domain entities (Story, StoryState, DORScore)
- ✅ Use cases (Create, Transition, Approve, Reject)
- ✅ gRPC server
- ✅ NATS adapter (publicar eventos)
- ✅ Neo4j adapter (persistir stories)
- ✅ Tests unitarios >90%

**RBAC Domain Model**:
- ✅ Agent (Aggregate Root)
- ✅ Role (Value Object)
- ✅ Action (Value Object)
- ✅ RoleFactory (predefined roles)
- ✅ Tests unitarios 100%

**Deployment**:
- ✅ Planning Service en K8s (internal-planning:50051)
- ✅ ConfigMap con FSM states
- ✅ Integration tests con NATS + Neo4j

**Entregable**: Planning Service funcional, RBAC listo para integración

---

#### **Sprint 2: Infrastructure (Semanas 3-4)**

**Objetivo**: API Gateway + SSE bridge para conectar UI con servicios

**API Gateway (FastAPI)**:
- ✅ REST routers (planner, context, events)
- ✅ gRPC clients (Planning, Context)
- ✅ SSE bridge (NATS → Server-Sent Events)
- ✅ CORS middleware
- ✅ Error handling (gRPC → HTTP status codes)
- ✅ OpenAPI documentation
- ✅ Tests unitarios + integration

**Endpoints**:
```
GET    /api/planner/stories
POST   /api/planner/stories
POST   /api/planner/stories/{id}/transition
POST   /api/planner/decisions/{id}/approve
POST   /api/planner/decisions/{id}/reject
GET    /api/context/{storyId}/{role}/{phase}
GET    /api/events/stream?storyId={id}          # SSE
```

**Deployment**:
- ✅ API Gateway en K8s (https://api.underpassai.com)
- ✅ Ingress configurado (TLS via cert-manager)
- ✅ Integration tests E2E

**Entregable**: API Gateway funcional con SSE streaming

---

#### **Sprint 3: Integration (Semanas 5-6)**

**Objetivo**: UI adaptado + Task Derivation + E2E flow completo

**UI Adaptaciones**:
- ✅ PlannerBoard.tsx adaptado (botones approve/reject)
- ✅ DeliberationViewer.tsx (nuevo componente)
- ✅ DecisionApproval.tsx (workflow de aprobación)
- ✅ SSE hook actualizado (nuevos event types)
- ✅ API client wrapper (error handling)
- ✅ Tests E2E con Playwright

**Task Derivation**:
- ✅ DeriveSubtasksUseCase implementado (básico)
- ✅ LLM adapter para descomponer stories
- ✅ Integration con Neo4j (task graph)
- ⚠️ Deuda técnica documentada: "Refactor a Planner Service en P1"

**E2E Flow**:
```
1. PO crea story via UI
2. Story entra en DRAFT
3. Orchestrator dispara deliberation
4. Agents proponen soluciones (Architect, Dev, QA)
5. Council rankea propuestas
6. Propuesta ganadora enviada a PO (SSE live update)
7. PO aprueba decisión via UI
8. Orchestrator ejecuta propuesta ganadora
9. Workspace valida resultados
10. Story transiciona a DONE
```

**Deployment**:
- ✅ UI desplegado en K8s (https://po.underpassai.com)
- ✅ E2E test passing (flujo completo)

**Entregable**: Sistema P0 completo funcional

---

### Fase P1: Enhancements (Semanas 7-10)

**Objetivo**: Features avanzadas y optimizaciones

**Semanas 7-8**:
- Rehydration extendida (navegación de grafo histórico)
- Task Derivation refactorizado (mover a Planner Service)
- Notification system (email/Slack para decisiones pendientes)

**Semanas 9-10**:
- Ceremonias ágiles (Sprint Planning, Dailies, Review, Retro)
- UI mejorada (dashboards, analytics)
- E2E tests exhaustivos
- Performance optimization

---

### Timeline Summary

| Fase | Duración | Entregable Clave |
|------|----------|------------------|
| **Sprint 1** | 2 sem | Planning Service + RBAC domain |
| **Sprint 2** | 2 sem | API Gateway + SSE bridge |
| **Sprint 3** | 2 sem | UI adaptado + E2E flow |
| **P0 Total** | **6 semanas** | **Sistema MVP funcional** |
| **P1** | 4 sem | Enhancements + features avanzadas |
| **TOTAL** | **10 semanas** | **Sistema completo en producción** |

---

### Definition of Done (P0)

**Para cada feature**:
- ✅ Código implementado siguiendo DDD + Hexagonal Architecture
- ✅ No reflection, no setattr, no dynamic mutation
- ✅ Frozen dataclasses con fail-fast validation
- ✅ Tests unitarios ≥90% coverage
- ✅ Integration tests passing
- ✅ Linter errors = 0 (Ruff)
- ✅ Documentation en docstrings
- ✅ Self-check section confirming rules compliance
- ✅ Deployed a K8s (for services)

**Para el sistema completo (P0)**:
- ✅ PO puede crear story vía UI
- ✅ Agents deliberan automáticamente
- ✅ PO recibe propuesta ganadora (SSE live update)
- ✅ PO puede aprobar/rechazar decisión
- ✅ RBAC enforcement funciona (Architect ✅ approve design, QA ❌ approve design)
- ✅ Execution se dispara tras aprobación
- ✅ Story transiciona a DONE
- ✅ E2E test completo passing
- ✅ Sistema desplegado en K8s con TLS
- ✅ Performance: deliberation <60s, execution <120s

---

## 📊 Comparativa de Decisiones vs Recomendaciones del Asistente

| Decision | Recomendación Asistente | Decisión Arquitecto | Match |
|----------|-------------------------|---------------------|-------|
| **1. Planning** | B - Nuevo servicio Planner | A - Nuevo Planning en Python | ✅ Similar |
| **2. PO UI** | A - React + API Gateway | C - Revivir UI legacy | ⚠️ Diferente |
| **3. RBAC** | A - Centralizado | B - Distribuido (DDD) | ⚠️ Diferente |
| **4. Timeline** | C - Incremental | B - Incremental ajustado | ✅ Match |

**Análisis**:
- ✅ **Decision 1**: Ambas opciones crean nuevo servicio, arquitectura limpia
- ⚠️ **Decision 2**: Arquitecto eligió revivir UI (ahorro de tiempo) vs desde cero (más flexible)
- ⚠️ **Decision 3**: Arquitecto prefiere RBAC como dominio (DDD puro) vs servicio centralizado
- ✅ **Decision 4**: Enfoque incremental con foco MVP

**Todas las decisiones son arquitecturalmente sólidas y respetan los principios DDD + Hexagonal.**

---

## 🚀 Próximos Pasos Inmediatos

### Paso 1: Preparación (Esta semana)
- [ ] Crear feature branches:
  - `feature/planning-service-python`
  - `feature/rbac-domain-model`
  - `feature/api-gateway`
  - `feature/ui-adaptations`
- [ ] Setup CI/CD para nuevos servicios
- [ ] Configurar entornos de desarrollo

### Paso 2: Iniciar Sprint 1 (Semanas 1-2)
- [ ] Implementar Planning Service
- [ ] Implementar RBAC Domain Model
- [ ] Tests unitarios >90%
- [ ] Deploy a K8s

### Paso 3: Daily Standups
- Seguimiento diario de progreso
- Bloqueos identificados y resueltos
- Integración continua

---

## 📝 Documentos de Referencia

1. **ARCHITECTURE_GAPS_EXECUTIVE_SUMMARY.md** - Las 4 decisiones originales
2. **ARCHITECTURAL_DECISIONS_2025-11-02.md** - Análisis detallado
3. **IMPLEMENTATION_ROADMAP_2025-11-02.md** - Roadmap ejecutable
4. **DECISIONS_SUMMARY.md** - Resumen de decisiones
5. **FINAL_DECISIONS_2025-11-02.md** - Este documento (síntesis oficial)

**Código recuperado**:
- `ui/po-react/` - UI legacy listo para adaptaciones

---

## ✅ SELF-VERIFICATION REPORT

### Completeness ✓
- ✅ 4 decisiones arquitecturales documentadas
- ✅ Justificación detallada para cada decisión
- ✅ Timeline completo (P0 + P1)
- ✅ Especificación técnica (código, APIs, arquitectura)
- ✅ Definition of Done clara

### Logical and Architectural Consistency ✓
- ✅ Todas las decisiones respetan DDD + Hexagonal Architecture
- ✅ No reflection, no dynamic mutation
- ✅ Frozen dataclasses con fail-fast validation
- ✅ Dependency injection via ports
- ✅ Layer boundaries respetadas

### Domain Boundaries Validated ✓
- ✅ Planning Service = bounded context propio
- ✅ Agent + RBAC = dominio del orchestrator
- ✅ API Gateway = infrastructure layer
- ✅ UI = presentation layer

### Trade-offs Analyzed ✓
**Decision 2 (Revivir UI vs desde cero)**:
- **Pro**: Ahorro de 3-4 semanas
- **Con**: Código posiblemente obsoleto → Mitigado (stack moderno)

**Decision 3 (RBAC distribuido vs centralizado)**:
- **Pro**: Performance, DDD puro, self-contained
- **Con**: Policies hardcoded → Aceptable (cambios infrecuentes)

### Security & Observability ✓
- ✅ RBAC enforcement documentado
- ✅ Audit trail de decisiones (NATS events)
- ✅ Structured logging en todos los servicios
- ✅ Metrics & tracing (to be implemented in P1)

### IaC / CI-CD Feasibility ✓
- ✅ Todos los servicios containerizables (Dockerfiles)
- ✅ Deployment a K8s (Helm charts / manifests)
- ✅ gRPC APIs auto-generables
- ✅ Tests automatizables (pytest, Playwright)

### Real-world Deployability ✓
- ✅ Compatible con cluster K8s existente
- ✅ No requiere infraestructura nueva
- ✅ Escalable horizontalmente
- ✅ TLS automático (cert-manager + Route53)

### Confidence Level
**ALTA** - Decisiones basadas en:
- ✅ Auditoría arquitectural exhaustiva (11 documentos, ~7,200 líneas)
- ✅ Código recuperado del histórico (UI viable)
- ✅ Arquitectura probada (DDD + Hexagonal en servicios actuales)
- ✅ Deployment actual en K8s funcionando

### Unresolved Questions
**Ninguna** - Todas las decisiones confirmadas por el arquitecto.

---

**Documentación oficial lista. Ready to code.** 🚀

**Fecha de aprobación**: 2 de noviembre, 2025
**Firmado**: Tirso García Ibáñez (Software Architect & Founder)

