# Workflow Actions - Semantic Analysis & Fisuras

**Date:** 2025-11-06  
**Architect:** Tirso García Ibáñez + AI  
**Context:** Shared Kernel Migration + RBAC L2+L3  
**Branch:** feature/rbac-level-2-orchestrator

---

## 📋 Executive Summary

**Actions agregadas al Shared Kernel:** 8 nuevas
- ✅ **7 correctas** semánticamente
- ❌ **4 fisuras** detectadas que requieren corrección

**Estado:** Shared Kernel funcional pero con **inconsistencias** que deben resolverse antes de producción.

---

## 🆕 Nuevas Actions - Razonamiento Detallado

### 1. FIX_BUGS (TECHNICAL Scope) ✅

**FSM Usage:**
```yaml
# qa_failed → implementing (línea 246)
- from: qa_failed
  to: implementing
  action: FIX_BUGS
  role_required: developer
```

**Semántica:**
- Developer corrige bugs después de feedback de QA
- Diferente de REVISE_CODE (que es para cambios arquitecturales)

**Distinción Conceptual:**
```
REVISE_CODE (Post-Architect Rejection):
  Feedback: "Refactoriza para usar Strategy pattern"
  Feedback: "Cambia bcrypt por argon2 (mejor seguridad)"
  Scope: Diseño/arquitectura
  
FIX_BUGS (Post-QA Rejection):
  Feedback: "Test case login con email inválido falla"
  Feedback: "Edge case timeout no manejado"
  Scope: Bugs funcionales
```

**Real Team Parallel:**
```
Code Review (Architect): "Changes requested" → Developer revises design
QA Testing (QA): "Bugs found" → Developer fixes bugs

Son flujos DISTINTOS en un equipo real.
```

**Validación:** ✅ **CORRECTO**
- Semántica diferenciada
- Scope TECHNICAL apropiado
- Refleja realidad de equipos software

---

### 2. ASSIGN_TO_DEVELOPER (WORKFLOW Scope) ✅

**FSM Usage:**
```yaml
# todo → implementing (línea 158)
- from: todo
  to: implementing
  action: ASSIGN_TO_DEVELOPER
  role_required: null  # System action
```

**Semántica:**
- Initial task assignment
- System action (Planning Service trigger)
- Comienza el workflow

**Flujo de Integración:**
```
1. Planning Service: story.state = IN_PROGRESS
2. Planning Service publica: planning.story.transitioned
3. Workflow Service consume evento
4. Workflow Service: Para cada task:
     - Crea WorkflowState(current_state=TODO)
     - Transición: TODO → IMPLEMENTING (ASSIGN_TO_DEVELOPER)
     - Publica: workflow.task.assigned {role: developer}
5. Orchestrator asigna a developer agent
```

**Real Team Parallel:**
```
Sprint Planning:
  PO moves story to "In Progress" sprint
  → Scrum Master assigns tasks to developers
  → Developer picks up task from "To Do"
```

**Validación:** ✅ **CORRECTO**
- System-initiated workflow start
- Scope WORKFLOW apropiado
- Refleja assignment process

---

### 3-6. AUTO_ROUTE_TO_* Actions (WORKFLOW Scope) ✅

**AUTO_ROUTE_TO_ARCHITECT:**
```yaml
# dev_completed → pending_arch_review (línea 174)
- from: dev_completed
  to: pending_arch_review
  action: AUTO_ROUTE_TO_ARCHITECT
  role_required: null
  auto: true
```

**AUTO_ROUTE_TO_QA:**
```yaml
# arch_approved → pending_qa (línea 214)
- from: arch_approved
  to: pending_qa
  action: AUTO_ROUTE_TO_QA
  role_required: null
  auto: true
```

**AUTO_ROUTE_TO_PO:**
```yaml
# qa_passed → pending_po_approval (línea 254)
- from: qa_passed
  to: pending_po_approval
  action: AUTO_ROUTE_TO_PO
  role_required: null
  auto: true
```

**AUTO_COMPLETE:**
```yaml
# po_approved → done (línea 278)
- from: po_approved
  to: done
  action: AUTO_COMPLETE
  role_required: null
  auto: true
```

**Patrón Consistente:**
```
{intermediate_state} → AUTO_ROUTE_TO_{NEXT_ROLE} → {pending_state}

dev_completed   → AUTO_ROUTE_TO_ARCHITECT → pending_arch_review
arch_approved   → AUTO_ROUTE_TO_QA        → pending_qa
qa_passed       → AUTO_ROUTE_TO_PO        → pending_po_approval
po_approved     → AUTO_COMPLETE           → done
```

**Real Team Parallel:**
```
GitHub Actions Automation:
  on:
    pull_request:
      types: [approved]
    jobs:
      notify-qa:
        runs-on: ubuntu-latest
        steps:
          - name: Notify QA team
            # Auto-assign to QA after approval

JIRA Automation:
  When: Issue transitions to "Code Review Done"
  Then: Auto-move to "Ready for QA"
  And: Assign to QA team
```

**Validación:** ✅ **CORRECTO**
- Modelan JIRA/GitHub automation rules
- Patrón consistente AUTO_ROUTE_TO_{ROLE}
- Scope WORKFLOW apropiado
- System actions (auto: true)

---

### 7. CANCEL_TASK (WORKFLOW Scope) ✅

**FSM Usage:**
```yaml
# Wildcard transition (línea 284-289)
- from: "*"  # Any non-terminal state
  to: cancelled
  action: CANCEL_TASK
  role_required: po
```

**Semántica:**
- PO authority: Cancel work at any time
- Business decision override

**Real Team Parallel:**
```
Real Scenario:
  Mid-implementation, business priorities change
  PO: "Stop work on this, we're pivoting to X instead"
  Dev: "OK, closing ticket as cancelled"

SWE AI Fleet:
  Task in any state (implementing, arch_reviewing, etc.)
  PO Agent: ACTION: CANCEL_TASK
  Workflow: current_state → cancelled
```

**Validación:** ✅ **CORRECTO**
- PO authority modeled correctly
- Wildcard transition (flexible)
- Business override of technical workflow

---

### 8. CLAIM_TESTING (WORKFLOW Scope) ✅

**FSM Usage:**
```yaml
# pending_qa → qa_testing (línea 222)
- from: pending_qa
  to: qa_testing
  action: CLAIM_TESTING
  role_required: qa
```

**Pattern Consistency:**
```
Developer: CLAIM_TASK      (todo → implementing)
Architect: CLAIM_REVIEW    (pending_arch_review → arch_reviewing)
QA:        CLAIM_TESTING   (pending_qa → qa_testing)
PO:        (MISSING!)
```

**Real Team Parallel:**
```
Jira Board:
  Column "Ready for QA" (pending_qa)
  → QA picks ticket: "In Testing" (qa_testing)
  → Status change = "claim"
```

**Validación:** ✅ **CORRECTO**
- Consistente con CLAIM_TASK y CLAIM_REVIEW
- Prevents concurrent QA work on same task

---

## 🔴 FISURAS CRÍTICAS DETECTADAS

### FISURA 1: Test FSM Config vs Real FSM Config ❌

**Severidad:** HIGH  
**Ubicación:**
- `services/workflow/tests/unit/domain/test_workflow_state_machine.py` (líneas 48-61)
- `config/workflow.fsm.yaml` (real config)

**Problema:**
```python
# Test usa REQUEST_REVIEW genérico para TODAS las auto-transitions:
{"from": "dev_completed", "to": "pending_arch_review", "action": "request_review", "auto": True}
{"from": "arch_approved", "to": "pending_qa", "action": "request_review", "auto": True}
{"from": "qa_passed", "to": "done", "action": "request_review", "auto": True}

# FSM real usa actions específicas:
AUTO_ROUTE_TO_ARCHITECT
AUTO_ROUTE_TO_QA
AUTO_ROUTE_TO_PO
AUTO_COMPLETE
```

**Impacto:**
- Tests validan comportamiento INCORRECTO
- REQUEST_REVIEW sobrecargado (bad semantics)
- Tests pasan pero no reflejan production behavior

**Fix Required:**
```python
# Actualizar test_workflow_state_machine.py para usar FSM real
{
    "transitions": [
        {"from": "dev_completed", "to": "pending_arch_review", 
         "action": "auto_route_to_architect", "auto": True},
        {"from": "arch_approved", "to": "pending_qa", 
         "action": "auto_route_to_qa", "auto": True},
        # ... etc
    ]
}
```

---

### FISURA 2: WorkflowStateMetadata Desincronizado ❌

**Severidad:** CRITICAL  
**Ubicación:** `services/workflow/domain/services/workflow_state_metadata.py` línea 56

**Problema:**
```python
# Metadata dice:
WorkflowStateEnum.QA_FAILED: Action(value=ActionEnum.REVISE_CODE),  # ❌ WRONG

# FSM real dice:
- from: qa_failed
  to: implementing
  action: FIX_BUGS  # ✅ CORRECT
```

**Impacto:**
- Domain service retorna action incorrecta
- Use cases esperan REVISE_CODE pero FSM permite FIX_BUGS
- Transiciones fallan en producción

**Fix Required:**
```python
# Update workflow_state_metadata.py línea 56:
WorkflowStateEnum.QA_FAILED: Action(value=ActionEnum.FIX_BUGS),  # ✅ FIXED
```

---

### FISURA 3: CANCEL vs CANCEL_TASK (Duplicación) ⚠️

**Severidad:** MEDIUM  
**Ubicación:** `core/shared/domain/action.py`

**Problema:**
```python
CANCEL = "cancel"         # Línea 58 - ¿Usado dónde?
CANCEL_TASK = "cancel_task"  # Línea 65 - Usado en workflow.fsm.yaml
```

**Búsqueda de uso:**
```bash
# CANCEL no aparece en workflow.fsm.yaml
# CANCEL_TASK SÍ aparece en línea 286
```

**Decision Required:**
- Opción A: Eliminar CANCEL (legacy/no usado)
- Opción B: Aclarar diferencia (CANCEL = generic, CANCEL_TASK = workflow specific)
- Opción C: Alias (CANCEL_TASK = CANCEL para backward compatibility)

**Recomendación:** Mantener ambos por ahora, documentar diferencia

---

### FISURA 4: Naming Inconsistency en CLAIM Actions ⚠️

**Severidad:** LOW (naming convention)  
**Ubicación:** Action naming pattern

**Problema:**
```
CLAIM_TASK      → Specific (developer only)
CLAIM_REVIEW    → Generic (architect, po?)
CLAIM_TESTING   → Specific (qa only)
CLAIM_APPROVAL  → MISSING (po needs?)
```

**Inconsistencia:**
- 2 specific (TASK, TESTING)
- 1 generic (REVIEW)
- 1 missing (APPROVAL for PO)

**Opciones:**

**Opción A: All Specific**
```python
CLAIM_TASK              # Developer
CLAIM_ARCHITECTURE_REVIEW  # Architect
CLAIM_TESTING           # QA
CLAIM_BUSINESS_APPROVAL    # PO
```

**Opción B: Generic Grouping**
```python
CLAIM_IMPLEMENTATION    # Developer (CLAIM_TASK)
CLAIM_VALIDATION        # Architect, QA, PO (CLAIM_REVIEW, CLAIM_TESTING)
```

**Opción C: Keep Current + Add Missing**
```python
CLAIM_TASK      # Developer (existing)
CLAIM_REVIEW    # Architect (existing)
CLAIM_TESTING   # QA (existing)
CLAIM_APPROVAL  # PO (NEW - for consistency)
```

**Recomendación:** **Opción C** - menos breaking changes

---

## 📊 Resumen de Fisuras

| ID | Fisura | Severidad | Fix Required | Breaking Change |
|----|--------|-----------|--------------|-----------------|
| 1 | Test FSM vs Real FSM | HIGH | Update test config | No |
| 2 | Metadata QA_FAILED action | CRITICAL | Update metadata | No |
| 3 | CANCEL vs CANCEL_TASK duplicate | MEDIUM | Document or remove | Possible |
| 4 | CLAIM naming inconsistency | LOW | Add CLAIM_APPROVAL | No |

---

## ✅ Actions Validadas Como Correctas

### Correctas Semánticamente:

1. ✅ **FIX_BUGS** - Developer fixes bugs post-QA
2. ✅ **ASSIGN_TO_DEVELOPER** - System initial assignment
3. ✅ **AUTO_ROUTE_TO_ARCHITECT** - Auto-route after dev
4. ✅ **AUTO_ROUTE_TO_QA** - Auto-route after architect
5. ✅ **AUTO_ROUTE_TO_PO** - Auto-route after QA
6. ✅ **AUTO_COMPLETE** - Auto-complete to done
7. ✅ **CANCEL_TASK** - PO cancels from any state
8. ✅ **CLAIM_TESTING** - QA claims testing work

### Correctas Arquitecturalmente:

- ✅ Scopes asignados correctamente
- ✅ Role permissions coherentes
- ✅ Patrón AUTO_ROUTE_TO_{ROLE} consistente
- ✅ Patrón CLAIM_{WORK_TYPE} emergente
- ✅ Approval/Rejection pairs balanceados

---

## 🔧 Fixes Requeridos

### Fix 1: Actualizar WorkflowStateMetadata

**File:** `services/workflow/domain/services/workflow_state_metadata.py`

**Change:**
```python
# Línea 56 - BEFORE:
WorkflowStateEnum.QA_FAILED: Action(value=ActionEnum.REVISE_CODE),  # ❌ WRONG

# Línea 56 - AFTER:
WorkflowStateEnum.QA_FAILED: Action(value=ActionEnum.FIX_BUGS),  # ✅ CORRECT
```

---

### Fix 2: Actualizar Test FSM Config

**File:** `services/workflow/tests/unit/domain/test_workflow_state_machine.py`

**Change:**
```python
# Líneas 48-61 - BEFORE (simplified/wrong):
{"from": "dev_completed", "to": "pending_arch_review", "action": "request_review", "auto": True},
{"from": "arch_approved", "to": "pending_qa", "action": "request_review", "auto": True},
{"from": "qa_passed", "to": "done", "action": "request_review", "auto": True},

# Líneas 48-61 - AFTER (match real FSM):
{"from": "dev_completed", "to": "pending_arch_review", "action": "auto_route_to_architect", "auto": True},
{"from": "arch_approved", "to": "pending_qa", "action": "auto_route_to_qa", "auto": True},
{"from": "qa_passed", "to": "pending_po_approval", "action": "auto_route_to_po", "auto": True},
{"from": "pending_po_approval", "to": "po_approved", "action": "approve_story"},
{"from": "po_approved", "to": "done", "action": "auto_complete", "auto": True},
```

---

### Fix 3: Agregar CLAIM_APPROVAL (Opcional)

**File:** `core/shared/domain/action.py`

**Change:**
```python
# Después de línea 66:
CLAIM_TESTING = "claim_testing"
CLAIM_APPROVAL = "claim_approval"  # NEW - PO claims approval work
```

**Rationale:**
- Consistencia: CLAIM_{WORK_TYPE} pattern
- Concurrency: Soporte para múltiples PO agents (futuro)
- Completeness: Todos los roles tienen CLAIM action

**FSM Update Required:**
```yaml
# En config/workflow.fsm.yaml, agregar transition:
- from: pending_po_approval
  to: po_approving  # NEW intermediate state
  action: CLAIM_APPROVAL
  role_required: po
```

**Breaking Change:** NO (nueva funcionalidad opcional)

---

### Fix 4: Documentar CANCEL vs CANCEL_TASK

**File:** `core/shared/domain/action.py`

**Change:**
```python
# Línea 58 - Add docstring:
RETRY = "retry"
CANCEL = "cancel"  # Generic cancellation (legacy - use CANCEL_TASK)
# ... other actions ...
CANCEL_TASK = "cancel_task"  # Workflow: PO cancels specific task
```

**O eliminar CANCEL si no se usa:**
```bash
# Buscar uso de CANCEL en codebase:
$ grep -r "ActionEnum.CANCEL[^_]" .
# Si no hay resultados → safe to remove
```

---

## 🎯 Action Scope Validation

### Technical Scope (Implementation)
```python
COMMIT_CODE     ✅  # Developer implements
REVISE_CODE     ✅  # Developer revises design
FIX_BUGS        ✅  # Developer fixes bugs
APPROVE_DESIGN  ✅  # Architect validates
REJECT_DESIGN   ✅  # Architect rejects
```

**Validación:** ✅ Scope correcto (todos son technical work)

### Business Scope (Product Decisions)
```python
APPROVE_STORY   ✅  # PO approves
REJECT_STORY    ✅  # PO rejects
CANCEL_TASK     ⚠️  # PO cancels (¿WORKFLOW o BUSINESS?)
```

**Debate:** CANCEL_TASK es business decision pero ejecutada via workflow.
**Current:** WORKFLOW scope (acceptable)
**Alternative:** BUSINESS scope (también válido)

### Quality Scope (Testing)
```python
APPROVE_TESTS   ✅  # QA approves
REJECT_TESTS    ✅  # QA rejects
RUN_TESTS       ✅  # QA executes (though currently TECHNICAL)
```

**Inconsistencia menor:**
- RUN_TESTS está en TECHNICAL scope
- Debería estar en QUALITY scope?
- **Decisión:** TECHNICAL es correcto (es ejecución técnica)

### Workflow Scope (Coordination)
```python
CLAIM_TASK              ✅  # Concurrent access control
CLAIM_REVIEW            ✅  # Concurrent access control
CLAIM_TESTING           ✅  # Concurrent access control
ASSIGN_TO_DEVELOPER     ✅  # System routing
AUTO_ROUTE_TO_ARCHITECT ✅  # System routing
AUTO_ROUTE_TO_QA        ✅  # System routing
AUTO_ROUTE_TO_PO        ✅  # System routing
AUTO_COMPLETE           ✅  # System routing
RETRY                   ✅  # System recovery
CANCEL_TASK             ⚠️  # Could be BUSINESS
```

**Validación:** ✅ Scope assignments coherent

---

## 📚 Modelo de Dominio: Action Categories

### Category 1: Work Claim (Concurrent Access Prevention)
```
CLAIM_TASK       → Developer claims implementation
CLAIM_REVIEW     → Architect claims review
CLAIM_TESTING    → QA claims testing
(CLAIM_APPROVAL) → PO claims approval? (MISSING)
```

**Real Team:** Multiple people can work simultaneously, need to "claim" work to avoid duplicates.

### Category 2: Implementation (Developer)
```
COMMIT_CODE  → Initial implementation complete
REVISE_CODE  → Revise after architect feedback
FIX_BUGS     → Fix bugs after QA feedback
```

**Real Team:** Different types of code changes based on feedback source.

### Category 3: Validation (Architect, QA, PO)
```
APPROVE_DESIGN / REJECT_DESIGN  → Architect validates architecture
APPROVE_TESTS / REJECT_TESTS    → QA validates quality
APPROVE_STORY / REJECT_STORY    → PO validates business value
```

**Real Team:** Each validator has approval/rejection power in their domain.

### Category 4: System Routing (Auto-transitions)
```
ASSIGN_TO_DEVELOPER      → Initial workflow kickoff
AUTO_ROUTE_TO_ARCHITECT  → Route to architecture review
AUTO_ROUTE_TO_QA         → Route to quality assurance
AUTO_ROUTE_TO_PO         → Route to business approval
AUTO_COMPLETE            → Complete workflow
```

**Real Team:** JIRA/GitHub automation rules that move tickets automatically.

### Category 5: Coordination (Cross-role Communication)
```
REQUEST_REVIEW  → Explicit request for review (¿o reemplazado por AUTO_ROUTE?)
RETRY           → System-initiated retry after failure
CANCEL_TASK     → PO-initiated cancellation
```

**Real Team:** Communication actions between roles.

---

## 🎯 Decisiones Arquitecturales Pendientes

### Decisión 1: ¿REQUEST_REVIEW es necesario?

**Contexto:**
- Test FSM usa REQUEST_REVIEW para auto-transitions
- Real FSM usa AUTO_ROUTE_TO_* específicos
- ¿REQUEST_REVIEW tiene uso legítimo o es legacy?

**Opciones:**
A. **Eliminar REQUEST_REVIEW** - Reemplazado por AUTO_ROUTE_*
B. **Mantener REQUEST_REVIEW** - Developer explicitly requests review (manual trigger)
C. **Deprecar REQUEST_REVIEW** - Mark as legacy, migrate to AUTO_ROUTE_*

**Recomendación:** **Opción B** si queremos soporte para manual review request.

**Caso de Uso:**
```yaml
# Trigger manual (developer decides when ready):
- from: implementing
  to: dev_completed
  action: REQUEST_REVIEW  # ← Developer explicitly requests
  role_required: developer

# Luego auto-transition:
- from: dev_completed
  to: pending_arch_review
  action: AUTO_ROUTE_TO_ARCHITECT  # ← System auto-routes
  auto: true
```

**Validación:** Revisar workflow.fsm.yaml para confirmar si REQUEST_REVIEW existe

---

### Decisión 2: ¿CLAIM_APPROVAL para PO?

**Context:** PO puede ser múltiples agents (escalabilidad)

**Opciones:**
A. **No agregar** - PO siempre único (no concurrency)
B. **Agregar ahora** - Anticipar scaling futuro
C. **Agregar más tarde** - YAGNI (You Ain't Gonna Need It)

**Recomendación:** **Opción C** - Agregar cuando necesitemos múltiples PO agents

---

### Decisión 3: CANCEL scope (WORKFLOW vs BUSINESS)

**Debate:**
- CANCEL_TASK es business decision (PO authority)
- Pero se ejecuta via workflow system

**Current:** WORKFLOW scope  
**Alternative:** BUSINESS scope

**Recomendación:** **Mantener WORKFLOW** - Es coordinación cross-cutting

---

## 🏆 Conclusión

### Actions Agregadas: 8/8 ✅

Todas las actions son **semánticamente correctas** y reflejan workflows reales de equipos software.

### Fisuras Detectadas: 4 🔴

1. ❌ **CRITICAL:** WorkflowStateMetadata usa REVISE_CODE en vez de FIX_BUGS
2. ❌ **HIGH:** Test FSM config no refleja real FSM (REQUEST_REVIEW vs AUTO_ROUTE_*)
3. ⚠️ **MEDIUM:** CANCEL vs CANCEL_TASK duplicación
4. ⚠️ **LOW:** CLAIM naming inconsistency (falta CLAIM_APPROVAL)

### Next Steps

1. **Fix CRITICAL:** Update WorkflowStateMetadata.QA_FAILED
2. **Fix HIGH:** Update test FSM config para usar actions reales
3. **Document:** CANCEL vs CANCEL_TASK difference
4. **Future:** Agregar CLAIM_APPROVAL cuando se necesite

---

**Status:** Shared Kernel funcional, fisuras documentadas, fixes planificados  
**Quality:** Arquitectura sólida, necesita refinamiento  
**Confidence:** HIGH - Problemas identificados y solucionables



