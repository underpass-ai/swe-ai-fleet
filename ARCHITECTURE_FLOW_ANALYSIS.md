# SWE AI Fleet - Architecture Flow Analysis

## 🎯 Current Architecture (As Implemented)

### 📊 Services Deployed

| Service | Port | Language | Status | Purpose |
|---------|------|----------|--------|---------|
| **Planning** | 50051 | Go | ✅ Running | FSM story lifecycle |
| **StoryCoach** | 50052 | Go | ✅ Running | Story scoring |
| **Workspace** | 50053 | Go | ✅ Running | Result scoring |
| **Context** | 50054 | Python | ✅ Running | Context hydration |
| **Orchestrator** | 50055 | Python | ✅ Running | Multi-agent coordination |
| **UI** | 80 | React | ✅ Running | Product Owner interface |

### 🔄 Communication Patterns

#### 1. **Synchronous (gRPC)**

```
Gateway → Orchestrator:50055 → Context:50054
              ↓
          Deliberate(role, task)
              ↓
          Returns: winner + candidates
```

#### 2. **Asynchronous (NATS JetStream)**

```
Planning → agile.events
             ↓
    OrchestratorPlanningConsumer
             ↓
    Derive subtasks (TO DO)
             ↓
    agent.requests
             ↓
    Workspace Runner (TO DO)
             ↓
    K8s Jobs
             ↓
    agent.responses
             ↓
    Context Service Consumer
```

#### 3. **Ray Jobs (Distributed Execution)**

```
Orchestrator.DeliberateAsync
    ↓
Creates N Ray jobs (VLLMAgentJob.remote)
    ↓
Ray Cluster executes in parallel
    ├─→ Agent 1 → vLLM Server → generate()
    ├─→ Agent 2 → vLLM Server → generate()
    └─→ Agent 3 → vLLM Server → generate()
    ↓
Agents publish to NATS: agent.results.{task_id}
    ↓
DeliberationResultCollector
    ↓
Returns aggregated results
```

---

## 🔍 Current Flow for Task Execution

### Scenario: "Add hello_world() function to utils.py"

#### **Path A: Sync Deliberation (Mock Agents)**

```
1. gRPC Call: Orchestrator.Deliberate
   {
     role: "DEV",
     task_description: "Add hello_world() function to src/utils.py",
     rounds: 1,
     num_agents: 3
   }

2. Orchestrator checks councils["DEV"]
   - If empty → ERROR: "No agents configured"
   
3. Council executes deliberation
   Deliberate.execute(task, constraints)
   ├─→ Agent1.generate(task) → proposal1
   ├─→ Agent2.generate(task) → proposal2
   └─→ Agent3.generate(task) → proposal3
   
4. Peer review (if rounds > 1)
   ├─→ Agent1.critique(proposal2)
   ├─→ Agent2.critique(proposal3)
   └─→ Agent3.critique(proposal1)
   
5. Scoring.score(proposals, rubric)
   └─→ Ranked: [proposal1(0.95), proposal2(0.87), proposal3(0.82)]
   
6. Return DeliberateResponse
   {
     winner_id: "agent-dev-001",
     results: [...],
     duration_ms: 2500
   }
```

#### **Path B: Async Deliberation (Ray + vLLM)**

```
1. gRPC Call: Orchestrator.Deliberate (with async flag)
   OR Planning event consumed

2. DeliberateAsync.execute(task_id, task, role, num_agents)
   
3. Connect to Ray Cluster
   ray.init(address="ray://ray-head:10001")
   
4. Create N Ray Actors
   for i in range(num_agents):
       agent_actor = VLLMAgentJob.remote(
           agent_id=f"agent-{role}-{i}",
           vllm_url="http://vllm-server:8000",
           model="Qwen/Qwen3-0.6B",
           nats_url="nats://nats:4222"
       )
       
5. Submit jobs (non-blocking)
   job_refs = [
       agent_actor.run.remote(task_id, task, constraints)
       for agent in agents
   ]
   
6. Return immediately
   {
     task_id: "task-12345",
     status: "PENDING",
     agent_count: 3,
     ray_job_ids: [...]
   }
   
7. Ray executes jobs in parallel
   Each VLLMAgentJob:
   ├─→ Calls vLLM API
   ├─→ Generates proposal
   ├─→ Publishes to NATS: agent.results.task-12345
   └─→ Job completes
   
8. DeliberationResultCollector (NATS consumer)
   ├─→ Collects agent.results.{task_id}
   ├─→ Waits for all N agents (with timeout)
   ├─→ Ranks results
   └─→ Stores in memory cache
   
9. Client polls: GetDeliberationResult(task_id)
   {
     status: "COMPLETED",
     winner: {...},
     results: [...],
     duration_ms: 5000
   }
```

---

## ❌ **CRITICAL GAP: Tools Not Integrated**

### Current State
```python
# VLLMAgentJob.run() currently:
class VLLMAgentJob:
    def run(self, task_id, task_description, constraints):
        # 1. Call vLLM API
        prompt = f"Complete task: {task_description}"
        response = vllm_client.generate(prompt)
        
        # 2. Publish result to NATS
        nats.publish(f"agent.results.{task_id}", response)
```

**Problem**: Agent generates TEXT response, but doesn't EXECUTE code changes using tools!

### What's Missing

```python
# What we NEED:
class ToolEnabledAgentJob:
    def __init__(self, agent_id, role, workspace_path, tools):
        self.agent_id = agent_id
        self.role = role
        self.workspace_path = workspace_path
        
        # Initialize tools
        self.git = GitTool(workspace_path)
        self.files = FileTool(workspace_path)
        self.tests = TestTool(workspace_path)
    
    def run(self, task_id, task_description, constraints):
        # 1. Call LLM to get PLAN
        prompt = f"""Task: {task_description}
        Available tools: git, files, tests
        Generate step-by-step plan using tools.
        """
        plan = vllm_client.generate(prompt)
        
        # 2. EXECUTE plan using tools
        for step in plan:
            if step.tool == "files.write":
                self.files.write_file(step.path, step.content)
            elif step.tool == "git.commit":
                self.git.commit(step.message)
            elif step.tool == "tests.pytest":
                result = self.tests.pytest()
                if not result.success:
                    # Retry or report failure
        
        # 3. Verify and publish result
        verification = self._verify_task_completion(task_description)
        nats.publish(f"agent.results.{task_id}", verification)
```

---

## 🎯 Solution: E2E Flow with Tools

### Architecture Update

```
Orchestrator
    ↓
Create Workspace Container (K8s Job)
    ├─→ Clone repo
    ├─→ Initialize tools (git, files, tests)
    └─→ /workspace ready
    ↓
Execute Agent with Tools
    ├─→ LLM generates plan
    ├─→ Agent uses FileTool.write_file()
    ├─→ Agent uses TestTool.pytest()
    ├─→ Agent uses GitTool.commit()
    └─→ Workspace execution complete
    ↓
Publish Results to NATS
    ↓
Context Service updates Neo4j
    ↓
Task complete ✅
```

### Implementation Plan

```
Phase 1: Standalone Tool Execution (Current PR) ✅
- Tools implemented
- Unit tests passing
- Tools work in workspace container

Phase 2: Agent + Tools Integration (Next)
- Create ToolEnabledAgent class
- Agent calls tools during task execution
- E2E test: Agent uses tools to complete task

Phase 3: Workspace Runner Integration
- Workspace Runner creates K8s Job
- Job includes tools
- Agent executes within Job
- Results published to NATS

Phase 4: Full Flow
- Planning → agile.events
- Orchestrator → derives tasks
- Workspace Runner → creates Jobs with tools
- Agent → executes using tools
- Results → Context Service
```

---

## 🚀 E2E Test Scenario (For This Session)

### Goal: Agent uses tools to add a function

```
1. Test creates workspace
   /workspace/
     /src/utils.py    (existing file)
     /tests/          (existing tests)

2. Test calls: orchestrator.execute_task_with_tools()
   task = "Add hello_world() function to src/utils.py"
   role = "DEV"

3. Orchestrator dispatches to ToolEnabledMockAgent
   agent = ToolEnabledMockAgent(
       agent_id="agent-dev-001",
       workspace="/workspace",
       tools=[GitTool, FileTool, TestTool]
   )

4. Agent executes task:
   Step 1: files.read_file("src/utils.py")
   Step 2: files.append_file("src/utils.py", new_function_code)
   Step 3: tests.pytest() to verify
   Step 4: git.add(["src/utils.py"])
   Step 5: git.commit("feat: add hello_world()")

5. Agent returns result:
   {
     success: true,
     operations: [read, append, pytest, add, commit],
     audit_trail: [...],
     final_state: "committed"
   }

6. Test verifies:
   ✓ Function added to file
   ✓ Tests pass
   ✓ Commit created
   ✓ Audit trail complete
```

---

## 🔧 Required Components

### 1. ToolEnabledMockAgent

```python
# src/swe_ai_fleet/orchestrator/domain/agents/tool_enabled_mock_agent.py

from swe_ai_fleet.tools import GitTool, FileTool, TestTool

class ToolEnabledMockAgent(Agent):
    """Mock agent that can use tools to complete tasks."""
    
    def __init__(self, agent_id, role, workspace_path):
        super().__init__(agent_id, role)
        self.workspace_path = workspace_path
        
        # Initialize tools
        self.git = GitTool(workspace_path)
        self.files = FileTool(workspace_path)
        self.tests = TestTool(workspace_path)
    
    def generate(self, task, constraints, diversity=False):
        """Generate solution by EXECUTING task with tools."""
        # Parse task
        if "add" in task.lower() and "function" in task.lower():
            return self._add_function_task(task)
        elif "fix" in task.lower() and "bug" in task.lower():
            return self._fix_bug_task(task)
        else:
            return {"content": f"Mock solution for: {task}"}
    
    def _add_function_task(self, task):
        """Execute task to add a function."""
        # 1. Read file
        result = self.files.read_file("src/utils.py")
        if not result.success:
            return {"error": "Cannot read file"}
        
        # 2. Add function
        new_code = '''

def hello_world():
    """Return greeting."""
    return "Hello, World!"
'''
        append = self.files.append_file("src/utils.py", new_code)
        
        # 3. Run tests
        test_result = self.tests.pytest()
        
        # 4. Commit if tests pass
        if test_result.success:
            self.git.add(["src/utils.py"])
            self.git.commit("feat: add hello_world() function")
            
            return {
                "content": "Successfully added hello_world() function",
                "tests_passed": True,
                "committed": True
            }
        else:
            return {
                "content": "Added function but tests failed",
                "tests_passed": False
            }
```

### 2. K8s Job Template

```yaml
# tests/e2e/agent_tooling/k8s-agent-task-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: agent-task-{{ task_id }}
  namespace: swe-ai-fleet
spec:
  template:
    spec:
      containers:
      - name: agent-workspace
        image: registry.underpassai.com/swe-fleet/agent-workspace:latest
        command: ["/bin/bash", "-c"]
        args:
          - |
            # Clone repo
            git clone {{ repo_url }} /workspace
            cd /workspace
            
            # Initialize Python environment
            source .venv/bin/activate
            
            # Execute agent task with tools
            python -m swe_ai_fleet.orchestrator.agent_executor \
              --task-id {{ task_id }} \
              --role {{ role }} \
              --task "{{ task_description }}" \
              --workspace /workspace \
              --nats-url nats://nats:4222
        
        volumeMounts:
          - name: workspace
            mountPath: /workspace
        
        env:
          - name: TASK_ID
            value: "{{ task_id }}"
          - name: AGENT_ROLE
            value: "{{ role }}"
          - name: NATS_URL
            value: "nats://nats:4222"
      
      volumes:
        - name: workspace
          emptyDir: {}
      
      restartPolicy: Never
```

---

## 🎯 E2E Test Implementation

### Objective
Test complete flow: Orchestrator → Agent → Tools → Task Completion

### Current Limitations
1. ❌ VLLMAgentJob doesn't have access to tools
2. ❌ MockAgent doesn't use tools
3. ❌ No workspace container integration yet

### Solution for This Session

**Simplified E2E**: Direct tool usage by test (simulating agent behavior)

```python
# tests/e2e/agent_tooling/test_orchestrator_agent_tools_e2e.py

@pytest.mark.e2e
def test_agent_completes_coding_task_with_tools():
    """
    E2E: Simulated agent uses tools to complete task.
    
    Simulates what a real agent would do:
    1. Receive task from Orchestrator
    2. Use FileTool to read/modify code
    3. Use TestTool to verify
    4. Use GitTool to commit
    5. Report completion
    """
    
    # Setup workspace (like K8s Job would)
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Initialize workspace
        setup_test_workspace(workspace)
        
        # === SIMULATE AGENT EXECUTION ===
        
        # Agent receives task (from Orchestrator)
        task = {
            "task_id": "task-001",
            "role": "DEV",
            "description": "Add hello_world() function to src/utils.py"
        }
        
        # Agent initializes tools
        git = GitTool(workspace)
        files = FileTool(workspace)
        tests = TestTool(workspace)
        
        # Agent completes task
        result = complete_coding_task(task, git, files, tests)
        
        # Verify
        assert result["success"]
        assert result["tests_passed"]
        assert result["committed"]
        
        # Would publish to NATS in real scenario
        # nats.publish(f"agent.results.{task['task_id']}", result)
```

---

## 🔧 What Needs to be Built

### Immediate (This Session)
1. ✅ Tools implemented (git, file, test, docker, http, db)
2. ✅ Unit tests for tools
3. ✅ E2E test simulating agent tool usage
4. ⏳ K8s Job to run E2E test in cluster

### Short-term (Next Sprint)
1. ⏳ ToolEnabledAgent class
2. ⏳ Integration with VLLMAgentJob
3. ⏳ Workspace Runner that creates K8s Jobs
4. ⏳ agent-executor script for Job container

### Medium-term
1. ⏳ Tool Gateway (FastAPI) for unified API
2. ⏳ Policy Engine (RBAC) for tool access
3. ⏳ LLM-based tool selection (agent decides which tools to use)

---

## 📊 Current vs Target Architecture

### Current (Implemented)
```
Orchestrator
    ↓
MockAgent.generate()
    ↓
Returns text proposal
    ↓
No actual code execution
```

### Target (This Session's Goal)
```
Orchestrator
    ↓
ToolEnabledAgent.generate()
    ↓
Uses FileTool, GitTool, TestTool
    ↓
Executes actual code changes
    ↓
Returns execution result + audit
```

### Future (Full System)
```
Planning
    ↓ NATS: agile.events
Orchestrator Consumer
    ↓ Derives tasks
Workspace Runner
    ↓ Creates K8s Job
Agent Container (with tools)
    ├─→ vLLM generates plan
    ├─→ Tools execute plan
    ├─→ Verify completion
    └─→ Publish to NATS
Context Service
    ↓ Updates Neo4j
Task Complete ✅
```

---

## 🎯 Next Steps for E2E Test

1. **Run E2E test locally** ✅ DONE
   - Tools work in temp workspace
   - Agent workflow simulated
   - 5 tests passing

2. **Create K8s Job manifest** ✅ DONE
   - Job clones repo
   - Installs dependencies
   - Runs E2E tests
   - Reports results

3. **Execute in Kubernetes cluster** ⏳ NEXT
   - Apply Job to cluster
   - Monitor execution
   - Verify tools work in K8s
   - Check audit trail

4. **Integrate with Orchestrator** (Future)
   - ToolEnabledAgent
   - Workspace Runner
   - Full async flow

---

**Status**: Ready to execute E2E in Kubernetes cluster! 🚀

The tools are implemented, tests pass locally, and K8s Job is configured.
Next: Deploy to cluster and verify agent tooling works in production environment.

