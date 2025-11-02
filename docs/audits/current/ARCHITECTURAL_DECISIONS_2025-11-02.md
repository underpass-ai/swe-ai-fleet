# Decisiones Arquitecturales - 2 de Noviembre 2025

**Fecha**: 2 de noviembre, 2025  
**Arquitecto**: Tirso García Ibáñez (Software Architect & Founder)  
**Contexto**: Resolución de Gaps Arquitecturales Post-Cleanup (PR #86)  
**Branch**: `audit/architecture-gaps-evaluation`

---

## 🎯 Resumen Ejecutivo

Este documento registra las **4 decisiones arquitecturales críticas** tomadas para resolver los gaps identificados en la auditoría arquitectural completa realizada el 2 de noviembre de 2025.

**Documentos de referencia**:
- `ARCHITECTURE_GAPS_EXECUTIVE_SUMMARY.md`
- `CRITICAL_GAPS_AUDIT.md`
- `ORCHESTRATOR_RESPONSIBILITY_ANALYSIS.md`
- `PO_UI_AND_API_GAP_ANALYSIS.md`

---

## 📋 Decisiones Registradas

### ✅ Decisión 1: Task Derivation (Planificación)

**Pregunta**: ¿Cómo implementamos la descomposición de stories en tasks ejecutables?

**Opción elegida**: **A - Temporal en Orchestrator (1 semana)**

**Justificación**:
- Prioridad en velocidad de entrega
- Task derivation es crítico para el flujo P0
- Se acepta deuda técnica controlada
- Será refactorizado en fase P1 como servicio separado

**Implicaciones**:
- ⚠️ Incrementa responsabilidades del orchestrator (riesgo de God Object)
- ⚠️ Deuda técnica documentada para Sprint P1
- ✅ Desbloquea flujo end-to-end rápidamente
- ✅ Permite validar viabilidad antes de crear servicio dedicado

**Entregable**: `DeriveSubtasks` implementado en `core/orchestrator/usecases/`

**Timeline**: 1 semana

---

### ✅ Decisión 2: PO UI (Interfaz de Usuario)

**Pregunta**: ¿Cómo implementamos la UI para que el PO apruebe/rechace decisiones?

**Opción elegida**: **CUSTOM - Rescatar UI del histórico de GitHub**

**Justificación**:
- UI existente encontrado en commit `c4fc4b5~` (anterior al cleanup)
- Stack tecnológico moderno y compatible:
  - React 18.2 + TypeScript
  - Vite (build tool rápido)
  - Tailwind CSS (diseño moderno)
  - SSE (Server-Sent Events para actualizaciones en tiempo real)
- Ahorra 3-4 semanas de desarrollo desde cero
- UI ya implementaba workflows críticos:
  - Crear stories
  - Ver estados de stories (FSM)
  - Aprobar scope
  - Ver contexto por role/phase
  - Actualizaciones live vía SSE

**UI Recuperado**:
```
ui/po-react/
├── src/
│   ├── App.tsx                      # Layout principal
│   ├── components/
│   │   ├── PlannerBoard.tsx         # Gestión de stories
│   │   ├── ContextViewer.tsx        # Visualización de contexto
│   │   └── useSSE.ts                # Hook para Server-Sent Events
│   ├── main.tsx
│   └── index.css
├── Dockerfile                        # Containerización
├── package.json                      # Dependencies
├── vite.config.ts
└── tailwind.config.js
```

**Gaps Identificados en el UI Rescatado**:

1. **API Gateway No Existe** 🔴
   - UI usa REST endpoints (`/api/planner/*`, `/api/context/*`, `/api/events/stream`)
   - Servicios actuales son gRPC
   - **Solución**: Crear API Gateway que traduzca REST → gRPC

2. **Planning Service Eliminado** 🔴
   - UI espera endpoints: `/api/planner/stories`, `/api/planner/stories/{id}/transition`
   - **Solución**: Recrear Planning Service (ya cubierto en Decisión 1)

3. **SSE No Implementado** 🟡
   - UI espera `/api/events/stream?storyId={id}` para live updates
   - **Solución**: API Gateway implementa SSE bridge a NATS subscriptions

4. **Decision Approval APIs Faltantes** 🔴
   - UI tiene solo `approve_scope`, necesita:
     - `approve_design` (Architect)
     - `approve_proposal` (PO)
     - `reject_proposal` (PO)
     - `request_refinement` (PO)
   - **Solución**: Extender Planning Service APIs

**Adaptaciones Necesarias**:

| Componente | Estado Actual | Adaptación Necesaria |
|------------|---------------|----------------------|
| **PlannerBoard.tsx** | ✅ Funcional | Añadir botones approve/reject para decisiones |
| **ContextViewer.tsx** | ✅ Funcional | Mostrar deliberaciones de agentes |
| **API Gateway** | ❌ No existe | Crear nuevo servicio (Python FastAPI) |
| **Planning Service** | ❌ Eliminado | Recrear en Python (DDD + Hexagonal) |
| **SSE Bridge** | ❌ No existe | Implementar en API Gateway (NATS → SSE) |

**Entregables**:

1. **UI Adaptado** (1 semana)
   - Adaptar `PlannerBoard.tsx` para decision approval
   - Añadir componente `DeliberationViewer.tsx`
   - Actualizar endpoints a nueva API Gateway

2. **API Gateway** (2 semanas)
   - FastAPI service
   - REST → gRPC translation
   - SSE bridge (NATS subscriptions → Server-Sent Events)
   - Authentication/Authorization middleware
   - Deployment a K8s

3. **Planning Service APIs Extendidas** (1 semana)
   - gRPC endpoints para decision approval
   - FSM transitions extendido
   - NATS event publishing

**Timeline**: 4 semanas (vs 5-6 semanas desde cero)

---

### ✅ Decisión 3: RBAC (Control de Acceso)

**Pregunta**: ¿Cómo implementamos Role-Based Access Control para agentes?

**Opción elegida**: **CUSTOM - RBAC Embedded en Agent Domain (DDD Aggregate)**

**Justificación**:
- RBAC es parte del **dominio del agente**, no infraestructura externa
- Cada agente es responsable de sus propias capacidades (cohesión)
- Agent es el **Aggregate Root**, Role es un **Value Object**
- Validación self-contained: el agente se pregunta a sí mismo si puede ejecutar una acción
- Alineado con DDD principles y Hexagonal Architecture
- Evita servicios adicionales innecesarios
- Performance: validación local sin llamadas de red

**Modelo DDD Propuesto**:

```python
# core/orchestrator/domain/entities/agent.py

from dataclasses import dataclass
from typing import Protocol

from core.orchestrator.domain.value_objects.role import Role
from core.orchestrator.domain.value_objects.action import Action
from core.orchestrator.domain.value_objects.agent_id import AgentId


@dataclass(frozen=True)
class Agent:
    """
    Aggregate Root for Agent bounded context.
    
    Responsibilities:
    - Identity (agent_id)
    - Capabilities (role → allowed_actions)
    - Self-validation (can_execute)
    - Execution context (current_task, current_phase)
    
    Domain Invariants:
    - Agent MUST have a role
    - Agent can ONLY execute actions within its role's allowed_actions
    - Agent identity is immutable
    """
    
    agent_id: AgentId
    role: Role
    name: str
    current_task_id: str | None = None
    current_phase: str | None = None
    
    def __post_init__(self) -> None:
        if not self.agent_id.value:
            raise ValueError("AgentId cannot be empty")
        if not self.name:
            raise ValueError("Agent name cannot be empty")
    
    def can_execute(self, action: Action) -> bool:
        """
        Self-validation: Agent asks itself if it can execute an action.
        
        Business Rule: An agent can execute an action IFF:
        1. The action is in its role's allowed_actions
        2. The action's scope matches the agent's current context
        
        Returns:
            True if agent can execute the action, False otherwise
        """
        return self.role.can_perform(action)
    
    def assign_task(self, task_id: str, phase: str) -> "Agent":
        """
        Immutable update: Returns new Agent with assigned task.
        
        Raises:
            ValueError if task_id or phase is empty
        """
        if not task_id:
            raise ValueError("task_id cannot be empty")
        if not phase:
            raise ValueError("phase cannot be empty")
        
        # Frozen dataclass: create new instance
        return Agent(
            agent_id=self.agent_id,
            role=self.role,
            name=self.name,
            current_task_id=task_id,
            current_phase=phase,
        )
    
    def is_available(self) -> bool:
        """Agent is available if not currently assigned to a task."""
        return self.current_task_id is None


# core/orchestrator/domain/value_objects/role.py

from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    """
    Value Object: Agent's role in the SWE team.
    
    A Role defines:
    - What actions the agent can perform
    - The scope of those actions (technical, business, quality)
    
    Domain Invariants:
    - Role name MUST be one of the predefined roles
    - Allowed actions MUST be non-empty
    - Allowed actions are immutable
    """
    
    name: str  # "architect" | "qa" | "developer" | "po" | "devops"
    allowed_actions: frozenset[str]  # Immutable set of action names
    scope: str  # "technical" | "business" | "quality" | "operations"
    
    # Predefined roles (class constants)
    ARCHITECT = "architect"
    QA = "qa"
    DEVELOPER = "developer"
    PO = "po"
    DEVOPS = "devops"
    
    VALID_ROLES = frozenset([ARCHITECT, QA, DEVELOPER, PO, DEVOPS])
    VALID_SCOPES = frozenset(["technical", "business", "quality", "operations"])
    
    def __post_init__(self) -> None:
        if self.name not in self.VALID_ROLES:
            raise ValueError(
                f"Invalid role: {self.name}. Must be one of {self.VALID_ROLES}"
            )
        if not self.allowed_actions:
            raise ValueError("allowed_actions cannot be empty")
        if self.scope not in self.VALID_SCOPES:
            raise ValueError(
                f"Invalid scope: {self.scope}. Must be one of {self.VALID_SCOPES}"
            )
    
    def can_perform(self, action: "Action") -> bool:
        """
        Check if this role can perform the given action.
        
        Business Rules:
        1. Action MUST be in allowed_actions
        2. Action scope MUST match or be compatible with role scope
        
        Scope compatibility:
        - "architect" (technical) can approve technical decisions
        - "qa" (quality) can approve quality decisions
        - "po" (business) can approve business decisions
        - Cross-scope actions are forbidden (enforced here)
        """
        return (
            action.name in self.allowed_actions
            and action.scope == self.scope
        )


# core/orchestrator/domain/value_objects/action.py

from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    """
    Value Object: Acción que un agente puede ejecutar.
    
    Domain Invariants:
    - Action name MUST be one of the predefined actions
    - Scope MUST match the action's domain
    - Actions are immutable
    """
    
    name: str
    scope: str  # "technical" | "business" | "quality" | "operations"
    description: str
    
    # Predefined actions (class constants)
    # Technical actions (Architect)
    APPROVE_DESIGN = "approve_design"
    REJECT_DESIGN = "reject_design"
    REVIEW_ARCHITECTURE = "review_architecture"
    
    # Business actions (PO)
    APPROVE_PROPOSAL = "approve_proposal"
    REJECT_PROPOSAL = "reject_proposal"
    REQUEST_REFINEMENT = "request_refinement"
    APPROVE_SCOPE = "approve_scope"
    
    # Quality actions (QA)
    APPROVE_TESTS = "approve_tests"
    REJECT_TESTS = "reject_tests"
    VALIDATE_COMPLIANCE = "validate_compliance"
    
    # Development actions (Developer)
    EXECUTE_TASK = "execute_task"
    RUN_TESTS = "run_tests"
    COMMIT_CODE = "commit_code"
    
    # Operations actions (DevOps)
    DEPLOY_SERVICE = "deploy_service"
    CONFIGURE_INFRA = "configure_infra"
    
    VALID_ACTIONS = frozenset([
        APPROVE_DESIGN, REJECT_DESIGN, REVIEW_ARCHITECTURE,
        APPROVE_PROPOSAL, REJECT_PROPOSAL, REQUEST_REFINEMENT, APPROVE_SCOPE,
        APPROVE_TESTS, REJECT_TESTS, VALIDATE_COMPLIANCE,
        EXECUTE_TASK, RUN_TESTS, COMMIT_CODE,
        DEPLOY_SERVICE, CONFIGURE_INFRA,
    ])
    
    def __post_init__(self) -> None:
        if self.name not in self.VALID_ACTIONS:
            raise ValueError(
                f"Invalid action: {self.name}. Must be one of {self.VALID_ACTIONS}"
            )
        if not self.description:
            raise ValueError("Action description cannot be empty")


# Predefined Role Factories

class RoleFactory:
    """Factory for creating predefined roles with their allowed actions."""
    
    @staticmethod
    def create_architect() -> Role:
        return Role(
            name=Role.ARCHITECT,
            allowed_actions=frozenset([
                Action.APPROVE_DESIGN,
                Action.REJECT_DESIGN,
                Action.REVIEW_ARCHITECTURE,
            ]),
            scope="technical",
        )
    
    @staticmethod
    def create_qa() -> Role:
        return Role(
            name=Role.QA,
            allowed_actions=frozenset([
                Action.APPROVE_TESTS,
                Action.REJECT_TESTS,
                Action.VALIDATE_COMPLIANCE,
            ]),
            scope="quality",
        )
    
    @staticmethod
    def create_po() -> Role:
        return Role(
            name=Role.PO,
            allowed_actions=frozenset([
                Action.APPROVE_PROPOSAL,
                Action.REJECT_PROPOSAL,
                Action.REQUEST_REFINEMENT,
                Action.APPROVE_SCOPE,
            ]),
            scope="business",
        )
    
    @staticmethod
    def create_developer() -> Role:
        return Role(
            name=Role.DEVELOPER,
            allowed_actions=frozenset([
                Action.EXECUTE_TASK,
                Action.RUN_TESTS,
                Action.COMMIT_CODE,
            ]),
            scope="technical",
        )
    
    @staticmethod
    def create_devops() -> Role:
        return Role(
            name=Role.DEVOPS,
            allowed_actions=frozenset([
                Action.DEPLOY_SERVICE,
                Action.CONFIGURE_INFRA,
            ]),
            scope="operations",
        )
```

**Ejemplo de Uso**:

```python
from core.orchestrator.domain.entities.agent import Agent
from core.orchestrator.domain.value_objects.agent_id import AgentId
from core.orchestrator.domain.value_objects.action import Action
from core.orchestrator.domain.factories.role_factory import RoleFactory


# Create an Architect agent
architect_role = RoleFactory.create_architect()
architect = Agent(
    agent_id=AgentId("agent-arch-001"),
    role=architect_role,
    name="Senior Architect Agent",
)

# Create actions
approve_design_action = Action(
    name=Action.APPROVE_DESIGN,
    scope="technical",
    description="Approve architectural design proposal",
)

approve_proposal_action = Action(
    name=Action.APPROVE_PROPOSAL,
    scope="business",
    description="Approve business proposal",
)

# Self-validation
assert architect.can_execute(approve_design_action) == True   # ✅ Allowed
assert architect.can_execute(approve_proposal_action) == False  # ❌ Forbidden (wrong scope)
```

**Enforcement en Use Cases**:

```python
# core/orchestrator/application/usecases/execute_action_usecase.py

from core.orchestrator.domain.entities.agent import Agent
from core.orchestrator.domain.value_objects.action import Action


class ExecuteActionUseCase:
    """
    Use Case: Execute an action on behalf of an agent.
    
    Preconditions:
    - Agent MUST be able to execute the action (RBAC check)
    
    Postconditions:
    - Action is executed
    - Domain event is published
    """
    
    def __init__(self, messaging_port: MessagingPort) -> None:
        self._messaging_port = messaging_port
    
    async def execute(self, agent: Agent, action: Action) -> None:
        # RBAC enforcement: Agent validates itself
        if not agent.can_execute(action):
            raise PermissionDeniedError(
                f"Agent {agent.agent_id.value} with role {agent.role.name} "
                f"cannot execute action {action.name} (scope: {action.scope})"
            )
        
        # Execute action (delegated to infrastructure)
        # ...
        
        # Publish domain event
        await self._messaging_port.publish_event(
            topic="agent.action.executed",
            payload={
                "agent_id": agent.agent_id.value,
                "action": action.name,
                "scope": action.scope,
            },
        )
```

**Ventajas de este Approach**:

1. ✅ **DDD Compliant**: Agent es Aggregate Root, Role y Action son Value Objects
2. ✅ **Hexagonal Architecture**: RBAC en dominio, no en infraestructura
3. ✅ **Self-contained**: Agent valida sus propias capacidades sin dependencias externas
4. ✅ **Performance**: Validación local, sin red
5. ✅ **Type-safe**: Frozen dataclasses + type hints completos
6. ✅ **Testable**: Pure functions, fácil de mockear
7. ✅ **Immutable**: Dataclasses frozen, fail-fast validation
8. ✅ **Explicit**: No reflection, no magic, no dynamic routing

**Desventajas (aceptadas)**:

1. ⚠️ RBAC policies hardcoded en código (vs BD externa)
   - **Justificación**: Policies son parte del dominio, no configuración
   - **Alternativa**: Si necesitamos RBAC dinámico, refactor a servicio dedicado en P1

2. ⚠️ Cambios en roles requieren redeploy
   - **Justificación**: Roles no cambian frecuentemente, son parte del dominio

**Timeline**: 1 semana (implementación + tests)

---

### ⏸️ Decisión 4: Timeline de Implementación

**Pregunta**: ¿Cuál es la estrategia temporal para implementar los gaps P0?

**Opción elegida**: **C - Incremental (6 sem P0 + 4 sem P1) "pero rápido"**

**⚠️ PENDIENTE ACLARACIÓN**: ¿Qué significa "rápido"?

**Interpretaciones posibles**:

**A. Timeline comprimido** (mismo scope, ejecución paralela)
- P0: 4 semanas (vs 6) - paralelización agresiva
- P1: 3 semanas (vs 4) - acelerado
- Total: 7 semanas

**B. Scope reducido en P0** (solo mínimo viable)
- P0 (4 semanas): Planning + Decision Approval mínimo + RBAC
- P1 (3 semanas): Task Derivation + Rehydration + UI completo
- Total: 7 semanas

**C. Ambas (compresión + reducción)**
- P0 (3-4 semanas): Features críticas, ejecución paralela
- P1 (3 semanas): Resto de features
- Total: 6-7 semanas

**¿Cuál de estas interpretaciones es la correcta?**

**Pendiente de confirmación por el arquitecto.**

---

## 📊 Resumen de Decisiones

| # | Decisión | Opción | Timeline | Deuda Técnica | Prioridad |
|---|----------|--------|----------|---------------|-----------|
| **1** | Task Derivation | A - Temporal en Orchestrator | 1 sem | ⚠️ Sí (refactor en P1) | **P0-A** |
| **2** | PO UI | CUSTOM - Rescatar del histórico | 4 sem | ✅ No | **P0-B** |
| **3** | RBAC | CUSTOM - Embedded en Agent | 1 sem | ✅ No | **P0-C** |
| **4** | Timeline | C - Incremental "rápido" | ⏸️ TBD | N/A | **P0-D** |

**Total estimado (pending Decision 4)**: 6-10 semanas

---

## 🚀 Próximos Pasos

1. ✅ **Confirmar Decisión 4 con el arquitecto**
2. Crear roadmap de implementación detallado
3. Generar epics y user stories
4. Asignar recursos y comenzar Sprint 1

---

## 📝 Referencias

- `docs/audits/current/ARCHITECTURE_GAPS_EXECUTIVE_SUMMARY.md`
- `docs/audits/current/CRITICAL_GAPS_AUDIT.md`
- `docs/audits/current/ORCHESTRATOR_RESPONSIBILITY_ANALYSIS.md`
- `docs/audits/current/PO_UI_AND_API_GAP_ANALYSIS.md`
- `ui/po-react/` (código rescatado del histórico)

---

**Documento listo para revisión y aprobación.** 🚀

