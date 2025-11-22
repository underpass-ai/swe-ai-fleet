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

import asyncio
import logging
from typing import Any

from core.agents_and_tools.agents.application.dtos.next_action_dto import NextActionDTO
from core.agents_and_tools.agents.application.usecases.execute_task_iterative_usecase import (
    ExecuteTaskIterativeUseCase,
)
from core.agents_and_tools.agents.application.usecases.execute_task_usecase import ExecuteTaskUseCase
from core.agents_and_tools.agents.application.usecases.generate_next_action_usecase import (
    GenerateNextActionUseCase,
)
from core.agents_and_tools.agents.application.usecases.generate_plan_usecase import GeneratePlanUseCase
from core.agents_and_tools.agents.domain.entities import (
    AgentResult,
    ExecutionConstraints,
    ExecutionPlan,
    ExecutionStep,
    ObservationHistories,
    ReasoningLogs,
    StepExecutionResult,
)
from core.agents_and_tools.agents.domain.entities.core.agent import Agent
from core.agents_and_tools.agents.domain.entities.core.agent_id import AgentId
from core.agents_and_tools.agents.domain.entities.rbac import Action
from core.agents_and_tools.agents.domain.ports.llm_client import LLMClientPort
from core.agents_and_tools.agents.infrastructure.dtos.agent_initialization_config import (
    AgentInitializationConfig,
)
from core.agents_and_tools.agents.infrastructure.mappers.execution_step_mapper import ExecutionStepMapper
from core.agents_and_tools.common.domain.entities import AgentCapabilities
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort

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

    def __init__(
        self,
        config: AgentInitializationConfig,
        llm_client_port: LLMClientPort,
        tool_execution_port: ToolExecutionPort,
        generate_plan_usecase: GeneratePlanUseCase,
        generate_next_action_usecase: GenerateNextActionUseCase,
        step_mapper: ExecutionStepMapper,
        execute_task_usecase: ExecuteTaskUseCase,
        execute_task_iterative_usecase: ExecuteTaskIterativeUseCase,
    ):
        """
        Initialize vLLM agent with all dependencies (fail-fast).

        Args:
            config: AgentInitializationConfig with all initialization parameters (required)
            llm_client_port: LLM client port for communication (required)
            tool_execution_port: Tool execution port (required)
            generate_plan_usecase: Use case for generating execution plans (required)
            generate_next_action_usecase: Use case for deciding next action (required)
            step_mapper: Mapper for converting execution steps (required)
            execute_task_usecase: Use case for executing tasks with static planning (required)
            execute_task_iterative_usecase: Use case for executing tasks iteratively (required)

        Note:
            All dependencies must be provided. This ensures hexagonal architecture
            and enables full testability through dependency injection.

            VLLMAgent is now a thin facade that delegates to use cases.
        """
        # Use config values (all validated in AgentInitializationConfig.__post_init__)
        self.agent_id = config.agent_id
        self.role = config.role  # Role value object (RBAC)
        self.workspace_path = config.workspace_path
        self.vllm_url = config.vllm_url
        self.audit_callback = config.audit_callback
        self.enable_tools = config.enable_tools

        # Fail fast: all dependencies required
        if not llm_client_port:
            raise ValueError("llm_client_port is required (fail-fast)")
        if not tool_execution_port:
            raise ValueError("tool_execution_port is required (fail-fast)")
        if not generate_plan_usecase:
            raise ValueError("generate_plan_usecase is required (fail-fast)")
        if not generate_next_action_usecase:
            raise ValueError("generate_next_action_usecase is required (fail-fast)")
        if not step_mapper:
            raise ValueError("step_mapper is required (fail-fast)")
        if not execute_task_usecase:
            raise ValueError("execute_task_usecase is required (fail-fast)")
        if not execute_task_iterative_usecase:
            raise ValueError("execute_task_iterative_usecase is required (fail-fast)")

        # Store injected dependencies
        self.llm_client_port = llm_client_port
        self.tool_execution_port = tool_execution_port
        self.generate_plan_usecase = generate_plan_usecase
        self.generate_next_action_usecase = generate_next_action_usecase
        self.step_mapper = step_mapper
        self.execute_task_usecase = execute_task_usecase
        self.execute_task_iterative_usecase = execute_task_iterative_usecase

        # For backward compatibility, keep direct access to tools dict
        # Pre-create all tools and cache them (lazy initialization)
        self.tools = self.tool_execution_port.get_all_tools()

        # Keep self.toolset for backward compatibility (delegates to port)
        # This ensures existing code continues to work
        self.toolset = self.tool_execution_port

        # Create Agent aggregate root with RBAC-filtered capabilities
        # 1. Get all available capabilities from toolset
        all_capabilities = self.tool_execution_port.get_available_tools_description(
            enable_write_operations=self.enable_tools
        )

        # 2. Filter capabilities by role's allowed_tools (RBAC enforcement)
        filtered_capabilities = all_capabilities.filter_by_allowed_tools(self.role.allowed_tools)

        # 3. Create Agent aggregate root (encapsulates identity + role + capabilities)
        self.agent = Agent(
            agent_id=AgentId(self.agent_id),
            role=self.role,
            name=f"{self.role.get_name()} Agent ({self.agent_id})",
            capabilities=filtered_capabilities,
        )

        mode = "full execution" if self.enable_tools else "read-only (planning)"
        logger.info(
            f"VLLMAgent initialized: {self.agent_id} ({self.role.get_name()}) "
            f"at {self.workspace_path} [{mode}]"
        )

    def get_available_tools(self) -> AgentCapabilities:
        """
        Get description of available tools and their operations (RBAC-filtered).

        Returns capabilities filtered by the agent's role permissions.
        Only tools that the role is allowed to use are included.

        This enforces RBAC at the domain level: the agent's capabilities
        are automatically restricted based on its role.

        This is used to inform the LLM about the agent's capabilities
        so it can generate realistic, executable plans.

        Returns:
            AgentCapabilities entity with RBAC-filtered tools, mode, operations, and summary

        Examples:
            >>> # Architect agent can only access files, git, db, http (read-only)
            >>> architect_agent.get_available_tools()
            AgentCapabilities(tools=['files', 'git', 'db', 'http'], mode='read_only', ...)

            >>> # Developer agent can access files, git, tests (read/write)
            >>> developer_agent.get_available_tools()
            AgentCapabilities(tools=['files', 'git', 'tests'], mode='full', ...)
        """
        # Return RBAC-filtered capabilities from Agent aggregate root
        return self.agent.capabilities

    def can_execute(self, action: Action) -> bool:
        """
        Check if agent can execute the given action (RBAC enforcement).

        Delegates to Agent aggregate root for RBAC logic.

        Args:
            action: The Action to check

        Returns:
            True if agent can execute action, False otherwise

        Examples:
            >>> from core.agents_and_tools.agents.domain.entities.rbac import Action, ActionEnum
            >>> architect_agent.can_execute(Action(value=ActionEnum.APPROVE_DESIGN))
            True
            >>> architect_agent.can_execute(Action(value=ActionEnum.DEPLOY_DOCKER))
            False  # Not in architect's allowed_actions
        """
        return self.agent.can_execute(action)

    def can_use_tool(self, tool_name: str) -> bool:
        """
        Check if agent can use the given tool (RBAC enforcement).

        Delegates to Agent aggregate root for RBAC logic.

        Args:
            tool_name: Name of the tool (e.g., "files", "git", "tests")

        Returns:
            True if agent can use tool, False otherwise

        Examples:
            >>> architect_agent.can_use_tool("files")
            True
            >>> architect_agent.can_use_tool("docker")
            False  # Not in architect's allowed_tools
        """
        return self.agent.can_use_tool(tool_name)

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
        Execute task with static planning (delegates to use case).

        This method is now a thin facade that delegates to ExecuteTaskUseCase
        following hexagonal architecture principles.
        """
        return await self.execute_task_usecase.execute(
            task=task,
            context=context,
            constraints=constraints,
            enable_write=self.enable_tools,
        )

    async def _execute_task_iterative(
        self,
        task: str,
        context: str,
        constraints: ExecutionConstraints,
    ) -> AgentResult:
        """
        Execute task with iterative planning (delegates to use case).

        This method is now a thin facade that delegates to ExecuteTaskIterativeUseCase
        following hexagonal architecture principles.
        """
        return await self.execute_task_iterative_usecase.execute(
            task=task,
            context=context,
            constraints=constraints,
            enable_write=self.enable_tools,
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
                role=self.role,  # Pass Role entity to use case
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
        Execute a single plan step with RBAC enforcement.

        Args:
            step: ExecutionStep entity or dict with tool, operation, params

        Returns:
            StepExecutionResult with success, result entity, and error

        Raises:
            ValueError: If tool is not allowed for agent's role (RBAC violation)
        """
        # Convert dict to ExecutionStep if needed (eliminates reflection)
        step_entity = self._ensure_execution_step(step)

        tool_name = step_entity.tool
        operation = step_entity.operation
        params = step_entity.params or {}

        # 🔒 RBAC ENFORCEMENT: Validate tool access BEFORE execution (fail-fast)
        if not self.agent.can_use_tool(tool_name):
            error_msg = (
                f"RBAC Violation: Tool '{tool_name}' not allowed for role '{self.role.get_name()}'. "
                f"Allowed tools: {sorted(self.role.allowed_tools)}"
            )
            logger.error(f"[{self.agent_id}] {error_msg}")
            return StepExecutionResult(
                success=False,
                result=None,
                error=error_msg,
                operation=operation,
                tool_name=tool_name,
            )

        try:
            # Delegate to toolset for execution (returns domain entity)
            # ToolFactory handles read-only verification based on enable_tools flag
            # Run sync operation in thread pool to properly use async/await
            try:
                result = await asyncio.to_thread(
                    self.toolset.execute_operation,
                    tool_name=tool_name,
                    operation=operation,
                    params=params,
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
            role=self.role.get_name(),  # Tell, Don't Ask: Role knows its name
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

