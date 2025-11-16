# SWE AI Fleet - Component Interactions & Communication Flows

**Last Updated**: October 14, 2025
**Status**: 🟢 Active - Reflects current implementation

---

## 🎯 Executive Summary

This document describes **how components communicate** in the SWE AI Fleet system, including:
- Synchronous communication (gRPC)
- Asynchronous messaging (NATS JetStream)
- Distributed execution (Ray)
- Tool execution within workspace containers

---

## 📊 System Components

### Deployed Services

| Service | Port | Language | Status | Purpose |
|---------|------|----------|--------|---------|
| **Planning** | 50051 | Go | ✅ Running | FSM-based story lifecycle management |
| **StoryCoach** | 50052 | Go | ✅ Running | Story quality scoring (INVEST) |
| **Workspace** | 50053 | Go | ✅ Running | Workspace result validation & scoring |
| **Context** | 50054 | Python | ✅ Running | Context hydration & management |
| **Orchestrator** | 50055 | Python | ✅ Running | Multi-agent deliberation & coordination |
| **UI (PO React)** | 80 | React | ✅ Running | Product Owner interface |
| **Gateway** | 8080 | Go | 🚧 Planned | REST API + SSE bridge (future) |

### Infrastructure

| Component | Port | Purpose |
|-----------|------|---------|
| **NATS JetStream** | 4222 | Async event bus |
| **Redis/Valkey** | 6379 | Short-term cache & planning data |
| **Neo4j** | 7687 | Decision graph & long-term memory |
| **Ray Cluster** | 10001 | Distributed agent execution |
| **vLLM Server** | 8000 | LLM inference engine |

---

## 🔄 Communication Patterns

### 1. **Synchronous Communication (gRPC)**

**When**: Real-time operations, request-response needed immediately

**Pattern**:
```
Client → gRPC Call → Server → Response → Client
        (protobuf)            (protobuf)
```

**Examples**:

#### Gateway → Orchestrator
```python
# Gateway calls Orchestrator
orchestrator_stub = OrchestratorServiceStub(channel)
response = orchestrator_stub.Orchestrate(
    OrchestrateRequest(
        task_id="task-001",
        role="DEV",
        task_description="Add hello_world() function",
        constraints=TaskConstraints(...)
    )
)
# Returns: winner, candidates, duration_ms
```

#### Orchestrator → Context
```python
# Orchestrator gets hydrated context
context_stub = ContextServiceStub(channel)
response = context_stub.GetContext(
    GetContextRequest(
        story_id="US-123",
        role="DEV",
        phase="BUILD",
        token_budget=4096
    )
)
# Returns: context text, token_count, scopes
```

**Service Communication Map**:
```
Gateway → Orchestrator:50055
Gateway → Context:50054
Gateway → Planning:50051
Gateway → StoryCoach:50052

Orchestrator → Context:50054
Orchestrator → Planning:50051 (future)

Context → Neo4j:7687
Context → Redis:6379
```

---

### 2. **Asynchronous Messaging (NATS JetStream)**

**When**: Event-driven workflows, decoupled communication, guaranteed delivery

**Pattern**:
```
Publisher → NATS Stream → Durable Consumer → Handler
           (fire-forget)    (queue group)     (async)
```

**Streams Configured**:

| Stream | Subjects | Retention | Purpose |
|--------|----------|-----------|---------|
| **PLANNING_EVENTS** | `planning.>` | 30d | Story/plan lifecycle events |
| **CONTEXT** | `context.>` | 7d | Context updates & decisions |
| **ORCHESTRATOR_EVENTS** | `orchestration.>` | 7d | Deliberation & task dispatch |
| **AGENT_RESULTS** | `agent.results.>` | 1h | Agent execution results (Ray) |

**Key Subjects**:
```
planning.story.transitioned      # Story moved to new phase
planning.plan.approved           # Plan approved by PO

context.updated                  # Context changed (decisions, etc)

orchestration.deliberation.completed    # Agents deliberated, decision made
orchestration.task.dispatched          # Task sent to agent

agent.results.{task_id}          # Agent completed task (from Ray)
```

---

### 3. **Distributed Execution (Ray)**

**When**: Parallel agent execution, GPU workloads, async deliberation

**Pattern**:
```
Orchestrator → Ray.remote() → Ray Cluster → N Parallel Jobs → NATS Results
```

**Flow**:

```python
# 1. Orchestrator submits Ray jobs
class DeliberateAsync:
    def execute(self, task_id, task, role, num_agents=3):
        # Create N Ray actors
        for i in range(num_agents):
            agent_actor = VLLMAgentJob.remote(
                agent_id=f"agent-{role}-{i}",
                vllm_url="http://vllm-server:8000",
                model="Qwen/Qwen3-0.6B",
                nats_url="nats://nats:4222"
            )

            # Submit job (non-blocking)
            job_ref = agent_actor.run.remote(
                task_id=task_id,
                task_description=task,
                constraints=constraints
            )

        # Return immediately (don't wait)
        return {"task_id": task_id, "status": "PENDING"}

# 2. Ray executes in parallel
Ray Cluster:
  ├─→ Agent 1 → vLLM:8000 → generate() → NATS publish
  ├─→ Agent 2 → vLLM:8000 → generate() → NATS publish
  └─→ Agent 3 → vLLM:8000 → generate() → NATS publish

# 3. Results collected via NATS
DeliberationResultCollector (consumer):
    - Subscribes to: agent.results.{task_id}
    - Collects all N responses
    - Ranks by quality
    - Stores in memory cache

# 4. Client retrieves result
orchestrator_stub.GetDeliberationResult(task_id)
# Returns: status, winner, candidates, duration
```

**Actual Implementation**:
- File: `src/swe_ai_fleet/orchestrator/usecases/deliberate_async_usecase.py`
- Ray Job: `src/swe_ai_fleet/orchestrator/ray_jobs/vllm_agent_job.py`
- Collector: `services/orchestrator/consumers/deliberation_collector.py`

---

## 🔄 Complete Task Execution Flow

### Scenario: "Add hello_world() function to utils.py"

#### **Current Flow (Text Generation Only)**

```
Step 1: Orchestrator receives task
├─→ gRPC: Orchestrator.Orchestrate(role="DEV", task="Add hello_world()")
│
Step 2: Get context for agent
├─→ gRPC: Context.GetContext(story_id, role="DEV", phase="BUILD")
├─→ Returns: hydrated context with story, decisions, subtasks
│
Step 3: Execute deliberation (Ray-based)
├─→ DeliberateAsync.execute(task_id, task, role, num_agents=3)
├─→ Creates 3 Ray actors: VLLMAgentJob.remote()
├─→ Each calls vLLM API: "Generate solution for: {task}"
├─→ Each publishes to NATS: agent.results.{task_id}
│
Step 4: Collect results
├─→ DeliberationResultCollector subscribes to agent.results.{task_id}
├─→ Waits for all 3 responses (with 5min timeout)
├─→ Ranks by quality score
├─→ Stores: {status: "COMPLETED", winner: best_response, candidates: []}
│
Step 5: Publish completion
├─→ NATS: orchestration.deliberation.completed
├─→ {story_id, task_id, decisions: [...]}
│
Step 6: Update context
├─→ Context Service consumes event
├─→ Updates Neo4j with decisions
├─→ NATS: context.updated
│
Result: TEXT proposal generated, NO actual code changes executed ❌
```

#### **Target Flow (With Tools - This Session's Goal)**

```
Step 1: Orchestrator receives task
├─→ gRPC: Orchestrator.ExecuteTaskWithTools(role="DEV", task="Add hello_world()")
│
Step 2: Create workspace container
├─→ K8s Job created with:
│   ├─→ Git clone of repository
│   ├─→ Tools initialized (GitTool, FileTool, TestTool)
│   └─→ Agent with tool access
│
Step 3: Agent executes task WITH tools
├─→ ToolEnabledAgent.execute(task)
├─→ Step 3a: LLM plans actions
│   └─→ "1. Read file, 2. Add function, 3. Test, 4. Commit"
├─→ Step 3b: Execute plan using tools
│   ├─→ FileTool.read_file("src/utils.py")
│   ├─→ FileTool.append_file("src/utils.py", new_function)
│   ├─→ TestTool.pytest() → verify no regressions
│   ├─→ GitTool.add(["src/utils.py"])
│   └─→ GitTool.commit("feat: add hello_world()")
├─→ Step 3c: Verify completion
│   └─→ Function exists, tests pass, commit created ✅
│
Step 4: Publish execution result
├─→ NATS: agent.results.{task_id}
├─→ {
│     task_id: "task-001",
│     status: "completed",
│     operations: [read, append, pytest, add, commit],
│     audit_trail: [...],
│     artifacts: {
│       commit_sha: "abc123",
│       test_results: "5 passed in 0.3s",
│       files_changed: ["src/utils.py"]
│     }
│   }
│
Step 5: Update context with real changes
├─→ Context Service consumes event
├─→ Updates Neo4j: commit info, test results, files changed
├─→ NATS: context.updated
│
Result: ACTUAL CODE CHANGES made and committed ✅
```

---

## 📡 NATS Event Streams (Detailed)

### Stream: PLANNING_EVENTS

**Subjects**:
```
planning.story.created          # New story created by PO
planning.story.transitioned     # Story moved between phases
planning.plan.approved          # Plan approved, ready for execution
planning.task.created           # Subtask derived from plan
planning.task.assigned          # Task assigned to role
planning.task.completed         # Task marked complete
```

**Publishers**: Planning Service
**Consumers**:
- Context Service (context-planning-events) - Cache invalidation
- Orchestrator Service (orchestrator-planning-events) - Task derivation

**Example Event**:
```json
{
  "subject": "planning.plan.approved",
  "data": {
    "event_type": "PLAN_APPROVED",
    "story_id": "US-123",
    "plan_id": "plan-v2",
    "roles": ["DEV", "QA", "DEVOPS"],
    "subtasks_count": 12,
    "approved_by": "tirso@underpassai.com",
    "timestamp": "2025-10-14T10:30:00Z"
  }
}
```

---

### Stream: ORCHESTRATOR_EVENTS

**Subjects**:
```
orchestration.deliberation.started     # Deliberation begun
orchestration.deliberation.completed   # Agents deliberated, winner selected
orchestration.task.dispatched          # Task sent to agent for execution
orchestration.council.created          # New council formed for role
```

**Publishers**: Orchestrator Service
**Consumers**:
- Context Service (context-orchestration-events) - Decision recording
- Planning Service (planning-orchestration-events) - Task status updates

**Example Event**:
```json
{
  "subject": "orchestration.deliberation.completed",
  "data": {
    "event_type": "DELIBERATION_COMPLETED",
    "story_id": "US-123",
    "task_id": "task-001",
    "role": "DEV",
    "decisions": [
      {
        "id": "dec-001",
        "type": "TECHNICAL_CHOICE",
        "rationale": "Use FastAPI for better async support",
        "alternatives": ["Flask", "Django"],
        "decided_by": "agent-dev-001",
        "affected_subtask": "subtask-api-001"
      }
    ],
    "winner_agent_id": "agent-dev-001",
    "duration_ms": 3500,
    "timestamp": "2025-10-14T10:35:00Z"
  }
}
```

---

### Stream: CONTEXT

**Subjects**:
```
context.updated                 # Context changed (decisions, subtasks, etc)
context.decision.added          # New decision recorded
context.milestone.reached       # Milestone achieved
```

**Publishers**: Context Service
**Consumers**:
- Orchestrator Service (orchestrator-context-updates) - Context awareness
- Gateway Service (gateway-all-events) - SSE to frontend

**Example Event**:
```json
{
  "subject": "context.updated",
  "data": {
    "event_type": "CONTEXT_UPDATED",
    "story_id": "US-123",
    "version": 5,
    "changes": ["decisions", "subtasks"],
    "affected_roles": ["DEV", "QA"],
    "timestamp": "2025-10-14T10:36:00Z"
  }
}
```

---

### Stream: AGENT_RESULTS

**Subjects**:
```
agent.results.{task_id}         # Agent completed task (from Ray jobs)
```

**Publishers**: Ray VLLMAgentJob actors
**Consumers**:
- DeliberationResultCollector - Aggregates multi-agent responses

**Example Event**:
```json
{
  "subject": "agent.results.task-001",
  "data": {
    "agent_id": "agent-dev-001",
    "task_id": "task-001",
    "status": "completed",
    "proposal": {
      "content": "Use FastAPI with async handlers...",
      "confidence": 0.95
    },
    "metadata": {
      "vllm_model": "Qwen/Qwen3-0.6B",
      "tokens_used": 1024,
      "latency_ms": 850
    },
    "timestamp": "2025-10-14T10:34:30Z"
  }
}
```

---

## 🌊 Complete Workflow Examples

### Workflow 1: Story Creation → Deliberation (Synchronous)

```
┌─────────┐
│ User/PO │
└────┬────┘
     │ UI Action: Create Story
     ↓
┌─────────────┐
│  UI (React) │
└──────┬──────┘
       │ REST: POST /api/stories
       ↓
┌─────────────┐
│  Gateway    │ (Future - TBD)
└──────┬──────┘
       │ gRPC: Planning.CreateStory()
       ↓
┌──────────────┐
│  Planning    │
│   :50051     │
└──────┬───────┘
       │ Compute DoR score
       │ NATS: planning.story.created
       ↓
┌─────────────────┐
│ Context Service │ (Consumer)
│   :50054        │
└──────┬──────────┘
       │ Cache story metadata
       │ Ready for context queries
       ↓
     [Story ready for planning]
```

---

### Workflow 2: Plan Approved → Task Execution (Asynchronous)

```
┌──────────────┐
│ Planning     │
│  :50051      │
└──────┬───────┘
       │ NATS: planning.plan.approved
       │ {story_id, plan_id, roles: [DEV, QA]}
       ↓
┌───────────────────────────┐
│ OrchestratorPlanningConsumer │
│ (orchestrator-planning-events)│
└──────┬────────────────────┘
       │ [TODO] derive_subtasks(plan_id)
       │ → List[Task]
       ↓
┌──────────────┐
│ TaskQueue    │ [TODO: Implement]
│ (Redis)      │
└──────┬───────┘
       │ enqueue(tasks)
       ↓
┌──────────────┐
│ Task Dispatcher │ [TODO]
└──────┬───────┘
       │ For each task:
       │   1. Get context
       │   2. Trigger deliberation
       ↓
┌─────────────────┐
│ DeliberateAsync │
│ (Ray-based)     │
└──────┬──────────┘
       │ Creates N Ray jobs
       ↓
┌──────────────┐     ┌──────────────┐
│ Ray Cluster  │────→│ vLLM Server  │
│              │←────│   :8000      │
└──────┬───────┘     └──────────────┘
       │ N agents generate proposals
       │ Each publishes to NATS
       ↓
┌─────────────────────────┐
│ DeliberationResultCollector │
│ (NATS consumer)         │
└──────┬──────────────────┘
       │ Collects N responses
       │ Ranks by quality
       │ NATS: orchestration.deliberation.completed
       ↓
┌──────────────────────┐
│ OrchestrationEventsConsumer │
│ (Context Service)    │
└──────┬───────────────┘
       │ ProjectDecisionUseCase.execute()
       │ Updates Neo4j
       │ NATS: context.updated
       ↓
     [Task complete]
```

**Status**: 🟡 Partially implemented
- ✅ Ray job submission works
- ✅ NATS event publishing works
- ✅ Context updates work
- ❌ Task derivation not implemented
- ❌ TaskQueue not implemented

---

### Workflow 3: Planning Agent Analyzes Codebase with Tools

```
┌──────────────┐
│ Planning     │
│  :50051      │
└──────┬───────┘
       │ NATS: planning.story.created
       │ {story_id: "US-123", title: "Add authentication"}
       ↓
┌──────────────────────┐
│ Architect Agent      │
│ (with tools)         │
└──────┬───────────────┘
       │ Task: "Analyze codebase for authentication implementation"
       │
       │ Step 1: Clone & analyze structure
       ├─→ GitTool.clone(repo_url)
       ├─→ FileTool.list_files("src/", recursive=True)
       │   Result: Understand project structure
       │
       │ Step 2: Find existing auth code
       ├─→ FileTool.search_in_files("auth|login|session", path="src/")
       │   Result: Found auth patterns in 5 files
       │
       │ Step 3: Read existing implementation
       ├─→ FileTool.read_file("src/auth/middleware.py")
       ├─→ FileTool.read_file("src/models/user.py")
       │   Result: Understand current auth approach
       │
       │ Step 4: Check test coverage
       ├─→ TestTool.pytest(path="tests/auth/", coverage=True)
       │   Result: 60% coverage on auth module
       │
       │ Step 5: Analyze database schema
       ├─→ DatabaseTool.postgresql_query(
       │       "SELECT * FROM information_schema.tables WHERE table_name LIKE '%user%'"
       │   )
       │   Result: 3 user-related tables found
       │
       │ Step 6: Test existing API
       ├─→ HttpTool.get("http://localhost:8080/api/auth/login")
       │   Result: 401 when not authenticated (expected)
       │
       │ Step 7: Check git history
       ├─→ GitTool.log(max_count=50)
       ├─→ GitTool.diff("HEAD~5", "HEAD")
       │   Result: Recent auth changes by team
       ↓
┌──────────────────────┐
│ Generated Plan       │
└──────┬───────────────┘
       │ Based on ACTUAL codebase analysis:
       │
       │ Subtasks derived:
       │ 1. [DEV] Extend User model with 2FA fields
       │    Dependencies: Current User model uses SQLAlchemy
       │    Files: src/models/user.py, migrations/
       │
       │ 2. [DEV] Implement 2FA token generation
       │    Dependencies: Found pyotp in requirements.txt
       │    Files: src/auth/two_factor.py (new)
       │
       │ 3. [QA] Add 2FA tests (coverage currently 60%)
       │    Dependencies: Existing test pattern in tests/auth/
       │    Files: tests/auth/test_two_factor.py (new)
       │
       │ 4. [DEVOPS] Update Docker image with pyotp
       │    Dependencies: Dockerfile exists at root
       │    Files: Dockerfile, requirements.txt
       ↓
┌──────────────┐
│ Planning     │
│  :50051      │
└──────┬───────┘
       │ NATS: planning.plan.approved
       │ {story_id, plan_id, subtasks: 4}
       ↓
     [Execution phase begins]
```

**Key Benefit**: Plan is based on **ACTUAL** codebase state, not assumptions!

---

### Workflow 4: Agent Executes Task with Tools (Implementation Phase)

```
┌──────────────┐
│ Orchestrator │
└──────┬───────┘
       │ gRPC: ExecuteTaskWithTools(role, task)
       ↓
┌────────────────────┐
│ Workspace Runner   │ [TODO: Implement]
└──────┬─────────────┘
       │ Creates K8s Job:
       │   - Git clone repo
       │   - Initialize tools
       │   - Execute agent
       ↓
┌──────────────────────────────┐
│ Agent Workspace Container     │
│ (K8s Job Pod)                │
├──────────────────────────────┤
│ /workspace/                   │
│   ├─→ GitTool                │
│   ├─→ FileTool               │
│   ├─→ TestTool               │
│   ├─→ DockerTool             │
│   ├─→ HttpTool               │
│   └─→ DatabaseTool           │
└──────┬─────────────────────┘
       │
       │ Agent workflow:
       │ 1. Read file (FileTool)
       │ 2. Modify code (FileTool)
       │ 3. Run tests (TestTool)
       │ 4. Commit (GitTool)
       │
       │ Audit trail:
       │   ├─→ File: /workspace/.task/audit.log
       │   ├─→ Redis Stream: tool_audit
       │   └─→ Neo4j: :ToolExecution nodes
       ↓
┌──────────────┐
│ NATS         │
└──────┬───────┘
       │ agent.results.{task_id}
       │ {
       │   status: "completed",
       │   operations: [read, append, pytest, commit],
       │   artifacts: {
       │     commit_sha: "abc123",
       │     files_changed: ["src/utils.py"],
       │     tests_passed: true
       │   }
       │ }
       ↓
┌──────────────────────┐
│ Context Service      │
│ (Consumer)           │
└──────┬───────────────┘
       │ Updates Neo4j:
       │   - Commit info
       │   - Test results
       │   - Tool usage
       │ NATS: context.updated
       ↓
     [Task complete with actual changes] ✅
```

**Status**: 🟡 Partially implemented
- ✅ Tools implemented (git, file, test, docker, http, db)
- ✅ E2E test simulates agent workflow
- ❌ Workspace Runner not implemented
- ❌ K8s Job template not integrated
- ❌ Tool-enabled agent not integrated with Ray

---

## 🏗️ Service Dependencies

### Orchestrator Service Dependencies

**Outbound (calls)**:
- Context Service (gRPC) - For GetContext, UpdateContext
- Ray Cluster (Ray API) - For distributed agent execution
- NATS (publish) - For orchestration.* events

**Inbound (called by)**:
- Gateway (gRPC) - For Orchestrate, Deliberate
- NATS consumers - For planning.plan.approved, agent.results.*

**Storage**:
- None directly (stateless) - All state in Context/Planning services

### Context Service Dependencies

**Outbound (calls)**:
- Neo4j (bolt) - For decision graph queries/commands
- Redis/Valkey (redis://) - For planning data cache
- NATS (publish) - For context.* events

**Inbound (called by)**:
- Orchestrator (gRPC) - For GetContext, UpdateContext, RehydrateSession
- NATS consumers - For planning.*, orchestration.* events

**Storage**:
- Neo4j - Decision graph, cases, subtasks, plans
- Redis/Valkey - Cached planning data, timeline

---

## 🔧 Tool Execution Architecture

### Tools Available in Workspace

| Tool | Operations | Purpose | Planning Phase | Implementation Phase |
|------|-----------|---------|----------------|---------------------|
| **GitTool** | 9 ops | clone, status, add, commit, push, pull, checkout, branch, diff, log | ✅ log, diff, status | ✅ add, commit, push |
| **FileTool** | 10 ops | read, write, append, search, list, edit, delete, mkdir, info, diff | ✅ read, search, list, info, diff | ✅ write, edit, append |
| **TestTool** | 5 frameworks | pytest, go test, npm test, cargo test, make test | ✅ Run existing tests | ✅ Run after changes |
| **DockerTool** | 7 ops | build, run, exec, ps, logs, stop, rm | ✅ ps, logs (analyze) | ✅ build, run (deploy) |
| **HttpTool** | 6 methods | GET, POST, PUT, PATCH, DELETE, HEAD | ✅ GET (analyze APIs) | ✅ POST/PUT (test APIs) |
| **DatabaseTool** | 3 DBs | PostgreSQL, Redis, Neo4j queries | ✅ Read schema, query data | ✅ Migrations, updates |

### Tool Usage by Phase

#### 🔍 **Planning/Analysis Phase** - Tools for Understanding

**Use Cases**:
1. **Codebase Analysis**
   ```python
   # Agent reads existing code to understand patterns
   files = FileTool(workspace)

   # Find all Python files
   py_files = files.list_files("src/", recursive=True, pattern="*.py")

   # Read key files
   for file in important_files:
       content = files.read_file(file)
       # Agent analyzes architecture, patterns, conventions

   # Search for patterns
   results = files.search_in_files("class.*Service", path="src/")
   # Agent understands service structure
   ```

2. **Git History Analysis**
   ```python
   # Understand recent changes
   git = GitTool(workspace)

   # Recent commits
   history = git.log(max_count=50)
   # Agent sees what's been worked on

   # See current branch strategy
   branches = git.branch(list_all=True)

   # Check for uncommitted changes
   status = git.status()
   ```

3. **Test Coverage Analysis**
   ```python
   # Run existing tests to understand coverage
   tests = TestTool(workspace)

   result = tests.pytest(coverage=True, junit_xml="/tmp/results.xml")
   # Agent knows what's tested, what needs tests
   ```

4. **Database Schema Analysis**
   ```python
   # Understand current data model
   db = DatabaseTool()

   # Get PostgreSQL schema
   schema = db.postgresql_query(
       conn_str,
       "SELECT table_name, column_name, data_type FROM information_schema.columns"
   )

   # Check Neo4j graph structure
   nodes = db.neo4j_query(uri, user, pass,
       "MATCH (n) RETURN DISTINCT labels(n), count(n)"
   )
   ```

5. **API Endpoint Analysis**
   ```python
   # Test existing API to understand behavior
   http = HttpTool(allow_localhost=True)

   # Check health endpoint
   health = http.get("http://localhost:8080/health")

   # Get API spec
   spec = http.get("http://localhost:8080/api/openapi.json")
   # Agent understands API structure
   ```

6. **Docker Container Analysis**
   ```python
   # Check running services
   docker = DockerTool(workspace)

   containers = docker.ps(all_containers=True)
   # Agent sees what's deployed

   # Check service logs
   logs = docker.logs("service-name", tail=100)
   # Agent understands errors, warnings
   ```

**Planning Agent Workflow**:
```
1. GitTool.clone() → Get codebase
2. FileTool.list_files() → Understand structure
3. FileTool.search_in_files() → Find relevant code
4. FileTool.read_file() → Analyze implementation
5. TestTool.pytest() → Check test coverage
6. DatabaseTool.query() → Understand data model
7. HttpTool.get() → Test API endpoints

→ Agent creates INFORMED plan based on ACTUAL codebase state
```

#### ⚙️ **Implementation Phase** - Tools for Execution

**Use Cases**:
1. **Code Changes**
   ```python
   # Implement planned changes
   files.write_file("src/new_module.py", generated_code)
   files.edit_file("src/main.py", search="old", replace="new")
   ```

2. **Test Execution**
   ```python
   # Verify changes don't break existing functionality
   result = tests.pytest(markers="not e2e")
   assert result.success
   ```

3. **Version Control**
   ```python
   # Commit changes
   git.add(["src/new_module.py", "src/main.py"])
   git.commit("feat: implement new feature")
   git.push("origin", "feature/new-feature")
   ```

4. **Deployment**
   ```python
   # Build and test container
   docker.build(tag="myapp:v2.0")
   docker.run(image="myapp:v2.0", ports={"8080": "8080"})

   # Test deployment
   http.get("http://localhost:8080/health")
   ```

**Implementation Agent Workflow**:
```
1. FileTool.read_file() → Understand current code
2. FileTool.write_file() → Make changes
3. TestTool.pytest() → Verify changes
4. FileTool.diff_files() → Review changes
5. GitTool.commit() → Save changes
6. DockerTool.build() → Build image
7. HttpTool.post() → Test API

→ Agent EXECUTES plan and VERIFIES results
```

#### 🎭 **Tool Usage by Agent Role**

Different agent roles use tools for different purposes:

##### **ARCHITECT Agent** - Analysis & Design
```python
# Analyzes codebase to create informed architecture decisions
tools_used = [
    "FileTool.list_files()",      # Understand structure
    "FileTool.search_in_files()", # Find patterns
    "FileTool.read_file()",       # Read key files
    "GitTool.log()",              # See evolution
    "DatabaseTool.query()",       # Analyze schema
    "HttpTool.get()",             # Test APIs
]

workflow = [
    "1. Analyze current architecture",
    "2. Identify patterns and anti-patterns",
    "3. Design solution aligned with existing code",
    "4. Generate detailed plan with file-level changes"
]
```

##### **DEV Agent** - Implementation
```python
# Implements features and fixes bugs
tools_used = [
    "FileTool.read_file()",      # Understand context
    "FileTool.write_file()",     # Create new code
    "FileTool.edit_file()",      # Modify existing code
    "TestTool.pytest()",         # Verify changes
    "GitTool.add/commit/push()", # Save changes
]

workflow = [
    "1. Read existing code",
    "2. Implement changes",
    "3. Run unit tests",
    "4. Commit working code"
]
```

##### **QA Agent** - Testing & Validation
```python
# Creates tests and validates quality
tools_used = [
    "FileTool.read_file()",      # Read implementation
    "FileTool.write_file()",     # Create test files
    "TestTool.pytest()",         # Run test suites
    "TestTool.go_test()",        # Run Go tests
    "HttpTool.get/post()",       # Integration tests
    "FileTool.diff_files()",     # Review changes
]

workflow = [
    "1. Analyze implementation",
    "2. Create comprehensive tests",
    "3. Run full test suite",
    "4. Validate coverage thresholds"
]
```

##### **DEVOPS Agent** - Deployment & Infrastructure
```python
# Manages deployment and infrastructure
tools_used = [
    "FileTool.read_file()",       # Read Dockerfile, k8s yamls
    "FileTool.edit_file()",       # Update configs
    "DockerTool.build()",         # Build images
    "DockerTool.run()",           # Test locally
    "TestTool.pytest()",          # Run e2e tests
    "HttpTool.get()",             # Health checks
    "DatabaseTool.query()",       # Migration verification
]

workflow = [
    "1. Review current deployment",
    "2. Update Dockerfile/k8s manifests",
    "3. Build and test locally",
    "4. Verify deployment health"
]
```

##### **DATA Agent** - Data & Analytics
```python
# Manages data pipelines and schemas
tools_used = [
    "DatabaseTool.postgresql_query()",  # Schema analysis
    "DatabaseTool.neo4j_query()",       # Graph queries
    "DatabaseTool.redis_command()",     # Cache operations
    "FileTool.read_file()",             # Read migration files
    "FileTool.write_file()",            # Create migrations
    "TestTool.pytest()",                # Data validation tests
]

workflow = [
    "1. Analyze current schema",
    "2. Design migration",
    "3. Create migration files",
    "4. Test with sample data"
]
```

**Cross-Role Collaboration Example**:
```
Story: "Add user profile pictures"

1. ARCHITECT analyzes:
   ├─→ FileTool.search("user", "profile", "upload")
   ├─→ DatabaseTool.query("DESCRIBE users")
   ├─→ HttpTool.get("/api/users/123")
   └─→ Decides: Use S3 for storage, add image_url to User model

2. DATA designs schema:
   ├─→ DatabaseTool.query("SHOW COLUMNS FROM users")
   ├─→ FileTool.write_file("migrations/add_profile_image.sql")
   └─→ Creates migration script

3. DEV implements:
   ├─→ FileTool.read_file("src/models/user.py")
   ├─→ FileTool.edit_file() → Add image_url field
   ├─→ FileTool.write_file("src/api/upload.py")
   └─→ GitTool.commit()

4. QA validates:
   ├─→ FileTool.write_file("tests/test_upload.py")
   ├─→ TestTool.pytest()
   ├─→ HttpTool.post("/api/upload", files=test_image)
   └─→ Verifies upload works

5. DEVOPS deploys:
   ├─→ FileTool.edit_file("Dockerfile") → Add image processing libs
   ├─→ DockerTool.build(tag="v2.1.0")
   ├─→ DockerTool.run() → Test locally
   └─→ HttpTool.get("http://localhost/health") → Verify

All agents use tools to work with REAL code, not imaginary solutions!
```

### Tool Security Features

**All tools implement**:
- ✅ Workspace isolation - Operations restricted to /workspace
- ✅ Input validation - Prevent path traversal, command injection
- ✅ Timeout protection - Auto-terminate long operations
- ✅ Audit trail - Log to file + Redis + Neo4j
- ✅ Resource limits - File size, result size, request size
- ✅ No credential logging - Passwords/tokens redacted

### Tool Audit Flow

```
Tool Operation
    ↓
AuditLogger.log()
    ├─→ File: /workspace/.task/audit.log (NDJSON)
    │   └─→ {"tool": "git", "operation": "commit", "success": true, ...}
    │
    ├─→ Redis Stream: tool_audit
    │   └─→ XADD tool_audit * tool git operation commit success true
    │
    └─→ Neo4j: (:ToolExecution)
        └─→ CREATE (e:ToolExecution {tool, operation, timestamp, ...})
```

**Query audit trail**:
```python
# From file
audit_logger.query_logs(tool="git", success=True, limit=100)

# From Redis
redis.xrange("tool_audit", "-", "+", count=100)

# From Neo4j
MATCH (e:ToolExecution {tool: "git"})
WHERE e.timestamp > timestamp() - 3600000
RETURN e
ORDER BY e.timestamp DESC
LIMIT 100
```

---

## 🎯 Integration Gaps & Roadmap

### Current State (October 2025)

| Component | Status | Notes |
|-----------|--------|-------|
| **Orchestrator gRPC** | ✅ 95% | Deliberate, Orchestrate, GetStatus working |
| **Context gRPC** | ✅ 95% | GetContext, UpdateContext, RehydrateSession working |
| **NATS Consumers** | 🟡 60% | Consume events but don't fully process |
| **Ray Integration** | ✅ 80% | DeliberateAsync works, publishes to NATS |
| **Tools** | ✅ 100% | All 8 tools implemented & tested |
| **Tool-enabled Agents** | ❌ 0% | Not yet integrated |
| **Workspace Runner** | ❌ 0% | Not yet implemented |
| **Task Queue** | ❌ 0% | Not yet implemented |

### Critical Gaps

#### 1. **Task Derivation** (Orchestrator)
**Gap**: Planning publishes `plan.approved`, but Orchestrator doesn't derive subtasks

**Need**:
```python
class OrchestrationUseCase:
    def derive_subtasks(
        self, story_id: str, plan_id: str, roles: list[str]
    ) -> list[Task]:
        """
        Parse plan and extract atomic executable tasks.
        Assign to roles, identify dependencies, set priorities.
        """
```

**Status**: 🔴 Not implemented

#### 2. **Task Queue** (Orchestrator)
**Gap**: No persistent queue for managing task execution order

**Need**:
```python
class TaskQueue:
    def enqueue(self, task: Task, priority: int)
    def dequeue(self) -> Task | None
    def mark_completed(self, task_id: str)
    def get_status(self, task_id: str) -> str
```

**Status**: 🔴 Not implemented (Redis/Valkey backend needed)

#### 3. **Tool-Enabled Agents** (Orchestrator)
**Gap**: Agents generate text but don't execute code using tools

**Need**:
```python
class ToolEnabledAgent(Agent):
    def __init__(self, agent_id, role, workspace_path, tools):
        self.git = GitTool(workspace_path)
        self.files = FileTool(workspace_path)
        self.tests = TestTool(workspace_path)

    def generate(self, task, constraints, diversity=False):
        # 1. LLM generates plan
        plan = self.llm.generate(f"Plan for: {task}")

        # 2. Execute plan using tools
        for step in plan.steps:
            if step.tool == "files.write":
                self.files.write_file(step.path, step.content)
            # ... etc

        # 3. Verify and return results
        return {"success": True, "operations": [...]}
```

**Status**: 🔴 Not implemented (tools ready, needs integration)

#### 4. **Workspace Runner** (Infrastructure)
**Gap**: No component creates K8s Jobs for agent execution

**Need**:
```python
class WorkspaceRunner:
    """
    NATS consumer that:
    1. Subscribes to agent.cmd.execute
    2. Creates K8s Job with workspace container
    3. Job clones repo, initializes tools, runs agent
    4. Publishes results to agent.results.{task_id}
    """
```

**Status**: 🔴 Not implemented (design exists in `workers/workspace_runner.py` skeleton)

---

## 🚀 Implementation Phases

### Phase 1: Tools Foundation ✅ COMPLETED (This Session)
- [x] Git, File, Test, Docker, HTTP, Database tools
- [x] Security validators & audit system
- [x] 55 unit tests (100% passing)
- [x] E2E test simulating agent workflow
- [x] Documentation complete

**Deliverable**: Tools ready for agent integration

---

### Phase 2: Tool-Enabled Agent Integration (Next Sprint)

**Goal**: Agent uses tools to execute tasks

**Tasks**:
1. Create `ToolEnabledMockAgent` class
   ```python
   class ToolEnabledMockAgent(Agent):
       def __init__(self, agent_id, role, workspace_path):
           self.tools = {
               "git": GitTool(workspace_path),
               "files": FileTool(workspace_path),
               "tests": TestTool(workspace_path),
           }

       def generate(self, task, constraints, diversity=False):
           # Parse task and use appropriate tools
           if "add function" in task.lower():
               return self._add_function_with_tools(task)
   ```

2. Update `VLLMAgentJob` to accept tools
   ```python
   class VLLMAgentJob(ray.remote):
       def __init__(self, agent_id, role, vllm_url, workspace_path):
           self.agent = ToolEnabledVLLMAgent(
               agent_id, role, vllm_url, workspace_path
           )

       def run(self, task_id, task, constraints):
           # Agent generates plan using LLM
           # Agent executes plan using tools
           # Agent publishes results to NATS
   ```

3. Test E2E: Orchestrator → Ray → Agent with Tools

**Deliverable**: Agent can complete coding tasks using tools

---

### Phase 3: Workspace Runner (Sprint N+2)

**Goal**: Automated K8s Job creation for agent execution

**Tasks**:
1. Implement `WorkspaceRunner` (Python)
   - NATS consumer for `agent.cmd.execute`
   - K8s Job template with tools
   - Result publishing

2. Agent Workspace Container image
   - Base: Python 3.13 + Go + Node
   - Tools pre-installed
   - Non-root user (UID 1000)

3. Test E2E: Planning → Orchestrator → WorkspaceRunner → K8s Job → Results

**Deliverable**: Full async task execution flow

---

### Phase 4: Task Queue & Derivation (Sprint N+3)

**Goal**: Complete task management system

**Tasks**:
1. Implement `TaskQueue` with Redis
2. Implement `derive_subtasks()` in Orchestrator
3. Connect Planning → Orchestrator → TaskQueue
4. Task dependency management

**Deliverable**: Planning-driven task execution

---

### Phase 5: Gateway & SSE (Sprint N+4)

**Goal**: Real-time UI updates

**Tasks**:
1. Implement Gateway service (Go)
2. REST API for UI
3. SSE endpoint for events
4. NATS → SSE bridge

**Deliverable**: Real-time frontend

---

## 📋 Service Communication Matrix

| From → To | Protocol | Purpose | Status |
|-----------|----------|---------|--------|
| **Gateway → Orchestrator** | gRPC | Execute tasks | 🚧 Gateway TBD |
| **Gateway → Context** | gRPC | Get context | 🚧 Gateway TBD |
| **Gateway → Planning** | gRPC | Manage stories | 🚧 Gateway TBD |
| **Orchestrator → Context** | gRPC | Get/update context | ✅ Working |
| **Orchestrator → Ray** | Ray API | Distribute jobs | ✅ Working |
| **Planning → NATS** | Pub/Sub | Story events | ✅ Working |
| **Orchestrator → NATS** | Pub/Sub | Orchestration events | ✅ Working |
| **Context → NATS** | Pub/Sub | Context updates | ✅ Working |
| **Ray Jobs → NATS** | Pub/Sub | Agent results | ✅ Working |
| **Context → Neo4j** | Bolt | Graph queries/commands | ✅ Working |
| **Context → Redis** | Redis protocol | Cache operations | ✅ Working |

---

## 🔍 Monitoring & Debugging

### Health Checks

```bash
# Check all services
kubectl get pods -n swe-ai-fleet

# Orchestrator health
grpcurl -plaintext orchestrator:50055 \
  orchestrator.v1.OrchestratorService/GetStatus

# Context health
grpcurl -plaintext context:50054 \
  fleet.context.v1.ContextService/GetContext
```

### NATS Monitoring

```bash
# Stream stats
nats stream info ORCHESTRATOR_EVENTS

# Consumer lag
nats consumer info ORCHESTRATOR_EVENTS orchestrator-planning-events

# View messages
nats stream view ORCHESTRATOR_EVENTS --last=10
```

### Ray Monitoring

```bash
# Ray dashboard
kubectl port-forward -n swe-ai-fleet svc/ray-head 8265:8265
# Open: http://localhost:8265

# Ray jobs status
ray job list

# Job logs
ray job logs {job_id}
```

---

## 📖 Related Documentation

- [Microservices Architecture](./MICROSERVICES_ARCHITECTURE.md) - Overall system design
- [NATS Consumers Design](./NATS_CONSUMERS_DESIGN.md) - Detailed consumer specs
- [Orchestrator Interactions](../../docs/microservices/ORCHESTRATOR_INTERACTIONS.md) - Orchestrator-specific flows
- [Context Management](./CONTEXT_MANAGEMENT.md) - Context service architecture
- [Deliberate & Orchestrate Design](./DELIBERATE_ORCHESTRATE_DESIGN.md) - Use case integration
- [Tools README](../../src/swe_ai_fleet/tools/README.md) - Agent tools documentation

---

## 🎯 Quick Reference: Current vs Target Architecture

### Current (Implemented)
```
Planning → NATS → Orchestrator → Ray → vLLM → TEXT proposal
                      ↓
                  Context Service → Neo4j
```

### Target (With Tools)
```
Planning → NATS → Orchestrator → WorkspaceRunner → K8s Job
                                                       ↓
                                           Agent + Tools execute CODE
                                                       ↓
                                           NATS → Context → Neo4j
                                                       ↓
                                           Actual changes committed ✅
```

---

**Document Purpose**: Central reference for understanding how SWE AI Fleet components communicate and coordinate to execute software engineering tasks.

**Audience**: Developers, architects, and contributors need to understand system integration points.

**Status**: Living document - Updated as architecture evolves.

