# Context Access Pattern - Per-Task vs Per-Step

**Date:** 2025-11-04  
**Decision:** ✅ Per-Task (NOT Per-Step)  
**Status:** Already Implemented Correctly

---

## 🎯 Design Decision

### ✅ Context Access: **PER-TASK** (Una vez al inicio)

```python
# Orchestrator calls Context Service ONCE
context = context_service.GetContext(
    task_id="task-001",
    role="developer",
    phase="BUILD"
)  # Returns 2-4K tokens

# Agent receives context and executes ENTIRE task
result = agent.execute_task(
    task="Implement JWT auth",
    context=context,  # ← Usado para TODA la task
    constraints=ExecutionConstraints(max_operations=100)
)

# Agent ejecuta N steps con el MISMO context
# NO llama a Context Service por cada step ✅
```

### ❌ Alternative (NOT Implemented): Per-Step

```python
# ❌ NO HACER ESTO:
for step in plan.steps:
    # Llamar Context Service por cada step
    step_context = context_service.GetContext(
        task_id=task_id,
        step_id=step.id  # ← Too many calls
    )
    result = agent.execute_step(step, step_context)
```

---

## 🏗️ Current Architecture (Correct)

### Call Flow:

```
┌─────────────────┐
│  Orchestrator   │
└────────┬────────┘
         │
         │ 1. Get context (ONCE per task)
         ├──────────────────────────────────────┐
         │                                      ▼
         │                            ┌──────────────────┐
         │                            │ Context Service  │
         │                            │ GetContext()     │
         │                            │   task_id        │
         │                            │   role           │
         │                            │   phase          │
         │                            └─────────┬────────┘
         │                                      │
         │ 2. Receive smart context             │
         │    (2-4K tokens)                     │
         │◄─────────────────────────────────────┘
         │
         │ 3. Create agent + execute task
         ├──────────────────────────────────────┐
         │                                      ▼
         │                            ┌──────────────────┐
         │                            │   VLLMAgent      │
         │                            │   execute_task() │
         │                            │     ├─ task      │
         │                            │     └─ context ◄─┤─── Same context
         │                            └─────────┬────────┘    for ALL steps
         │                                      │
         │                                      │ 4. Generate plan with context
         │                                      ├─► GeneratePlanUseCase
         │                                      │      (uses context)
         │                                      │
         │                                      │ 5. Execute steps (N iterations)
         │                                      ├─► Step 1: files.read()
         │                                      ├─► Step 2: files.write()
         │                                      ├─► Step 3: tests.pytest()
         │                                      ├─► Step 4: git.commit()
         │                                      │
         │                                      │ All steps use SAME context ✅
         │                                      │
         │ 6. Return result                     │
         │◄─────────────────────────────────────┘
         │
         ▼
    Task Complete
```

---

## 📊 Evidence from Code

### VLLMAgent.execute_task() Signature:

```python
# core/agents_and_tools/agents/vllm_agent.py:356-420

async def execute_task(
    self,
    task: str,
    constraints: ExecutionConstraints,
    context: str = "",  # ← Recibido UNA VEZ como parámetro
) -> AgentResult:
    """
    Execute a task using LLM + tools with smart context.
    
    **Key Innovation**: This agent receives SMART CONTEXT from Context Service:
    - Pre-filtered by role, phase, story
    - Only relevant decisions, code, history
    - 2-4K tokens, NOT 1M tokens
    
    Args:
        task: Atomic, clear task description
        context: SMART context from Context Service (2-4K tokens) ← ONCE
    """
```

### GeneratePlanUseCase Uses Same Context:

```python
# generate_plan_usecase.py:63-92

async def execute(
    self,
    task: str,
    context: str,  # ← El MISMO context que recibió execute_task()
    role: Role,
    available_tools: AgentCapabilities,
    constraints: ExecutionConstraints | None = None,
) -> PlanDTO:
    # Build user prompt
    user_prompt = user_template.format(
        task=task,
        context=context  # ← Usado aquí para generar plan
    )
    
    # LLM genera plan basado en context
    response = await self.llm_client.generate(system_prompt, user_prompt)
```

### Iterative Mode Also Uses Same Context:

```python
# generate_next_action_usecase.py:63-113

async def execute(
    self,
    task: str,
    context: str,  # ← El MISMO context original
    observation_history: ObservationHistories,  # ← Se actualiza con observaciones
    available_tools: AgentCapabilities,
) -> NextActionDTO:
    # Build user prompt
    user_prompt = user_template.format(
        task=task,
        context=context,  # ← Context original + observation history
        observation_history=observation_history_str
    )
```

---

## 🔄 How Context is Used Across Steps

### Context Composition:

```
┌────────────────────────────────────────────────────────────┐
│         CONTEXT (obtained ONCE per task)                   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  STATIC PART (from Context Service):                       │
│  ├─ Story: US-123 - Add JWT auth                          │
│  ├─ Decisions: [Decision-042, Decision-051]               │
│  ├─ Code Structure: src/auth/middleware.py exists         │
│  └─ Dependencies: pyjwt==2.8.0 installed                   │
│                                                            │
│  DYNAMIC PART (accumulated during execution):              │
│  └─ Observation History (if iterative mode):               │
│      ├─ Step 1: Read middleware.py → Found simple auth    │
│      ├─ Step 2: Updated middleware.py → Added JWT         │
│      └─ Step 3: Ran tests → All passing                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
           │
           │ Used by ALL steps in the plan
           ├──► Step 1 planning
           ├──► Step 2 planning (if iterative)
           ├──► Step 3 planning (if iterative)
           └──► ...
```

### Static Planning (Default):

```python
# 1. Get context ONCE
context = context_service.GetContext(task_id, role, phase)

# 2. Generate FULL plan with context
plan = await generate_plan_usecase.execute(
    task=task,
    context=context,  # ← Used once to generate ALL steps
    role=role,
    available_tools=tools
)

# 3. Execute ALL steps (no more context calls)
for step in plan.steps:
    result = await execute_step(step)  # ← No context parameter
    # Uses tools to read files, not context service
```

### Iterative Planning (ReAct):

```python
# 1. Get context ONCE
context = context_service.GetContext(task_id, role, phase)

# 2. Iterative loop
observation_history = ObservationHistories()
while not done:
    # Generate NEXT action (uses original context + observations)
    next_action = await generate_next_action_usecase.execute(
        task=task,
        context=context,  # ← Original context (static)
        observation_history=observation_history,  # ← Accumulated observations (dynamic)
        available_tools=tools
    )
    
    # Execute step
    result = await execute_step(next_action.step)
    
    # Add observation to history
    observation_history.add(
        step=next_action.step,
        result=result,
        reasoning=next_action.reasoning
    )
    # ← Context Service NOT called again ✅
```

---

## ♻️ Retry Behavior with Per-Task Context

### When Task Fails:

```python
# Task fails at any point → Complete retry

# Workflow Orchestration Service:
async def handle_task_failure(task_id: str, error: str):
    # 1. Reset workflow state
    reset_state = WorkflowState(
        task_id=task_id,
        current_state="todo",  # ✅ Back to start
        ...
    )
    
    # 2. Publish retry event
    await publish_task_assigned(
        task_id=task_id,
        assigned_to_role="developer",
        required_action="IMPLEMENT_FEATURE"
    )

# Orchestrator receives retry event:
async def handle_task_assignment(task_id: str, role: str):
    # 1. Get FRESH context (may have changed since last attempt)
    context = context_service.GetContext(
        task_id=task_id,
        role=role,
        # Context may include info from failed attempt:
        include_previous_attempts=True
    )
    
    # 2. Create NEW agent
    agent = VLLMAgentFactory.create(config)
    
    # 3. Execute task from beginning with FRESH context
    result = await agent.execute_task(
        task=task,
        context=context  # ← Fresh context, may include lessons from failure
    )
```

---

## 💡 Why Per-Task Context Makes Sense

### Rationale:

#### 1. **Smart Context is Already Precise**
```python
# Context Service ya filtra:
context = """
Relevant Decisions: 2 (not 100)
Relevant Code: 3 files (not entire repo)
Dependencies: pyjwt installed
Test Coverage: auth module 60%
"""
# ✅ 2-4K tokens, not 1M
# ✅ Agent usa tools para leer files específicos si necesita más
```

#### 2. **Tasks are Atomic**
```
Task: "Add JWT authentication to login endpoint"

✅ Atomic scope - single feature
✅ Clear deliverable - working JWT auth
✅ Self-contained - doesn't depend on other tasks mid-execution
```

#### 3. **Tools Provide Dynamic Context**
```python
# Agent usa tools para obtener info específica:
step_1 = {"tool": "files", "operation": "read_file", "params": {"path": "src/auth.py"}}
# ← Lee contenido exacto del archivo

step_2 = {"tool": "git", "operation": "log", "params": {"path": "src/auth.py"}}
# ← Ve historial de cambios

# NO necesita Context Service por cada step ✅
```

#### 4. **Simplicity**
```python
# Per-task: 1 call to Context Service
context = get_context_once()  # ✅ Simple

# Per-step: N calls to Context Service
for step in steps:
    context = get_context(step)  # ❌ Complex, expensive
```

---

## 🔄 Context Updates Between Workflow Phases

### Context DOES Update Between Workflow Transitions:

```python
# Developer completes → Architect reviews
# Context Service provides DIFFERENT context for Architect:

# Developer context:
dev_context = context_service.GetContext(
    task_id="task-001",
    role="developer",
    workflow_state="implementing"
)
# Returns: {story, decisions, code_structure, dependencies}

# After Developer commits → Workflow transitions to "pending_arch_review"

# Architect context (DIFFERENT):
arch_context = context_service.GetContext(
    task_id="task-001",
    role="architect",
    workflow_state="pending_arch_review"
)
# Returns: {
#   story, decisions,
#   work_to_review: {
#     commit_sha: "abc123",
#     files_changed: ["src/auth.py"],
#     developer_reasoning: "..."
#   }
# }
```

**Key Point:** Context updates between **workflow phases** (Dev → Arch → QA), not between **steps within a phase**.

---

## 📊 Summary

| Granularity | Context Calls | When | Why |
|-------------|---------------|------|-----|
| **Per-Task** | 1 call | ✅ At task start | Simple, sufficient |
| **Per-Workflow-Phase** | 1 call per phase | ✅ When role changes | Context for new role |
| **Per-Step** | N calls | ❌ NOT done | Unnecessary, expensive |

---

## 🎯 Conclusion

**Your Understanding is Correct:** ✅

- Context se obtiene **UNA VEZ por task** (no por step)
- Si task falla y retry → Context se obtiene de nuevo (fresh)
- Context puede actualizarse entre **workflow phases** (Dev → Arch → QA)
- Dentro de una phase, agent usa el MISMO context para todos los steps

**Benefits:**
- ✅ Simple (1 call per task)
- ✅ Efficient (no multiple context calls)
- ✅ Consistent (same context across steps)
- ✅ Smart context + tools = suficiente información

**Consistency with Retry Strategy:**
- Retry completo → Fresh context call ✅
- No step checkpoints → No step-level context ✅
- Workflow-level state → Workflow-level context ✅

---

**Decision:** ✅ **CONFIRMED** - Per-task context access is the correct design.

**Author:** AI Assistant + Tirso García  
**Date:** 2025-11-04

