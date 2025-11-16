# Separación: Ceremonias Agile vs FSM Workflow

**Date:** 2025-11-06
**Architect:** Tirso García Ibáñez
**Key Insight:** Ceremonias NO cambian estado FSM

---

## 🎯 Insight Crítico del Arquitecto

> **"En ceremonias (dailys, sprint review) los agentes hablan, pueden salir problemas, pero la TASK NO cambia de estado"**

Esto es **FUNDAMENTAL** para el diseño correcto del FSM.

---

## 🔄 Dos Tipos de Interacciones

### 1. **Transiciones Formales (FSM)** - Cambian Estado

```yaml
implementing → COMMIT_CODE → dev_completed
pending_arch_review → APPROVE_DESIGN → arch_approved
pending_qa → APPROVE_TESTS → qa_passed
```

**Características:**
- ✅ Cambian estado de task
- ✅ Registradas en audit trail
- ✅ Triggereran notificaciones
- ✅ Parte del workflow formal

**En Jira real:**
- Status change: "In Progress" → "Code Review"
- Transición visible en board

---

### 2. **Consultas/Ceremonias (FUERA FSM)** - NO Cambian Estado

```
Daily Standup:
  Dev: "Bloqueado en implementing task-001"
  Architect: "Te ayudo después"
  → Task SIGUE en "implementing"

Sprint Review:
  PO: "task-005 no cumple acceptance criteria"
  Dev: "Ok, lo corrijo"
  → Task SIGUE en su estado actual

Consultation:
  Dev: "¿Cómo implemento X?"
  Architect: "Usa patrón Y"
  → Task SIGUE en "implementing"
```

**Características:**
- ❌ NO cambian estado FSM
- ✅ Eventos NATS separados
- ✅ Comunicación asíncrona
- ✅ Feedback loops

**En Jira real:**
- Comentarios en ticket (task sigue "In Progress")
- Mentions (@architect)
- Slack threads

---

## 🏗️ Arquitectura Correcta

### FSM Workflow (Formal State Transitions)

```python
# services/workflow/domain/services/workflow_state_machine.py
# Solo transiciones que CAMBIAN estado:

CLAIM_TASK              # todo → implementing
COMMIT_CODE             # implementing → dev_completed
AUTO_ROUTE_TO_ARCHITECT # dev_completed → pending_arch_review (auto)
CLAIM_REVIEW            # pending_arch_review → arch_reviewing
APPROVE_DESIGN          # arch_reviewing → arch_approved
REJECT_DESIGN           # arch_reviewing → arch_rejected
REVISE_CODE             # arch_rejected → implementing
AUTO_ROUTE_TO_QA        # arch_approved → pending_qa (auto)
CLAIM_TESTING           # pending_qa → qa_testing
APPROVE_TESTS           # qa_testing → qa_passed
REJECT_TESTS            # qa_testing → qa_failed
AUTO_ROUTE_TO_PO        # qa_passed → pending_po_approval (auto)
APPROVE_STORY           # pending_po_approval → po_approved
REJECT_STORY            # pending_po_approval → cancelled
AUTO_COMPLETE           # po_approved → done (auto)
DISCARD_TASK            # * → cancelled
```

---

### Ceremony Events (NO FSM, NATS Events)

```python
# Eventos de comunicación paralelos:

Subject: "ceremony.daily.question"
Payload: {
  from_agent: "agent-dev-001",
  to_role: "architect",
  task_id: "task-001",  # Task sigue en implementing
  question: "¿Cómo implemento autenticación?"
}

Subject: "ceremony.sprint_review.feedback"
Payload: {
  from_role: "po",
  task_id: "task-005",
  feedback: "No cumple acceptance criteria",
  action_required: "revise"  # Sugerencia, NO transición
}

Subject: "ceremony.retrospective.issue"
Payload: {
  from_role: "qa",
  task_id: "task-003",
  issue: "Tests incompletos",
  proposal: "agregar test cases"
}
```

---

## ✅ Corrección del Diseño

### LO QUE ELIMINO:

```python
# ❌ Estas NO son transiciones FSM:
ROUTE_TO_ARCHITECT_BY_DEV  # Es evento ceremony, NO FSM
ROUTE_TO_ARCHITECT_BY_PO   # Es evento ceremony, NO FSM
```

### LO QUE MANTENGO (FSM Actions):

```python
# ✅ Solo actions que transicionan estados:
CLAIM_TASK, COMMIT_CODE, REVISE_CODE
CLAIM_REVIEW, APPROVE_DESIGN, REJECT_DESIGN
CLAIM_TESTING, APPROVE_TESTS, REJECT_TESTS
APPROVE_STORY, REJECT_STORY, DISCARD_TASK
ASSIGN_TO_DEVELOPER (system)
AUTO_ROUTE_TO_* (system auto-transitions)
AUTO_COMPLETE (system)
```

---

## 🎯 Arquitectura Correcta: 2 Sistemas Paralelos

```
┌────────────────────────────────────────────────┐
│          WORKFLOW FSM (Formal)                  │
│  Transiciones de estado oficiales              │
│  implementing → pending_arch_review → ...       │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│       CEREMONY EVENTS (Informal)                │
│  Comunicación entre agentes (dailys, etc.)     │
│  agent.consultation.*, ceremony.*              │
│  NO cambian estado FSM                         │
└────────────────────────────────────────────────┘
```

---

## 📝 Cambios que Aplico

1. ✅ **ELIMINAR** ROUTE_TO_ARCHITECT_BY_DEV del Shared Kernel
2. ✅ **ELIMINAR** ROUTE_TO_ARCHITECT_BY_PO del Shared Kernel
3. ✅ **DOCUMENTAR** separación FSM vs Ceremonies
4. ✅ **FUTURO:** Implementar ceremony events (fuera de este PR)

---

**¿Correcto ahora?** Ceremonias = eventos paralelos, NO transiciones FSM.


