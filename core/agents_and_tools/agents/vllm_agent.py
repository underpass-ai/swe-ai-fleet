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
from typing import Any

from core.agents_and_tools.agents.application.dtos.next_action_dto import NextActionDTO
from core.agents_and_tools.agents.application.usecases.generate_next_action_usecase import (
    GenerateNextActionUseCase,
)
from core.agents_and_tools.agents.application.usecases.generate_plan_usecase import GeneratePlanUseCase
from core.agents_and_tools.agents.domain.entities.agent_result import AgentResult
from core.agents_and_tools.agents.domain.entities.artifacts import Artifacts
from core.agents_and_tools.agents.domain.entities.audit_trails import AuditTrails
from core.agents_and_tools.agents.domain.entities.execution_constraints import ExecutionConstraints
from core.agents_and_tools.agents.domain.entities.execution_plan import ExecutionPlan
from core.agents_and_tools.agents.domain.entities.execution_step import ExecutionStep
from core.agents_and_tools.agents.domain.entities.observation_histories import ObservationHistories
from core.agents_and_tools.agents.domain.entities.operations import Operations
from core.agents_and_tools.agents.domain.entities.reasoning_logs import ReasoningLogs
from core.agents_and_tools.agents.domain.entities.step_execution_result import StepExecutionResult
from core.agents_and_tools.agents.infrastructure.adapters.tool_factory import ToolFactory
from core.agents_and_tools.agents.infrastructure.adapters.vllm_client_adapter import VLLMClientAdapter
from core.agents_and_tools.agents.infrastructure.dtos.agent_initialization_config import (
    AgentInitializationConfig,
)
from core.agents_and_tools.agents.infrastructure.mappers.execution_step_mapper import ExecutionStepMapper
from core.agents_and_tools.common.domain.entities import AgentCapabilities

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

        # Initialize mapper for converting dicts to ExecutionStep entities
        # This eliminates reflection (.get()) from domain logic
        self.step_mapper = ExecutionStepMapper()

        mode = "full execution" if self.enable_tools else "read-only (planning)"
        logger.info(
            f"VLLMAgent initialized: {self.agent_id} ({self.role}) at {self.workspace_path} [{mode}]"
        )

    def get_available_tools(self) -> AgentCapabilities:
        """
        Get description of available tools and their operations.

        Returns a structured description of all tools the agent can use,
        including which operations are available in read-only mode.

        This is used to inform the LLM about the agent's capabilities
        so it can generate realistic, executable plans.

        Returns:
            AgentCapabilities entity with tools, mode, capabilities, and summary
        """
        # Delegate to toolset
        return self.toolset.get_available_tools_description(enable_write_operations=self.enable_tools)

    async def execute_task(
        self,
        task: str,
        constraints: ExecutionConstraints,
        context: str = "",
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
            constraints: Execution constraints entity (None for defaults):
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
        if constraints.iterative:
            return await self._execute_task_iterative(task, context, constraints)
        else:
            return await self._execute_task_static(task, context, constraints)

    async def _execute_task_static(
        self,
        task: str,
        context: str,
        constraints: ExecutionConstraints,
    ) -> AgentResult:
        """
        Execute task with static planning (original behavior).

        Flow:
        1. Generate full plan upfront
        2. Execute all steps sequentially
        3. Return results
        """
        operations = Operations()
        artifacts = Artifacts()
        audit_trail = AuditTrails()
        reasoning_log = ReasoningLogs()

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
                related_operations=[f"{s.tool}.{s.operation}" for s in plan.steps],
            )

            # Step 2: Execute plan
            for i, step in enumerate(plan.steps):
                logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step}")

                # Ensure step is ExecutionStep entity
                step_entity = self._ensure_execution_step(step)

                # Log what agent is about to do
                self._log_thought(
                    reasoning_log,
                    iteration=i + 1,
                    thought_type="action",
                    content=f"Executing: {step_entity.tool}.{step_entity.operation}({step_entity.params or {}})",
                )

                result = await self._execute_step(step_entity)

                # Log observation
                if result.success:
                    self._log_thought(
                        reasoning_log,
                        iteration=i + 1,
                        thought_type="observation",
                        content=(
                            f"✅ Operation succeeded. "
                            f"{self._summarize_result(step_entity, result.result, step_entity.params or {})}"
                        ),
                        confidence=1.0,
                    )
                else:
                    self._log_thought(
                        reasoning_log,
                        iteration=i + 1,
                        thought_type="observation",
                        content=f"❌ Operation failed: {result.error or 'Unknown error'}",
                        confidence=0.0,
                    )

                operations.add(
                    tool_name=step_entity.tool,
                    operation=step_entity.operation,
                    success=result.success,
                    params=step_entity.params,
                    result=result.result,
                    error=result.error,
                )

                # Collect artifacts
                if result.success:
                    new_artifacts = self._collect_artifacts(step_entity, result.result, artifacts)
                    artifacts.update_from_dict(new_artifacts)

                # Check if step failed
                if not result.success:
                    error_msg = result.error or "Unknown error"
                    logger.error(f"Step {i+1} failed: {error_msg}")

                    # Decide: abort or continue?
                    if constraints.abort_on_error:
                        return AgentResult(
                            success=False,
                            operations=operations,
                            artifacts=artifacts,
                            audit_trail=audit_trail,
                            error=f"Step {i+1} failed: {error_msg}",
                        )

                # Check max operations limit
                if i + 1 >= constraints.max_operations:
                    logger.warning("Max operations limit reached")
                    break

            # Step 3: Verify completion
            success = all(op.success for op in operations.get_all())

            logger.info(
                f"Task completed: {success} ({operations.count()} operations)"
            )

            # Log final conclusion
            self._log_thought(
                reasoning_log,
                iteration=len(plan.steps) + 1,
                thought_type="conclusion",
                content=f"Task {'completed successfully' if success else 'failed'}. "
                        f"Executed {operations.count()} operations. "
                        f"Artifacts: {list(artifacts.get_all().keys())}",
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
        constraints: ExecutionConstraints,
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
        operations = Operations()
        artifacts = Artifacts()
        audit_trail = AuditTrails()
        observation_history = ObservationHistories()
        reasoning_log = ReasoningLogs()

        try:
            logger.info(f"Agent {self.agent_id} executing task (iterative): {task}")

            self._log_thought(
                reasoning_log,
                iteration=0,
                thought_type="analysis",
                content=f"[{self.role}] Starting iterative execution: {task}",
            )

            max_iterations = constraints.max_iterations
            max_operations = constraints.max_operations

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
                if next_step.done:
                    logger.info("Agent determined task is complete")
                    break

                # Step 2: Execute the decided action
                step_info = next_step.step
                if not step_info:
                    logger.warning("No step decided, ending iteration")
                    break

                logger.info(f"Executing: {step_info}")
                result = await self._execute_step(step_info)

                # Record operation
                operations.add(
                    tool_name=step_info["tool"],
                    operation=step_info["operation"],
                    params=self._get_step_params(step_info),
                    result=result.result,
                    success=result.success,
                    error=result.error,
                )

                # Step 3: Observe result and update history
                observation_history.add(
                    iteration=iteration + 1,
                    action=step_info,
                    result=result.result,
                    success=result.success,
                    error=result.error,
                )

                # Collect artifacts
                if result.success:
                    new_artifacts = self._collect_artifacts(step_info, result.result, artifacts)
                    artifacts.update_from_dict(new_artifacts)
                else:
                    # On error, decide whether to continue
                    if constraints.abort_on_error:
                        return AgentResult(
                            success=False,
                            operations=operations,
                            artifacts=artifacts,
                            audit_trail=audit_trail,
                            error=f"Iteration {iteration + 1} failed: {result.error}",
                        )

                # Check limits
                if operations.count() >= max_operations:
                    logger.warning("Max operations limit reached")
                    break

            # Verify completion
            success = all(op.success for op in operations.get_all())

            logger.info(
                f"Task completed: {success} ({operations.count()} operations, "
                        f"{observation_history.count()} iterations)"
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
        observation_history: ObservationHistories,
        constraints: ExecutionConstraints,
    ) -> NextActionDTO:
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
            NextActionDTO with done, step, and reasoning
        """
        # Get available tools
        available_tools = self.get_available_tools()

        # Use case is required - no fallbacks
        if not self.generate_next_action_usecase:
            raise RuntimeError("Next action use case not available - vLLM must be configured")

        logger.info("Using use case for next action decision")
        decision = await self.generate_next_action_usecase.execute(
            task=task,
            context=context,
            observation_history=observation_history,
            available_tools=available_tools,
        )
        return decision

    async def _generate_plan(
        self, task: str, context: str, constraints: ExecutionConstraints
    ) -> ExecutionPlan:
        """
        Generate execution plan from task description.

        Delegates to GeneratePlanUseCase for business logic.

        Args:
            task: Task description
            context: Smart context from Context Service
            constraints: Execution constraints

        Returns:
            ExecutionPlan with steps to execute
        """
        # Get available tools for planning context
        available_tools = self.get_available_tools()

        # Use case handles all business logic (LLM + fallback)
        if self.generate_plan_usecase:
            logger.info("Using use case for plan generation")
            plan_dto = await self.generate_plan_usecase.execute(
                task=task,
                context=context,
                role=self.role,
                available_tools=available_tools,
                constraints=constraints,
            )

            # Convert DTO to domain entity
            return ExecutionPlan(
                steps=plan_dto.steps,
                reasoning=plan_dto.reasoning,
            )
        else:
            # No use case available - should not happen in production
            logger.warning("No plan generation use case available")
            from core.agents_and_tools.agents.domain.entities.execution_step import ExecutionStep

            fallback_step = ExecutionStep(
                tool="files",
                operation="list_files",
                params={"path": ".", "recursive": False}
            )

            return ExecutionPlan(
                steps=[fallback_step],
                reasoning="No planning use case available",
            )


    async def _execute_step(self, step: dict | ExecutionStep) -> StepExecutionResult:
        """
        Execute a single plan step.

        Args:
            step: ExecutionStep entity or dict with tool, operation, params

        Returns:
            StepExecutionResult with success, result entity, and error
        """
        # Convert dict to ExecutionStep if needed (eliminates reflection)
        step_entity = self._ensure_execution_step(step)

        tool_name = step_entity.tool
        operation = step_entity.operation
        params = step_entity.params or {}

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

                return StepExecutionResult(
                    success=result.success,
                    result=result,
                    error=error_msg,
                    operation=operation,
                    tool_name=tool_name,
                )
            except ValueError as e:
                return StepExecutionResult(
                    success=False,
                    result=None,
                    error=str(e),
                    operation=operation,
                    tool_name=tool_name,
                )

        except Exception as e:
            logger.exception(f"Step execution failed: {e}")
            return StepExecutionResult(
                success=False,
                result=None,
                error=str(e),
                operation=operation,
                tool_name=tool_name,
            )


    def _log_thought(
        self,
        reasoning_log: ReasoningLogs,
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
        reasoning_log.add(
            agent_id=self.agent_id,
            role=self.role,
            iteration=iteration,
            thought_type=thought_type,
            content=content,
            related_operations=related_operations,
            confidence=confidence,
        )

        # Also log to standard logger for real-time observability
        logger.info(f"[{self.agent_id}] {thought_type.upper()}: {content}")

    def _summarize_result(self, step: dict | ExecutionStep, tool_result: Any, params: dict[str, Any]) -> str:
        """
        Summarize tool operation result for logging.

        Delegates to the tool's own summarize_result method.

        Args:
            step: The step that was executed (dict or ExecutionStep)
            tool_result: The actual result domain entity from the tool
            params: Operation parameters

        Returns:
            Human-readable summary
        """
        # Convert to ExecutionStep entity (eliminates reflection)
        step_entity = self._ensure_execution_step(step)

        tool_name = step_entity.tool
        operation = step_entity.operation

        # Get the tool instance from factory cache
        tool = self.toolset.get_tool_by_name(tool_name)
        if not tool:
            return "Operation completed"

        # Delegate to tool's summarize_result method
        return tool.summarize_result(operation, tool_result, params)

    def _ensure_execution_step(self, step: dict | ExecutionStep) -> ExecutionStep:
        """
        Convert step (dict or ExecutionStep) to ExecutionStep entity.

        This helper eliminates reflection (.get()) by using mapper.

        Args:
            step: Step as dict or ExecutionStep

        Returns:
            ExecutionStep entity
        """
        if isinstance(step, ExecutionStep):
            return step
        # Convert dict to ExecutionStep using mapper (eliminates reflection)
        return self.step_mapper.to_entity(step)

    def _get_step_params(self, step: dict | ExecutionStep) -> dict[str, Any]:
        """
        Extract params from step (dict or ExecutionStep).

        This helper delegates to _ensure_execution_step to eliminate reflection.

        Args:
            step: Step as dict or ExecutionStep

        Returns:
            Params dict (empty dict if None)
        """
        step_entity = self._ensure_execution_step(step)
        return step_entity.params or {}

    def _collect_artifacts(
        self, step: dict | ExecutionStep, result: Any, artifacts: dict[str, Any]
    ) -> dict:
        """
        Collect artifacts from step execution.

        Delegates to the tool's own collect_artifacts method.

        Args:
            step: Step that was executed (dict or ExecutionStep)
            result: Result from the tool
            artifacts: Current artifacts dict

        Returns:
            New artifacts collected from this step
        """
        # Convert to ExecutionStep entity (eliminates reflection)
        step_entity = self._ensure_execution_step(step)

        tool_name = step_entity.tool
        operation = step_entity.operation
        params = step_entity.params or {}

        # result is now the actual domain entity from tool
        tool_result = result

        # Get the tool instance from factory cache
        tool = self.toolset.get_tool_by_name(tool_name)
        if not tool:
            return {}

        # Delegate to tool's collect_artifacts method
        return tool.collect_artifacts(operation, tool_result, params)

