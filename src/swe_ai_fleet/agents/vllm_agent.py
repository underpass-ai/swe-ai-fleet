"""
VLLMAgent: Universal agent for SWE AI Fleet that combines vLLM reasoning with tool execution.

## 🎯 Key Innovation: Smart Context + Focused Tools

Unlike other AI coding systems that dump entire repositories into massive prompts (1M+ tokens),
SWE AI Fleet provides agents with SMART, FILTERED context (2-4K tokens) from the Context Service:

- **What other systems do**: "Here's the entire codebase, figure out what's relevant"
- **What we do**: Context Service analyzes decision graph → filters by role/phase/story
                   → Agent receives ONLY what matters for this specific task

The agent then uses tools to read SPECIFIC files it needs, not scan the whole repo.

Result: **Faster, cheaper, more accurate** 🚀

## Agent Architecture

ALL agents in the system are VLLMAgents, differentiated by their ROLE:
- DEV: Implements features, fixes bugs (uses: git, files, tests)
- QA: Creates tests, validates quality (uses: files, tests, http)
- ARCHITECT: Analyzes codebase, designs solutions (uses: files, git, db for analysis)
- DEVOPS: Deploys, monitors infrastructure (uses: docker, http, files)
- DATA: Manages schemas, migrations (uses: db, files, tests)

## Inputs to Agent

1. **Smart Context** (from Context Service):
   - Relevant decisions from Neo4j graph
   - Related subtasks and dependencies
   - Filtered timeline and history
   - Role-specific information
   - 2-4K tokens, NOT 1M tokens

2. **Task Description**:
   - Clear, atomic task
   - "Add JWT authentication to login endpoint"

3. **Tools** (for targeted access):
   - Read specific files agent needs
   - Execute specific operations
   - No need to scan entire repo

## Operating Modes

1. **Read-only (Planning)**: Uses READ tools to analyze + generate informed plans
2. **Full (Implementation)**: Uses ALL tools to analyze + execute changes
3. **Iterative**: Executes tool → observes → decides next → repeat (ReAct-style)

## Example: Context-Driven Execution

```python
# 1. Context Service provides SMART context
context = \"\"\"
Story: US-123 - Add JWT authentication
Phase: BUILD
Role: DEV

Relevant Decisions (from Neo4j):
- Decision-042: Use JWT tokens (ARCHITECT, 2025-10-10)
- Decision-051: Store sessions in Redis (DATA, 2025-10-12)

Existing Code Structure:
- src/auth/middleware.py exists (uses simple auth)
- src/models/user.py has User model
- Redis client at src/db/redis_client.py

Dependencies:
- pyjwt==2.8.0 already installed

Test Coverage:
- auth module: 60% (needs improvement)
\"\"\"

# 2. Agent receives task + smart context
agent = VLLMAgent(agent_id="agent-dev-001", role="DEV", ...)

result = await agent.execute_task(
    task="Implement JWT token generation in login endpoint",
    context=context,  # Smart, filtered, 2K tokens
    constraints={"enable_tools": True}
)

# 3. Agent uses tools PRECISELY:
operations = [
    files.read_file("src/auth/middleware.py"),  # Only this file, not entire repo
    files.read_file("src/models/user.py"),      # Only this file
    files.edit_file("src/auth/middleware.py", old_code, new_code),  # Targeted change
    tests.pytest("tests/auth/"),                # Only auth tests
    git.commit("feat: add JWT token generation")
]

# Result: Fast (seconds), cheap (few API calls), accurate ✅
```

This agent receives a task and smart context, uses vLLM to generate a plan,
then executes the plan using targeted tool operations.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from swe_ai_fleet.tools import (
    DatabaseTool,
    DockerTool,
    FileTool,
    GitTool,
    HttpTool,
    TestTool,
)

try:
    from swe_ai_fleet.agents.vllm_client import VLLMClient
    VLLM_CLIENT_AVAILABLE = True
except ImportError:
    VLLM_CLIENT_AVAILABLE = False
    VLLMClient = None

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result of agent task execution."""

    success: bool
    operations: list[dict]  # List of tool operations executed
    artifacts: dict[str, Any] = field(default_factory=dict)  # commit_sha, files_changed, etc
    audit_trail: list[dict] = field(default_factory=list)  # Full audit log
    reasoning_log: list[dict] = field(default_factory=list)  # Agent's internal thoughts
    error: str | None = None  # Error message if failed


@dataclass
class AgentThought:
    """
    Captures agent's internal reasoning (for observability and debugging).
    
    This is logged to show HOW the agent thinks and decides.
    Useful for:
    - Debugging why agent made a decision
    - Demo to investors (show intelligence)
    - Audit trail of reasoning
    - Training data for future models
    """
    
    iteration: int
    thought_type: str  # "analysis", "decision", "observation", "conclusion"
    content: str  # What the agent is thinking
    related_operations: list[str] = field(default_factory=list)  # Tool operations related
    confidence: float | None = None  # How confident (0.0-1.0)
    timestamp: str | None = None


@dataclass
class ExecutionPlan:
    """Structured execution plan from LLM."""

    steps: list[dict]  # [{"tool": "files", "operation": "read_file", "params": {...}}]
    reasoning: str | None = None  # Why this plan


class VLLMAgent:
    """
    Universal agent for SWE AI Fleet - combines vLLM reasoning with tool execution.

    This is THE agent class used by ALL roles in the system (DEV, QA, ARCHITECT, DEVOPS, DATA).
    The ROLE determines HOW the agent uses tools, not WHETHER it can use them.

    Workflow:
    1. Receives task: "Add hello_world() function to utils.py"
    2. Calls vLLM to generate execution plan (or uses simple pattern matching for now)
    3. Parses plan into tool operations
    4. Executes tools sequentially based on role
    5. Returns results with audit trail

    Role-Specific Tool Usage:
    - DEV: git.commit(), files.write(), tests.pytest()
    - QA: files.read(), tests.pytest(), http.post()
    - ARCHITECT: files.search(), git.log(), db.query()
    - DEVOPS: docker.build(), http.get(), files.edit()
    - DATA: db.query(), files.write(), tests.pytest()

    Example:
        # DEV agent implementing a feature
        agent = VLLMAgent(
            agent_id="agent-dev-001",
            role="DEV",
            workspace_path="/workspace/project",
            vllm_url="http://vllm:8000"
        )

        result = await agent.execute_task(
            task="Add hello_world() function to src/utils.py",
            context="Project uses Python 3.13",
            constraints={"max_operations": 10}
        )

        print(f"Success: {result.success}")
        print(f"Operations: {len(result.operations)}")
        print(f"Commit: {result.artifacts.get('commit_sha')}")

        # QA agent validating the implementation
        qa_agent = VLLMAgent(
            agent_id="agent-qa-001",
            role="QA",
            workspace_path="/workspace/project",
            vllm_url="http://vllm:8000"
        )

        result = await qa_agent.execute_task(
            task="Validate hello_world() function and create tests",
            context="Function should return 'Hello, World!'",
        )
    """

    def __init__(
        self,
        agent_id: str,
        role: str,
        workspace_path: str | Path,
        vllm_url: str | None = None,
        audit_callback: Callable | None = None,
        enable_tools: bool = True,
    ):
        """
        Initialize vLLM agent.

        Args:
            agent_id: Unique agent identifier (e.g., "agent-dev-001")
            role: Agent role - determines tool usage patterns
                  Options: DEV, QA, ARCHITECT, DEVOPS, DATA, PO
            workspace_path: Path to workspace (must exist)
            vllm_url: URL to vLLM server (optional - can use pattern matching)
            audit_callback: Callback for audit logging
            enable_tools: Whether to enable tool execution (default: True)
                         False = text-only mode (deliberation without execution)
        """
        self.agent_id = agent_id
        self.role = role.upper()  # Normalize role to uppercase
        self.workspace_path = Path(workspace_path).resolve()
        self.vllm_url = vllm_url
        self.audit_callback = audit_callback
        self.enable_tools = enable_tools

        if not self.workspace_path.exists():
            raise ValueError(f"Workspace path does not exist: {self.workspace_path}")
        
        # Initialize vLLM client if URL provided
        self.vllm_client = None
        if vllm_url and VLLM_CLIENT_AVAILABLE:
            try:
                self.vllm_client = VLLMClient(
                    vllm_url=vllm_url,
                    model="Qwen/Qwen3-0.6B",  # TODO: Make configurable
                    temperature=0.7,
                )
                logger.info(f"vLLM client initialized at {vllm_url}")
            except Exception as e:
                logger.warning(f"Failed to initialize vLLM client: {e}. Using fallback planning.")
                self.vllm_client = None

        # Initialize tools (ALWAYS - needed for both planning and execution)
        # The enable_tools flag controls WHICH operations are allowed, not whether tools exist
        self.tools = {
            "git": GitTool(workspace_path, audit_callback),
            "files": FileTool(workspace_path, audit_callback),
            "tests": TestTool(workspace_path, audit_callback),
            "docker": DockerTool(workspace_path, audit_callback=audit_callback),
            "http": HttpTool(audit_callback=audit_callback),
            "db": DatabaseTool(audit_callback=audit_callback),
        }

        mode = "full execution" if enable_tools else "read-only (planning)"
        logger.info(
            f"VLLMAgent initialized: {agent_id} ({role}) at {workspace_path} [{mode}]"
        )
        
    def get_available_tools(self) -> dict[str, Any]:
        """
        Get description of available tools and their operations.
        
        Returns a structured description of all tools the agent can use,
        including which operations are available in read-only mode.
        
        This is used to inform the LLM about the agent's capabilities
        so it can generate realistic, executable plans.
        
        Returns:
            Dictionary with:
            - tools: dict of tool_name -> {operations, description}
            - mode: "read_only" or "full"
            - capabilities: list of what agent can do
        """
        tool_descriptions = {
            "files": {
                "description": "File system operations for reading and modifying code",
                "read_operations": [
                    "read_file(file_path) - Read file contents",
                    "search_in_files(pattern, path) - Search for pattern in files",
                    "list_files(path, recursive, pattern) - List files in directory",
                    "file_info(file_path) - Get file metadata (size, modified, etc)",
                    "diff_files(file1, file2) - Compare two files",
                ],
                "write_operations": [
                    "write_file(file_path, content) - Create/overwrite file",
                    "append_file(file_path, content) - Append to file",
                    "edit_file(file_path, search, replace) - Find and replace in file",
                    "delete_file(file_path) - Delete file",
                    "mkdir(dir_path) - Create directory",
                ],
            },
            "git": {
                "description": "Git version control operations",
                "read_operations": [
                    "status() - Show working tree status",
                    "log(max_count) - Show commit history",
                    "diff(ref1, ref2) - Show changes between commits",
                    "branch(list_all) - List branches",
                ],
                "write_operations": [
                    "add(files) - Stage files for commit",
                    "commit(message) - Create commit with staged changes",
                    "push(remote, branch) - Push commits to remote",
                    "checkout(branch) - Switch branches",
                ],
            },
            "tests": {
                "description": "Test execution for various frameworks",
                "read_operations": [
                    "pytest(path, markers, coverage) - Run Python tests",
                    "go_test(path, verbose) - Run Go tests",
                    "npm_test(script) - Run npm test script",
                    "cargo_test(path) - Run Rust tests",
                    "make_test(target) - Run make test target",
                ],
                "write_operations": [],  # Tests are read-only
            },
            "docker": {
                "description": "Docker/Podman container operations",
                "read_operations": [
                    "ps(all_containers) - List containers",
                    "logs(container, tail, follow) - Get container logs",
                ],
                "write_operations": [
                    "build(context_path, tag, dockerfile) - Build image",
                    "run(image, command, ports, volumes) - Run container",
                    "exec(container, command) - Execute command in container",
                    "stop(container) - Stop container",
                    "rm(container) - Remove container",
                ],
            },
            "http": {
                "description": "HTTP client for API calls",
                "read_operations": [
                    "get(url, params, headers) - HTTP GET request",
                    "head(url, headers) - HTTP HEAD request",
                ],
                "write_operations": [
                    "post(url, data, headers) - HTTP POST request",
                    "put(url, data, headers) - HTTP PUT request",
                    "patch(url, data, headers) - HTTP PATCH request",
                    "delete(url, headers) - HTTP DELETE request",
                ],
            },
            "db": {
                "description": "Database query operations",
                "read_operations": [
                    "postgresql_query(conn_str, query) - Execute PostgreSQL query",
                    "redis_command(host, port, command) - Execute Redis command",
                    "neo4j_query(uri, user, password, query) - Execute Neo4j query",
                ],
                "write_operations": [],  # DB writes via queries (controlled by query content)
            },
        }
        
        # Filter available tools based on mode
        mode = "full" if self.enable_tools else "read_only"
        capabilities = []
        
        for tool_name, tool_info in tool_descriptions.items():
            if tool_name in self.tools:
                # Always include read operations
                capabilities.extend([
                    f"{tool_name}.{op}" 
                    for op in tool_info["read_operations"]
                ])
                
                # Include write operations only if tools enabled
                if self.enable_tools:
                    capabilities.extend([
                        f"{tool_name}.{op}" 
                        for op in tool_info["write_operations"]
                    ])
        
        return {
            "tools": tool_descriptions,
            "mode": mode,
            "capabilities": capabilities,
            "summary": f"Agent has {len(self.tools)} tools available in {mode} mode"
        }

    async def execute_task(
        self,
        task: str,
        context: str = "",
        constraints: dict | None = None,
    ) -> AgentResult:
        """
        Execute a task using LLM + tools with smart context.

        **Key Innovation**: This agent receives SMART CONTEXT from Context Service:
        - Pre-filtered by role, phase, story
        - Only relevant decisions, code, history
        - 2-4K tokens, NOT 1M tokens (vs other AI coding systems)
        
        The agent then uses tools to:
        - Read SPECIFIC files it needs (not scan entire repo)
        - Execute TARGETED operations
        - Work efficiently with minimal API calls
        
        Result: Faster, cheaper, more accurate than massive-context approaches.

        Planning Modes:
        1. Static: Generate full plan upfront, then execute (default)
        2. Iterative: Execute → observe → decide next → repeat (ReAct-style)

        Args:
            task: Atomic, clear task description
                  e.g., "Add JWT token generation to login endpoint"
            context: SMART context from Context Service (2-4K tokens):
                     - Relevant decisions from Neo4j graph
                     - Related subtasks and dependencies
                     - Filtered code structure
                     - Role-specific information
            constraints: Execution constraints:
                - max_operations: Maximum tool operations (default: 100)
                - abort_on_error: Stop on first error (default: True)
                - iterative: Use iterative planning (default: False)
                - max_iterations: Max iterations if iterative (default: 10)

        Returns:
            AgentResult with:
            - success: bool
            - operations: list[dict] - Tool operations executed
            - artifacts: dict - Commits, files changed, test results
            - audit_trail: list[dict] - Full execution log

        Example:
            # Context Service provides smart, filtered context
            context = context_service.GetContext(
                story_id="US-123",
                role="DEV",
                phase="BUILD"
            ).context  # Returns 2-4K tokens of RELEVANT info
            
            # Agent uses that precise context + tools
            agent = VLLMAgent(agent_id="agent-dev-001", role="DEV", ...)
            result = await agent.execute_task(
                task="Add JWT authentication",
                context=context,  # Smart, not massive
            )
            
            # Agent only reads files it needs (efficient)
            assert "src/auth/middleware.py" in result.artifacts["files_read"]
            assert len(result.operations) < 10  # Focused, not scanning
        """
        constraints = constraints or {}
        iterative = constraints.get("iterative", False)
        
        if iterative:
            return await self._execute_task_iterative(task, context, constraints)
        else:
            return await self._execute_task_static(task, context, constraints)
    
    async def _execute_task_static(
        self,
        task: str,
        context: str,
        constraints: dict,
    ) -> AgentResult:
        """
        Execute task with static planning (original behavior).
        
        Flow:
        1. Generate full plan upfront
        2. Execute all steps sequentially
        3. Return results
        """
        operations = []
        artifacts = {}
        audit_trail = []
        reasoning_log = []

        try:
            logger.info(f"Agent {self.agent_id} executing task (static): {task}")

            # Log initial thought
            self._log_thought(
                reasoning_log,
                iteration=0,
                thought_type="analysis",
                content=f"[{self.role}] Analyzing task: {task}. Mode: {'full execution' if self.enable_tools else 'planning only'}",
            )

            # Step 1: Generate execution plan
            plan = await self._generate_plan(task, context, constraints)
            logger.info(f"Generated plan with {len(plan.steps)} steps")
            
            self._log_thought(
                reasoning_log,
                iteration=0,
                thought_type="decision",
                content=f"Generated execution plan with {len(plan.steps)} steps. Reasoning: {plan.reasoning}",
                related_operations=[f"{s['tool']}.{s['operation']}" for s in plan.steps],
            )

            # Step 2: Execute plan
            for i, step in enumerate(plan.steps):
                logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step}")
                
                # Log what agent is about to do
                self._log_thought(
                    reasoning_log,
                    iteration=i + 1,
                    thought_type="action",
                    content=f"Executing: {step['tool']}.{step['operation']}({step.get('params', {})})",
                )

                result = await self._execute_step(step)
                
                # Log observation
                if result.get("success"):
                    self._log_thought(
                        reasoning_log,
                        iteration=i + 1,
                        thought_type="observation",
                        content=f"✅ Operation succeeded. {self._summarize_result(step, result)}",
                        confidence=1.0,
                    )
                else:
                    self._log_thought(
                        reasoning_log,
                        iteration=i + 1,
                        thought_type="observation",
                        content=f"❌ Operation failed: {result.get('error')}",
                        confidence=0.0,
                    )
                
                operations.append(
                    {
                        "step": i + 1,
                        "tool": step["tool"],
                        "operation": step["operation"],
                        "success": result.get("success", False),
                        "error": result.get("error"),
                    }
                )

                # Collect artifacts
                if result.get("success"):
                    self._collect_artifacts(step, result, artifacts)

                # Check if step failed
                if not result.get("success"):
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Step {i+1} failed: {error_msg}")

                    # Decide: abort or continue?
                    if constraints.get("abort_on_error", True):
                        return AgentResult(
                            success=False,
                            operations=operations,
                            artifacts=artifacts,
                            audit_trail=audit_trail,
                            error=f"Step {i+1} failed: {error_msg}",
                        )

                # Check max operations limit
                if i + 1 >= constraints.get("max_operations", 100):
                    logger.warning("Max operations limit reached")
                    break

            # Step 3: Verify completion
            success = all(op["success"] for op in operations)

            logger.info(
                f"Task completed: {success} ({len(operations)} operations)"
            )
            
            # Log final conclusion
            self._log_thought(
                reasoning_log,
                iteration=len(plan.steps) + 1,
                thought_type="conclusion",
                content=f"Task {'completed successfully' if success else 'failed'}. "
                        f"Executed {len(operations)} operations. "
                        f"Artifacts: {list(artifacts.keys())}",
                confidence=1.0 if success else 0.5,
            )

            return AgentResult(
                success=success,
                operations=operations,
                artifacts=artifacts,
                audit_trail=audit_trail,
                reasoning_log=reasoning_log,
            )

        except Exception as e:
            logger.exception(f"Agent execution failed: {e}")
            self._log_thought(
                reasoning_log,
                iteration=-1,
                thought_type="error",
                content=f"Fatal error: {str(e)}",
                confidence=0.0,
            )
            return AgentResult(
                success=False,
                operations=operations,
                artifacts=artifacts,
                audit_trail=audit_trail,
                reasoning_log=reasoning_log,
                error=str(e),
            )
    
    async def _execute_task_iterative(
        self,
        task: str,
        context: str,
        constraints: dict,
    ) -> AgentResult:
        """
        Execute task with iterative planning (ReAct-style).
        
        Flow:
        1. Decide next action based on task + previous results
        2. Execute action with tool
        3. Observe result
        4. Repeat until task complete or max iterations
        
        This allows the agent to adapt its plan based on what it finds.
        
        Example:
            Task: "Fix the bug in auth module"
            
            Iteration 1:
            - Thought: Need to find the auth module first
            - Action: files.search("auth", path="src/")
            - Observation: Found src/auth/login.py, src/auth/session.py
            
            Iteration 2:
            - Thought: Let's read the main auth file
            - Action: files.read_file("src/auth/login.py")
            - Observation: [file content with BUG marker]
            
            Iteration 3:
            - Thought: Found bug, need to fix it
            - Action: files.edit_file("src/auth/login.py", "buggy_code", "fixed_code")
            - Observation: File updated successfully
            
            Iteration 4:
            - Thought: Should verify tests pass
            - Action: tests.pytest("tests/auth/")
            - Observation: All tests passed
            
            Done!
        """
        operations = []
        artifacts = {}
        audit_trail = []
        observation_history = []
        reasoning_log = []

        try:
            logger.info(f"Agent {self.agent_id} executing task (iterative): {task}")
            
            self._log_thought(
                reasoning_log,
                iteration=0,
                thought_type="analysis",
                content=f"[{self.role}] Starting iterative execution: {task}",
            )
            
            max_iterations = constraints.get("max_iterations", 10)
            max_operations = constraints.get("max_operations", 100)
            
            for iteration in range(max_iterations):
                logger.info(f"Iteration {iteration + 1}/{max_iterations}")
                
                # Step 1: Decide next action based on history
                next_step = await self._decide_next_action(
                    task=task,
                    context=context,
                    observation_history=observation_history,
                    constraints=constraints,
                )
                
                # Check if agent thinks task is complete
                if next_step.get("done", False):
                    logger.info("Agent determined task is complete")
                    break
                
                # Step 2: Execute the decided action
                step_info = next_step.get("step")
                if not step_info:
                    logger.warning("No step decided, ending iteration")
                    break
                
                logger.info(f"Executing: {step_info}")
                result = await self._execute_step(step_info)
                
                # Record operation
                operations.append(
                    {
                        "iteration": iteration + 1,
                        "tool": step_info["tool"],
                        "operation": step_info["operation"],
                        "success": result.get("success", False),
                        "error": result.get("error"),
                    }
                )
                
                # Step 3: Observe result and update history
                observation = {
                    "iteration": iteration + 1,
                    "action": step_info,
                    "result": result.get("result"),
                    "success": result.get("success", False),
                    "error": result.get("error"),
                }
                observation_history.append(observation)
                
                # Collect artifacts
                if result.get("success"):
                    self._collect_artifacts(step_info, result, artifacts)
                else:
                    # On error, decide whether to continue
                    if constraints.get("abort_on_error", True):
                        return AgentResult(
                            success=False,
                            operations=operations,
                            artifacts=artifacts,
                            audit_trail=audit_trail,
                            error=f"Iteration {iteration + 1} failed: {result.get('error')}",
                        )
                
                # Check limits
                if len(operations) >= max_operations:
                    logger.warning("Max operations limit reached")
                    break
            
            # Verify completion
            success = all(op["success"] for op in operations)
            
            logger.info(
                f"Task completed: {success} ({len(operations)} operations, "
                f"{len(observation_history)} iterations)"
            )
            
            return AgentResult(
                success=success,
                operations=operations,
                artifacts=artifacts,
                audit_trail=audit_trail,
                reasoning_log=reasoning_log,
            )
            
        except Exception as e:
            logger.exception(f"Agent iterative execution failed: {e}")
            self._log_thought(
                reasoning_log,
                iteration=-1,
                thought_type="error",
                content=f"Fatal error: {str(e)}",
                confidence=0.0,
            )
            return AgentResult(
                success=False,
                operations=operations,
                artifacts=artifacts,
                audit_trail=audit_trail,
                reasoning_log=reasoning_log,
                error=str(e),
            )
    
    async def _decide_next_action(
        self,
        task: str,
        context: str,
        observation_history: list[dict],
        constraints: dict,
    ) -> dict:
        """
        Decide next action based on task and observation history (ReAct-style).
        
        Uses vLLM to analyze:
        - Original task
        - What it's done so far (observation_history)
        - What it learned from previous actions
        
        And intelligently decides what to do next.
        
        Args:
            task: Original task description
            context: Project context
            observation_history: List of previous actions and their results
            constraints: Execution constraints
        
        Returns:
            Dictionary with:
            - done: bool (is task complete?)
            - step: dict (next action to take) or None
            - reasoning: str (why this action?)
        """
        # Get available tools
        available_tools = self.get_available_tools()
        
        # If vLLM client available, use it for intelligent decision
        if self.vllm_client:
            logger.info("Using vLLM for next action decision")
            try:
                decision = await self.vllm_client.decide_next_action(
                    task=task,
                    context=context,
                    observation_history=observation_history,
                    available_tools=available_tools,
                )
                return decision
                
            except Exception as e:
                logger.warning(f"vLLM decision failed: {e}. Using fallback.")
                # Fall through to fallback
        
        # Fallback: Simple heuristic
        logger.info("Using fallback heuristic for next action (vLLM not available)")
        
        if not observation_history:
            # First iteration: generate initial plan
            plan = await self._generate_plan(task, context, constraints)
            if plan.steps:
                return {
                    "done": False,
                    "step": plan.steps[0],
                    "reasoning": "Starting execution with first planned step",
                }
        
        # If we have history, check if last operation succeeded
        if observation_history:
            last = observation_history[-1]
            if not last["success"]:
                # Last operation failed, mark as done (simple heuristic)
                return {
                    "done": True,
                    "step": None,
                    "reasoning": "Previous operation failed, ending iteration",
                }
        
        # Otherwise mark as done
        return {
            "done": True,
            "step": None,
            "reasoning": "Fallback: marking as done",
        }

    async def _generate_plan(
        self, task: str, context: str, constraints: dict
    ) -> ExecutionPlan:
        """
        Generate execution plan from task description.

        The agent uses vLLM to intelligently generate a plan based on:
        - Task description
        - Smart context (2-4K tokens)
        - Available tools and their operations
        - Current mode (read-only vs full execution)

        Args:
            task: Task description
            context: Smart context from Context Service
            constraints: Execution constraints

        Returns:
            ExecutionPlan with steps to execute
        """
        # Get available tools for planning context
        available_tools = self.get_available_tools()
        
        # If vLLM client available, use it for intelligent planning
        if self.vllm_client:
            logger.info("Using vLLM for intelligent plan generation")
            try:
                plan_dict = await self.vllm_client.generate_plan(
                    task=task,
                    context=context,
                    role=self.role,
                    available_tools=available_tools,
                    constraints=constraints,
                )
                
                return ExecutionPlan(
                    steps=plan_dict.get("steps", []),
                    reasoning=plan_dict.get("reasoning", "Generated by vLLM"),
                )
                
            except Exception as e:
                logger.warning(f"vLLM planning failed: {e}. Using fallback.")
                # Fall through to pattern matching
        
        # Fallback: Use simple pattern matching
        logger.info("Using pattern matching for plan generation (vLLM not available)")
        task_lower = task.lower()

        # Pattern: "add function to file"
        if "add" in task_lower and "function" in task_lower:
            return self._plan_add_function(task)

        # Pattern: "fix bug in file"
        if "fix" in task_lower or "bug" in task_lower:
            return self._plan_fix_bug(task)

        # Pattern: "run tests"
        if "test" in task_lower:
            return self._plan_run_tests(task)

        # Default: simple read and report
        return ExecutionPlan(
            steps=[
                {
                    "tool": "files",
                    "operation": "list_files",
                    "params": {"path": ".", "recursive": False},
                }
            ],
            reasoning="Default plan: list files in workspace",
        )

    def _plan_add_function(self, task: str) -> ExecutionPlan:
        """Generate plan for adding a function to a file."""
        # Extract file name from task (simple regex or parsing)
        # For demo, assume format: "Add function_name() to file.py"

        # Default to src/utils.py if not specified
        target_file = "src/utils.py"
        function_name = "hello_world"

        return ExecutionPlan(
            steps=[
                {
                    "tool": "files",
                    "operation": "read_file",
                    "params": {"path": target_file},  # Correct param name
                },
                {
                    "tool": "files",
                    "operation": "append_file",
                    "params": {
                        "path": target_file,  # Correct param name
                        "content": f'\n\ndef {function_name}():\n    """Added by agent."""\n    return "Hello, World!"\n',
                    },
                },
                {
                    "tool": "tests",
                    "operation": "pytest",
                    "params": {"path": "tests/", "markers": "not e2e"},
                },
                {
                    "tool": "git",
                    "operation": "status",
                    "params": {},
                },
            ],
            reasoning=f"Add {function_name}() to {target_file}, run tests, check status",
        )

    def _plan_fix_bug(self, task: str) -> ExecutionPlan:
        """Generate plan for fixing a bug."""
        return ExecutionPlan(
            steps=[
                {
                    "tool": "files",
                    "operation": "search_in_files",
                    "params": {"pattern": "BUG|TODO|FIXME", "path": "src/"},
                },
                {"tool": "tests", "operation": "pytest", "params": {"path": "tests/"}},
            ],
            reasoning="Search for bugs and run tests",
        )

    def _plan_run_tests(self, task: str) -> ExecutionPlan:
        """Generate plan for running tests."""
        return ExecutionPlan(
            steps=[
                {
                    "tool": "tests",
                    "operation": "pytest",
                    "params": {"path": "tests/", "verbose": True},
                }
            ],
            reasoning="Run pytest suite",
        )

    async def _execute_step(self, step: dict) -> dict:
        """
        Execute a single plan step.

        Args:
            step: {"tool": "files", "operation": "read_file", "params": {...}}

        Returns:
            {"success": bool, "result": Any, "error": str | None}
        """
        tool_name = step["tool"]
        operation = step["operation"]
        params = step.get("params", {})

        try:
            # Get tool
            tool = self.tools.get(tool_name)
            if not tool:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

            # Check if operation is allowed based on enable_tools flag
            if not self.enable_tools:
                # In read-only mode, only allow read operations
                if not self._is_read_only_operation(tool_name, operation):
                    logger.warning(
                        f"Operation {tool_name}.{operation} blocked in read-only mode"
                    )
                    return {
                        "success": False,
                        "error": f"Write operation '{operation}' not allowed in read-only mode",
                        "skipped": True,
                    }

            # Get method
            method = getattr(tool, operation, None)
            if not method:
                return {
                    "success": False,
                    "error": f"Unknown operation: {tool_name}.{operation}",
                }

            # Execute
            result = method(**params)

            # Check if result is a tool result object (has .success attribute)
            if hasattr(result, "success"):
                # Get error message from result object
                error_msg = None
                if not result.success:
                    # Try different error attribute names
                    error_msg = getattr(result, "error", None) or getattr(result, "stderr", "")
                
                return {
                    "success": result.success,
                    "result": result,
                    "error": error_msg,
                }

            # Otherwise assume success
            return {"success": True, "result": result, "error": None}

        except Exception as e:
            logger.exception(f"Step execution failed: {e}")
            return {"success": False, "error": str(e)}

    def _is_read_only_operation(self, tool_name: str, operation: str) -> bool:
        """
        Check if an operation is read-only (allowed in planning mode).

        Read-only operations are those that don't modify state:
        - File reads, searches, lists (but not writes, edits, deletes)
        - Git log, status, diff (but not add, commit, push)
        - Test runs (read-only - checks existing code)
        - Database queries (read-only)
        - HTTP GET (read-only)
        - Docker ps, logs (read-only)

        Args:
            tool_name: Name of the tool
            operation: Operation to check

        Returns:
            True if operation is read-only, False otherwise
        """
        # Define read-only operations per tool
        read_only_ops = {
            "files": {
                "read_file",
                "search_in_files",
                "list_files",
                "file_info",
                "diff_files",
            },
            "git": {
                "status",
                "log",
                "diff",
                "branch",  # Listing branches only
            },
            "tests": {
                "pytest",
                "go_test",
                "npm_test",
                "cargo_test",
                "make_test",
            },
            "db": {
                "postgresql_query",  # SELECT queries only (tool validates)
                "redis_command",     # GET commands only (tool validates)
                "neo4j_query",       # MATCH queries only (tool validates)
            },
            "http": {
                "get",    # GET is read-only
                "head",   # HEAD is read-only
            },
            "docker": {
                "ps",     # List containers
                "logs",   # Read logs
            },
        }

        allowed_ops = read_only_ops.get(tool_name, set())
        return operation in allowed_ops

    def _log_thought(
        self,
        reasoning_log: list[dict],
        iteration: int,
        thought_type: str,
        content: str,
        related_operations: list[str] | None = None,
        confidence: float | None = None,
    ) -> None:
        """
        Log agent's internal thought/reasoning.
        
        This captures the agent's "stream of consciousness" for observability.
        
        Args:
            reasoning_log: List to append thought to
            iteration: Which iteration/step this thought belongs to
            thought_type: Type of thought (analysis, decision, action, observation, conclusion, error)
            content: The thought content
            related_operations: Tool operations this thought relates to
            confidence: Confidence level (0.0-1.0)
        """
        from datetime import datetime, timezone
        
        thought = {
            "agent_id": self.agent_id,
            "role": self.role,
            "iteration": iteration,
            "type": thought_type,
            "content": content,
            "related_operations": related_operations or [],
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        reasoning_log.append(thought)
        
        # Also log to standard logger for real-time observability
        logger.info(f"[{self.agent_id}] {thought_type.upper()}: {content}")
    
    def _summarize_result(self, step: dict, result: dict) -> str:
        """
        Summarize tool operation result for logging.
        
        Creates human-readable summary of what the tool returned.
        
        Args:
            step: The step that was executed
            result: The result from the tool
        
        Returns:
            Human-readable summary
        """
        tool_name = step["tool"]
        operation = step["operation"]
        tool_result = result.get("result")
        
        # Files
        if tool_name == "files":
            if operation == "read_file":
                if hasattr(tool_result, "content"):
                    lines = len(tool_result.content.split("\n"))
                    return f"Read file ({lines} lines)"
            elif operation == "list_files":
                if hasattr(tool_result, "content"):
                    files = tool_result.content.split("\n")
                    return f"Found {len(files)} files"
            elif operation == "search_in_files":
                if hasattr(tool_result, "content"):
                    matches = len([l for l in tool_result.content.split("\n") if l.strip()])
                    return f"Found {matches} matches"
            elif operation in ["write_file", "append_file", "edit_file"]:
                return f"Modified {step['params'].get('path', 'file')}"
        
        # Git
        if tool_name == "git":
            if operation == "status":
                if hasattr(tool_result, "stdout"):
                    changes = len([l for l in tool_result.stdout.split("\n") if l.strip() and not l.startswith("#")])
                    return f"{changes} files changed"
            elif operation == "log":
                if hasattr(tool_result, "stdout"):
                    commits = len([l for l in tool_result.stdout.split("\n") if l.strip()])
                    return f"{commits} commits in history"
            elif operation == "commit":
                return "Created commit"
        
        # Tests
        if tool_name == "tests":
            if hasattr(tool_result, "stdout"):
                if "passed" in tool_result.stdout:
                    # Extract "5 passed"
                    for word in tool_result.stdout.split():
                        if word.isdigit():
                            return f"{word} tests passed"
        
        # Database
        if tool_name == "db":
            if hasattr(tool_result, "content"):
                rows = len(tool_result.content.split("\n"))
                return f"Query returned {rows} rows"
        
        # HTTP
        if tool_name == "http":
            if hasattr(tool_result, "status_code"):
                return f"HTTP {tool_result.status_code}"
        
        # Default
        return "Operation completed"
    
    def _collect_artifacts(
        self, step: dict, result: dict, artifacts: dict
    ) -> None:
        """
        Collect artifacts from step execution.

        Artifacts:
        - commit_sha: from git.commit()
        - files_changed: list of modified files
        - test_results: from tests.pytest()
        - etc.
        """
        tool_name = step["tool"]
        operation = step["operation"]
        tool_result = result.get("result")

        # Git operations
        if tool_name == "git":
            if operation == "commit" and hasattr(tool_result, "stdout"):
                # Extract commit SHA from output
                if "commit" in tool_result.stdout.lower():
                    artifacts["commit_sha"] = tool_result.stdout.split()[1][:7]

            if operation == "status" and hasattr(tool_result, "stdout"):
                # Extract changed files
                changed = [
                    line.split()[-1]
                    for line in tool_result.stdout.split("\n")
                    if line.strip() and not line.startswith("#")
                ]
                artifacts.setdefault("files_changed", []).extend(changed)

        # Test operations
        if tool_name == "tests":
            if operation == "pytest" and hasattr(tool_result, "stdout"):
                # Extract test results
                if "passed" in tool_result.stdout.lower():
                    artifacts["tests_passed"] = True
                    # Parse "5 passed in 0.3s"
                    for word in tool_result.stdout.split():
                        if word.isdigit():
                            artifacts["tests_count"] = int(word)
                            break

        # File operations
        if tool_name == "files":
            if operation in ["write_file", "append_file", "edit_file"]:
                file_path = step["params"].get("file_path")
                if file_path:
                    artifacts.setdefault("files_modified", []).append(file_path)

