# 🛑 CHECKPOINT - Review Arquitectural Requerida

**Date:** 2025-11-06
**Status:** ⚠️ PAUSED - Awaiting Architect Validation
**Architect:** Tirso García Ibáñez (Agile Expert)
**Context:** Cambios al núcleo de SWE AI Fleet - Workflow FSM

---

## ⚠️ CRITICAL: Changes to Core System

He realizado cambios significativos al **núcleo del sistema** (Workflow FSM) que requieren validación de arquitecto con experiencia en equipos agile reales.

---

## 📋 Cambios Realizados

### 1. **Shared Kernel Creado** ✅

**File:** `core/shared/domain/action.py` (nuevo)

**Cambio:**
- Movido Action/ActionEnum desde `core/agents_and_tools` a `core/shared`
- Ambos bounded contexts (agents_and_tools + workflow) ahora lo importan

**Rationale:** Evitar coupling entre bounded contexts

**Status:** 278 tests pasando ✅

---

### 2. **Actions Agregadas** (8 nuevas)

**File:** `core/shared/domain/action.py`

**Actions nuevas:**
```python
FIX_BUGS = "fix_bugs"                          # Developer fixes QA bugs
ASSIGN_TO_DEVELOPER = "assign_to_developer"    # System initial assignment
AUTO_ROUTE_TO_ARCHITECT = "auto_route_to_architect"  # Auto-routing
AUTO_ROUTE_TO_QA = "auto_route_to_qa"          # Auto-routing
AUTO_ROUTE_TO_PO = "auto_route_to_po"          # Auto-routing
AUTO_COMPLETE = "auto_complete"                # Auto-complete
CANCEL_TASK = "cancel_task"                    # PO cancels
CLAIM_TESTING = "claim_testing"                # QA claims work
```

**Rationale:**
- Requeridas por workflow.fsm.yaml (ya existían en FSM)
- Solo las agregué al Shared Kernel para que compile

**Status:** Compilando, semántica a validar

---

### 3. **WorkflowStateMetadata Actualizado**

**File:** `services/workflow/domain/services/workflow_state_metadata.py`

**Cambio:**
```python
# BEFORE:
WorkflowStateEnum.QA_FAILED: Action(value=ActionEnum.REVISE_CODE),

# AFTER:
WorkflowStateEnum.QA_FAILED: Action(value=ActionEnum.FIX_BUGS),
```

**Rationale:** workflow.fsm.yaml usa FIX_BUGS (línea 246)

**Status:** ⚠️ **REQUIERE VALIDACIÓN**

---

### 4. **Test FSM Config Actualizado**

**File:** `services/workflow/tests/unit/domain/test_workflow_state_machine.py`

**Cambios:**
- REQUEST_REVIEW → AUTO_ROUTE_TO_* (matching real FSM)
- Agregado CLAIM_REVIEW antes de APPROVE_DESIGN
- Agregado CLAIM_TESTING antes de APPROVE_TESTS
- Agregado estado po_approved
- qa_failed usa FIX_BUGS (no REVISE_CODE)

**Status:** ⚠️ **REQUIERE VALIDACIÓN - Cambia máquina de estados**

---

## 🤔 PREGUNTAS CRÍTICAS para el Arquitecto

Como arquitecto con experiencia en equipos agile reales, necesito que valides:

### Pregunta 1: CLAIM States (Concurrent Access)

**En equipos agile reales:**

¿Es realista que TODOS los validators necesiten "claim" explícitamente?

```
Developer: TODO → CLAIM_TASK → IMPLEMENTING
Architect: PENDING_REVIEW → CLAIM_REVIEW → REVIEWING
QA:        PENDING_QA → CLAIM_TESTING → TESTING
PO:        PENDING_APPROVAL → ¿CLAIM_APPROVAL? → APPROVING
```

**O es más realista:**

```
Developer: TODO → (auto-assign) → IMPLEMENTING (CLAIM implícito)
Architect: PENDING_REVIEW → (claim si múltiples) O (directo a REVIEWING si único)
QA:        PENDING_QA → (claim si múltiples) O (directo a TESTING si único)
PO:        PENDING_APPROVAL → (directo a approval, típicamente único PO)
```

**En JIRA/GitHub real:**
- ¿Architects "claim" PRs antes de review?
- ¿O simplemente empiezan a reviewear?

---

### Pregunta 2: FIX_BUGS vs REVISE_CODE

**Mi razonamiento:**
```
REVISE_CODE: Architect feedback (diseño/arquitectura)
  → "Refactoriza para usar Strategy pattern"
  → Cambios arquitecturales

FIX_BUGS: QA feedback (bugs funcionales)
  → "Test case X falla"
  → Bug fixes
```

**En tu experiencia agile:**
- ¿Es una distinción válida?
- ¿O ambos son "developer revises code"?
- ¿En JIRA diferencian "Rework" vs "Bug Fix"?

---

### Pregunta 3: AUTO_ROUTE_TO_* Actions

**Mi implementación:**
```
dev_completed → AUTO_ROUTE_TO_ARCHITECT → pending_arch_review
arch_approved → AUTO_ROUTE_TO_QA → pending_qa
qa_passed → AUTO_ROUTE_TO_PO → pending_po_approval
```

**En equipos agile reales:**
- ¿JIRA hace auto-transitions así?
- ¿O son status changes sin "action" explícita?
- ¿GitHub Actions hace esto automáticamente?

**Alternativa:**
- Estados cambian automáticamente sin action explícita
- Actions solo para work manual (COMMIT_CODE, APPROVE_DESIGN)

---

### Pregunta 4: Flujo Completo PO

**Mi implementación actual:**
```
pending_po_approval → APPROVE_STORY (directo) → po_approved → done
```

**NO tiene CLAIM_APPROVAL** (decidí YAGNI)

**En tu experiencia:**
- ¿PO "claims" stories antes de aprobar?
- ¿O simplemente aprueba directamente?
- ¿Múltiples POs en mismo equipo?

---

## 🎯 Lo Que NECESITO de Ti

**Como arquitecto experto en agile:**

1. **Valida semántica de actions:**
   - ¿FIX_BUGS vs REVISE_CODE hace sentido?
   - ¿CLAIM_* es realista o over-engineering?

2. **Valida flujo FSM:**
   - ¿Refleja workflow agile real?
   - ¿Demasiados estados intermedios?
   - ¿Falta algún estado crítico?

3. **Valida modelo de concurrency:**
   - ¿Cuántos architects/QAs/POs típicamente en equipo?
   - ¿CLAIM necesario para todos o solo algunos?

4. **Decisión arquitectural:**
   - ¿Procedo con estos cambios?
   - ¿Revierto y simplifico?
   - ¿Ajusto basado en tu feedback?

---

## 📊 Impacto de Cambios Propuestos

### Si Procedo:
- ✅ Test FSM refleja FSM real
- ✅ Metadata consistente con FSM
- ⚠️ FSM más complejo (require CLAIMs explícitos)
- ⚠️ Puede no reflejar agile real

### Si Revierto:
- ✅ FSM más simple (menos estados intermedios)
- ⚠️ Tests siguen siendo inconsistentes
- ⚠️ Metadata sigue incorrecto

### Si Ajusto:
- Esperando tu input como experto

---

## 🎯 Mi Recomendación (Tentativa)

**PAUSAR implementación hasta validar con arquitecto.**

**Razones:**
1. Workflow FSM es el **núcleo** del sistema
2. Cambios aquí impactan TODA la coordinación
3. Debe reflejar realidad agile (no teoría)
4. Tirso tiene experiencia real que yo no tengo

---

## 📝 Próximos Pasos

**Opción A:** Tirso valida cambios → Procedo con implementación

**Opción B:** Tirso pide ajustes → Corrijo basado en feedback

**Opción C:** Tirso rechaza → Revierto y replanteo

---

**Esperando validación del arquitecto antes de continuar** ⏸️



