# Human-in-the-Loop Architecture

**Date:** 2025-11-04
**Critical Design Decision:** PO es HUMANO, no AI agent
**Future:** Arquitecto Principal también puede ser humano

---

## 🎯 Hybrid Team Model

### Current (M4):

```
┌────────────────────────────────────────────────────────────┐
│                    SWE AI Fleet Team                        │
├────────────────────────────────────────────────────────────┤
│  🤖 Developer Agents    (AI - 3 agents deliberate)         │
│  🤖 Architect Agents    (AI - validation, scoring)         │
│  🤖 QA Agent            (AI - testing, validation)         │
│  👤 Product Owner       (HUMAN - via UI)                   │
└────────────────────────────────────────────────────────────┘
```

### Future (M5+):

```
┌────────────────────────────────────────────────────────────┐
│              Hybrid AI + Human Team                         │
├────────────────────────────────────────────────────────────┤
│  🤖 Developer Agents       (AI - implementation)           │
│  🤖 Junior Architect Agent (AI - initial review)           │
│  👤 Senior Architect       (HUMAN - final validation)      │
│  🤖 QA Agent               (AI - automated testing)        │
│  👤 Product Owner          (HUMAN - business decisions)    │
│  👤 DevOps Lead            (HUMAN - production approval)   │
└────────────────────────────────────────────────────────────┘
```

---

## 🔄 Updated Workflow with Humans

### Workflow States with Actor Type:

```yaml
# config/workflow.fsm.yaml - Enhanced

states:
  - id: implementing
    actor_type: agent  # AI agent
    allowed_roles: [developer]

  - id: pending_arch_review
    actor_type: agent  # AI architect (for now)
    allowed_roles: [architect]
    # future: actor_type: hybrid (AI first, human if needed)

  - id: pending_po_approval
    actor_type: human  # HUMAN PO via UI
    allowed_roles: [po]
    ui_enabled: true  # Show in UI for human interaction
    notification_required: true  # Notify human

  - id: pending_senior_arch_approval
    actor_type: human  # HUMAN senior architect (future)
    allowed_roles: [architect]
    ui_enabled: true
    notification_required: true

transitions:
  # AI → AI transition (automatic)
  - from: dev_completed
    to: pending_arch_review
    actor_type: system  # Automatic routing

  # AI → Human transition (requires UI)
  - from: qa_passed
    to: pending_po_approval
    actor_type: system  # Auto-route to human
    notification:
      channel: [email, slack, ui]
      message: "Story US-101 ready for PO approval"

  # Human approval (via UI)
  - from: pending_po_approval
    to: po_approved
    action: APPROVE_STORY
    actor_type: human  # Human clicks button in UI
    requires_ui_interaction: true
```

---

## 🖥️ UI Integration for Human Actors

### PO-UI Dashboard (Already Exists):

```
https://swe-fleet.underpassai.com

Current Features:
  ✅ Create stories
  ✅ View stories
  ✅ Edit stories
  ✅ FSM transitions

NEW Features Needed for Workflow:
  📋 Pending Approvals Tab
  ├─ Stories awaiting PO approval
  ├─ Context: Story + Epic + Business value
  ├─ Actions: [Approve ✅] [Reject ❌]
  └─ Feedback textbox (if rejecting)
```

### Updated UI Workflow View:

```typescript
// PO-UI: Pending Approvals Component

interface PendingApproval {
  story_id: string;
  title: string;
  epic: string;
  workflow_state: "pending_po_approval";

  // Work completed by AI agents:
  dev_implementation: {
    commit_sha: string;
    files_changed: string[];
    summary: string;
  };

  architect_review: {
    decision: "APPROVE_DESIGN";
    reviewer: "agent-arch-001";
    feedback: "Good implementation, follows patterns";
  };

  qa_testing: {
    decision: "APPROVE_TESTS";
    test_results: {
      passed: 45,
      failed: 0,
      coverage: 92
    };
  };

  // Human PO must decide:
  actions_available: ["APPROVE_STORY", "REJECT_STORY"];
}

// UI Component:
function PendingApprovalCard({ approval }: { approval: PendingApproval }) {
  const handleApprove = async () => {
    // Calls Workflow Service gRPC
    await workflowService.executeAction({
      task_id: approval.story_id,
      role: "po",
      action: "APPROVE_STORY",
      actor_type: "human",
      actor_id: currentUser.id  // Human user ID
    });
  };

  const handleReject = async (feedback: string) => {
    await workflowService.executeAction({
      task_id: approval.story_id,
      role: "po",
      action: "REJECT_STORY",
      feedback: feedback,
      actor_type: "human",
      actor_id: currentUser.id
    });
  };

  return (
    <Card>
      <h3>{approval.title}</h3>
      <p>Epic: {approval.epic}</p>

      {/* Show AI agents' work */}
      <Section title="Implementation (AI Developer)">
        <CommitSummary commit={approval.dev_implementation.commit_sha} />
        <FilesList files={approval.dev_implementation.files_changed} />
      </Section>

      <Section title="Architecture Review (AI Architect)">
        <Decision decision={approval.architect_review.decision} />
        <Feedback text={approval.architect_review.feedback} />
      </Section>

      <Section title="Quality Assurance (AI QA)">
        <TestResults results={approval.qa_testing.test_results} />
      </Section>

      {/* Human decision */}
      <Actions>
        <Button onClick={handleApprove} color="green">
          ✅ Approve Story
        </Button>
        <Button onClick={() => setShowFeedback(true)} color="red">
          ❌ Reject Story
        </Button>
      </Actions>

      {showFeedback && (
        <FeedbackForm onSubmit={handleReject} />
      )}
    </Card>
  );
}
```

---

## 🔄 Updated Workflow Flows

### Flow 1: AI → AI → AI → HUMAN (Current)

```
Developer Agent (AI)
  ↓ COMMIT_CODE
Architect Agent (AI)
  ↓ APPROVE_DESIGN
QA Agent (AI)
  ↓ APPROVE_TESTS
Product Owner (HUMAN via UI) 👤
  ↓ APPROVE_STORY
DONE ✅
```

### Flow 2: AI → HUMAN → AI (Future - Critical Decisions)

```
Developer Agent (AI)
  ↓ COMMIT_CODE
  ↓ REQUEST_REVIEW
Junior Architect Agent (AI)
  ↓ PRELIMINARY_REVIEW
Senior Architect (HUMAN via UI) 👤
  ↓ APPROVE_DESIGN or REJECT_DESIGN
  ↓ (if approved)
QA Agent (AI)
  ↓ APPROVE_TESTS
Product Owner (HUMAN via UI) 👤
  ↓ APPROVE_STORY
DONE ✅
```

---

## 📡 Communication Patterns

### AI Agent → Workflow Service (NATS Event):

```python
# VLLMAgent publishes:
await nats.publish("agent.work.completed", {
    "task_id": "task-001",
    "agent_id": "agent-dev-001",
    "actor_type": "agent",  # ← AI agent
    "role": "developer",
    "action_performed": "COMMIT_CODE",
    "result": {...}
})
```

### Human → Workflow Service (gRPC Request):

```python
# PO-UI calls:
response = workflow_service.ExecuteAction(
    task_id="US-101",
    role="po",
    action="APPROVE_STORY",
    actor_type="human",  # ← Human actor
    actor_id="user-tirso@underpassai.com",
    feedback="Meets all acceptance criteria"
)

# Returns immediately (synchronous for UI responsiveness)
```

### Workflow Service → Human (Notification):

```python
# When work awaits human approval:
await notification_service.notify(
    user_role="po",
    channel=["email", "slack", "ui"],
    message="Story US-101 ready for your approval",
    link="https://swe-fleet.underpassai.com/approvals/US-101"
)
```

---

## 🔐 RBAC for Humans vs AI Agents

### Same RBAC Rules Apply:

```python
# Human PO tries to approve design (not their action):
if not po_role.can_perform(Action(value=ActionEnum.APPROVE_DESIGN)):
    return Error("PO cannot approve designs, only stories")

# ✅ Same validation for humans and AI agents
```

### Actor Type Tracking:

```python
# Audit trail distinguishes human vs AI:
{
    "task_id": "task-001",
    "state_transition": {
        "from": "pending_po_approval",
        "to": "po_approved",
        "action": "APPROVE_STORY",
        "actor_type": "human",  # ← HUMAN
        "actor_id": "user-tirso@underpassai.com",
        "timestamp": "2025-11-04T10:30:00Z"
    }
}

{
    "task_id": "task-001",
    "state_transition": {
        "from": "implementing",
        "to": "dev_completed",
        "action": "COMMIT_CODE",
        "actor_type": "agent",  # ← AI AGENT
        "actor_id": "agent-dev-001",
        "timestamp": "2025-11-04T10:15:00Z"
    }
}
```

---

## 🎨 Workflow Orchestration Service Updates

### Support for Human Actors:

```python
# services/workflow/domain/workflow_state_machine.py

@dataclass(frozen=True)
class StateTransition:
    from_state: str
    to_state: str
    action: ActionEnum
    actor_role: str  # "developer", "po", etc.
    actor_type: ActorType  # "agent" or "human" ← NEW
    actor_id: str  # "agent-dev-001" or "user-tirso@..."
    timestamp: datetime
    feedback: str | None

class ActorType(Enum):
    AGENT = "agent"  # AI agent
    HUMAN = "human"  # Human user
    SYSTEM = "system"  # Automatic transition

class WorkflowStateMachine:
    def execute_transition(
        self,
        workflow_state: WorkflowState,
        action: ActionEnum,
        actor_role: str,
        actor_type: ActorType,  # ← NEW parameter
        actor_id: str,
        result: dict,
    ) -> WorkflowState:
        """Execute state transition (supports humans and AI agents)."""

        # 1. Validate RBAC (same for humans and agents)
        role = RoleFactory.create_role_by_name(actor_role)
        action_obj = Action(value=action)

        if not role.can_perform(action_obj):
            raise ValueError(
                f"RBAC Violation: {actor_type.value} {actor_id} "
                f"with role {actor_role} cannot perform {action}"
            )

        # 2. Validate state transition is allowed
        if not self.can_transition(workflow_state.current_state, action, actor_role):
            raise ValueError(f"Invalid transition: {workflow_state.current_state} → {action}")

        # 3. Check if state requires human interaction
        target_state = self._get_target_state(workflow_state.current_state, action)
        state_config = self.states[target_state]

        if state_config.get("actor_type") == "human" and actor_type == ActorType.AGENT:
            raise ValueError(
                f"State {target_state} requires human actor, but AI agent attempted transition"
            )

        # 4. Execute transition
        new_transition = StateTransition(
            from_state=workflow_state.current_state,
            to_state=target_state,
            action=action,
            actor_role=actor_role,
            actor_type=actor_type,  # ← Track if human or agent
            actor_id=actor_id,
            timestamp=datetime.now(),
            feedback=result.get("feedback")
        )

        # 5. Determine next step
        next_role, next_action, requires_human = self._get_next_step(target_state)

        # 6. Notify if human required
        if requires_human:
            await self.notification_service.notify_human(
                role=next_role,
                task_id=workflow_state.task_id,
                required_action=next_action
            )

        return WorkflowState(
            task_id=workflow_state.task_id,
            current_state=target_state,
            role_in_charge=next_role,
            required_action=next_action,
            requires_human=requires_human,  # ← NEW
            history=workflow_state.history + (new_transition,),
            feedback=result.get("feedback")
        )
```

---

## 🖥️ UI for Human Actions

### PO-UI: Approval Interface

```typescript
// frontend/src/components/ApprovalQueue.tsx

interface StoryApproval {
  story_id: string;
  title: string;
  description: string;

  // AI agents' work summary
  ai_work_summary: {
    developer: {
      agent_id: string;
      commit_sha: string;
      files_changed: number;
      reasoning: string;
    };
    architect: {
      decision: "APPROVED" | "REJECTED";
      feedback: string;
    };
    qa: {
      tests_passed: number;
      tests_failed: number;
      coverage: number;
    };
  };

  // Business context
  acceptance_criteria: string[];
  business_value: string;
  user_impact: string;

  // Actions available to human PO
  available_actions: ["APPROVE_STORY", "REJECT_STORY"];
}

export function ApprovalQueue() {
  const [pending, setPending] = useState<StoryApproval[]>([]);

  useEffect(() => {
    // Poll or WebSocket for pending approvals
    const subscription = workflowService.subscribeToPendingApprovals(
      role: "po",
      onUpdate: (approvals) => setPending(approvals)
    );

    return () => subscription.unsubscribe();
  }, []);

  const handleApprove = async (storyId: string) => {
    // Human PO approves story
    await workflowService.executeAction({
      story_id: storyId,
      role: "po",
      action: "APPROVE_STORY",
      actor_type: "human",
      actor_id: currentUser.email,
    });

    // Show success toast
    toast.success("Story approved! Moving to production backlog.");
  };

  const handleReject = async (storyId: string, feedback: string) => {
    await workflowService.executeAction({
      story_id: storyId,
      role: "po",
      action: "REJECT_STORY",
      actor_type: "human",
      actor_id: currentUser.email,
      feedback: feedback,
    });

    toast.info("Story rejected. Feedback sent to team.");
  };

  return (
    <div className="approval-queue">
      <h2>📋 Pending Your Approval ({pending.length})</h2>

      {pending.map(story => (
        <ApprovalCard
          key={story.story_id}
          story={story}
          onApprove={() => handleApprove(story.story_id)}
          onReject={(feedback) => handleReject(story.story_id, feedback)}
        />
      ))}
    </div>
  );
}
```

---

## 📊 Actor Types in System

### Agent Actor (AI):

```python
# Characteristics:
- Autonomous execution
- Event-driven (NATS)
- No UI needed
- Fast (seconds to minutes)
- Deterministic retry
- 24/7 availability

# Example:
{
    "actor_type": "agent",
    "actor_id": "agent-dev-001",
    "role": "developer",
    "action": "COMMIT_CODE",
    "automated": true
}
```

### Human Actor:

```python
# Characteristics:
- Manual approval via UI
- Synchronous (user waits for response)
- Requires notification
- Variable time (minutes to days)
- Business judgment required
- Working hours only

# Example:
{
    "actor_type": "human",
    "actor_id": "user-tirso@underpassai.com",
    "role": "po",
    "action": "APPROVE_STORY",
    "automated": false,
    "ui_session_id": "session-123"
}
```

### System Actor (Automatic):

```python
# Characteristics:
- Automatic state transitions
- No approval needed
- Routing logic
- Instant

# Example:
{
    "actor_type": "system",
    "action": "AUTO_ROUTE",
    "from": "arch_approved",
    "to": "pending_qa",
    "automated": true
}
```

---

## 🔄 Updated Flow Examples

### Flow 1: Happy Path (2 Humans, 3 AI Agents)

```
1. 👤 PO (Human via UI):
   - Creates story: "Secure login"
   - Defines acceptance criteria
   - Assigns to sprint

2. 🤖 Developer Agent (AI):
   - Picks task from queue
   - Context: Task + Story + Epic (2-3K tokens)
   - Implements JWT auth
   - Commits code
   - Publishes: COMMIT_CODE

3. 🔄 Workflow Service:
   - Auto-routes to Architect

4. 🤖 Architect Agent (AI):
   - Context: Epic + All Stories + All Tasks (8-12K tokens)
   - Reviews implementation
   - Validates architectural consistency
   - Decision: APPROVE_DESIGN
   - Publishes: APPROVE_DESIGN

5. 🔄 Workflow Service:
   - Auto-routes to QA

6. 🤖 QA Agent (AI):
   - Context: Story + All Tasks + Quality gates (4-6K tokens)
   - Runs integration tests
   - Validates coverage >90%
   - Decision: APPROVE_TESTS
   - Publishes: APPROVE_TESTS

7. 🔄 Workflow Service:
   - State: pending_po_approval
   - Notifies: 📧 Email to PO
   - Notifies: 💬 Slack message
   - Notifies: 🔔 UI notification

8. 👤 PO (Human via UI):
   - Sees notification: "Story ready for approval"
   - Opens UI: https://swe-fleet.underpassai.com/approvals
   - Reviews:
     ✅ Dev implementation (commit abc123)
     ✅ Architect approval
     ✅ QA tests passing (92% coverage)
   - Validates acceptance criteria met
   - Clicks: "✅ Approve Story"
   - UI calls: workflow.ExecuteAction(APPROVE_STORY, actor_type=human)

9. 🔄 Workflow Service:
   - Validates: po.can_perform(APPROVE_STORY) ✅
   - Validates: actor_type=human ✅ (expected for this state)
   - Transition: pending_po_approval → po_approved → done
   - Publishes: workflow.state.changed {state: done}

10. ✅ Story DONE
    - Context Service updates Neo4j
    - Planning Service marks story complete
    - Monitoring dashboard shows metrics
```

---

### Flow 2: Architect Rejects (Human Override - Future)

```
1-6. (Same as Flow 1)

7. 🤖 Junior Architect Agent (AI):
   - Reviews code
   - Decision: APPROVE_DESIGN
   - Confidence: 0.75 (< 0.9 threshold)

8. 🔄 Workflow Service:
   - Sees: confidence < 0.9
   - Decision: Requires senior architect review
   - State: pending_senior_arch_approval
   - Notifies: 📧 Senior Architect (Maria)

9. 👤 Senior Architect (Human via UI):
   - Reviews AI architect's analysis
   - Reviews code directly
   - Decision: "AI missed security issue"
   - Clicks: "❌ Reject Design"
   - Feedback: "Passwords stored in plaintext, use argon2"

10. 🔄 Workflow Service:
    - Transition: pending_senior_arch_approval → arch_rejected → implementing
    - Publishes: workflow.task.assigned {
        role: developer,
        action: REVISE_CODE,
        feedback: "Passwords in plaintext...",
        rejected_by: "human-architect (Maria)"
      }

11. 🤖 Developer Agent:
    - Receives task with human feedback
    - Context includes: "Senior architect (human) feedback: ..."
    - Revises code
    - Re-submits
```

---

## 🎯 Why Human-in-the-Loop Matters

### Critical Decision Points Require Humans:

| Decision | Why Human? | Who? |
|----------|------------|------|
| **Business value** | Judgment, stakeholder input | PO (always human) |
| **Production approval** | Risk assessment, timing | DevOps Lead (future) |
| **Critical architecture** | Experience, trade-offs | Senior Architect (future) |
| **Security review** | Compliance, regulations | Security Lead (future) |

### AI Can Handle:

| Decision | Why AI? | Who? |
|----------|---------|------|
| **Code implementation** | Repetitive, well-defined | Developer agents |
| **Initial code review** | Pattern matching, best practices | Junior Architect agent |
| **Automated testing** | Deterministic, fast | QA agent |
| **Code suggestions** | Context-aware, fast | Developer agents |

---

## 🔐 RBAC Validation for Humans

### Same Domain Model:

```python
# Human PO and AI PO agent use SAME role:
po_role = RoleFactory.create_po()

# Human validation:
if human_user.role == "po":
    role = RoleFactory.create_po()
    if role.can_perform(Action(value=ActionEnum.APPROVE_STORY)):
        # Allow human to approve ✅
        pass

# AI agent validation:
if agent.role.value == RoleEnum.PO:
    if agent.can_execute(Action(value=ActionEnum.APPROVE_STORY)):
        # Allow AI agent to approve ✅
        pass

# ✅ Same RBAC rules, different actor types
```

---

## 🚀 Implementation Phases

### Phase 1: PO Human-in-the-Loop (Current Sprint)

- [x] PO-UI exists (swe-fleet.underpassai.com)
- [ ] Add Approval Queue component
- [ ] Integrate with Workflow Service
- [ ] Notification system (email + Slack)
- [ ] gRPC API: ExecuteAction(actor_type=human)

### Phase 2: Architect Human Override (Future)

- [ ] Add Architect UI section
- [ ] AI confidence threshold
- [ ] Escalation to human if low confidence
- [ ] Senior Architect approval flow

### Phase 3: Full Hybrid Team (Future)

- [ ] DevOps human approval for production
- [ ] Security human review for sensitive changes
- [ ] Configurable: which roles are human vs AI

---

## 📋 Workflow FSM Configuration

### Actor Type Declaration:

```yaml
# config/workflow.fsm.yaml - Enhanced

states:
  - id: implementing
    actor_type: agent  # Always AI
    allowed_roles: [developer]

  - id: pending_arch_review
    actor_type: agent  # AI for now
    allowed_roles: [architect]
    confidence_threshold: 0.9  # If < 0.9, escalate to human
    escalation_state: pending_senior_arch_approval

  - id: pending_senior_arch_approval
    actor_type: human  # Always human
    allowed_roles: [architect]
    ui_enabled: true
    notification_required: true
    ui_path: "/approvals/architecture/{task_id}"

  - id: qa_testing
    actor_type: agent  # Always AI
    allowed_roles: [qa]

  - id: pending_po_approval
    actor_type: human  # Always human
    allowed_roles: [po]
    ui_enabled: true
    notification_required: true
    ui_path: "/approvals/stories/{story_id}"
    notification_channels: [email, slack, ui]
    sla_hours: 48  # Human has 48h to respond
```

---

## 🎯 Benefits of Hybrid Model

### 1. **Best of Both Worlds**

```
AI Agents:
  ✅ Speed (seconds)
  ✅ Consistency
  ✅ 24/7 availability
  ✅ No human bias

Humans:
  ✅ Business judgment
  ✅ Experience-based decisions
  ✅ Stakeholder coordination
  ✅ Accountability
```

### 2. **Gradual Automation**

```
Phase 1: Humans approve everything
Phase 2: AI agents handle routine approvals
Phase 3: Humans only for critical decisions
Phase 4: AI with human oversight (confidence-based)
```

### 3. **Accountability & Trust**

```
Critical decisions (production, business value):
  → Human approval required ✅
  → Audit trail shows: "Approved by Tirso García"
  → Legal/compliance requirements met

Routine decisions (code quality, tests):
  → AI agent approval sufficient ✅
  → Faster iteration
  → Human can override if needed
```

---

## 📊 Updated Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                   HYBRID TEAM ARCHITECTURE                        │
└──────────────────────────────────────────────────────────────────┘

┌─────────────┐
│  PO (HUMAN) │ 👤
│   via UI    │
└──────┬──────┘
       │ APPROVE_STORY / REJECT_STORY
       ↓
┌─────────────────────────────────────────────────────────────────┐
│              Workflow Orchestration Service                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │         State Machine (supports human + agent)             │ │
│  │  - Validates RBAC for both actor types                     │ │
│  │  - Routes to AI agents OR notifies humans                  │ │
│  │  - Tracks actor_type in audit trail                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
       │                              ↑
       │ workflow.task.assigned       │ agent.work.completed
       ↓                              │
┌─────────────┐              ┌────────┴──────┐
│ Orchestrator│              │  VLLMAgent    │ 🤖
│             ├──────────────┤  (AI actors)  │
│  Routes to  │  Executes    │               │
│  AI agents  │  tasks       └───────────────┘
└─────────────┘

┌─────────────┐
│  PO-UI      │ 👤
│  Dashboard  │
│             │
│  Sections:  │
│  • Stories  │
│  • Approvals│ ← NEW: Human approval queue
│  • Metrics  │
└─────────────┘
```

---

## 🎯 Key Design Decisions

### 1. **PO is Always Human** ✅

**Why:**
- Business decisions require human judgment
- Stakeholder coordination
- Legal accountability
- Product vision

**Implementation:**
- PO-UI for approvals
- Workflow notifies PO when ready
- PO executes APPROVE_STORY or REJECT_STORY via UI

### 2. **Architect Can Be Human or AI** (Configurable)

**Default:** AI Architect agent
**Option:** Human senior architect for critical reviews
**Trigger:** Confidence < threshold OR manual escalation

**Implementation:**
- AI architect reviews first
- If confidence low → Escalate to human
- Human can always override AI decision

### 3. **Same RBAC Model for Both**

```python
# ✅ SAME role definition:
po_role = RoleFactory.create_po()

# ✅ SAME action validation:
if not po_role.can_perform(Action(value=ActionEnum.APPROVE_STORY)):
    raise ValueError("PO cannot perform this action")

# ✅ DIFFERENT actor types:
if actor_type == ActorType.HUMAN:
    # Show in UI, send notification
    await ui_service.show_approval_request(...)
else:
    # Route to AI agent
    await orchestrator.assign_to_agent(...)
```

---

## 🎯 Summary

**Vision:** ✅ CLARIFIED

- **PO = HUMANO** (siempre) via UI
- **Senior Architect = HUMANO** (futuro) via UI
- **Dev, QA, Junior Arch = AI AGENTS** (siempre)
- **DevOps Lead = HUMANO** (futuro) for production approvals

**Architecture:**
- ✅ Workflow Service supports BOTH actor types
- ✅ Same RBAC rules apply to humans and AI
- ✅ UI for human approvals
- ✅ NATS events for AI agents
- ✅ Audit trail tracks actor_type

**Next Steps:**
1. Update Workflow Service design with actor_type
2. Design PO-UI approval queue
3. Implement notification system
4. Add human approval flow to E2E tests

---

**Author:** Tirso García
**Date:** 2025-11-04
**Status:** Critical design clarification - Human actors integrated into RBAC model

