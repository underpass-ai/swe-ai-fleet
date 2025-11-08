# Shared Kernel - Final Design (Validated by Architect)

**Date:** 2025-11-06
**Architect:** Tirso García Ibáñez (Agile Expert)
**Status:** ✅ VALIDATED - 688 tests passing
**Location:** `core/shared/domain/action.py`

---

## 🎯 Final Action Inventory (FSM Transitions Only)

### Technical Actions (Implementation)
```python
COMMIT_CODE = "commit_code"      # Developer completes implementation
REVISE_CODE = "revise_code"      # Developer revises (arch OR qa feedback)
RUN_TESTS = "run_tests"          # QA runs tests
```

**Key Insight from Architect:**
- ✅ REVISE_CODE es genérico (arch feedback O qa feedback)
- ❌ FIX_BUGS eliminado (no existe en agile real)
- Ambos (arch_rejected, qa_failed) → implementing con REVISE_CODE

---

### Validation Actions (Approvals/Rejections)
```python
APPROVE_DESIGN = "approve_design"  # Architect approves
REJECT_DESIGN = "reject_design"    # Architect rejects
APPROVE_TESTS = "approve_tests"    # QA approves
REJECT_TESTS = "reject_tests"      # QA rejects
APPROVE_STORY = "approve_story"    # PO approves
REJECT_STORY = "reject_story"      # PO rejects
```

**Pattern:** Consistent APPROVE/REJECT pairs per role

---

### Workflow Coordination (Concurrency Control)
```python
CLAIM_TASK = "claim_task"        # Developer claims implementation
CLAIM_REVIEW = "claim_review"    # Architect claims review
CLAIM_TESTING = "claim_testing"  # QA claims testing
```

**Key Insight from Architect:**
- ✅ TODOS los validators necesitan CLAIM explícito
- ✅ Previene concurrent work (múltiples agents por rol)
- ❌ PO NO tiene CLAIM (único PO, no concurrency)

**Real Team Parallel:**
```
Jira Board:
  "Ready for Code Review" column
  → Multiple architects available
  → One "claims" (assigns to self) → "In Review"
  → Prevents duplicate reviews
```

---

### System Routing (Auto-Transitions)
```python
ASSIGN_TO_DEVELOPER = "assign_to_developer"          # Initial assignment
AUTO_ROUTE_TO_ARCHITECT = "auto_route_to_architect"  # After dev complete
AUTO_ROUTE_TO_QA = "auto_route_to_qa"                # After arch approve
AUTO_ROUTE_TO_PO = "auto_route_to_po"                # After QA pass
AUTO_COMPLETE = "auto_complete"                      # Final transition
```

**Key Insight from Architect:**
- ✅ Auto-transitions SÍ tienen action (para audit trail)
- ✅ Registradas como StateTransition (actor_role="system")
- Pattern: AUTO_ROUTE_TO_{ROLE} consistente

**Real Team Parallel:**
```
GitHub Actions:
  on:
    pull_request:
      types: [approved]
  then:
    - auto-assign to QA
    - move to "Ready for Testing"

Action logged: "AUTOMATION_TRIGGERED"
```

---

### Business Control
```python
DISCARD_TASK = "discard_task"  # PO discards task (business decision)
CANCEL = "cancel"              # Generic cancel (legacy)
RETRY = "retry"                # System retry
```

**Key Insight from Architect:**
- ✅ DISCARD_TASK (renamed from CANCEL_TASK)
- PO authority: Can discard from any state

---

## 🚫 Actions ELIMINADAS (No son Transiciones FSM)

```python
❌ FIX_BUGS  # Eliminado - mismo que REVISE_CODE
❌ ROUTE_TO_ARCHITECT_BY_DEV  # Ceremonia, NO transición
❌ ROUTE_TO_ARCHITECT_BY_PO   # Ceremonia, NO transición
```

**Rationale:**
- Ceremonias agile (dailys, sprint review) NO cambian estado task
- Son eventos paralelos (agent.consultation.*, ceremony.*)
- FSM solo track transiciones formales

---

## 📊 Action Categories (Final)

### Category 1: Work Claim (3 actions)
```
CLAIM_TASK     → Developer
CLAIM_REVIEW   → Architect
CLAIM_TESTING  → QA
```

### Category 2: Implementation (2 actions)
```
COMMIT_CODE  → Complete implementation
REVISE_CODE  → Revise after feedback (arch OR qa)
```

### Category 3: Validation (6 actions)
```
APPROVE_DESIGN / REJECT_DESIGN  → Architect
APPROVE_TESTS / REJECT_TESTS    → QA
APPROVE_STORY / REJECT_STORY    → PO
```

### Category 4: System Routing (5 actions)
```
ASSIGN_TO_DEVELOPER
AUTO_ROUTE_TO_ARCHITECT
AUTO_ROUTE_TO_QA
AUTO_ROUTE_TO_PO
AUTO_COMPLETE
```

### Category 5: Control (3 actions)
```
DISCARD_TASK  → PO discards
RETRY         → System retry
REQUEST_REVIEW → (legacy, evaluar uso)
```

**Total: 19 workflow actions** (clean, no cruft)

---

## 🏗️ FSM Design Principles (Validated by Architect)

### 1. **Ceremonies ≠ FSM Transitions**

```
Daily Standup / Sprint Review / Consultation:
  → Agent communication (NATS events)
  → Task state UNCHANGED
  → Feedback loops outside FSM

Formal Transitions:
  → State changes (implementing → pending_review)
  → Audit trail
  → Workflow gates
```

---

### 2. **CLAIM States for Concurrency**

```
Multiple Agents Per Role:
  → CLAIM required (prevent duplicate work)
  → Real team: Multiple people pick from backlog

Single Agent:
  → CLAIM optional (but good for consistency)
  → Real team: One person, still "assigns to self"
```

**Decision:** ALL validators have CLAIM except PO (single PO)

---

### 3. **REVISE_CODE is Generic**

```
Architect Rejects → implementing (REVISE_CODE)
QA Rejects → implementing (REVISE_CODE)

Same state, same action.
Context differentiates via feedback field.
```

**Real Team:** Jira status "In Progress" (rework) - mismo estado

---

### 4. **Auto-Transitions Have Actions**

```
StateTransition(
  from_state="dev_completed",
  to_state="pending_arch_review",
  action=AUTO_ROUTE_TO_ARCHITECT,
  actor_role="system"
)
```

**Rationale:** Audit trail completo (saber POR QUÉ cambió)

---

## ✅ Validación del Arquitecto

**Feedback incorporado:**
1. ✅ FIX_BUGS eliminado (usa REVISE_CODE)
2. ✅ ROUTE_BY_DEV eliminado (ceremonias, no FSM)
3. ✅ AUTO_* actions mantenidas (audit trail)
4. ✅ PO directo sin CLAIM (correcto)
5. ✅ DISCARD_TASK (renamed from CANCEL_TASK)

**Tests:**
- ✅ 688 tests passing (agents + orchestrator + planning + workflow)
- ✅ Coverage maintained
- ✅ No breaking changes

---

## 📚 Bounded Contexts Using Shared Kernel

### core/agents_and_tools
```python
from core.shared.domain import Action, ActionEnum, ScopeEnum

# Used in:
- Role (can_perform validation)
- RoleFactory (role definitions)
- Agent (RBAC enforcement)
```

### services/workflow
```python
from core.shared.domain import Action, ActionEnum

# Used in:
- WorkflowState (required_action field)
- StateTransition (action field)
- WorkflowStateMachine (transition validation)
- FSM config parsing
```

---

## 🎯 Next Steps (Validated)

**Shared Kernel:** ✅ COMPLETE
**Bounded Contexts:** ✅ DECOUPLED
**Tests:** ✅ PASSING

**Ready for:**
1. Claim Locks implementation
2. RBAC L3 (Context scoping)
3. Integrations
4. Deployment

---

**Approved By:** Tirso García Ibáñez (Architect)
**Quality:** Production-ready
**Confidence:** HIGH



