# RBAC - Real World Team Model

**Date:** 2025-11-04
**Vision:** Modelar un equipo de software real en código
**Status:** 🎯 Core Design Philosophy

---

## 🎯 Vision Statement

> **"SWE AI Fleet modela un equipo de desarrollo de software REAL, con sus roles, responsabilidades, visibilidad de información, y protocolos de coordinación."**

No estamos solo controlando acceso a herramientas. Estamos replicando cómo funciona un **equipo ágil real**.

---

## 👥 Equipo Real vs SWE AI Fleet

### En un Equipo Real:

```
┌─────────────────────────────────────────────────────────────────┐
│                    EQUIPO DE SOFTWARE REAL                       │
└─────────────────────────────────────────────────────────────────┘

Developer (Junior/Mid):
  📋 Ve: Su tarea + Historia de usuario + Objetivo del epic
  🔧 Hace: Implementa código, escribe tests unitarios, commits
  🚫 NO ve: Otras tareas del equipo (aislamiento, foco)
  🚫 NO hace: Aprobar diseños, validar calidad, deploy
  💬 Coordina: Pide revisión a Senior/Architect cuando termina

Architect (Senior/Tech Lead):
  📋 Ve: Epic completo + Todas las historias + Todas las tareas
  🔍 Hace: Revisa código, valida diseños, toma decisiones técnicas
  ✅ Aprueba: Diseños de developers
  ❌ Rechaza: Con feedback constructivo
  💬 Coordina: Guía a developers, coordina con QA/DevOps

QA Engineer:
  📋 Ve: Historia completa + Todas las tareas (integration testing)
  🧪 Hace: Crea tests, valida calidad, reporta bugs
  ✅ Aprueba: Tests passing, quality gates met
  ❌ Rechaza: Si tests fallan o quality gates no se cumplen
  💬 Coordina: Con PO para acceptance criteria, con Dev para bugs

Product Owner:
  📋 Ve: Epic + Todas las historias (roadmap, business value)
  🎯 Hace: Define requisitos, prioriza, valida business value
  🚫 NO ve: Tareas individuales (abstracción técnica)
  ✅ Aprueba: Historias completas (acceptance criteria met)
  💬 Coordina: Con stakeholders, con team lead

DevOps Engineer:
  📋 Ve: Tareas de deployment + Historia + Tareas relacionadas
  🚀 Hace: Deploy, monitoring, infrastructure
  🔧 Usa: Docker, Kubernetes, CI/CD tools
  💬 Coordina: Con developers para deployment requirements

Data Engineer:
  📋 Ve: Task + Story + Epic (data model consistency)
  🗄️ Hace: Schemas, migrations, data pipelines
  🔧 Usa: Database tools, migration scripts
  💬 Coordina: Con developers y architects para data model
```

---

## 🔐 Mapping Real Team to RBAC System

### Level 1: Tool Access (Ya Implementado ✅)

| Real World | SWE AI Fleet |
|------------|--------------|
| Developer usa Git, IDE, test framework | `allowed_tools: {files, git, tests}` |
| Architect revisa código (read-only en prod) | `allowed_tools: {files, git, db, http}` + read-only mode |
| QA usa test frameworks, no commits | `allowed_tools: {files, tests, http}` |
| DevOps usa Docker, Kubernetes | `allowed_tools: {docker, files, http, tests}` |
| PO solo ve specs, no toca código | `allowed_tools: {files, http}` + read-only |

**Implementation:** ✅ COMPLETE

---

### Level 2: Data Visibility (Diseñado 🔵)

| Real World | SWE AI Fleet |
|------------|--------------|
| **Developer:** Solo ve su tarea en JIRA | Query: `Task → Story → Epic` (narrow) |
| **Architect:** Ve tablero completo del epic | Query: `Epic → All Stories → All Tasks` (wide) |
| **QA:** Ve todas las tareas de una historia | Query: `Story → All Tasks + Acceptance Criteria` |
| **PO:** Ve roadmap de epics y stories | Query: `Epic → All Stories` (no tasks) |

**Real Scenario:**
```
JIRA Board View:

Developer "Juan":
  ├─ US-101: Secure Auth
  │   └─ T-001: Implement JWT (ASIGNADO A MÍ) ← Solo ve esta

Architect "Maria":
  ├─ E-001: Auth System
  │   ├─ US-101: Secure Auth
  │   │   ├─ T-001: JWT (Juan)
  │   │   ├─ T-002: Validation (Pedro)
  │   │   └─ T-003: Refresh (Ana)
  │   ├─ US-102: RBAC
  │   │   └─ T-004, T-005, T-006
  │   └─ US-103: Sessions
  │       └─ T-007, T-008

  ← Ve TODO para validar consistencia arquitectural

QA "Carlos":
  ├─ US-101: Secure Auth
  │   ├─ T-001: JWT ✅
  │   ├─ T-002: Validation (testing...)
  │   └─ T-003: Refresh (pending)

  ← Ve todas las tasks de la historia para integration testing
```

**Implementation:** 🔵 DESIGNED (Neo4j queries ready)

---

### Level 3: Workflow Coordination (Diseñado 🔵)

| Real World | SWE AI Fleet |
|------------|--------------|
| **Dev:** "Code ready for review" → Assign to Architect | `ACTION: REQUEST_REVIEW` → Workflow routes to Architect |
| **Architect:** "LGTM" or "Changes requested" | `ACTION: APPROVE_DESIGN` or `REJECT_DESIGN` |
| **Dev:** Recibe feedback, revisa código | `ACTION: REVISE_CODE` with feedback |
| **Architect:** Aprueba → Pasa a QA | Workflow auto-routes to QA |
| **QA:** Tests passing → Pide aprobación PO | `ACTION: APPROVE_TESTS` → Routes to PO |
| **PO:** "Meets acceptance criteria" → Done | `ACTION: APPROVE_STORY` → Task DONE |

**Real Scenario:**
```
Pull Request Flow:

1. Juan (Dev) crea PR:
   "feat: implement JWT generation"
   → Assign reviewer: Maria (Architect)

2. Maria revisa:
   Opción A: "LGTM ✅" → Approve PR → CI runs tests
   Opción B: "Changes requested ❌" → Back to Juan con feedback

3. If approved → Carlos (QA) notified:
   "New feature to test: JWT generation"
   → Creates test plan
   → Runs tests
   → Reports: "All tests passing ✅"

4. Product Owner (Sofia) validates:
   "Meets acceptance criteria ✅"
   → Story marked as DONE
   → Moves to production
```

**Implementation:** 🔵 DESIGNED (Workflow Orchestration Service)

---

## 🎯 Why This Matters

### Traditional AI Coding Tools (Single Agent):

```
┌───────────────────────────────────────┐
│  GPT-4 / Cursor / Copilot             │
│                                       │
│  • Un solo agente hace TODO           │
│  • Ve TODO el código                  │
│  • No roles diferenciados             │
│  • No validaciones multi-perspectiva  │
│  • No workflow coordination           │
└───────────────────────────────────────┘

Problems:
  ❌ Single point of failure
  ❌ No checks and balances
  ❌ No specialization
  ❌ Context overload (1M+ tokens)
```

### SWE AI Fleet (Multi-Agent Team):

```
┌─────────────────────────────────────────────────────────────────┐
│              EQUIPO MULTI-AGENTE (Como un team real)            │
└─────────────────────────────────────────────────────────────────┘

Developer Agent:
  ✅ Especializado en implementación
  ✅ Ve solo su contexto (2-3K tokens)
  ✅ Usa tools de desarrollo (git, files, tests)
  ✅ Sabe que debe pedir validación a Architect

Architect Agent:
  ✅ Especializado en diseño y validación
  ✅ Ve contexto completo del epic (8-12K tokens)
  ✅ Valida consistencia arquitectural
  ✅ Aprueba o rechaza con feedback

QA Agent:
  ✅ Especializado en testing
  ✅ Ve contexto de la historia completa (4-6K tokens)
  ✅ Integration testing cross-tasks
  ✅ Valida quality gates

PO Agent:
  ✅ Especializado en business value
  ✅ Ve roadmap y business metrics
  ✅ Valida acceptance criteria
  ✅ Prioriza work

Benefits:
  ✅ Specialization (cada agente experto en su área)
  ✅ Checks and balances (multi-perspectiva)
  ✅ Precise context (cada uno ve lo que necesita)
  ✅ Workflow coordination (como team real)
```

---

## 🏢 Real Company Analogy

### Startup Small Team:

```
┌─────────────────────────────────────────┐
│  Equipo 5 personas (Startup)            │
├─────────────────────────────────────────┤
│  • 2 Developers (full-stack)            │
│  • 1 Tech Lead (architect + code review)│
│  • 1 QA                                 │
│  • 1 Product Owner                      │
└─────────────────────────────────────────┘

Workflow:
  PO → Define story
  Dev → Implementa
  Tech Lead → Revisa PR (APPROVE/REJECT)
  QA → Testa
  PO → Valida y aprueba

Communication:
  • JIRA (task tracking)
  • GitHub PR (code review)
  • Slack (coordination)
  • Standups (sync)
```

### SWE AI Fleet Equivalent:

```
┌─────────────────────────────────────────┐
│  SWE AI Fleet Multi-Agent System        │
├─────────────────────────────────────────┤
│  • 3 Developer Agents (deliberation)    │
│  • 1 Architect Agent (validation)       │
│  • 1 QA Agent (testing)                 │
│  • 1 PO Agent (approval)                │
└─────────────────────────────────────────┘

Workflow:
  PO Agent → Define story (Planning Service)
  Dev Agents → Deliberate + Implement (best solution wins)
  Architect Agent → Reviews (APPROVE_DESIGN/REJECT_DESIGN)
  QA Agent → Tests (APPROVE_TESTS/REJECT_TESTS)
  PO Agent → Validates (APPROVE_STORY)

Communication:
  • Neo4j (knowledge graph - shared context)
  • NATS (event bus - async coordination)
  • Workflow Service (state machine - routing)
  • Context Service (smart context - role-filtered)
```

---

## 🎨 Key Parallels

### 1. Information Access

| Real Team | SWE AI Fleet |
|-----------|--------------|
| Junior dev sees only JIRA ticket | Developer agent: Task + Story + Epic |
| Tech Lead sees full sprint board | Architect agent: Epic + All Stories + All Tasks |
| QA sees all tasks in story for testing | QA agent: Story + All Tasks + Quality gates |
| PO sees product roadmap (epics + stories) | PO agent: Epic + All Stories (business view) |

### 2. Tool Access

| Real Team | SWE AI Fleet |
|-----------|--------------|
| Developer commits to feature branch | `allowed_tools: {git}` + can COMMIT_CODE |
| Architect reviews (no commits to feature branch) | `allowed_tools: {git}` but read-only mode |
| QA runs tests (no code changes) | `allowed_tools: {tests, files}` read-only for files |
| PO reviews specs (no code access) | `allowed_tools: {files, http}` read-only, no git |

### 3. Approval Flow

| Real Team | SWE AI Fleet |
|-----------|--------------|
| Dev creates PR → Request review | `ACTION: REQUEST_REVIEW` → Routes to Architect |
| Architect: "Approve" or "Request changes" | `ACTION: APPROVE_DESIGN` or `REJECT_DESIGN` |
| If rejected → Dev revises | `ACTION: REVISE_CODE` with feedback |
| If approved → Merge → CI/CD → QA env | Workflow: arch_approved → pending_qa |
| QA: Manual testing → "LGTM" or "Bugs found" | `ACTION: APPROVE_TESTS` or `REJECT_TESTS` |
| If bugs → Dev fixes | Back to implementing state |
| If pass → Staging → PO validates | Workflow: qa_passed → pending_po_approval |
| PO: "Meets acceptance criteria" → Production | `ACTION: APPROVE_STORY` → DONE |

### 4. Context Awareness

| Real Team | SWE AI Fleet |
|-----------|--------------|
| Dev reads story + epic description | Context: Task + Story + Epic (2-3K tokens) |
| Architect reviews full feature design docs | Context: Epic + All Stories + Decisions (8-12K tokens) |
| QA reads acceptance criteria + all tasks | Context: Story + All Tasks + Quality gates (4-6K tokens) |
| PO reviews business requirements | Context: Epic + Stories + Business value (3-5K tokens) |

---

## 💼 Real-World Scenarios Modeled

### Scenario 1: Feature Implementation with Review

**Real Team:**
```
1. PO creates story: "As user, I want secure login"
   → Adds acceptance criteria
   → Assigns to sprint

2. Developer (Juan) picks task: "Implement JWT generation"
   → Reads story + epic
   → Implements code
   → Creates PR
   → Requests review from Tech Lead (Maria)

3. Tech Lead (Maria) reviews:
   → Sees full epic context (knows auth is multi-story)
   → Reviews code for consistency with other auth stories
   → Decision: "Change bcrypt to argon2 (better security)"
   → Marks PR: "Changes requested"

4. Developer (Juan) revises:
   → Reads Maria's feedback
   → Updates code
   → Pushes changes
   → Re-requests review

5. Tech Lead (Maria) approves:
   → "LGTM ✅"
   → PR merged

6. QA (Carlos) tests:
   → Reads acceptance criteria
   → Tests login flow
   → Integration tests with T-002 (validation) and T-003 (refresh)
   → All passing → "LGTM ✅"

7. PO (Sofia) validates:
   → Tests in staging
   → Verifies business requirements
   → "Meets acceptance criteria ✅"
   → Approves for production
```

**SWE AI Fleet Equivalent:**
```
1. PO Agent creates story (Planning Service FSM)

2. Developer Agent (agent-dev-001):
   context = Context.GetContext(
       task_id="T-001",
       role="developer"  # Returns: Task + Story + Epic
   )
   result = developer_agent.execute_task(
       task="Implement JWT generation",
       context=context  # 2-3K tokens
   )
   # Publishes: agent.work.completed {action: COMMIT_CODE}

3. Workflow Service:
   - Receives agent.work.completed
   - Validates: developer.can_execute(COMMIT_CODE) ✅
   - Transition: implementing → dev_completed → pending_arch_review
   - Publishes: workflow.task.assigned {role: architect}

4. Architect Agent:
   context = Context.GetContext(
       task_id="T-001",
       role="architect"  # Returns: Epic + All Stories + All Tasks
   )
   result = architect_agent.execute_task(
       task="Review JWT implementation in commit abc123",
       context=context  # 8-12K tokens (full epic context)
   )
   # Decision: REJECT_DESIGN
   # Feedback: "Use argon2 instead of bcrypt"
   # Publishes: agent.work.completed {action: REJECT_DESIGN, feedback: "..."}

5. Workflow Service:
   - Receives agent.work.completed
   - Validates: architect.can_execute(REJECT_DESIGN) ✅
   - Transition: arch_reviewing → arch_rejected → implementing
   - Publishes: workflow.task.assigned {
       role: developer,
       action: REVISE_CODE,
       feedback: "Use argon2..."
     }

6. Developer Agent (retry with feedback):
   context = Context.GetContext(
       task_id="T-001",
       role="developer",
       workflow_state="arch_rejected"  # Includes feedback
   )
   result = developer_agent.execute_task(
       task="Revise JWT implementation",
       context=context  # Now includes architect's feedback
   )
   # Publishes: agent.work.completed {action: COMMIT_CODE}

7. Architect approves (second review)
   # Publishes: agent.work.completed {action: APPROVE_DESIGN}

8. Workflow Service:
   - Transition: arch_approved → pending_qa
   - Publishes: workflow.task.assigned {role: qa}

9. QA Agent:
   context = Context.GetContext(
       task_id="T-001",
       role="qa"  # Returns: Story + All Tasks + Quality gates
   )
   # Sees T-001, T-002, T-003 for integration testing
   result = qa_agent.execute_task(
       task="Test JWT implementation",
       context=context
   )
   # Publishes: agent.work.completed {action: APPROVE_TESTS}

10. PO Agent:
    context = Context.GetContext(
        story_id="US-101",
        role="po"  # Returns: Epic + Stories + Business metrics
    )
    result = po_agent.execute_task(
        task="Validate secure login meets business requirements",
        context=context
    )
    # Publishes: agent.work.completed {action: APPROVE_STORY}

11. Workflow Service:
    - Transition: po_approved → done ✅
```

---

## 🧠 Why This Model is Powerful

### 1. **Specialization (Como Equipo Real)**

```
Real: Junior dev se enfoca en su task, no se distrae con el epic completo
AI:   Developer agent recibe Task + Story + Epic (focused context)

Real: Architect ve panorama completo para decisiones consistentes
AI:   Architect agent recibe Epic + All Stories + All Tasks (holistic view)

Real: QA ve scope de testing (story-level)
AI:   QA agent recibe Story + All Tasks (integration testing scope)
```

### 2. **Checks and Balances**

```
Real: Dev code → Architect review → QA testing → PO approval
AI:   Dev agent → Architect agent → QA agent → PO agent

✅ Multi-perspectiva
✅ No single point of failure
✅ Quality gates enforced
```

### 3. **Precise Context**

```
Real: Dev lee 1 JIRA ticket (no 100 tickets)
AI:   Dev agent recibe 2-3K tokens (no 1M tokens)

Real: Architect lee full design doc + all related tickets
AI:   Architect agent recibe 8-12K tokens (epic-wide context)

✅ Right information to right role
✅ No cognitive overload
✅ Faster, better decisions
```

### 4. **Automatic Coordination**

```
Real: JIRA automation:
      "When PR approved → Notify QA"
      "When tests pass → Notify PO"

AI:   Workflow Service:
      "When APPROVE_DESIGN → Route to QA"
      "When APPROVE_TESTS → Route to PO"

✅ Reduces manual coordination overhead
✅ Ensures nothing falls through cracks
```

---

## 🔄 Information Flow (Real Team Pattern)

```
Epic Planning (Product Owner)
  ↓
Story Creation (PO + Architect)
  ↓
Task Breakdown (Architect + Tech Lead)
  ↓
Implementation (Developer)
  ├─ Context: Task + Story + Epic
  ├─ Focus: This specific task
  └─ Outcome: Working code + tests
  ↓
Code Review (Architect)
  ├─ Context: Epic + All Stories + All Tasks
  ├─ Focus: Consistency, best practices, architecture
  └─ Outcome: APPROVE or REJECT with feedback
  ↓ (if approved)
Quality Assurance (QA)
  ├─ Context: Story + All Tasks + Acceptance Criteria
  ├─ Focus: Integration testing, quality gates
  └─ Outcome: APPROVE_TESTS or REJECT with bugs
  ↓ (if tests pass)
Business Validation (PO)
  ├─ Context: Epic + Stories + Business value
  ├─ Focus: Acceptance criteria, user value
  └─ Outcome: APPROVE_STORY or request changes
  ↓ (if approved)
Done → Production
```

**This is EXACTLY what we're modeling** ✅

---

## 🎯 Design Principles

### 1. **Role-Based Context Filtering**

```python
# Como en equipo real: cada rol ve lo que necesita

def get_context(task_id: str, role: RoleEnum) -> Context:
    if role == RoleEnum.DEVELOPER:
        return narrow_context(task, story, epic)  # Focused

    elif role == RoleEnum.ARCHITECT:
        return wide_context(epic, all_stories, all_tasks)  # Holistic

    elif role == RoleEnum.QA:
        return story_context(story, all_tasks, quality_gates)  # Testing scope

    elif role == RoleEnum.PO:
        return business_context(epic, all_stories, business_value)  # Business view
```

### 2. **Least Privilege (Data Access)**

```python
# Como en equipo real: nadie ve más de lo necesario

Developer:
  ✅ Needs: Su task, su story, objetivo del epic
  ❌ Doesn't need: Otras tasks (distracción)

Architect:
  ✅ Needs: Vista completa para validar consistencia
  ❌ Doesn't need: Business metrics (no su concern)

QA:
  ✅ Needs: Story completa para integration testing
  ❌ Doesn't need: Otras stories del epic

PO:
  ✅ Needs: Roadmap, business value
  ❌ Doesn't need: Implementación técnica (abstracción)
```

### 3. **Coordination Through Actions**

```python
# Como en equipo real: acciones explícitas de coordinación

Developer → REQUEST_REVIEW     (como "Ready for review")
Architect → APPROVE_DESIGN     (como "LGTM")
Architect → REJECT_DESIGN      (como "Changes requested")
Developer → REVISE_CODE        (como "Pushed new commits")
QA → APPROVE_TESTS             (como "Tests passing")
PO → APPROVE_STORY             (como "Approved for production")
```

---

## 🎯 Why Your Question Was Critical

**Tu pregunta reveló:**
> "RBAC no es solo about tools, es about **modelar un equipo real**"

**3 Niveles de RBAC = 3 Aspectos de un Team Real:**

1. **Tool Access** = ¿Qué herramientas usa cada rol?
2. **Data Visibility** = ¿Qué información ve cada rol?
3. **Workflow Actions** = ¿Cómo coordinan los roles?

**Sin Level 2 y 3:** Tenemos agentes con tools correctas pero **sin coordinación** (como developers sin code review)

**Con 3 Levels:** Tenemos un **equipo de software funcional** que se auto-coordina ✅

---

## 📊 Implementation Priority

| Level | Status | Priority | Reason |
|-------|--------|----------|--------|
| **Level 1: Tools** | ✅ DONE | P0 (CRITICAL) | Security básica |
| **Level 2: Data** | 🔵 DESIGNED | P1 (HIGH) | Context precision |
| **Level 3: Workflow** | 🔵 DESIGNED | P1 (HIGH) | Team coordination |

**Recommendation:** Implementar Levels 2 y 3 juntos (son complementarios)

---

## 🚀 Next Steps

### Sprint Plan:

**Sprint N+1: Context Service Enhancement**
- Implement role-based Neo4j queries
- Update GetContext API with role parameter
- Test with different roles
- Verify context sizes (2-3K dev, 8-12K architect)

**Sprint N+2: Workflow Orchestration Service**
- Implement FSM engine
- NATS event consumers
- State persistence (Neo4j + Valkey)
- Action routing logic

**Sprint N+3: Integration**
- Update VLLMAgent to publish work completion
- Update Orchestrator to consume task assignments
- Enhance LLM prompts with workflow context
- E2E tests (full workflow: Dev → Arch → QA → PO)

---

## 🎯 Vision

**SWE AI Fleet = Digital Software Team**

Not just "AI that codes", but **"AI team that works like real humans"**:
- ✅ Specialization
- ✅ Checks and balances
- ✅ Precise context per role
- ✅ Workflow coordination
- ✅ Knowledge sharing (Neo4j graph)
- ✅ Async communication (NATS)

**This is Domain-Driven Design at its finest** - modeling the real-world domain of software teams.

---

**Author:** AI Assistant + Tirso García
**Date:** 2025-11-04
**Philosophy:** "Code models reality, reality validates code"

