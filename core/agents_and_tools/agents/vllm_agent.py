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
    tests.pytest(TESTS_PATH + "auth/"),                # Only auth tests
    git.commit("feat: add JWT token generation")
]

# Result: Fast (seconds), cheap (few API calls), accurate ✅
```

This agent receives a task and smart context, uses vLLM to generate a plan,
then executes the plan using targeted tool operations.
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import Any

from core.agents_and_tools.agents.application.usecases.generate_next_action_usecase import (
    GenerateNextActionUseCase,
)
from core.agents_and_tools.agents.application.usecases.generate_plan_usecase import GeneratePlanUseCase
from core.agents_and_tools.agents.domain.entities.agent_result import AgentResult
from core.agents_and_tools.agents.domain.entities.execution_plan import ExecutionPlan
from core.agents_and_tools.agents.infrastructure.adapters.tool_factory import ToolFactory
from core.agents_and_tools.agents.infrastructure.adapters.vllm_client_adapter import VLLMClientAdapter
from core.agents_and_tools.agents.infrastructure.dtos.agent_initialization_config import (
    AgentInitializationConfig,
)

logger = logging.getLogger(__name__)

# Constants
TESTS_PATH = "tests/"


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

    def __init__(self, config: AgentInitializationConfig):
        """
        Initialize vLLM agent.

        Args:
            config: AgentInitializationConfig with all initialization parameters (required)

        Note:
            The agent should be initialized with `config` to maintain separation
            of concerns between bounded contexts. Config is required (fail-first).
        """
        # Use config values (all validated in AgentInitializationConfig.__post_init__)
        self.agent_id = config.agent_id
        self.role = config.role  # Already normalized in config
        self.workspace_path = config.workspace_path
        self.vllm_url = config.vllm_url
        self.audit_callback = config.audit_callback
        self.enable_tools = config.enable_tools

        # Initialize use cases (vllm_url is required)
        if not self.vllm_url:
            raise ValueError("vllm_url is required for VLLMAgent. Provide it in AgentInitializationConfig.")

        # Load role-specific model configuration using use case
        from core.agents_and_tools.agents.application.usecases.load_profile_usecase import (
            LoadProfileUseCase,
        )
        from core.agents_and_tools.agents.infrastructure.adapters.profile_config import ProfileConfig
        from core.agents_and_tools.agents.infrastructure.adapters.yaml_profile_adapter import (
            YamlProfileLoaderAdapter,
        )

        # Get default profiles directory (fail-fast: must exist)
        profiles_url = ProfileConfig.get_default_profiles_url()
        profile_adapter = YamlProfileLoaderAdapter(profiles_url)

        # Use case with injected adapter
        load_profile_usecase = LoadProfileUseCase(profile_adapter)
        profile = load_profile_usecase.execute(self.role)

        # Create adapter
        llm_adapter = VLLMClientAdapter(
            vllm_url=self.vllm_url,
            model=profile.model,
            temperature=profile.temperature,
            max_tokens=profile.max_tokens,
        )

        # Create use cases
        self.generate_plan_usecase = GeneratePlanUseCase(llm_adapter)
        self.generate_next_action_usecase = GenerateNextActionUseCase(llm_adapter)

        logger.info(
            f"Use cases initialized for {self.role}: {profile.model} "
            f"(temp={profile.temperature}, max_tokens={profile.max_tokens})"
        )

        # Initialize tool factory (handles all tool creation and lifecycle)
        # The enable_tools flag controls WHICH operations are allowed, not whether tools exist
        self.toolset = ToolFactory(
            workspace_path=self.workspace_path,
            audit_callback=self.audit_callback,
        )

        # Pre-create all tools and cache them (lazy initialization in factory)
        self.tools = self.toolset.get_all_tools()

        mode = "full execution" if self.enable_tools else "read-only (planning)"
        logger.info(
            f"VLLMAgent initialized: {self.agent_id} ({self.role}) at {self.workspace_path} [{mode}]"
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
            - summary: summary of available tools
        """
        # Delegate to toolset
        return self.toolset.get_available_tools_description(enable_write_operations=self.enable_tools)

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
                content=(
                    f"[{self.role}] Analyzing task: {task}. "
                    f"Mode: {'full execution' if self.enable_tools else 'planning only'}"
                ),
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
                    new_artifacts = self._collect_artifacts(step, result, artifacts)
                    artifacts.update(new_artifacts)

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
            - Action: tests.pytest(TESTS_PATH + "auth/")
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
                    new_artifacts = self._collect_artifacts(step_info, result, artifacts)
                    artifacts.update(new_artifacts)
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

        # If use case available, use it for intelligent decision
        if self.generate_next_action_usecase:
            logger.info("Using use case for next action decision")
            try:
                decision = await self.generate_next_action_usecase.execute(
                    task=task,
                    context=context,
                    observation_history=observation_history,
                    available_tools=available_tools,
                )
                return decision

            except Exception as e:
                logger.warning(f"Next action decision failed: {e}. Using fallback.")
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

        # If use case available, use it for intelligent planning
        if self.generate_plan_usecase:
            logger.info("Using use case for intelligent plan generation")
            try:
                plan_dict = await self.generate_plan_usecase.execute(
                    task=task,
                    context=context,
                    role=self.role,
                    available_tools=available_tools,
                    constraints=constraints,
                )

                return ExecutionPlan(
                    steps=plan_dict.get("steps", []),
                    reasoning=plan_dict.get("reasoning", "Generated by LLM"),
                )

            except Exception as e:
                logger.warning(f"Plan generation failed: {e}. Using fallback.")
                # Fall through to pattern matching

        # Fallback: Use simple pattern matching
        logger.info("Using pattern matching for plan generation (vLLM not available)")
        task_lower = task.lower()

        # Pattern: "add function to file"
        if "add" in task_lower and "function" in task_lower:
            return self._plan_add_function(task)

        # Pattern: "fix bug in file"
        if "fix" in task_lower or "bug" in task_lower:
            return self._plan_fix_bug()

        # Pattern: "run tests"
        if "test" in task_lower:
            return self._plan_run_tests()

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
                        "content": (
                            f'\n\ndef {function_name}():\n    """Added by agent."""\n    '
                            f'return "Hello, World!"\n'
                        ),
                    },
                },
                {
                    "tool": "tests",
                    "operation": "pytest",
                    "params": {"path": TESTS_PATH, "markers": "not e2e"},
                },
                {
                    "tool": "git",
                    "operation": "status",
                    "params": {},
                },
            ],
            reasoning=f"Add {function_name}() to {target_file}, run tests, check status",
        )

    def _plan_fix_bug(self) -> ExecutionPlan:
        """Generate plan for fixing a bug."""
        return ExecutionPlan(
            steps=[
                {
                    "tool": "files",
                    "operation": "search_in_files",
                    "params": {"pattern": "BUG|TODO|FIXME", "path": "src/"},
                },
                {"tool": "tests", "operation": "pytest", "params": {"path": TESTS_PATH}},
            ],
            reasoning="Search for bugs and run tests",
        )

    def _plan_run_tests(self) -> ExecutionPlan:
        """Generate plan for running tests."""
        return ExecutionPlan(
            steps=[
                {
                    "tool": "tests",
                    "operation": "pytest",
                    "params": {"path": TESTS_PATH, "verbose": True},
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
            # Delegate to toolset for execution (returns domain entity)
            # ToolFactory handles read-only verification based on enable_tools flag
            try:
                result = self.toolset.execute_operation(
                    tool_name,
                    operation,
                    params,
                    enable_write=self.enable_tools,
                )

                # Use domain entity attributes directly
                error_msg = result.error if not result.success else None
                if not result.success and not error_msg:
                    error_msg = "Unknown error"

                return {
                    "success": result.success,
                    "result": result,
                    "error": error_msg,
                }
            except ValueError as e:
                return {"success": False, "error": str(e)}

        except Exception as e:
            logger.exception(f"Step execution failed: {e}")
            return {"success": False, "error": str(e)}


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
        from datetime import datetime

        thought = {
            "agent_id": self.agent_id,
            "role": self.role,
            "iteration": iteration,
            "type": thought_type,
            "content": content,
            "related_operations": related_operations or [],
            "confidence": confidence,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        reasoning_log.append(thought)

        # Also log to standard logger for real-time observability
        logger.info(f"[{self.agent_id}] {thought_type.upper()}: {content}")

    def _summarize_result(self, step: dict, result: dict) -> str:
        """
        Summarize tool operation result for logging.

        Delegates to the tool's own summarize_result method.

        Args:
            step: The step that was executed
            result: The result from the tool

        Returns:
            Human-readable summary
        """
        tool_name = step["tool"]
        operation = step["operation"]
        tool_result = result.get("result")
        params = step.get("params", {})

        # Get the tool instance from factory cache
        tool = self.toolset.get_tool_by_name(tool_name)
        if not tool:
            return "Operation completed"

        # Delegate to tool's summarize_result method
        return tool.summarize_result(operation, tool_result, params)

    def _collect_artifacts(
        self, step: dict, result: dict, artifacts: dict
    ) -> dict:
        """
        Collect artifacts from step execution.

        Delegates to the tool's own collect_artifacts method.

        Args:
            step: Step that was executed
            result: Result from the tool
            artifacts: Current artifacts dict

        Returns:
            New artifacts collected from this step
        """
        tool_name = step["tool"]
        operation = step["operation"]
        tool_result = result.get("result")
        params = step.get("params", {})

        # Get the tool instance from factory cache
        tool = self.toolset.get_tool_by_name(tool_name)
        if not tool:
            return {}

        # Delegate to tool's collect_artifacts method
        return tool.collect_artifacts(operation, tool_result, params)

