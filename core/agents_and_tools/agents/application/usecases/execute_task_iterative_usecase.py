"""Use case for executing tasks iteratively (ReAct-style)."""

from __future__ import annotations

import logging
from typing import Any

from core.agents_and_tools.agents.application.dtos.next_action_dto import NextActionDTO
from core.agents_and_tools.agents.application.dtos.step_execution_dto import StepExecutionDTO
from core.agents_and_tools.agents.application.usecases.generate_next_action_usecase import (
    GenerateNextActionUseCase,
)
from core.agents_and_tools.agents.domain.entities import (
    AgentResult,
    Artifact,
    Artifacts,
    AuditTrails,
    ExecutionConstraints,
    ExecutionStep,
    ObservationHistories,
    Operations,
    ReasoningLogs,
)
from core.agents_and_tools.agents.infrastructure.mappers.artifact_mapper import ArtifactMapper
from core.agents_and_tools.agents.infrastructure.mappers.execution_step_mapper import ExecutionStepMapper
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort

logger = logging.getLogger(__name__)


class ExecuteTaskIterativeUseCase:
    """
    Use case for executing tasks iteratively (ReAct-style).

    Flow:
    1. Decide next action based on history
    2. Execute action
    3. Observe result
    4. Repeat until complete or max iterations
    """

    def __init__(
        self,
        tool_execution_port: ToolExecutionPort,
        step_mapper: ExecutionStepMapper,
        artifact_mapper: ArtifactMapper,
        generate_next_action_usecase: GenerateNextActionUseCase,
        agent_id: str,
        role: str,
    ):
        """
        Initialize the use case with all dependencies (fail-fast).

        Args:
            tool_execution_port: Port for tool execution (required)
            step_mapper: Mapper for execution steps (required)
            artifact_mapper: Mapper for artifacts (required)
            generate_next_action_usecase: Use case for deciding next action (required)
            agent_id: Agent identifier for logging context (required)
            role: Agent role for logging context (required)

        Note:
            All dependencies must be provided. This ensures full testability.
        """
        if not tool_execution_port:
            raise ValueError("tool_execution_port is required (fail-fast)")
        if not step_mapper:
            raise ValueError("step_mapper is required (fail-fast)")
        if not artifact_mapper:
            raise ValueError("artifact_mapper is required (fail-fast)")
        if not generate_next_action_usecase:
            raise ValueError("generate_next_action_usecase is required (fail-fast)")
        if not agent_id:
            raise ValueError("agent_id is required (fail-fast)")
        if not role:
            raise ValueError("role is required (fail-fast)")

        self.tool_execution_port = tool_execution_port
        self.step_mapper = step_mapper
        self.artifact_mapper = artifact_mapper
        self.generate_next_action_usecase = generate_next_action_usecase
        self.agent_id = agent_id
        self.role = role

    async def execute(
        self,
        task: str,
        context: str,
        constraints: ExecutionConstraints,
        enable_write: bool = True,
    ) -> AgentResult:
        """
        Execute task iteratively.

        Args:
            task: Task description
            context: Project context
            constraints: Execution constraints
            enable_write: If False, only read operations allowed

        Returns:
            AgentResult with execution results
        """
        operations = Operations()
        artifacts = Artifacts()
        observation_history = ObservationHistories()
        audit_trail = AuditTrails()
        reasoning_log = ReasoningLogs()

        try:
            logger.info(f"[{self.agent_id}:{self.role}] Executing task (iterative): {task}")

            # Log initial thought
            self._log_thought(
                reasoning_log,
                iteration=0,
                thought_type="analysis",
                content=f"[{self.role}] Starting iterative execution: {task}",
            )

            max_iterations = constraints.max_iterations
            max_operations = constraints.max_operations

            for iteration in range(max_iterations):
                logger.info(f"[{self.agent_id}] Iteration {iteration + 1}/{max_iterations}")

                # Decide next action based on history
                next_action = await self._decide_next_action(
                    task=task,
                    context=context,
                    observation_history=observation_history,
                    constraints=constraints,
                )

                # Log decision
                if next_action.done:
                    decision_text = "Task complete"
                else:
                    tool = next_action.step.tool if next_action.step else "None"
                    op = next_action.step.operation if next_action.step else "None"
                    decision_text = f"Execute {tool}.{op}"

                self._log_thought(
                    reasoning_log,
                    iteration=iteration + 1,
                    thought_type="decision",
                    content=f"Decision: {decision_text}. Reasoning: {next_action.reasoning}",
                )

                # Check if done
                if next_action.done:
                    logger.info("Task complete")
                    break

                # Execute next action
                if not next_action.step:
                    logger.warning("No step decided")
                    break

                # Convert step to ExecutionStep entity (if it's a dict)
                if isinstance(next_action.step, dict):
                    step = self.step_mapper.to_entity(next_action.step)
                else:
                    step = next_action.step

                logger.info(f"[{self.agent_id}] Executing: {step.tool}.{step.operation}")

                # Log action
                self._log_thought(
                    reasoning_log,
                    iteration=iteration + 1,
                    thought_type="action",
                    content=f"Executing: {step.tool}.{step.operation}({step.params or {}})",
                )

                result = await self._execute_step(step, enable_write)

                # Log observation
                if result.success:
                    self._log_thought(
                        reasoning_log,
                        iteration=iteration + 1,
                        thought_type="observation",
                        content=(
                            f"✅ Operation succeeded. "
                            f"{self._summarize_result(step, result.result, step.params or {})}"
                        ),
                        confidence=1.0,
                    )
                else:
                    self._log_thought(
                        reasoning_log,
                        iteration=iteration + 1,
                        thought_type="observation",
                        content=f"❌ Operation failed: {result.error or 'Unknown error'}",
                        confidence=0.0,
                    )

                # Record operation
                operations.add(
                    tool_name=step.tool,
                    operation=step.operation,
                    success=result.success,
                    params=step.params,
                    result=result.result,
                    error=result.error,
                )

                # Observe result
                observation_history.add(
                    iteration=iteration + 1,
                    action=step,
                    result=result.result,
                    success=result.success,
                    error=result.error,
                )

                # Collect artifacts
                if result.success:
                    new_artifacts = self._collect_artifacts(step, result)
                    # Add artifacts to collection
                    for name, artifact_entity in new_artifacts.items():
                        artifacts.items[name] = artifact_entity
                else:
                    # On error, decide whether to continue
                    if constraints.abort_on_error:
                        return AgentResult(
                            success=False,
                            operations=operations,
                            artifacts=artifacts,
                            audit_trail=audit_trail,
                            reasoning_log=reasoning_log,
                            error=f"Iteration {iteration + 1} failed: {result.error}",
                        )

                # Check limits
                if operations.count() >= max_operations:
                    logger.warning("Max operations limit reached")
                    break

            # Verify completion
            success = all(op.success for op in operations.get_all())

            logger.info(
                f"[{self.agent_id}] Task {'completed successfully' if success else 'failed'}. "
                f"Executed {operations.count()} operations in {observation_history.count()} iterations."
            )

            # Log final conclusion
            self._log_thought(
                reasoning_log,
                iteration=observation_history.count() + 1,
                thought_type="conclusion",
                content=(
                    f"Task {'completed successfully' if success else 'failed'}. "
                    f"Executed {operations.count()} operations in {observation_history.count()} iterations. "
                    f"Artifacts: {list(artifacts.get_all().keys())}"
                ),
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
            logger.exception(f"[{self.agent_id}] Iterative execution failed: {e}")
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

    async def _execute_step(self, step: ExecutionStep, enable_write: bool) -> StepExecutionDTO:
        """Execute a single step."""
        tool_name = step.tool
        operation = step.operation
        params = step.params or {}

        try:
            result = self.tool_execution_port.execute_operation(
                tool_name=tool_name,
                operation=operation,
                params=params,
                enable_write=enable_write,
            )

            error_msg = result.error if not result.success else None
            if not result.success and not error_msg:
                error_msg = "Unknown error"

            return StepExecutionDTO(
                success=result.success,
                result=result,
                error=error_msg,
            )
        except Exception as e:
            logger.exception(f"Step execution failed: {e}")
            return StepExecutionDTO(success=False, result=None, error=str(e))

    async def _decide_next_action(
        self,
        task: str,
        context: str,
        observation_history: ObservationHistories,
        constraints: ExecutionConstraints,
    ) -> NextActionDTO:
        """
        Decide next action based on task and observation history (ReAct-style).

        Uses LLM to analyze:
        - Original task
        - What it's done so far (observation_history)
        - What it learned from previous actions

        And intelligently decides what to do next.

        Args:
            task: Task description
            context: Project context
            observation_history: History of previous observations
            constraints: Execution constraints

        Returns:
            NextActionDTO with done, step, and reasoning
        """
        # Get available tools
        available_tools = self.tool_execution_port.get_available_tools_description(
            enable_write_operations=True
        )

        # Delegate to GenerateNextActionUseCase for intelligent LLM-based decision
        logger.info(f"[{self.agent_id}] Using LLM to decide next action")
        decision = await self.generate_next_action_usecase.execute(
            task=task,
            context=context,
            observation_history=observation_history,
            available_tools=available_tools,
        )
        return decision

    def _collect_artifacts(self, step: ExecutionStep, result: StepExecutionDTO) -> dict[str, Artifact]:
        """Collect artifacts from step execution."""
        tool = self.tool_execution_port.get_tool_by_name(step.tool)
        if not tool:
            return {}

        artifacts_dict = tool.collect_artifacts(
            step.operation,
            result.result,
            step.params or {},
        )

        # Convert to Artifact entities using mapper
        return self.artifact_mapper.to_entity_dict(artifacts_dict)

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
            reasoning_log: ReasoningLogs collection to append thought to
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

    def _summarize_result(self, step: ExecutionStep, tool_result: Any, params: dict[str, Any]) -> str:
        """
        Summarize tool operation result for logging.

        Delegates to the tool's own summarize_result method.

        Args:
            step: The step that was executed
            tool_result: The actual result domain entity from the tool
            params: Operation parameters

        Returns:
            Human-readable summary
        """
        # Get the tool instance from factory cache
        tool = self.tool_execution_port.get_tool_by_name(step.tool)
        if not tool:
            return "Operation completed"

        # Delegate to tool's summarize_result method
        return tool.summarize_result(step.operation, tool_result, params)

