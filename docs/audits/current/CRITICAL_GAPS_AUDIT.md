# Auditoría de GAPS Críticos en Arquitectura

**Fecha**: 2 de noviembre, 2025
**Autor**: AI Assistant (Claude Sonnet 4.5)
**Solicitado por**: Tirso García Ibáñez (Software Architect)

---

## 🎯 Resumen Ejecutivo

Se identificaron **5 GAPS críticos** tras el refactor hexagonal y cleanup del proyecto:

1. **Planning Service (Go) ELIMINADO** - Nadie gestiona FSM de historias
2. **RBAC NO IMPLEMENTADO** - Roles documentados pero sin enforcement
3. **Rehydration limitada a 1 nodo** - PO no puede navegar grafo para explorar decisiones
4. **Reunión de Planificación NO EXISTE** - Solo deliberación individual por agente
5. **Ceremonias Ágiles NO IMPLEMENTADAS** - Dailies, Sprint Review, Retrospectives solo documentadas

---

## 🚨 GAP 1: Planning Service (Go) Eliminado

### ¿Qué Había?

**Ubicación histórica**: `services/planning/` (Go microservice)

**Responsabilidades**:
- FSM de historias de usuario (draft → po_review → ready_for_dev → in_progress → done)
- Gestión de transiciones con guards
- Evaluación de Definition of Ready (DoR score)
- Publicación de eventos planning.story.transitioned, planning.plan.approved

**Archivos eliminados** (Commit `c4fc4b5` - PR #86):
```
services/planning/cmd/main.go            (82 líneas)
services/planning/internal/fsmx/engine.go (274 líneas)
services/planning/internal/svc/planning.go (256 líneas)
services/planning/Dockerfile
services/bin/planning  (binario)
```

**API protobuf** (todavía existe el spec):
```proto
// specs/fleet/planning/v1/planning.proto
service PlanningService {
  rpc CreateStory (CreateStoryRequest) returns (CreateStoryResponse);
  rpc ListStories (ListStoriesRequest) returns (ListStoriesResponse);
  rpc GetStory (GetStoryRequest) returns (GetStoryResponse);
  rpc Transition (TransitionRequest) returns (TransitionResponse);
  rpc GetPlan (GetPlanRequest) returns (GetPlanResponse);
}
```

### ¿Qué Pasó?

**Eliminado en**: PR #86 - "Monitoring Hexagonal Refactor + Project Cleanup"

**Razón**: Cleanup de servicios no utilizados (junto con StoryCoach service también eliminado)

### ¿Quién lo Hace Ahora?

**NADIE**. No existe un bounded context que:
- Gestione FSM de historias de usuario
- Valide transiciones con guards
- Compute DoR score
- Publique eventos de cambio de fase

### Impacto

❌ **Crítico**:
- PO no tiene manera de gestionar historias de usuario en el sistema
- No hay FSM de agile workflow
- Orchestrator espera eventos `planning.plan.approved` que nadie publica
- Context Service puede crear historias pero no tiene lógica de transición

### Solución Propuesta

**Opción 1 (Rápida)**: Implementar FSM mínimo en Context Service
```python
# services/context/server.py
async def TransitionStory(self, request, context):
    """Transition story between phases with FSM validation."""
    # 1. Load FSM config from config/agile.fsm.yaml
    # 2. Evaluate guards (DoR score > 80%, etc.)
    # 3. Execute transition
    # 4. Update Neo4j + Valkey
    # 5. Publish planning.story.transitioned event
```

**Opción 2 (Ideal)**: Revivir Planning Service en Python
- Migrar FSM engine de Go a Python
- Implementar con hexagonal architecture
- Integrar con Context Service para persistencia

---

## 🚨 GAP 2: RBAC Sin Implementación Real (Dos Niveles)

### Contexto: DOS Dimensiones de RBAC

El sistema requiere RBAC en **DOS niveles distintos**:

1. **RBAC Nivel 1: Tool Execution** (técnico)
   - ¿Qué herramientas puede usar cada rol?
   - Ejemplo: DEV puede hacer `git.commit()`, QA NO

2. **RBAC Nivel 2: Decision Authority** (governance)
   - ¿Quién puede tomar qué decisiones?
   - ¿Quién puede aprobar/rechazar propuestas?
   - ¿Qué deliberaciones puede ver cada rol?
   - ¿Qué scope de revisión tiene cada rol?

**Ambos niveles están SIN IMPLEMENTAR**.

---

### Nivel 1: Tool Execution RBAC (Ya Identificado)

#### ¿Qué Está Documentado?

**Roles definidos**:
```python
class AgentRole(Enum):
    DEV = "DEV"
    QA = "QA"
    ARCHITECT = "ARCHITECT"
    DEVOPS = "DEVOPS"
    DATA = "DATA"
```

**Tool usage documentado** (`vllm_agent.py:151-156`):
```python
# Role-Specific Tool Usage:
# - DEV: git.commit(), files.write(), tests.pytest()
# - QA: files.read(), tests.pytest(), http.post()
# - ARCHITECT: files.search(), git.log(), db.query()
# - DEVOPS: docker.build(), http.get(), files.edit()
# - DATA: db.query(), files.write(), tests.pytest()
```

**Comentario en código**:
```python
# This is THE agent class used by ALL roles in the system (DEV, QA, ARCHITECT, DEVOPS, DATA).
# The ROLE determines HOW the agent uses tools, not WHETHER it can use them.
```

#### ¿Qué Falta?

❌ **NO HAY ENFORCEMENT**. Todos los agentes pueden usar TODAS las herramientas sin restricción.

**Ejemplo actual**:
```python
# Un agente QA puede hacer commit (¡no debería!)
qa_agent = VLLMAgent(role="QA", ...)
result = await qa_agent.execute_task(
    task="Fix bug and commit",
    context="..."
)
# → QA ejecuta git.commit() sin restricción
```

### Búsqueda en Código

**Archivos revisados**: 20 archivos con `permission|authorize|allowed`

**Resultado**: ❌ CERO validaciones de permisos encontradas en:
- `core/agents_and_tools/tools/*.py` (git_tool, file_tool, etc.)
- `core/agents_and_tools/agents/vllm_agent.py`
- `core/agents_and_tools/agents/infrastructure/adapters/tool_execution_adapter.py`

**Histórico Git**: No se encontraron commits con "RBAC" implementation, solo documentación.

### ¿Dónde Debería Estar?

**Opción 1**: En cada Tool (file_tool, git_tool, etc.)
```python
# core/agents_and_tools/tools/git_tool.py
class GitTool:
    ALLOWED_ROLES_PER_OPERATION = {
        "commit": ["DEV", "DATA"],
        "push": ["DEV"],
        "read": ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"],
    }

    def commit(self, message: str, author: str) -> ToolResult:
        # Validar rol antes de ejecutar
        if self.agent_role not in self.ALLOWED_ROLES_PER_OPERATION["commit"]:
            raise PermissionError(f"Role {self.agent_role} cannot commit")

        # Ejecutar operación
        ...
```

**Opción 2**: En ToolExecutionAdapter (centralized)
```python
# core/agents_and_tools/agents/infrastructure/adapters/tool_execution_adapter.py
class ToolExecutionAdapter:
    # RBAC policy
    TOOL_PERMISSIONS = {
        "DEV": ["git.commit", "files.write", "tests.pytest", ...],
        "QA": ["files.read", "tests.pytest", "http.post", ...],
        "ARCHITECT": ["files.search", "git.log", "db.query", ...],
        "DEVOPS": ["docker.build", "http.get", "files.edit", ...],
        "DATA": ["db.query", "files.write", "tests.pytest", ...],
    }

    async def execute_tool(self, tool: str, operation: str, params: dict) -> dict:
        # Validate permission BEFORE execution
        tool_op = f"{tool}.{operation}"
        if tool_op not in self.TOOL_PERMISSIONS[self.agent_role]:
            raise PermissionError(
                f"Role {self.agent_role} not allowed to use {tool_op}"
            )

        # Execute tool
        ...
```

### Impacto

⚠️ **Medio-Alto**:
- Agentes pueden ejecutar operaciones fuera de su rol
- No hay audit trail de violaciones de permisos
- Seguridad y compliance comprometidos
- No es producción-ready

#### Solución Propuesta (Nivel 1)

**Implementar Opción 2 (ToolExecutionAdapter)**:
1. Definir matriz de permisos en YAML config
2. Validar permisos antes de ejecutar herramientas
3. Loggear violaciones de permisos
4. Incluir en audit trail
5. Tests unitarios para cada rol

---

### Nivel 2: Decision Authority RBAC (CRÍTICO - Recién Identificado)

#### ¿Qué Debería Existir?

**Matriz de Autoridad por Rol**:

| Rol | Puede Aprobar | Puede Rechazar | Scope de Revisión | Puede Decidir |
|-----|---------------|----------------|-------------------|---------------|
| **ARCHITECT** | ✅ Propuestas DEV | ✅ Por falta de cohesión/calidad arquitectónica | Todas las deliberaciones técnicas | ✅ Arquitectura final |
| **QA** | ❌ Propuestas técnicas | ✅ Si no cumplen spec/acceptance criteria | Todas las deliberaciones (validar spec compliance) | ❌ NO puede meterse en temas técnicos |
| **DEV** | ❌ Solo peer review | ❌ Solo critique de peers | Solo deliberaciones de DEV | ❌ NO (Architect decide) |
| **DEVOPS** | ❌ Solo peer review | ❌ Solo critique de peers | Solo deliberaciones de DEVOPS | ❌ NO (Architect decide) |
| **DATA** | ❌ Solo peer review | ❌ Solo critique de peers | Solo deliberaciones de DATA | ❌ NO (Architect decide) |
| **PO** | ✅ TODAS | ✅ TODAS | TODO | ✅ Decisión final de negocio |

#### Casos de Uso Críticos

**Caso 1: Architect Rechaza Propuesta DEV**
```python
# Deliberación de 3 DEVs sobre "Add authentication"
dev_proposals = [
    {"dev_id": "dev-1", "approach": "Use custom JWT implementation", "rank": 1},
    {"dev_id": "dev-2", "approach": "Use passport.js library", "rank": 2},
    {"dev_id": "dev-3", "approach": "Use Auth0 service", "rank": 3},
]

# Architect revisa
architect = VLLMAgent(role="ARCHITECT", ...)
decision = await architect.review_deliberation(
    deliberation_id="delib-123",
    proposals=dev_proposals,
    criteria=["cohesion", "maintainability", "security"]
)

# Architect RECHAZA ganadora (rank 1) por falta de cohesión
if decision.action == "REJECT":
    # Architect puede:
    # A) Elegir otra propuesta (rank 2)
    # B) Pedir re-deliberación con nuevas constraints
    # C) Proponer su propia solución

    selected = decision.select_proposal(dev_proposals[1])  # Elige passport.js
    rationale = "Custom JWT is reinventing the wheel. Use battle-tested library."
```

**Actualmente**: ❌ Architect NO puede rechazar - Solo puede ver propuestas

**Caso 2: QA Valida Spec Compliance (Sin Opinar en Técnica)**
```python
# Deliberación de DEVs sobre implementación
dev_proposals = [...]

# QA revisa SOLO spec compliance
qa = VLLMAgent(role="QA", ...)
validation = await qa.validate_spec_compliance(
    deliberation_id="delib-123",
    proposals=dev_proposals,
    acceptance_criteria=[
        "User can login with email",
        "Password reset via email",
        "Session timeout after 30 min"
    ]
)

# QA puede RECHAZAR si proposals NO cumplen AC
if not validation.meets_acceptance_criteria:
    validation.reject(
        reason="None of the proposals address password reset requirement",
        missing_criteria=["Password reset via email"]
    )
    # Trigger re-deliberation with constraint

# QA NO puede opinar sobre:
# - "Should we use JWT or sessions?" ← Técnico, fuera de scope
# - "Database schema for users" ← Técnico, fuera de scope
# - "Which library to use" ← Técnico, fuera de scope

# QA SOLO valida:
# - ¿Se cumplen los acceptance criteria?
# - ¿La solución es testeable?
# - ¿Hay tests suficientes en el plan?
```

**Actualmente**: ❌ QA NO tiene mecanismo para validar spec compliance

**Caso 3: PO Tiene Decisión Final**
```python
# Architect seleccionó propuesta técnica
architect_selection = {
    "selected_proposal": "Use passport.js",
    "rationale": "Battle-tested library"
}

# QA validó spec compliance
qa_validation = {
    "approved": True,
    "all_criteria_met": True
}

# PO revisa decisión final
po = HumanPO(...)  # Human in the loop
po_decision = await po.review_final_decision(
    story_id="US-123",
    architect_selection=architect_selection,
    qa_validation=qa_validation,
    estimated_effort="8 hours"
)

# PO puede:
# A) Aprobar → Plan se ejecuta
# B) Rechazar → Pedir re-planificación
# C) Modificar → Cambiar constraints (ej: "Use free library, not Auth0")

if po_decision.action == "MODIFY":
    new_constraint = "Must use free/open-source solution only"
    # Trigger re-deliberation with new constraint
```

**Actualmente**: ❌ PO NO tiene interfaz para aprobar/rechazar decisiones

**Específicamente falta**:
- ❌ NO existe UI (dashboard/frontend) para PO
- ❌ NO existe API gRPC para approve/reject
- ❌ NO existe workflow de aprobación
- ❌ NO hay notificaciones al PO cuando hay decisiones pendientes
- ❌ NO hay tracking de decisiones aprobadas/rechazadas

**Ubicación esperada (NO EXISTE)**:
```
ui/po-react/           ← UI existe pero NO tiene review/approve features
services/context/      ← NO tiene APIs de aprobación
services/orchestrator/ ← NO tiene APIs de aprobación
```

#### ¿Qué Falta Implementar?

**A. API Layer (gRPC)**

```proto
// specs/fleet/orchestrator/v1/orchestrator.proto (AGREGAR)
service OrchestratorService {
  // ... existing RPCs ...
  
  // Decision review & approval APIs (NUEVOS)
  rpc ListPendingDecisions (ListPendingDecisionsRequest) 
      returns (ListPendingDecisionsResponse);
  
  rpc GetDecisionDetails (GetDecisionDetailsRequest) 
      returns (GetDecisionDetailsResponse);
  
  rpc ApproveDecision (ApproveDecisionRequest) 
      returns (ApproveDecisionResponse);
  
  rpc RejectDecision (RejectDecisionRequest) 
      returns (RejectDecisionResponse);
  
  rpc RequestChanges (RequestChangesRequest) 
      returns (RequestChangesResponse);
}

message ListPendingDecisionsRequest {
  string po_id = 1;
  string status = 2;  // "PENDING", "APPROVED", "REJECTED"
}

message PendingDecision {
  string decision_id = 1;
  string story_id = 2;
  string deliberation_id = 3;
  string role = 4;  // DEV, QA, ARCHITECT
  string selected_proposal = 5;
  string rationale = 6;
  repeated string alternatives = 7;
  string estimated_effort = 8;
  bool qa_validated = 9;
  bool architect_approved = 10;
  string created_at = 11;
}

message ListPendingDecisionsResponse {
  repeated PendingDecision decisions = 1;
  int32 total = 2;
}

message ApproveDecisionRequest {
  string decision_id = 1;
  string po_id = 2;
  string comments = 3;  // Optional PO comments
}

message RejectDecisionRequest {
  string decision_id = 1;
  string po_id = 2;
  string reason = 3;  // Why PO rejects
  string new_constraints = 4;  // New requirements for re-deliberation
}

message RequestChangesRequest {
  string decision_id = 1;
  string po_id = 2;
  repeated string changes_requested = 3;
  map<string, string> modified_constraints = 4;
}
```

**B. UI Layer (React Dashboard para PO)**

```tsx
// ui/po-react/src/pages/DecisionReview.tsx (NUEVO)
import { useState, useEffect } from 'react';

interface PendingDecision {
  decision_id: string;
  story_id: string;
  role: string;
  selected_proposal: string;
  rationale: string;
  alternatives: string[];
  estimated_effort: string;
  qa_validated: boolean;
  architect_approved: boolean;
}

export function DecisionReviewPage() {
  const [pendingDecisions, setPendingDecisions] = useState<PendingDecision[]>([]);
  
  useEffect(() => {
    // Fetch pending decisions from API
    fetch('/api/orchestrator/pending-decisions')
      .then(res => res.json())
      .then(data => setPendingDecisions(data.decisions));
  }, []);
  
  const handleApprove = async (decisionId: string) => {
    await fetch(`/api/orchestrator/approve/${decisionId}`, {
      method: 'POST',
      body: JSON.stringify({ po_id: 'po-001', comments: 'LGTM' })
    });
    // Refresh list
  };
  
  const handleReject = async (decisionId: string, reason: string) => {
    await fetch(`/api/orchestrator/reject/${decisionId}`, {
      method: 'POST',
      body: JSON.stringify({ 
        po_id: 'po-001', 
        reason,
        new_constraints: 'Use open-source libraries only'
      })
    });
    // Refresh list
  };
  
  return (
    <div className="decision-review-page">
      <h1>Pending Decisions for Review</h1>
      
      {pendingDecisions.map(decision => (
        <DecisionCard
          key={decision.decision_id}
          decision={decision}
          onApprove={() => handleApprove(decision.decision_id)}
          onReject={(reason) => handleReject(decision.decision_id, reason)}
        />
      ))}
    </div>
  );
}

function DecisionCard({ decision, onApprove, onReject }) {
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  
  return (
    <div className="decision-card border rounded-lg p-6 mb-4">
      {/* Story Info */}
      <div className="story-header">
        <h2>{decision.story_id}</h2>
        <span className="role-badge">{decision.role}</span>
      </div>
      
      {/* Selected Proposal */}
      <div className="selected-proposal mt-4">
        <h3>✅ Selected Proposal</h3>
        <p>{decision.selected_proposal}</p>
        <p className="text-sm text-gray-600">
          <strong>Rationale:</strong> {decision.rationale}
        </p>
        <p className="text-sm text-gray-600">
          <strong>Effort:</strong> {decision.estimated_effort}
        </p>
      </div>
      
      {/* Alternatives */}
      <div className="alternatives mt-4">
        <h3>Other Options Considered</h3>
        <ul>
          {decision.alternatives.map((alt, i) => (
            <li key={i} className="text-sm">{alt}</li>
          ))}
        </ul>
      </div>
      
      {/* Validation Status */}
      <div className="validation-status mt-4 flex gap-4">
        <div className={decision.architect_approved ? 'text-green-600' : 'text-gray-400'}>
          {decision.architect_approved ? '✅' : '⏳'} Architect Approved
        </div>
        <div className={decision.qa_validated ? 'text-green-600' : 'text-gray-400'}>
          {decision.qa_validated ? '✅' : '⏳'} QA Validated
        </div>
      </div>
      
      {/* Actions */}
      <div className="actions mt-6 flex gap-4">
        <button 
          onClick={onApprove}
          className="btn-approve bg-green-600 text-white px-6 py-2 rounded"
        >
          ✅ Approve & Execute
        </button>
        
        <button 
          onClick={() => setShowRejectDialog(true)}
          className="btn-reject bg-red-600 text-white px-6 py-2 rounded"
        >
          ❌ Reject
        </button>
        
        <button className="btn-changes bg-yellow-600 text-white px-6 py-2 rounded">
          🔄 Request Changes
        </button>
      </div>
      
      {/* Reject Dialog */}
      {showRejectDialog && (
        <RejectDialog
          onConfirm={(reason) => {
            onReject(reason);
            setShowRejectDialog(false);
          }}
          onCancel={() => setShowRejectDialog(false)}
        />
      )}
    </div>
  );
}
```

**C. Backend Use Cases (Orchestrator)**

**D. Notification System (NEW)**

```python
# services/orchestrator/application/usecases/notify_po_usecase.py
class NotifyPOUseCase:
    """Notify PO when there are pending decisions."""
    
    async def execute(self, decision_id: str) -> None:
        decision = await self.decision_store.get(decision_id)
        
        # Check if ready for PO review
        if not decision.architect_approved:
            return  # Wait for architect
        
        if not decision.qa_validated:
            return  # Wait for QA
        
        # Both approved, notify PO
        await self.notification_port.send_notification(
            recipient="PO",
            title=f"Decision ready for approval: {decision.story_id}",
            body=f"Role: {decision.role}, Proposal: {decision.selected_proposal}",
            action_url=f"/decisions/{decision_id}",
            priority="HIGH"
        )
        
        # Publish event
        await self.messaging.publish(
            "orchestration.decision.ready_for_po",
            decision.to_dict()
        )
```

**E. Decision Tracking (State Machine)**

```python
# services/orchestrator/domain/entities/decision_state.py
from enum import Enum

class DecisionState(Enum):
    """Decision approval workflow states."""
    DELIBERATION_COMPLETE = "DELIBERATION_COMPLETE"
    PENDING_ARCHITECT = "PENDING_ARCHITECT"
    PENDING_QA = "PENDING_QA"
    PENDING_PO = "PENDING_PO"
    PO_APPROVED = "PO_APPROVED"
    PO_REJECTED = "PO_REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"

# Workflow:
# DELIBERATION_COMPLETE 
#   → PENDING_ARCHITECT (architect reviews)
#   → PENDING_QA (QA validates spec)
#   → PENDING_PO (PO makes final decision)
#   → PO_APPROVED → EXECUTING → COMPLETED
#   OR
#   → PO_REJECTED (re-deliberate with new constraints)
#   OR
#   → CHANGES_REQUESTED (modify and re-submit)
```

**F. REST API Gateway (for UI)**

```python
# services/api-gateway/routes/decisions.py (NEW SERVICE)
from fastapi import APIRouter, HTTPException
from .grpc_clients import orchestrator_client

router = APIRouter(prefix="/api/decisions")

@router.get("/pending")
async def list_pending_decisions(po_id: str = "po-001"):
    """Get all decisions pending PO approval."""
    response = await orchestrator_client.ListPendingDecisions(
        po_id=po_id,
        status="PENDING_PO"
    )
    return {"decisions": response.decisions, "total": response.total}

@router.post("/{decision_id}/approve")
async def approve_decision(decision_id: str, body: dict):
    """PO approves decision."""
    response = await orchestrator_client.ApproveDecision(
        decision_id=decision_id,
        po_id=body["po_id"],
        comments=body.get("comments", "")
    )
    
    if response.success:
        # Trigger execution
        await orchestrator_client.ExecutePlan(
            decision_id=decision_id
        )
    
    return {"success": response.success}

@router.post("/{decision_id}/reject")
async def reject_decision(decision_id: str, body: dict):
    """PO rejects decision and requests re-deliberation."""
    response = await orchestrator_client.RejectDecision(
        decision_id=decision_id,
        po_id=body["po_id"],
        reason=body["reason"],
        new_constraints=body.get("new_constraints", "")
    )
    
    if response.success:
        # Trigger re-deliberation with new constraints
        await orchestrator_client.Deliberate(
            story_id=response.story_id,
            role=response.role,
            constraints=response.new_constraints
        )
    
    return {"success": response.success}
```

---

**1. Decision Authority Enforcement**
```python
# core/orchestrator/domain/ports/decision_authority_port.py
class DecisionAuthorityPort(Protocol):
    async def can_approve_deliberation(
        self,
        role: str,
        deliberation_type: str,  # "DEV", "QA", "ARCHITECT", etc.
    ) -> bool:
        """Check if role has authority to approve this deliberation."""

    async def can_reject_proposal(
        self,
        role: str,
        proposal: Proposal,
        reason: str,
    ) -> bool:
        """Check if role can reject with this reason."""

    async def get_review_scope(
        self,
        role: str,
    ) -> ReviewScope:
        """Get what this role can review."""
        # ARCHITECT: all technical deliberations
        # QA: all deliberations (for spec validation only)
        # DEV: only DEV deliberations (peer review)
```

**2. Deliberation Visibility Matrix**
```python
# Config: config/rbac/decision_authority.yaml
decision_authority:
  ARCHITECT:
    can_approve: ["DEV", "QA", "DEVOPS", "DATA"]
    can_reject: ["DEV", "QA", "DEVOPS", "DATA"]
    rejection_criteria:
      - "low_cohesion"
      - "poor_maintainability"
      - "security_risk"
      - "performance_issue"
    visibility: "ALL_TECHNICAL"
    final_decision: true

  QA:
    can_approve: []  # QA no aprueba, solo valida
    can_reject: ["DEV", "QA", "DEVOPS", "DATA"]  # Puede rechazar si no cumple spec
    rejection_criteria:
      - "missing_acceptance_criteria"
      - "insufficient_test_coverage"
      - "not_testable"
    visibility: "ALL"  # Ve todo para validar spec compliance
    final_decision: false
    scope_boundaries:  # Límites de lo que puede opinar
      allowed: ["spec_compliance", "testability", "acceptance_criteria"]
      forbidden: ["technical_implementation", "library_choice", "architecture"]

  DEV:
    can_approve: []
    can_reject: []  # Solo peer critique, no rechazo formal
    visibility: "SAME_ROLE_ONLY"  # Solo ve deliberaciones de DEV
    final_decision: false

  PO:
    can_approve: ["ALL"]
    can_reject: ["ALL"]
    rejection_criteria: ["ANY"]  # PO puede rechazar por cualquier razón
    visibility: "ALL"
    final_decision: true  # Decisión final de negocio
    can_modify_constraints: true
```

**3. Approval/Rejection Workflow**
```python
# services/orchestrator/application/usecases/approve_deliberation_usecase.py
class ApproveDeliberationUseCase:
    async def execute(
        self,
        deliberation_id: str,
        reviewer_role: str,
        action: str,  # "APPROVE", "REJECT", "REQUEST_CHANGES"
        rationale: str,
    ) -> ApprovalResult:
        # 1. Check authority
        if not await self.authority_port.can_approve_deliberation(
            role=reviewer_role,
            deliberation_type=deliberation.role
        ):
            raise PermissionError(
                f"Role {reviewer_role} cannot approve {deliberation.role} deliberations"
            )

        # 2. Validate rejection criteria (if rejecting)
        if action == "REJECT":
            if not await self.authority_port.can_reject_with_reason(
                role=reviewer_role,
                reason=rationale
            ):
                raise PermissionError(
                    f"Role {reviewer_role} cannot reject with reason: {rationale}"
                )

        # 3. Record decision
        decision = Decision(
            deliberation_id=deliberation_id,
            reviewer_role=reviewer_role,
            action=action,
            rationale=rationale,
            timestamp=now()
        )

        await self.decision_store.save(decision)

        # 4. Publish event
        await self.messaging.publish(
            "orchestration.deliberation.approved",
            decision.to_dict()
        )

        return ApprovalResult(success=True, decision_id=decision.id)
```

**4. Scope Boundary Validation (QA Case)**
```python
# services/orchestrator/domain/services/scope_validator.py
class ScopeValidator:
    """Validates that reviewers stay within their scope boundaries."""

    QA_ALLOWED_TOPICS = [
        "spec_compliance",
        "acceptance_criteria",
        "testability",
        "test_coverage",
        "edge_cases"
    ]

    QA_FORBIDDEN_TOPICS = [
        "technical_implementation",
        "library_choice",
        "architecture_design",
        "database_schema",
        "algorithm_choice"
    ]

    async def validate_qa_review(self, review_text: str) -> ValidationResult:
        """Ensure QA review stays within allowed scope."""
        # Use LLM to classify review topics
        topics = await self.llm_classifier.classify_topics(review_text)

        forbidden_found = []
        for topic in topics:
            if topic in self.QA_FORBIDDEN_TOPICS:
                forbidden_found.append(topic)

        if forbidden_found:
            return ValidationResult(
                valid=False,
                reason=f"QA review contains forbidden topics: {forbidden_found}",
                suggestion="Focus on spec compliance and testability only"
            )

        return ValidationResult(valid=True)
```

#### Ejemplos de Enforcement

**Ejemplo 1: Architect Rechaza por Falta de Cohesión**
```python
# Deliberation completada con winner
delib_result = {
    "deliberation_id": "delib-456",
    "role": "DEV",
    "winner": "dev-1",
    "proposals": [...]
}

# Architect revisa
architect_review = await approve_deliberation_usecase.execute(
    deliberation_id="delib-456",
    reviewer_role="ARCHITECT",
    action="REJECT",
    rationale="Winner proposal lacks cohesion. Database logic mixed with UI code."
)

# ✅ ALLOWED: Architect puede rechazar DEV deliberations por "low_cohesion"

# Architect selecciona otra propuesta
architect_selection = await select_proposal_usecase.execute(
    deliberation_id="delib-456",
    reviewer_role="ARCHITECT",
    selected_proposal="dev-2",  # Elige rank 2 en lugar de rank 1
    rationale="Proposal 2 has better separation of concerns"
)

# ✅ ALLOWED: Architect tiene decision authority
```

**Ejemplo 2: QA Intenta Opinar sobre Técnica (BLOQUEADO)**
```python
# QA intenta rechazar por razón técnica
qa_review = await approve_deliberation_usecase.execute(
    deliberation_id="delib-456",
    reviewer_role="QA",
    action="REJECT",
    rationale="Should use MongoDB instead of PostgreSQL for better performance"
)

# ❌ BLOCKED: QA no puede rechazar por razones técnicas
# Exception: PermissionError: Role QA cannot reject with technical reason

# QA puede rechazar por spec compliance
qa_valid_review = await approve_deliberation_usecase.execute(
    deliberation_id="delib-456",
    reviewer_role="QA",
    action="REJECT",
    rationale="None of the proposals address acceptance criteria: 'User can reset password'"
)

# ✅ ALLOWED: QA puede rechazar por missing acceptance criteria
```

**Ejemplo 3: DEV Intenta Aprobar (BLOQUEADO)**
```python
# DEV intenta aprobar deliberación
dev_approval = await approve_deliberation_usecase.execute(
    deliberation_id="delib-456",
    reviewer_role="DEV",
    action="APPROVE",
    rationale="I like proposal 1"
)

# ❌ BLOCKED: DEV no tiene decision authority
# Exception: PermissionError: Role DEV cannot approve DEV deliberations
#            Only ARCHITECT and PO can approve.
```

#### Solución Propuesta (Nivel 2)

**Implementación Completa**:

1. **Crear matriz de autoridad** (`config/rbac/decision_authority.yaml`)
2. **Port DecisionAuthorityPort** con validaciones
3. **Use case ApproveDeliberationUseCase** con enforcement
4. **ScopeValidator** para QA (evitar opiniones técnicas)
5. **Audit trail** de aprobaciones/rechazos
6. **UI para PO** (revisar y aprobar decisiones)
7. **Tests unitarios** para cada regla de RBAC

**Estimación**: 1 semana de desarrollo + tests

---

## 🚨 GAP 3: Rehydration Limitada a 1 Nodo

### ¿Qué Existe?

**Rehydration actual** (`CONTEXT_REHYDRATION_FLOW.md`):

```python
# core/context/session_rehydration.py
class SessionRehydrationUseCase:
    def build(self, request: RehydrationRequest) -> RehydrationBundle:
        # 1. Read from Neo4j (decision graph)
        decisions = self.graph.list_decisions(req.case_id)

        # 2. Read from Redis/Valkey (planning data)
        spec = self.plan_store.get_case_spec(req.case_id)

        # 3. Merge both sources into RoleContextFields
        # 4. Return bundle with packs per role
```

**Limitación identificada por usuario**:
> "Es posible que esté acotado a un solo nodo"

**Flujo actual**:
```
Context Service
    ↓
RehydrateContext(case_id, role)
    ↓
Query Neo4j: list_decisions(case_id)  ← SCOPED TO CASE
Query Valkey: get_case_spec(case_id)   ← SCOPED TO CASE
    ↓
Return context for THAT CASE ONLY
```

### ¿Qué Falta?

❌ **PO no puede navegar el grafo**:
- Ver decisiones históricas de otros casos
- Explorar soluciones pasadas
- Navegar por relaciones (SIMILAR_TO, DEPENDS_ON)
- Comparar decisiones entre casos
- Rehidratar contexto desde cualquier nodo del grafo

### Caso de Uso del PO

**Escenario**: PO quiere implementar feature similar a uno anterior

```
PO navega grafo:
1. Story actual: US-456 "Add OAuth2 login"
2. Busca: Stories similares en el pasado
3. Encuentra: US-123 "Add JWT authentication" (hace 3 meses)
4. Lee decisiones:
   - Decision-042: Use JWT tokens (ARCHITECT)
   - Decision-051: Store in Redis (DATA)
   - Decision-089: Hash passwords with bcrypt (SECURITY)
5. Rehidrata contexto de US-123 para ver:
   - Qué problemas surgieron
   - Qué soluciones funcionaron
   - Test coverage achieved
   - Performance metrics
6. Propone cambio: "Let's use the same approach for OAuth2"
```

**Actualmente**: ❌ IMPOSIBLE - Solo puede ver caso actual

### Solución Propuesta

**API Nueva en Context Service**:
```python
# services/context/server.py
async def NavigateGraph(self, request, context):
    """Navigate decision graph from any node."""
    # request.start_node_id = "US-123"
    # request.relationship_type = "SIMILAR_TO"
    # request.max_depth = 3

    # 1. Query Neo4j with graph traversal
    nodes = await self.graph_query.traverse_graph(
        start_node=request.start_node_id,
        relationship=request.relationship_type,
        max_depth=request.max_depth,
    )

    # 2. Return graph snapshot
    return NavigateGraphResponse(
        nodes=[...],
        edges=[...],
        total_nodes=len(nodes)
    )

async def RehydrateFromNode(self, request, context):
    """Rehydrate context from ANY node in graph."""
    # request.node_id = "US-123" or "Decision-042"
    # request.role = "PO" (new role!)

    # 1. Query Neo4j for node + neighborhood
    node_context = await self.graph_query.get_node_context(
        node_id=request.node_id,
        include_neighbors=True,
        include_history=True,
    )

    # 2. Build context for PO
    # PO needs DIFFERENT context than agents (more historical, less surgical)
    context = self.context_assembler.build_po_context(node_context)

    # 3. Return rich context
    return RehydrateFromNodeResponse(
        context_text=context,
        token_count=len(context.split()),
        related_nodes=[...],
        timeline=[...]
    )
```

**UI para PO** (necesario):
- Graph visualization (D3.js/Cytoscape)
- Click en nodo → Ver decisiones
- Click en "Rehidratar" → Ver contexto completo
- Comparar nodos side-by-side

---

## 🚨 GAP 4: Reunión de Planificación vs Deliberate

### Pregunta del Usuario

> "¿Cómo se hace la reunión de planificación? Entiendo que es deliberate pero deliberate es por agente."

### Estado Actual

**Deliberate** (`DeliberateUseCase`):
```python
# core/orchestrator/usecases/peer_deliberation_usecase.py
class Deliberate:
    async def execute(self, task: str, constraints: TaskConstraints) -> DeliberationResult:
        # Multi-agent deliberation (peer review)
        # N agents generate proposals
        # Peers critique each other
        # Architect ranks and selects winner
```

**Scope**: Deliberación **DENTRO de un role** (ej: 3 DEV agents deliberan entre ellos)

### ¿Qué Falta?

**Cross-Role Planning Session**: Deliberación **ENTRE roles diferentes**

**Ejemplo esperado**:
```
Reunion de Planificación (Cross-role):
Participantes: PO (human) + 1 DEV + 1 QA + 1 ARCHITECT + 1 DEVOPS

Story: "Add OAuth2 authentication"

Round 1: Cada rol propone approach
- DEV: "Use passport.js library"
- QA: "Need integration tests with OAuth providers"
- ARCHITECT: "Store tokens in Redis with encryption"
- DEVOPS: "Use environment variables for client secrets"

Round 2: Discusión y refinement
- DEV vs ARCHITECT: ¿Dónde almacenar tokens?
- QA vs DEVOPS: ¿Cómo hacer tests con secrets?

Round 3: PO decide
- PO: "Let's go with Redis storage, architect's approach"
- PO: "QA, use test fixtures for OAuth mocking"

Output: Plan aprobado con decisiones por rol
```

**Actualmente**: ❌ NO EXISTE - Solo deliberation dentro del mismo rol

### Dónde Está Documentado

**RFC-0003** (`docs/reference/rfcs/RFC-0003-collaboration-flow.md:48-56`):
```markdown
### 2. Refinement / Sprint Planning (agent proposal)

- A role-based agent council analyzes the case and proposes:
  - Required technical subtasks
  - Technologies and processes per subtask
  - Risks and dependencies
- The Architect integrates proposals into a Preliminary Plan.
```

**AGILE_TEAM.md** (`docs/architecture/AGILE_TEAM.md:27-32`):
```markdown
## Ceremonies

- Planning: PO defines and prioritizes; Architect decomposes; agents estimate
- Daily: PO joins as needed to clarify priorities and unblock work
- Review: PO validates against acceptance criteria; Architect selects final approach
- Retrospective: PO shares business feedback; outcomes recorded in the knowledge graph
```

**Estado**: 📋 DOCUMENTADO, ❌ NO IMPLEMENTADO

### Solución Propuesta

**Nuevo Use Case**: `CrossRolePlanningUseCase`

```python
# core/orchestrator/usecases/cross_role_planning_usecase.py
class CrossRolePlanningUseCase:
    """
    Coordina reunión de planificación con múltiples roles.

    Similar a Deliberate pero CROSS-ROLE en lugar de PEER (same role).
    """

    async def execute(
        self,
        story_id: str,
        participants: dict[str, Agent],  # {"DEV": agent1, "QA": agent2, ...}
        rounds: int = 3,
    ) -> PlanningSessionResult:
        # Round 1: Cada rol propone approach independiente
        proposals = {}
        for role, agent in participants.items():
            proposal = await agent.execute_task(
                task=f"Propose approach for {story_id} from {role} perspective",
                context=story_context,
            )
            proposals[role] = proposal

        # Round 2: Cross-role discussion (agents critique other roles)
        for role, agent in participants.items():
            for other_role, other_proposal in proposals.items():
                if role != other_role:
                    critique = await agent.critique(
                        proposal=other_proposal,
                        from_perspective=role,
                    )
                    # Store critiques

        # Round 3: Architect integrates into unified plan
        architect = participants["ARCHITECT"]
        integrated_plan = await architect.integrate_proposals(
            proposals=proposals,
            critiques=critiques,
        )

        # Return planning session result
        return PlanningSessionResult(
            plan=integrated_plan,
            proposals_by_role=proposals,
            duration_ms=...,
            # PO reviews and approves manually
        )
```

---

## 🚨 GAP 5: Ceremonias Ágiles No Implementadas

### ¿Qué Está Documentado?

**AGILE_TEAM.md**:
```markdown
## Ceremonies

- Planning: PO defines and prioritizes; Architect decomposes; agents estimate
- Daily: PO joins as needed to clarify priorities and unblock work
- Review: PO validates against acceptance criteria; Architect selects final approach
- Retrospective: PO shares business feedback; outcomes recorded in the knowledge graph
```

**RFC-0003**:
```markdown
### 5. Closure and Feedback

- Upon completion of all subtasks:
  - Generate a closure report with decisions, outcomes, durations, and learnings
  - Index the report for future retrieval in similar cases
  - Add lessons learned to the knowledge repository
```

### ¿Qué Falta?

**TODAS las ceremonias ágiles**:

#### 1. **Sprint Planning** ❌ NO EXISTE
```
Ceremonia: Sprint Planning
Participantes: PO + Team (DEV, QA, ARCHITECT, DEVOPS, DATA)
Input: Product Backlog (stories priorizadas)
Output: Sprint Goal + Sprint Backlog (tasks con estimaciones)

Actualmente: No implementado
Gap: No hay manera de crear sprints, asignar stories, estimar esfuerzo
```

#### 2. **Daily Standup** ❌ NO EXISTE
```
Ceremonia: Daily Standup
Participantes: Team (optional PO)
Input: Yesterday's work, today's plan, blockers
Output: Sincronización del equipo, identificación de blockers

Actualmente: No implementado
Gap: No hay tracking de progreso diario, no se identifican blockers
```

#### 3. **Sprint Review** ❌ NO EXISTE
```
Ceremonia: Sprint Review
Participantes: PO + Team + Stakeholders
Input: Sprint Backlog completado
Output: Demo de features, feedback del PO, acceptance/rejection

Actualmente: No implementado
Gap: PO no puede validar features, no hay demo automático
```

#### 4. **Retrospective** ❌ NO EXISTE
```
Ceremonia: Retrospective
Participantes: Team (NO PO)
Input: Sprint execution data
Output: What went well, what didn't, action items for next sprint

Actualmente: No implementado
Gap: No hay captura de lessons learned, no mejora continua
```

### Solución Propuesta

**Nuevo Bounded Context**: `agile-ceremonies`

```python
# services/agile-ceremonies/application/usecases/

class CreateSprintUseCase:
    """Create sprint and assign stories."""
    async def execute(self, stories: list[str], duration_days: int) -> Sprint

class DailyStandupUseCase:
    """Coordinate daily standup between agents."""
    async def execute(self, sprint_id: str) -> StandupSummary

class SprintReviewUseCase:
    """Present completed work to PO for validation."""
    async def execute(self, sprint_id: str) -> ReviewResult

class RetrospectiveUseCase:
    """Generate retrospective with lessons learned."""
    async def execute(self, sprint_id: str) -> RetrospectiveReport
```

**Persistencia** (Neo4j + Valkey):
```cypher
// Sprint nodes
(:Sprint {sprint_id, goal, start_date, end_date, status})
    -[:CONTAINS]->(:Story {story_id, ...})
    -[:HAS_TASK]->(:Task {task_id, ...})

// Retrospective nodes
(:Retrospective {retro_id, sprint_id, date})
    -[:LEARNED]->(:Lesson {what, why, action_items})
```

---

## 📊 Resumen de GAPS

| GAP | Severidad | Impacto | Esfuerzo Fix | Prioridad |
|-----|-----------|---------|--------------|-----------|
| 1. Planning Service eliminado | 🔴 Crítico | PO no puede gestionar stories | 1-2 semanas | P0 |
| 2. RBAC sin implementar | 🟡 Alto | Seguridad comprometida | 3-5 días | P1 |
| 3. Rehydration limitada | 🟡 Medio | PO no puede explorar grafo | 1 semana | P2 |
| 4. Planning meeting no existe | 🟡 Medio | Sin colaboración cross-role | 1-2 semanas | P2 |
| 5. Ceremonias no implementadas | 🟠 Bajo | Sin agile process tracking | 2-3 semanas | P3 |

---

## 🎯 Recomendaciones Priorizadas

### P0 - URGENTE (Esta Semana)
1. **Revivir Planning Service** o implementar FSM en Context Service
   - Gestión de historias de usuario
   - Transiciones de fase con guards
   - Eventos planning.*.* publicados

### P0 (bis) - URGENTE (Próximas 2 Semanas)
2. **Implementar RBAC Completo** (2 niveles)

   **Nivel 1 - Tool Execution**:
   - Matriz de permisos por rol
   - Validación antes de ejecutar herramientas
   - Audit trail de violaciones

   **Nivel 2 - Decision Authority** (MÁS CRÍTICO):
   - Decision authority matrix (quién aprueba/rechaza)
   - Architect puede rechazar propuestas DEV por falta de cohesión
   - QA puede validar spec compliance (con scope boundaries)
   - PO puede aprobar/rechazar decisiones finales
   - Scope validator para QA (no opinar en técnica)

### P2 - MEDIA (Próximos 2 Sprints)
3. **Extender Rehydration** para navegación de grafo
   - API NavigateGraph
   - API RehydrateFromNode
   - UI para PO (graph visualization)

4. **Implementar Cross-Role Planning**
   - Use case para reunión de planificación
   - Integración de propuestas multi-role
   - Aprobación del PO

### P3 - BAJA (Backlog)
5. **Implementar Ceremonias Ágiles**
   - Sprint Planning
   - Daily Standup
   - Sprint Review
   - Retrospective

---

**Decisión final**: Pendiente de aprobación del Software Architect (Tirso García Ibáñez)


