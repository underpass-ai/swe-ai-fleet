# Real vLLM Agent with Tools - Implementation Plan

**Goal**: Orchestrator → Ray → vLLM Agent → Execute Tools → Return Results

**Status**: Tools ✅ Ready | Integration ❌ Pending

---

## 🎯 What We Have Now

### ✅ Working Components

1. **Tools Package** (`src/swe_ai_fleet/tools/`)
   - 6 tools: Git, File, Test, Docker, HTTP, Database
   - 52 operations total
   - Security: validators, audit, isolation
   - Tests: 60/60 passing (local + cluster)

2. **Orchestrator Service** (`services/orchestrator/`)
   - gRPC: `Deliberate`, `Orchestrate`, `GetStatus`
   - Ray integration: `DeliberateAsync`
   - Creates Ray jobs, publishes to NATS

3. **Ray VLLMAgentJob** (`src/swe_ai_fleet/orchestrator/ray_jobs/vllm_agent_job.py`)
   - Runs in Ray cluster
   - Calls vLLM for text generation
   - Publishes results to NATS
   - ❌ NO usa tools

4. **Test Infrastructure**
   - E2E test simulates agent workflow
   - K8s Job verified in cluster
   - Pre-built image: `agent-tools-test:v0.1.0`

---

## ❌ What's Missing

### 1. ToolEnabledAgent Class

**Location**: `src/swe_ai_fleet/agents/tool_enabled_agent.py`

**Purpose**: Agent that uses vLLM + tools to complete tasks

```python
class ToolEnabledAgent:
    """
    Agent that combines vLLM reasoning with tool execution.
    
    Flow:
    1. Receives task: "Add hello_world() to utils.py"
    2. Calls vLLM to generate execution plan
    3. Parses plan into tool operations
    4. Executes tools sequentially
    5. Returns results with audit trail
    """
    
    def __init__(
        self,
        agent_id: str,
        role: str,
        vllm_url: str,
        workspace_path: str,
        model: str = "Qwen/Qwen3-0.6B"
    ):
        self.agent_id = agent_id
        self.role = role
        self.vllm_client = VLLMClient(vllm_url, model)
        
        # Initialize tools
        self.tools = {
            "git": GitTool(workspace_path),
            "files": FileTool(workspace_path),
            "tests": TestTool(workspace_path),
            "docker": DockerTool(workspace_path),
            "http": HttpTool(),
            "db": DatabaseTool(),
        }
    
    async def execute_task(
        self,
        task: str,
        context: str,
        constraints: dict
    ) -> AgentResult:
        """
        Main execution method.
        
        Returns:
            AgentResult with:
            - success: bool
            - operations: list[ToolOperation]
            - artifacts: dict (commit_sha, files_changed, etc)
            - audit_trail: list[AuditEntry]
        """
        # Step 1: Generate plan using vLLM
        plan = await self._generate_plan(task, context, constraints)
        
        # Step 2: Execute plan using tools
        results = await self._execute_plan(plan)
        
        # Step 3: Verify and return
        return self._create_result(results)
    
    async def _generate_plan(self, task, context, constraints):
        """
        Call vLLM to generate execution plan.
        
        Prompt engineering:
        - System: "You are a software engineer with access to tools"
        - User: task description + context
        - Format: JSON with steps
        """
        prompt = self._create_prompt(task, context, constraints)
        response = await self.vllm_client.generate(prompt)
        plan = self._parse_plan(response)
        return plan
    
    async def _execute_plan(self, plan):
        """
        Execute plan steps using tools.
        
        For each step:
        1. Identify tool (git, files, tests, etc)
        2. Extract parameters
        3. Call tool method
        4. Handle result (success/error)
        5. Log to audit trail
        """
        results = []
        for step in plan.steps:
            tool_name = step.tool
            operation = step.operation
            params = step.params
            
            tool = self.tools[tool_name]
            method = getattr(tool, operation)
            result = method(**params)
            
            results.append(result)
            
            if not result.success:
                # Handle error: retry, skip, abort?
                break
        
        return results
```

**Implementation Steps**:
1. Create `src/swe_ai_fleet/agents/tool_enabled_agent.py`
2. Define `AgentResult` dataclass
3. Implement prompt engineering for vLLM
4. Create plan parser (JSON or structured format)
5. Implement tool execution loop
6. Add error handling and retry logic
7. Unit tests: mock vLLM, real tools

---

### 2. VLLMAgentJob with Tools

**Location**: `src/swe_ai_fleet/orchestrator/ray_jobs/vllm_agent_job.py`

**Changes**: Integrate `ToolEnabledAgent`

```python
@ray.remote
class VLLMAgentJob:
    """
    Ray actor that runs ToolEnabledAgent in isolated workspace.
    """
    
    def __init__(
        self,
        agent_id: str,
        role: str,
        vllm_url: str,
        workspace_path: str,  # NEW: path to workspace
        nats_url: str,
        model: str = "Qwen/Qwen3-0.6B"
    ):
        self.agent = ToolEnabledAgent(
            agent_id=agent_id,
            role=role,
            vllm_url=vllm_url,
            workspace_path=workspace_path,
            model=model
        )
        self.nats_client = NATSClient(nats_url)
    
    async def run(
        self,
        task_id: str,
        task: str,
        context: str,
        constraints: dict
    ) -> dict:
        """
        Execute task using ToolEnabledAgent.
        
        Returns:
            {
                "task_id": str,
                "success": bool,
                "operations": list,
                "artifacts": dict,
                "audit_trail": list
            }
        """
        # Execute task with tools
        result = await self.agent.execute_task(task, context, constraints)
        
        # Publish to NATS
        await self.nats_client.publish(
            f"agent.results.{task_id}",
            result.to_dict()
        )
        
        return result.to_dict()
```

**Implementation Steps**:
1. Update `VLLMAgentJob.__init__` to accept `workspace_path`
2. Instantiate `ToolEnabledAgent` instead of direct vLLM calls
3. Update result format to include operations and artifacts
4. Update NATS publishing to include tool audit trail
5. Integration tests with Ray

---

### 3. Workspace Management

**Problem**: Where does the agent workspace come from?

**Options**:

#### Option A: Pre-cloned Workspace (Recommended)
```
K8s Job/Pod:
  initContainer:
    - name: clone-repo
      image: alpine/git
      command: git clone <repo> /workspace
  
  container:
    - name: agent
      image: agent-tools-test:v0.1.0
      volumeMounts:
        - /workspace  # Shared with initContainer
```

**Pros**: 
- ✅ Fast (git clone once)
- ✅ Already implemented (E2E test uses this)
- ✅ Clean separation

**Cons**:
- ⚠️ Requires K8s Job per agent execution

#### Option B: Agent Clones Inside Container
```python
class ToolEnabledAgent:
    async def execute_task(self, task, context, constraints):
        # Step 0: Clone repo if not exists
        if not self.workspace_path.exists():
            self.tools["git"].clone(constraints["repo_url"], self.workspace_path)
        
        # Step 1: Generate plan
        ...
```

**Pros**:
- ✅ Self-contained agent
- ✅ Works in any environment (Ray, K8s, local)

**Cons**:
- ⚠️ Slower (clone every time)
- ⚠️ Needs repo URL in constraints

**Decision**: Use **Option A** for K8s, **Option B** for local testing

---

### 4. Orchestrator Integration

**Location**: `services/orchestrator/usecases/deliberate_async_usecase.py`

**Changes**: Pass workspace path to Ray job

```python
class DeliberateAsync:
    async def execute(
        self,
        task_id: str,
        task: str,
        context: str,
        constraints: dict,
        num_agents: int = 3
    ) -> dict:
        """
        Execute deliberation with tool-enabled agents.
        """
        # Create workspace for this task (could be shared or per-agent)
        workspace_path = f"/tmp/workspaces/{task_id}"
        
        # Submit Ray jobs with workspace
        job_refs = []
        for i in range(num_agents):
            agent = VLLMAgentJob.remote(
                agent_id=f"agent-{self.role}-{i}",
                role=self.role,
                vllm_url=self.vllm_url,
                workspace_path=workspace_path,  # NEW
                nats_url=self.nats_url,
            )
            
            job_ref = agent.run.remote(
                task_id=task_id,
                task=task,
                context=context,
                constraints=constraints
            )
            job_refs.append(job_ref)
        
        return {"task_id": task_id, "status": "PENDING"}
```

**Implementation Steps**:
1. Update `DeliberateAsync` to create/manage workspaces
2. Pass `workspace_path` to `VLLMAgentJob.remote()`
3. Handle workspace cleanup after execution
4. Update result format to include tool operations

---

### 5. Workspace Runner (Future - Not Required Yet)

**Purpose**: Automatically create K8s Jobs for agent execution

**Location**: `workers/workspace_runner.py`

**Flow**:
```
NATS: agent.cmd.execute
    ↓
WorkspaceRunner (consumer)
    ↓ Create K8s Job
    │   - initContainer: clone repo
    │   - container: agent-tools-test:v0.1.0
    │   - env: TASK_ID, VLLM_URL, NATS_URL
    │   - command: python -m agent.execute_task
    ↓
Agent Container
    ↓ ToolEnabledAgent.execute_task()
    ↓ Tools execute
    ↓ NATS: agent.results.{task_id}
```

**Status**: ⏳ Not needed for first iteration (use Ray directly)

---

## 🚀 Implementation Roadmap

### Phase 1: ToolEnabledAgent (1-2 days)

**Goal**: Agent that uses vLLM + tools

**Tasks**:
1. ✅ Create `src/swe_ai_fleet/agents/tool_enabled_agent.py`
2. ✅ Implement prompt engineering for vLLM
3. ✅ Create plan parser (JSON format)
4. ✅ Implement tool execution loop
5. ✅ Add error handling
6. ✅ Unit tests (mock vLLM, real tools)
7. ✅ Local integration test

**Acceptance Criteria**:
- Agent can execute: "Add function to file"
- Agent uses: FileTool, TestTool, GitTool
- Result includes: operations, artifacts, audit_trail
- Tests: 10+ unit tests passing

---

### Phase 2: Ray Integration (1 day)

**Goal**: VLLMAgentJob uses ToolEnabledAgent

**Tasks**:
1. ✅ Update `VLLMAgentJob` to use `ToolEnabledAgent`
2. ✅ Add `workspace_path` parameter
3. ✅ Update result format
4. ✅ Ray integration tests

**Acceptance Criteria**:
- Ray job executes agent with tools
- Results published to NATS include operations
- Tests: 5+ Ray tests passing

---

### Phase 3: Orchestrator Integration (1 day)

**Goal**: Orchestrator triggers tool-enabled agents

**Tasks**:
1. ✅ Update `DeliberateAsync` to pass workspace_path
2. ✅ Update result collection to parse operations
3. ✅ Update Context Service to store tool operations
4. ✅ E2E test: Orchestrator → Ray → Agent → Tools

**Acceptance Criteria**:
- `Orchestrator.Orchestrate()` triggers tool execution
- Context Service stores commit info, files changed
- E2E test passes in cluster

---

### Phase 4: Production Readiness (2-3 days)

**Goal**: Robust, production-ready system

**Tasks**:
1. ⏳ Workspace cleanup after execution
2. ⏳ Error handling and retry logic
3. ⏳ Monitoring and observability
4. ⏳ Resource limits and timeouts
5. ⏳ Security audit
6. ⏳ Performance optimization

**Acceptance Criteria**:
- Handles errors gracefully
- No workspace leaks
- Metrics exported to Prometheus
- Security review passed

---

## 📋 First Step: Create ToolEnabledAgent

Let's start with the core component:

```bash
# Create agent module
mkdir -p src/swe_ai_fleet/agents
touch src/swe_ai_fleet/agents/__init__.py

# Create main agent file
touch src/swe_ai_fleet/agents/tool_enabled_agent.py

# Create tests
mkdir -p tests/unit/agents
touch tests/unit/agents/test_tool_enabled_agent.py
```

**Skeleton**:
```python
# src/swe_ai_fleet/agents/tool_enabled_agent.py

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from swe_ai_fleet.tools import FileTool, GitTool, TestTool


@dataclass
class AgentResult:
    success: bool
    operations: list[dict]
    artifacts: dict[str, Any]
    audit_trail: list[dict]
    error: str | None = None


class ToolEnabledAgent:
    """Agent that combines LLM reasoning with tool execution."""
    
    def __init__(
        self,
        agent_id: str,
        role: str,
        workspace_path: str | Path,
        vllm_url: str | None = None,
    ):
        self.agent_id = agent_id
        self.role = role
        self.workspace_path = Path(workspace_path)
        self.vllm_url = vllm_url
        
        # Initialize tools
        self.tools = {
            "git": GitTool(workspace_path),
            "files": FileTool(workspace_path),
            "tests": TestTool(workspace_path),
        }
    
    async def execute_task(
        self,
        task: str,
        context: str = "",
        constraints: dict | None = None,
    ) -> AgentResult:
        """Execute a task using LLM + tools."""
        # TODO: Implement
        raise NotImplementedError
```

---

## 🎯 Success Metrics

### Short-term (Phase 1-2)
- ✅ Agent can complete simple coding task
- ✅ Tools execute correctly
- ✅ Results include operations and artifacts
- ✅ 20+ tests passing

### Mid-term (Phase 3)
- ✅ Orchestrator triggers tool-enabled agents
- ✅ E2E test passes in cluster
- ✅ Context Service stores real changes

### Long-term (Phase 4+)
- ✅ Production-ready system
- ✅ Handles errors gracefully
- ✅ Monitored and observable
- ✅ Secure and performant

---

**Next Action**: Create `ToolEnabledAgent` class

**Ready to start?** Let's build the real thing! 🚀

