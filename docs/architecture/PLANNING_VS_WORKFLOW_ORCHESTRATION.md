# Planning Service vs Workflow Orchestration

**Date:** 2025-11-04
**Type:** Architecture Clarification
**Status:** 🎯 CRITICAL DECISION POINT

---

## 🎯 Problem Statement

**User Question:**
> "Planning Service vs RBAC Workflow Orchestration design - ¿Qué relación tienen?"

**Key Confusion:**
Tenemos **DOS workflows** en diferentes niveles:
1. **Story-level FSM** (Planning Service - YA EXISTE ✅)
2. **Task-level Workflow** (Workflow Orchestration - DISEÑADO 🔵)

---

## 📊 Planning Service (Existing)

### What It Does:

```
┌─────────────────────────────────────────────────────────────┐
│           PLANNING SERVICE - STORY LIFECYCLE FSM            │
└─────────────────────────────────────────────────────────────┘

Scope: USER STORY level (e.g., "As user, I want secure auth")

States (13):
  DRAFT → PO_REVIEW → READY_FOR_PLANNING → PLANNED →
  READY_FOR_EXECUTION → IN_PROGRESS → CODE_REVIEW →
  TESTING → READY_TO_REVIEW → ACCEPTED → DONE → ARCHIVED

Example Story Flow:
  1. PO creates story → DRAFT
  2. PO approves → PO_REVIEW → READY_FOR_PLANNING
  3. Tasks derived → PLANNED
  4. Story assigned to sprint → READY_FOR_EXECUTION
  5. Dev starts work → IN_PROGRESS
  6. Dev finishes → CODE_REVIEW
  7. Architect approves → TESTING
  8. QA tests → READY_TO_REVIEW
  9. PO approves → ACCEPTED → DONE
```

### Key Properties:

- **Granularity:** STORY level (not task level)
- **Purpose:** Agile lifecycle management (sprint, backlog, etc.)
- **Events:** `planning.story.created`, `planning.story.transitioned`
- **Storage:** Neo4j (structure) + Valkey (details)
- **Port:** 50051 (gRPC)

### What It DOESN'T Do:

❌ Task-level workflow (dentro de una story)
❌ RBAC action validation (APPROVE_DESIGN, REJECT_DESIGN)
❌ Agent-to-agent coordination
❌ Role-based task routing

---

## 🔵 Workflow Orchestration (Designed, Not Built)

### What It SHOULD Do:

```
┌─────────────────────────────────────────────────────────────┐
│        WORKFLOW ORCHESTRATION - TASK EXECUTION FSM          │
└─────────────────────────────────────────────────────────────┘

Scope: TASK level (e.g., "Implement JWT generation")

States (12):
  todo → implementing → dev_completed → pending_arch_review →
  arch_reviewing → arch_approved/arch_rejected →
  pending_qa → qa_testing → qa_passed/qa_failed →
  pending_po_approval → po_approved → done

Example Task Flow:
  1. Task assigned to Dev → implementing
  2. Dev commits code → dev_completed
  3. Auto-route to Architect → pending_arch_review
  4. Architect reviews → arch_approved
  5. Auto-route to QA → pending_qa
  6. QA tests → qa_passed
  7. Auto-route to PO → pending_po_approval
  8. PO approves → done

Actions Required:
  • Dev: COMMIT_CODE, REQUEST_REVIEW
  • Architect: APPROVE_DESIGN, REJECT_DESIGN
  • QA: APPROVE_TESTS, REJECT_TESTS
  • PO: APPROVE_STORY
```

### Key Properties:

- **Granularity:** TASK level (dentro de una story)
- **Purpose:** Multi-role coordination, RBAC action enforcement
- **Events:** `workflow.task.assigned`, `agent.work.completed`
- **Storage:** Neo4j (state) + Valkey (metadata)
- **Port:** 50056 (proposed, new microservice)

---

## 🔄 Relationship: Two Levels of FSM

### Level 1: Story FSM (Planning Service)

```
Story: "As user, I want secure authentication"

DRAFT → PO_REVIEW → READY_FOR_PLANNING → PLANNED
                                            ↓
                            Derive Tasks:
                              - T-001: Implement JWT
                              - T-002: Validate tokens
                              - T-003: Refresh tokens
                                            ↓
                         READY_FOR_EXECUTION
                                            ↓
                         IN_PROGRESS ← (Story level)
```

**Planning Service Responsibility:**
- Story lifecycle (sprint planning, PO approval, backlog)
- Task derivation (story → tasks)
- Epic/Story/Task hierarchy

---

### Level 2: Task FSM (Workflow Orchestration)

```
Task: "T-001: Implement JWT generation"

todo
  ↓
implementing (Developer working)
  ↓
dev_completed (Dev commits code)
  ↓
pending_arch_review (Architect must validate)
  ↓
arch_reviewing (Architect reviewing)
  ↓ (APPROVE_DESIGN)
arch_approved
  ↓
pending_qa (QA must test)
  ↓ (APPROVE_TESTS)
qa_passed
  ↓
pending_po_approval (PO must validate)
  ↓ (APPROVE_STORY)
done
```

**Workflow Orchestration Responsibility:**
- Task execution coordination
- Role-based routing (Dev → Arch → QA → PO)
- Action validation (APPROVE/REJECT)
- Agent-to-agent handoff

---

## 🎯 Integration: How They Work Together

### Story State → Multiple Task States

```
Planning Service (Story-level):
  Story US-101: IN_PROGRESS
    ├─ Task T-001: done ✅
    ├─ Task T-002: qa_passed (awaiting PO) ⏳
    └─ Task T-003: implementing ⏳

Workflow Service (Task-level):
  Task T-001:
    todo → implementing → dev_completed → arch_approved → qa_passed → done ✅

  Task T-002:
    todo → implementing → dev_completed → arch_approved → qa_passed ⏳
    (waiting for PO approval)

  Task T-003:
    todo → implementing ⏳
    (Dev currently working)
```

---

### Event Flow Integration:

```
┌─────────────────┐
│ Planning Service│
└────────┬────────┘
         │ 1. Story transitioned to READY_FOR_EXECUTION
         │    Event: planning.story.transitioned
         ↓
┌──────────────────────┐
│ Workflow Orchestration│
└────────┬─────────────┘
         │ 2. Creates workflow for each task
         │    Task T-001: todo
         │    Task T-002: todo
         │    Task T-003: todo
         │
         │ 3. Assigns first task to Developer
         │    Event: workflow.task.assigned {task_id: T-001, role: developer}
         ↓
┌─────────────────┐
│  Orchestrator   │
└────────┬────────┘
         │ 4. Creates Developer agent
         │    Executes task
         │    Publishes: agent.work.completed {action: COMMIT_CODE}
         ↓
┌──────────────────────┐
│ Workflow Orchestration│
└────────┬─────────────┘
         │ 5. Validates action (dev can COMMIT_CODE ✅)
         │    Transition: implementing → dev_completed → pending_arch_review
         │    Event: workflow.task.assigned {task_id: T-001, role: architect}
         ↓
┌─────────────────┐
│  Orchestrator   │
└────────┬────────┘
         │ 6. Creates Architect agent
         │    Reviews code
         │    Publishes: agent.work.completed {action: APPROVE_DESIGN}
         ↓
... (continues with QA, PO)
         ↓
┌──────────────────────┐
│ Workflow Orchestration│
└────────┬─────────────┘
         │ When ALL tasks done:
         │   Notifies Planning Service
         │   Event: workflow.story.tasks_completed
         ↓
┌─────────────────┐
│ Planning Service│
└─────────────────┘
         │ Transitions story:
         │   IN_PROGRESS → CODE_REVIEW → TESTING → DONE
```

---

## 🤔 Key Question: Where Should Task Workflow Live?

### Option A: Extend Planning Service (Monolith)

**Pros:**
- ✅ Everything in one place
- ✅ No new microservice
- ✅ Simpler deployment

**Cons:**
- ❌ Planning Service becomes complex (story FSM + task FSM)
- ❌ Mixing concerns (story lifecycle vs task execution)
- ❌ Harder to test
- ❌ Violates Single Responsibility Principle

**Code:**
```python
# services/planning/planning/domain/entities/task.py
# Would need to add:
class Task:
    task_id: str
    workflow_state: TaskWorkflowState  # NEW
    assigned_to_role: Role  # NEW
    required_action: Action  # NEW
    ...
```

---

### Option B: New Workflow Orchestration Service (Microservice) ✅ RECOMMENDED

**Pros:**
- ✅ Separation of Concerns (story lifecycle vs task execution)
- ✅ Single Responsibility
- ✅ Easier to test
- ✅ Can scale independently
- ✅ Clear boundaries

**Cons:**
- ⚠️ One more microservice to deploy
- ⚠️ One more service to maintain
- ⚠️ Additional complexity in communication

**Architecture:**
```
Planning Service:
  Responsibility: Story lifecycle (sprint planning, PO approval)
  Scope: Stories, Epics
  FSM: Story states (DRAFT → READY → IN_PROGRESS → DONE)

Workflow Orchestration Service:
  Responsibility: Task execution coordination (Dev → Arch → QA → PO)
  Scope: Tasks (within stories)
  FSM: Task workflow states (implementing → arch_approved → qa_passed → done)
  Actions: APPROVE_DESIGN, REJECT_DESIGN, etc.
```

---

## 🎯 Recommendation: Option B (Separate Service)

### Rationale:

1. **Different Domains:**
   - Planning = Agile/Scrum domain (backlog, sprints, stories)
   - Workflow = Task execution domain (implementation, validation, approval)

2. **Different Lifecycles:**
   - Story: Weeks to months (long-lived)
   - Task: Hours to days (short-lived)

3. **Different Actors:**
   - Planning: PO, Scrum Master (business)
   - Workflow: Developers, Architects, QA (technical)

4. **Different Event Sources:**
   - Planning: UI (PO creates stories), Planning FSM
   - Workflow: Agents (publishes work.completed), Workflow FSM

---

## 📊 Comparison Table

| Aspect | Planning Service | Workflow Orchestration Service |
|--------|------------------|--------------------------------|
| **Scope** | Story lifecycle | Task execution |
| **Granularity** | Story (US-101) | Task (T-001, T-002) |
| **FSM States** | 13 states (DRAFT → DONE) | 12 states (todo → done) |
| **Transitions** | PO approval, sprint changes | Agent completions, validations |
| **Actions** | N/A (or minimal) | RBAC Actions (APPROVE_DESIGN, etc.) |
| **Events In** | UI (PO), FSM timers | agent.work.completed |
| **Events Out** | planning.story.transitioned | workflow.task.assigned |
| **Consumers** | Orchestrator, Context | Orchestrator |
| **Storage** | Neo4j + Valkey | Neo4j + Valkey |
| **Port** | 50051 | 50056 (proposed) |
| **Language** | Python (gRPC) | Go (proposed, or Python) |
| **Status** | ✅ EXISTS | 🔵 DESIGNED |

---

## 🔗 Integration Points

### 1. Planning → Workflow

**When:** Story transitioned to READY_FOR_EXECUTION

```python
# Planning Service publishes:
await nats.publish("planning.story.transitioned", {
    "story_id": "US-101",
    "from_state": "PLANNED",
    "to_state": "READY_FOR_EXECUTION",
    "tasks": ["T-001", "T-002", "T-003"]  # Derived tasks
})

# Workflow Service consumes:
async def handle_story_ready(event):
    for task_id in event["tasks"]:
        # Create workflow for each task
        workflow_state = create_task_workflow(
            task_id=task_id,
            story_id=event["story_id"],
            initial_state="todo"
        )

        # Assign first task to Developer
        if is_first_task(task_id):
            await publish_task_assigned(
                task_id=task_id,
                role="developer",
                action="IMPLEMENT_FEATURE"
            )
```

---

### 2. Workflow → Planning

**When:** All tasks in story completed

```python
# Workflow Service tracks task completion:
if all_tasks_done_for_story(story_id):
    # Notify Planning Service
    await nats.publish("workflow.story.tasks_completed", {
        "story_id": story_id,
        "all_tasks_status": "done"
    })

# Planning Service consumes:
async def handle_tasks_completed(event):
    # Transition story: IN_PROGRESS → TESTING
    await transition_story(
        story_id=event["story_id"],
        to_state="TESTING"
    )
```

---

## 🏗️ Updated Architecture

### Current (M4):

```
┌─────────────────┐
│ Planning Service│  (Story FSM - EXISTS ✅)
│   50051 (gRPC)  │
└────────┬────────┘
         │ planning.story.transitioned
         ↓
┌─────────────────┐
│  Orchestrator   │  (Deliberation only - EXISTS ✅)
│   50055 (gRPC)  │
└────────┬────────┘
         │ Creates agents, no workflow coordination ❌
         ↓
┌─────────────────┐
│   VLLMAgent     │  (RBAC Level 1 - EXISTS ✅)
└─────────────────┘
```

**Gap:** No task-level coordination (Dev → Arch → QA → PO)

---

### Proposed (M5 - After RBAC Level 1):

```
┌─────────────────┐
│ Planning Service│  (Story FSM)
│   50051         │
└────────┬────────┘
         │ planning.story.transitioned
         │ {state: READY_FOR_EXECUTION, tasks: [T-001, T-002]}
         ↓
┌──────────────────────┐
│ Workflow Orchestration│  (Task FSM - NEW 🔵)
│   50056 (gRPC)        │
└────────┬─────────────┘
         │ Creates task workflows
         │ Routes based on Actions
         │
         │ workflow.task.assigned
         │ {task_id: T-001, role: developer, action: IMPLEMENT}
         ↓
┌─────────────────┐
│  Orchestrator   │  (Agent creation + deliberation)
│   50055         │
└────────┬────────┘
         │ Creates appropriate agent
         ↓
┌─────────────────┐
│   VLLMAgent     │  (RBAC Level 1)
│  (Developer)    │
└────────┬────────┘
         │ Executes task with RBAC enforcement
         │
         │ agent.work.completed
         │ {action: COMMIT_CODE}
         ↓
┌──────────────────────┐
│ Workflow Orchestration│
└────────┬─────────────┘
         │ Validates action (dev can COMMIT_CODE ✅)
         │ Transition: implementing → dev_completed → pending_arch_review
         │
         │ workflow.task.assigned
         │ {task_id: T-001, role: architect, action: REVIEW_DESIGN}
         ↓
┌─────────────────┐
│  Orchestrator   │
└────────┬────────┘
         │ Creates Architect agent
         ↓
┌─────────────────┐
│   VLLMAgent     │
│  (Architect)    │
└────────┬────────┘
         │ agent.work.completed
         │ {action: APPROVE_DESIGN}
         ↓
... (continues with QA, PO)
         ↓
┌──────────────────────┐
│ Workflow Orchestration│
└────────┬─────────────┘
         │ All tasks done
         │
         │ workflow.story.tasks_completed
         ↓
┌─────────────────┐
│ Planning Service│
└─────────────────┘
         │ Transition story: IN_PROGRESS → TESTING → DONE
```

---

## 🎯 Decision: Two Separate Services ✅

### Planning Service (Existing):

**Focus:** Story lifecycle management

```python
# Responsibilities:
✅ Create stories (PO via UI)
✅ FSM for story states (DRAFT → DONE)
✅ PO approval workflow
✅ Task derivation (story → tasks)
✅ Sprint management
✅ Backlog prioritization

# Events Published:
✅ planning.story.created
✅ planning.story.transitioned
✅ planning.decision.approved (for story-level decisions)

# Consumers:
✅ Orchestrator (starts deliberation when story ready)
✅ Context (enriches context graph)
✅ Monitoring (tracks metrics)
```

---

### Workflow Orchestration Service (NEW - Future):

**Focus:** Task execution coordination

```python
# Responsibilities:
🔵 Create task workflows (one per task)
🔵 FSM for task execution states
🔵 Route tasks to appropriate roles
🔵 Validate RBAC Actions
🔵 Coordinate Dev → Arch → QA → PO flow
🔵 Handle approvals/rejections
🔵 Retry logic for rejected work

# Events Consumed:
🔵 planning.story.transitioned (creates task workflows)
🔵 agent.work.completed (validates actions, routes next)

# Events Published:
🔵 workflow.task.assigned (tells Orchestrator which agent to create)
🔵 workflow.state.changed (for monitoring)
🔵 workflow.story.tasks_completed (notifies Planning when all done)

# Consumers:
🔵 Orchestrator (creates agents based on task assignments)
```

---

## 📋 Implementation Roadmap

### Current Status (M4):

- ✅ Planning Service exists and working
- ✅ RBAC Level 1 implemented (tool access)
- ✅ Actions defined in domain
- ❌ Workflow Orchestration Service doesn't exist
- ❌ Task-level workflow missing

### Sprint N+1: RBAC Level 1 Merge

- [ ] Merge feature/rbac-agent-domain to main
- [ ] Deploy with fresh-redeploy.sh
- [ ] Verify RBAC enforcement
- [ ] Planning Service continues working (no changes needed)

### Sprint N+2: Workflow Orchestration Service (NEW)

**Week 1-2: Design & Core FSM**
- [ ] Create new microservice: services/workflow/
- [ ] Implement task workflow FSM (12 states)
- [ ] Define transitions with RBAC Actions
- [ ] Unit tests (100% coverage)

**Week 3: NATS Integration**
- [ ] Consume planning.story.transitioned
- [ ] Consume agent.work.completed
- [ ] Publish workflow.task.assigned
- [ ] Publish workflow.story.tasks_completed

**Week 4: Integration**
- [ ] Update Orchestrator to consume workflow.task.assigned
- [ ] Update VLLMAgent to publish agent.work.completed with action
- [ ] Integration tests (full flow: Dev → Arch → QA → PO)
- [ ] Update fresh-redeploy.sh to include workflow service

---

## 🎯 Key Insight: Separation of Concerns

```
┌──────────────────────────────────────────────────────────────┐
│ PLANNING SERVICE = Agile/Scrum Domain                        │
│   • Sprint planning                                          │
│   • Backlog management                                       │
│   • Story approval (PO)                                      │
│   • Epic/Story hierarchy                                     │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ WORKFLOW ORCHESTRATION = Task Execution Domain               │
│   • Multi-role coordination                                  │
│   • Dev → Arch → QA → PO flow                                │
│   • RBAC action validation                                   │
│   • Approval/rejection loops                                 │
└──────────────────────────────────────────────────────────────┘
```

**They are COMPLEMENTARY, not redundant.**

---

## 📊 What to Deploy NOW (M4)

### RBAC Level 1 Merge:

```bash
# Merge & Deploy
git merge feature/rbac-agent-domain
cd scripts/infra
./fresh-redeploy.sh
```

**Services redeployed:**
- ✅ orchestrator (uses RBAC)
- ✅ ray-executor (uses RBAC)
- ✅ context (no changes, but redeployed)
- ✅ planning (no changes, but redeployed)
- ✅ monitoring (no changes, but redeployed)

**Planning Service:**
- ⚪ NO changes in this merge
- ⚪ Continues managing story FSM
- ⚪ Workflow Orchestration will integrate later (M5)

---

## 🎯 Summary

**Planning Service:**
- ✅ Exists and works
- ✅ Manages STORY lifecycle
- ✅ No changes needed for RBAC Level 1
- ✅ Will integrate with Workflow Service in M5

**Workflow Orchestration Service:**
- 🔵 Fully designed
- 🔵 Will manage TASK execution workflow
- 🔵 Implements RBAC Actions coordination
- 🔵 Sprint N+2 implementation

**Relationship:**
- Planning creates tasks → Workflow coordinates task execution
- Workflow completes all tasks → Planning transitions story state
- **Two levels, clean separation ✅**

---

**DECISION:** ✅ Keep as separate services

**NEXT STEPS:**
1. Merge RBAC Level 1 (no Planning changes)
2. Deploy with fresh-redeploy.sh (redeploys Planning too)
3. Sprint N+2: Build Workflow Orchestration Service
4. Integrate: Planning ↔ Workflow ↔ Orchestrator

---

**Author:** Tirso García + AI Assistant
**Date:** 2025-11-04
**Status:** Architecture clarified - Ready to proceed with merge & deploy

