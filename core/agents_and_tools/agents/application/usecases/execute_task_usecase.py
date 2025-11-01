"""Use case for executing tasks with tools."""

from __future__ import annotations

import logging
from typing import Any

from core.agents_and_tools.agents.application.dtos.step_execution_dto import StepExecutionDTO
from core.agents_and_tools.agents.application.usecases.generate_plan_usecase import GeneratePlanUseCase
from core.agents_and_tools.agents.domain.entities import (
    AgentResult,
    Artifact,
    Artifacts,
    AuditTrails,
    ExecutionConstraints,
    ExecutionPlan,
    ExecutionStep,
    Operations,
    ReasoningLogs,
)
from core.agents_and_tools.agents.infrastructure.mappers.artifact_mapper import ArtifactMapper
from core.agents_and_tools.agents.infrastructure.mappers.execution_step_mapper import ExecutionStepMapper
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort

logger = logging.getLogger(__name__)


class ExecuteTaskUseCase:
    """
    Use case for executing tasks with tools (static planning).

    This use case orchestrates:
    1. Plan generation
    2. Plan execution
    3. Result collection
    """

    def __init__(
        self,
        tool_execution_port: ToolExecutionPort,
        step_mapper: ExecutionStepMapper,
        artifact_mapper: ArtifactMapper,
        generate_plan_usecase: GeneratePlanUseCase,
        agent_id: str,
        role: str,
    ):
        """
        Initialize the use case with all dependencies (fail-fast).

        Args:
            tool_execution_port: Port for tool execution (required)
            step_mapper: Mapper for execution steps (required)
            artifact_mapper: Mapper for artifacts (required)
            generate_plan_usecase: Use case for generating execution plans (required)
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
        if not generate_plan_usecase:
            raise ValueError("generate_plan_usecase is required (fail-fast)")
        if not agent_id:
            raise ValueError("agent_id is required (fail-fast)")
        if not role:
            raise ValueError("role is required (fail-fast)")

        self.tool_execution_port = tool_execution_port
        self.step_mapper = step_mapper
        self.artifact_mapper = artifact_mapper
        self.generate_plan_usecase = generate_plan_usecase
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
        Execute a task with static planning.

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
        audit_trail = AuditTrails()
        reasoning_log = ReasoningLogs()

        try:
            logger.info(f"[{self.agent_id}:{self.role}] Executing task (static): {task}")

            # Log initial thought
            self._log_thought(
                reasoning_log,
                iteration=0,
                thought_type="analysis",
                content=(
                    f"[{self.role}] Analyzing task: {task}. "
                    f"Mode: {'full execution' if enable_write else 'planning only'}"
                ),
            )

            # Step 1: Generate execution plan
            available_tools = self.tool_execution_port.get_available_tools_description(
                enable_write_operations=enable_write
            )
            plan_dto = await self.generate_plan_usecase.execute(
                task=task,
                context=context,
                role=self.role,
                available_tools=available_tools,
                constraints=constraints,
            )
            plan = ExecutionPlan(steps=plan_dto.steps, reasoning=plan_dto.reasoning)
            logger.info(f"[{self.agent_id}] Generated plan with {len(plan.steps)} steps")

            self._log_thought(
                reasoning_log,
                iteration=0,
                thought_type="decision",
                content=f"Generated execution plan with {len(plan.steps)} steps. Reasoning: {plan.reasoning}",
                related_operations=[f"{s.tool}.{s.operation}" for s in plan.steps],
            )

            # Step 2: Execute plan
            for i, step in enumerate(plan.steps):
                logger.info(
                    f"[{self.agent_id}] Executing step {i+1}/{len(plan.steps)}: "
                    f"{step.tool}.{step.operation}"
                )

                # Log what agent is about to do
                self._log_thought(
                    reasoning_log,
                    iteration=i + 1,
                    thought_type="action",
                    content=(
                        f"Executing: {step.tool}.{step.operation}"
                        f"({step.params or {}})"
                    ),
                )

                result = await self._execute_step(step, enable_write)

                # Log observation
                if result.success:
                    self._log_thought(
                        reasoning_log,
                        iteration=i + 1,
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
                        iteration=i + 1,
                        thought_type="observation",
                        content=f"❌ Operation failed: {result.error or 'Unknown error'}",
                        confidence=0.0,
                    )

                # Add operation using collection entity method
                operations.add(
                    tool_name=step.tool,
                    operation=step.operation,
                    success=result.success,
                    params=step.params,
                    result=result.result,
                    error=result.error,
                )

                # Collect artifacts
                if result.success:
                    new_artifacts = self._collect_artifacts(step, result)
                    # Add artifacts to collection
                    for name, artifact_entity in new_artifacts.items():
                        artifacts.items[name] = artifact_entity

                # Check if step failed
                if not result.success:
                    error_msg = result.error or "Unknown error"

                    if constraints.abort_on_error:
                        return AgentResult(
                            success=False,
                            operations=operations,
                            artifacts=artifacts,
                            audit_trail=audit_trail,
                            reasoning_log=reasoning_log,
                            error=f"Step {i+1} failed: {error_msg}",
                        )

                # Check max operations limit
                if i + 1 >= constraints.max_operations:
                    logger.warning("Max operations limit reached")
                    break

            # Step 3: Verify completion
            success = all(op.success for op in operations.get_all())

            logger.info(
                f"[{self.agent_id}] Task {'completed successfully' if success else 'failed'}. "
                f"Executed {operations.count()} operations."
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
            logger.exception(f"[{self.agent_id}] Task execution failed: {e}")
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
        """Execute a single plan step."""
        tool_name = step.tool
        operation = step.operation
        params = step.params or {}

        try:
            # Delegate to tool execution port
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
        except ValueError as e:
            return StepExecutionDTO(success=False, result=None, error=str(e))
        except Exception as e:
            logger.exception(f"Step execution failed: {e}")
            return StepExecutionDTO(success=False, result=None, error=str(e))

    def _collect_artifacts(self, step: ExecutionStep, result: StepExecutionDTO) -> dict[str, Artifact]:
        """Collect artifacts from step execution."""
        # Get tool instance
        tool = self.tool_execution_port.get_tool_by_name(step.tool)
        if not tool:
            return {}

        # Delegate to tool's collect_artifacts method (returns dict of values)
        artifacts_dict = tool.collect_artifacts(
            step.operation,
            result.result,
            step.params or {},
        )

        # Convert dict to dict of Artifact entities using mapper
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

