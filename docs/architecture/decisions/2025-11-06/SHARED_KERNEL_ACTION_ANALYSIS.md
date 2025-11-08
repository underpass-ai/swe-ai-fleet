# Shared Kernel - Action Analysis & Fisuras Detectadas

**Date:** 2025-11-06  
**Context:** RBAC L2+L3 Implementation  
**Bounded Contexts:** `core/shared/domain/action.py` (Shared Kernel)

---

## 🎯 Nuevas Actions Agregadas (8 total)

### 1. **FIX_BUGS** (Technical Scope)

**Uso en FSM:** qa_failed → implementing (línea 246)

**Semántica:**
- Developer arregla bugs después de rechazo de QA
- Diferente de REVISE_CODE (que es para feedback de Architect)

**Razonamiento:**
```
REVISE_CODE: Cambios de diseño/arquitectura (feedback de Architect)
  → "Cambia bcrypt por argon2"
  → "Refactoriza para seguir patrón X"

FIX_BUGS: Corrección de bugs funcionales (feedback de QA)
  → "Test case Y falla"
  → "Edge case Z no manejado"
```

**Validación:** ✅ CORRECTO
- Son conceptos distintos del dominio
- Semántica diferenciada
- Scope: TECHNICAL (correcto)

---

### 2. **ASSIGN_TO_DEVELOPER** (Workflow Scope)

**Uso en FSM:** todo → implementing (línea 158)

**Semántica:**
- System action (role_required: null)
- Initial assignment cuando Planning Service crea task workflows

**Razonamiento:**
- Planning Service transiciona story a IN_PROGRESS
- Workflow Service crea workflow states para cada task
- Primera action = ASSIGN_TO_DEVELOPER (system)

**Validación:** ✅ CORRECTO
- System action (no role validation)
- Scope: WORKFLOW (coordinación)
- Semántica clara

---

### 3-6. **AUTO_ROUTE_TO_* Actions** (Workflow Scope)

**AUTO_ROUTE_TO_ARCHITECT:** dev_completed → pending_arch_review (línea 174)  
**AUTO_ROUTE_TO_QA:** arch_approved → pending_qa (línea 214)  
**AUTO_ROUTE_TO_PO:** qa_passed → pending_po_approval (línea 254)  
**AUTO_COMPLETE:** po_approved → done (línea 278)

**Semántica:**
- Auto-transitions (role_required: null, auto: true)
- Routing automático entre validadores
- Como JIRA automation: "When approved → Notify next role"

**Razonamiento:**
```
Real Team Workflow:
  Dev completes PR → Auto-assign to Tech Lead
  Tech Lead approves → Auto-notify QA
  QA passes → Auto-notify PO
  PO approves → Auto-close ticket

SWE AI Fleet:
  dev_completed → AUTO_ROUTE_TO_ARCHITECT → pending_arch_review
  arch_approved → AUTO_ROUTE_TO_QA → pending_qa
  qa_passed → AUTO_ROUTE_TO_PO → pending_po_approval
  po_approved → AUTO_COMPLETE → done
```

**Validación:** ✅ CORRECTO
- Modelan auto-transitions del FSM
- Scope: WORKFLOW (coordinación system)
- Semántica clara

---

### 7. **CANCEL_TASK** (Workflow Scope)

**Uso en FSM:** * → cancelled (línea 286, wildcard transition)

**Semántica:**
- PO puede cancelar desde cualquier estado
- Como en equipo real: PO decide si story/task ya no es necesaria

**Razonamiento:**
```
Real Team:
  PO: "Business priorities changed, close this ticket"
  → Task cancelled sin completar

SWE AI Fleet:
  PO agent: ACTION: CANCEL_TASK
  → Workflow: * → cancelled
  → Task terminada sin completar
```

**Validación:** ✅ CORRECTO
- PO authority (business decisions)
- Scope: WORKFLOW
- Wildcard transition (flexible)

---

### 8. **CLAIM_TESTING** (Workflow Scope)

**Uso en FSM:** pending_qa → qa_testing (línea 222)

**Semántica:**
- QA agent "claims" testing work
- Paralelo a CLAIM_TASK (developer) y CLAIM_REVIEW (architect)
- Previene concurrent access (múltiples QA agents)

**Razonamiento:**
```
Real Team (Jira):
  Ticket status: "Ready for QA" → QA picks it up → "In Testing"

SWE AI Fleet:
  pending_qa (waiting) → CLAIM_TESTING → qa_testing (active work)
  → Solo un QA agent puede claim a la vez
```

**Validación:** ✅ CORRECTO
- Consistent con CLAIM_TASK y CLAIM_REVIEW
- Scope: WORKFLOW
- Previene race conditions

---

## 🔴 FISURAS DETECTADAS

### FISURA 1: Inconsistencia Test vs FSM Real

**Ubicación:**
- `test_workflow_state_machine.py` línea 52, 55, 59
- `workflow.fsm.yaml` líneas 174, 214, 254

**Problema:**
```python
# Test usa (INCORRECTO):
{"from": "dev_completed", "to": "pending_arch_review", "action": "request_review", "auto": True}
{"from": "arch_approved", "to": "pending_qa", "action": "request_review", "auto": True}
{"from": "qa_passed", "to": "done", "action": "request_review", "auto": True}

# FSM real usa (CORRECTO):
{"from": "dev_completed", "to": "pending_arch_review", "action": "AUTO_ROUTE_TO_ARCHITECT", "auto": True}
{"from": "arch_approved", "to": "pending_qa", "action": "AUTO_ROUTE_TO_QA", "auto": True}
{"from": "qa_passed", "to": "pending_po_approval", "action": "AUTO_ROUTE_TO_PO", "auto": True}
{"from": "po_approved", "to": "done", "action": "AUTO_COMPLETE", "auto": True}
```

**Impacto:**
- ❌ Tests usan FSM config simplificado que NO refleja la realidad
- ❌ REQUEST_REVIEW es sobrecargado (3 semánticas diferentes)
- ✅ FSM real es más explícito y semánticamente correcto

**Decisión:** ✅ FSM real es correcto, test debe actualizarse

---

### FISURA 2: WorkflowStateMetadata desactualizado

**Ubicación:** `workflow_state_metadata.py` línea 56

**Problema:**
```python
# WorkflowStateMetadata dice:
WorkflowStateEnum.QA_FAILED: Action(value=ActionEnum.REVISE_CODE),

# workflow.fsm.yaml dice (línea 246):
- from: qa_failed
  to: implementing
  action: FIX_BUGS  # ← Diferente!
```

**Impacto:**
- ❌ Metadata retorna action incorrecta
- ❌ Use case espera REVISE_CODE pero FSM permite FIX_BUGS
- ❌ Inconsistencia domain logic

**Fix Required:** Actualizar WorkflowStateMetadata

---

### FISURA 3: CANCEL vs CANCEL_TASK (Duplicación)

**Ubicación:** `core/shared/domain/action.py`

**Problema:**
```python
# ActionEnum tiene:
CANCEL = "cancel"        # Original (línea 58)
CANCEL_TASK = "cancel_task"  # Nuevo (línea 65)
```

**Análisis:**
- CANCEL: ¿Para qué se usa? (no encontrado en FSM)
- CANCEL_TASK: Usado en workflow.fsm.yaml línea 286

**Decisión:**
- ❌ CANCEL parece legacy/no usado
- ✅ CANCEL_TASK es el correcto (más específico)
- ⚠️ Considerar deprecar CANCEL o aclarar diferencia

---

### FISURA 4: CLAIM_REVIEW usado en 2 contextos

**Ubicación:** workflow.fsm.yaml

**Problema:**
```yaml
# Architect claims review:
- from: pending_arch_review
  to: arch_reviewing
  action: CLAIM_REVIEW  # ← Architect

# ¿QA también usa CLAIM_REVIEW o CLAIM_TESTING?
- from: pending_qa
  to: qa_testing
  action: CLAIM_TESTING  # ← Específico para QA
```

**Análisis:**
- CLAIM_REVIEW: Generic (architect, po?)
- CLAIM_TESTING: Specific (qa)
- CLAIM_TASK: Specific (developer)

**¿Es correcto?**
- ✅ CLAIM_TASK (dev specific)
- ✅ CLAIM_TESTING (qa specific)
- ⚠️ CLAIM_REVIEW (generic, usado por architect)

**Validación:** ⚠️ INCONSISTENCIA DE NAMING

Más consistente sería:
- CLAIM_TASK (dev)
- CLAIM_REVIEW_ARCH (architect) ← Específico
- CLAIM_TESTING (qa)
- CLAIM_APPROVAL (po) ← Falta

O mantener:
- CLAIM_TASK (dev implementation)
- CLAIM_REVIEW (arch + po validation)
- CLAIM_TESTING (qa testing)

**Decisión arquitectural pendiente**

---

## 🔍 Análisis Semántico Profundo

### Categorías de Actions (por ciclo de vida):

#### 1. **Work Claim Actions** (Concurrent Access Control)
```
CLAIM_TASK         → Developer claims implementation work
CLAIM_REVIEW       → Architect claims review work
CLAIM_TESTING      → QA claims testing work
(CLAIM_APPROVAL?)  → PO claims approval work? (MISSING)
```

**Fisura:** PO no tiene CLAIM action. ¿Es necesario?

**Razonamiento:**
- Dev/Arch/QA pueden ser múltiples agentes (concurrency)
- PO típicamente es 1 persona (low concurrency)
- **¿Necesita claim?** Probablemente SÍ (si escalamos a múltiples PO agents)

**Recomendación:** Agregar `CLAIM_APPROVAL` para consistencia

---

#### 2. **Implementation Actions** (Developer)
```
COMMIT_CODE   → Developer commits implementation
REVISE_CODE   → Developer revises after architect feedback
FIX_BUGS      → Developer fixes bugs after QA feedback
```

**Semántica:** ✅ Clara y diferenciada

---

#### 3. **Validation Actions** (Validators)
```
APPROVE_DESIGN / REJECT_DESIGN  → Architect
APPROVE_TESTS / REJECT_TESTS    → QA
APPROVE_STORY / REJECT_STORY    → PO
```

**Patrón:** ✅ Consistente (APPROVE/REJECT por rol)

---

#### 4. **Auto-Routing Actions** (System)
```
ASSIGN_TO_DEVELOPER      → Initial assignment
AUTO_ROUTE_TO_ARCHITECT  → After dev completes
AUTO_ROUTE_TO_QA         → After arch approves
AUTO_ROUTE_TO_PO         → After QA passes
AUTO_COMPLETE            → Final transition to done
```

**Patrón:** ✅ Consistente (AUTO_ROUTE_TO_{ROLE})

---

#### 5. **Coordination Actions** (Cross-role)
```
REQUEST_REVIEW  → Developer requests review (¿o auto-transition?)
CANCEL_TASK     → PO cancels task
RETRY           → System retries failed task
```

**Fisura REQUEST_REVIEW:**
- En tests: Usado para auto-transitions
- En FSM real: ¿Usado o reemplazado por AUTO_ROUTE_*?

**Buscar en FSM:**
</thinking>

Perfecto, tengo todo el contexto. Voy a crear un análisis completo de las actions y fisuras detectadas:

<function_calls>
<invoke name="grep">
<parameter name="pattern">REQUEST_REVIEW

