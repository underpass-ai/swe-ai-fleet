# RBAC GAP: Workflow Orchestration Missing

**Date:** 2025-11-04
**Severity:** 🟡 **MEDIUM** (Functional gap, not security vulnerability)
**Type:** Missing Integration

---

## 🎯 Problem Statement

**Question from User:**
> "¿Cómo sabe Dev que el Arquitecto le tiene que validar?
> ¿Cómo sabe el Arquitecto que tiene que validar las soluciones de los Devs?
> ¿Cómo sabe QA que tiene que interactuar con PO?"

**Discovered Gap:**

We have **2 levels of RBAC**, but only Level 1 is fully integrated:

### ✅ Level 1: Tool Access Control (IMPLEMENTED)

**What it does:**
- Controls WHICH tools each role can use
- Validates at runtime before execution
- Prevents privilege escalation

**Example:**
```python
# QA cannot use docker
qa_agent.can_use_tool("docker")  # False ✅

# Developer cannot use db
dev_agent.can_use_tool("db")  # False ✅
```

**Status:** ✅ FULLY IMPLEMENTED & TESTED

---

### ❌ Level 2: Workflow Orchestration (NOT IMPLEMENTED)

**What it SHOULD do:**
- Define WHEN agents must interact
- Specify WHICH actions require OTHER role's approval
- Coordinate multi-agent workflows

**Example (MISSING):**
```python
# Developer implements feature
dev_result = developer.execute_task("Implement auth")

# ❓ How does system know Architect MUST validate?
# ❓ How does Architect know to review Dev's work?
# ❓ Is there automatic routing: Dev → Architect → QA → PO?
```

**Status:** ❌ NOT IMPLEMENTED

---

## 🔍 Current State Analysis

### What WE HAVE:

#### 1. Actions Defined (Domain)

```python
# action.py - 23 actions across 6 scopes
ActionEnum.APPROVE_DESIGN      # Architect approves design
ActionEnum.REJECT_DESIGN       # Architect rejects design
ActionEnum.REVIEW_ARCHITECTURE # Architect reviews code
ActionEnum.APPROVE_TESTS       # QA approves tests
ActionEnum.VALIDATE_COMPLIANCE # QA validates compliance
ActionEnum.APPROVE_STORY       # PO approves story
...
```

#### 2. Roles with Allowed Actions

```python
# role_factory.py
architect_role = Role(
    value=RoleEnum.ARCHITECT,
    allowed_actions=frozenset([
        ActionEnum.APPROVE_DESIGN,
        ActionEnum.REJECT_DESIGN,
        ActionEnum.REVIEW_ARCHITECTURE,
    ]),
    ...
)
```

#### 3. Agent Can Check Actions

```python
# agent.py
def can_execute(self, action: Action) -> bool:
    return self.role.can_perform(action)

# Usage (hypothetical):
architect.can_execute(Action(value=ActionEnum.APPROVE_DESIGN))  # True ✅
developer.can_execute(Action(value=ActionEnum.APPROVE_DESIGN))  # False ✅
```

---

### What WE DON'T HAVE:

#### 1. Actions NOT Used in Orchestrator

```python
# Current Orchestrator flow:
Orchestrate.execute(role="DEV", task="Implement feature")
  → Deliberate.execute() → 3 agents propose solutions
  → Architect.choose() → picks best proposal
  → Returns winner

# ❌ NO usa ActionEnum.APPROVE_DESIGN
# ❌ NO usa ActionEnum.REJECT_DESIGN
# ❌ NO hay validación explícita
```

#### 2. No Workflow State Machine

**Missing:**
```python
# Workflow should be:
1. DEV implements → TaskStatus.IMPLEMENTED
2. ARCHITECT reviews → can_execute(APPROVE_DESIGN)
   → If approved: TaskStatus.APPROVED
   → If rejected: TaskStatus.REJECTED → back to DEV
3. QA tests → can_execute(APPROVE_TESTS)
   → If pass: TaskStatus.QA_PASSED
4. PO validates → can_execute(APPROVE_STORY)
   → If approved: TaskStatus.DONE
```

**Current:**
```python
# Only has:
TaskStatus.TODO → IN_PROGRESS → COMPLETED
# No validation checkpoints ❌
```

#### 3. No Agent Coordination Protocol

**Missing:**
- How does system route Dev's output to Architect?
- How does Architect signal approval/rejection back to system?
- How does system trigger QA after Architect approves?
- How does QA coordinate with PO for validation?

---

## 🎯 How LLM Currently Knows Its Role

### What IS Communicated to LLM:

```python
# generate_plan_usecase.py:100-103
role_prompt = roles.get(
    role.get_prompt_key(),  # "DEVELOPER"
    f"You are an expert {role.get_name()} engineer."
)

# System prompt to LLM:
"""
You are an expert software developer focused on writing clean code.

Available tools: [files, git, tests]
Mode: full

Generate execution plan...
"""
```

**LLM knows:**
- ✅ Its role identity ("developer")
- ✅ Its allowed tools (files, git, tests)
- ✅ Its mode (full/read-only)

**LLM DOESN'T know:**
- ❌ Workflow responsibilities
- ❌ When to request validation
- ❌ Who validates its work
- ❌ Coordination protocol

---

## 💡 Gap Analysis

### Current Behavior (Without Workflow Orchestration):

```python
# Developer agent receives task:
task = "Implement JWT authentication"

# LLM generates plan:
plan = {
    "steps": [
        {"tool": "files", "operation": "read_file", ...},
        {"tool": "files", "operation": "write_file", ...},
        {"tool": "tests", "operation": "pytest", ...},
        {"tool": "git", "operation": "commit", ...}
    ]
}

# Agent executes and COMMITS ✅
# ❌ NO automatic routing to Architect for validation
# ❌ NO use of Action.APPROVE_DESIGN
# ❌ Architect doesn't even know this work exists
```

---

## 🔧 What's Missing

### 1. Workflow State Machine

**Needed:**
```python
class WorkflowState(Enum):
    DRAFT = "draft"
    IMPLEMENTED = "implemented"  # Dev done
    PENDING_ARCH_REVIEW = "pending_arch_review"  # Waiting for architect
    ARCH_APPROVED = "arch_approved"  # Architect approved
    ARCH_REJECTED = "arch_rejected"  # Architect rejected
    PENDING_QA = "pending_qa"  # Waiting for QA
    QA_PASSED = "qa_passed"
    PENDING_PO_APPROVAL = "pending_po_approval"
    DONE = "done"
```

### 2. Transition Rules with Actions

**Needed:**
```python
workflow_transitions = {
    (WorkflowState.IMPLEMENTED, ActionEnum.APPROVE_DESIGN): WorkflowState.ARCH_APPROVED,
    (WorkflowState.IMPLEMENTED, ActionEnum.REJECT_DESIGN): WorkflowState.ARCH_REJECTED,
    (WorkflowState.ARCH_APPROVED, ActionEnum.APPROVE_TESTS): WorkflowState.QA_PASSED,
    (WorkflowState.QA_PASSED, ActionEnum.APPROVE_STORY): WorkflowState.DONE,
}
```

### 3. Agent Task Context

**Needed in LLM prompt:**
```python
# Current prompt (partial):
"""
You are an expert software developer.
Tools: [files, git, tests]
"""

# Should include workflow context:
"""
You are an expert software developer.
Tools: [files, git, tests]

WORKFLOW RESPONSIBILITIES:
- Implement features based on architect's design
- Your work will be reviewed by Architect
- After architect approval, QA will test
- Write code that passes architectural review

ACTIONS YOU CAN PERFORM:
- COMMIT_CODE (finalize your implementation)
- REQUEST_REVIEW (send to architect)
- REVISE_CODE (after rejection)

ACTIONS YOU CANNOT PERFORM:
- APPROVE_DESIGN (only Architect)
- APPROVE_TESTS (only QA)
"""
```

### 4. Orchestrator Integration

**Needed:**
```python
class WorkflowOrchestrator:
    async def execute_workflow(self, task: Task) -> WorkflowResult:
        # Step 1: DEV implements
        dev_result = await self._execute_agent_task(
            role=RoleEnum.DEVELOPER,
            task=task,
            action=ActionEnum.IMPLEMENT_FEATURE
        )

        # Step 2: ARCHITECT validates
        if dev_result.status == "completed":
            arch_result = await self._request_validation(
                validator_role=RoleEnum.ARCHITECT,
                work_to_validate=dev_result,
                required_action=ActionEnum.APPROVE_DESIGN
            )

            if arch_result.action == ActionEnum.REJECT_DESIGN:
                # Loop back to DEV with feedback
                return await self._execute_agent_task(
                    role=RoleEnum.DEVELOPER,
                    task=task,
                    action=ActionEnum.REVISE_CODE,
                    feedback=arch_result.feedback
                )

        # Step 3: QA tests (if architect approved)
        if arch_result.action == ActionEnum.APPROVE_DESIGN:
            qa_result = await self._execute_agent_task(
                role=RoleEnum.QA,
                task=task,
                action=ActionEnum.RUN_TESTS
            )

            # Step 4: PO validates (if QA passed)
            if qa_result.action == ActionEnum.APPROVE_TESTS:
                po_result = await self._request_validation(
                    validator_role=RoleEnum.PO,
                    work_to_validate=qa_result,
                    required_action=ActionEnum.APPROVE_STORY
                )
```

---

## 📊 Current vs Needed

| Component | Current | Needed |
|-----------|---------|--------|
| **Actions** | ✅ Defined | ✅ Defined |
| **Role.allowed_actions** | ✅ Configured | ✅ Configured |
| **Agent.can_execute()** | ✅ Implemented | ✅ Implemented |
| **Workflow State Machine** | ❌ Missing | ⏳ TODO |
| **Transition Rules** | ❌ Missing | ⏳ TODO |
| **Orchestrator Integration** | ❌ Not using Actions | ⏳ TODO |
| **Agent Context (LLM prompt)** | ❌ No workflow info | ⏳ TODO |

---

## 💡 Where the Information Should Come From

### Option A: Context Service Provides Workflow State

```python
# Context Service returns:
context = {
    "story_id": "US-123",
    "current_phase": "IMPLEMENTATION",
    "workflow_state": "IMPLEMENTED",  # ← NEW
    "next_required_action": "APPROVE_DESIGN",  # ← NEW
    "required_validator": "ARCHITECT",  # ← NEW
    "previous_feedback": [...],  # ← From Architect if rejected
}

# Developer LLM prompt includes:
"""
Task: Implement JWT auth

Workflow Status:
- Your implementation will be reviewed by ARCHITECT
- Wait for APPROVE_DESIGN or REJECT_DESIGN action
- If rejected, you will receive feedback to revise
"""
```

### Option B: Planning Service FSM Integration

```yaml
# config/agile.fsm.yaml already has states:
states:
  - draft
  - po_review
  - coach_refinement
  - ready_for_dev
  - in_progress
  - code_review  # ← ARCHITECT validates here
  - testing      # ← QA tests here
  - done
```

**Integration needed:**
```python
# Planning Service transition requires Action:
planning.transition(
    story_id="US-123",
    from_state="in_progress",
    to_state="code_review",
    action=ActionEnum.REQUEST_REVIEW,  # ← Developer requests
    actor_role=RoleEnum.DEVELOPER
)

# Then Architect reviews:
planning.transition(
    story_id="US-123",
    from_state="code_review",
    to_state="testing",
    action=ActionEnum.APPROVE_DESIGN,  # ← Architect approves
    actor_role=RoleEnum.ARCHITECT
)
```

---

## 🎯 Recommendation

### SHORT TERM (Current Sprint):

**Document the gap** ✅ (this document)

Current RBAC is **sufficient for tool security** but **insufficient for workflow coordination**.

### MEDIUM TERM (Next Sprint):

**Integrate Actions with Workflow:**

1. **Update Context Service** to include workflow state:
   - Current state (IMPLEMENTED, PENDING_REVIEW, etc.)
   - Required next action
   - Required validator role

2. **Update LLM Prompts** to include workflow context:
   - Add "Workflow Responsibilities" section
   - Add "Required Actions" section
   - Add "Coordination Protocol" section

3. **Integrate with Planning Service FSM:**
   - Map FSM states to required Actions
   - Validate transitions require correct Action
   - Enforce role-based state transitions

4. **Update Orchestrator** to use Actions:
   - Route work based on required_action
   - Validate actor_role can perform action
   - Implement approval/rejection loops

### LONG TERM:

**Full Workflow Engine:**
- BPMN-style workflow definitions
- Role-based task routing
- Automatic coordination between agents
- Approval gates with Actions

---

## 📝 Immediate Action

Create **Q26** in challenge questions:

**Q26: Workflow Orchestration & Action Integration**

**Question:** ¿Cómo se integran las Actions con el workflow para coordinar aprobaciones entre roles?

**Answer:** ❌ **NOT IMPLEMENTED**

**Current State:**
- Actions are defined in domain ✅
- Roles have allowed_actions ✅
- Agent.can_execute() validates actions ✅
- **BUT**: Orchestrator doesn't use Actions ❌
- **BUT**: No workflow routing based on Actions ❌
- **BUT**: LLM doesn't know workflow responsibilities ❌

**Impact:**
- **Tool security:** ✅ Enforced
- **Workflow coordination:** ❌ Manual/missing
- **Agent knows:** Its tools
- **Agent doesn't know:** When to request validation, who validates

**Recommendation:**
- Document gap ✅
- Add to backlog for next iteration
- Not blocking current RBAC merge (tool-level RBAC is complete)

---

## 🎯 Conclusion

**User's Question is Valid:** ✅ **GAP EXISTS**

**Is it a Security Issue?** ❌ NO
- Tools are properly restricted
- No privilege escalation possible
- RBAC at tool level works correctly

**Is it a Functional Gap?** ✅ YES
- Workflow coordination manual
- Actions not integrated with Orchestrator
- LLM doesn't know workflow responsibilities

**Should it Block Merge?** ❌ NO
- Tool-level RBAC is production-ready
- Workflow orchestration is separate feature
- Can be added in next iteration

**Priority:** 🟡 MEDIUM (next sprint)

---

**Created:** 2025-11-04
**Author:** AI Assistant + Tirso García
**Status:** Documented for future implementation

