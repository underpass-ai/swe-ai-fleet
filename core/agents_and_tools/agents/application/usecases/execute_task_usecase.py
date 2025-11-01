"""Use case for executing tasks with tools."""

from __future__ import annotations

import logging

from core.agents_and_tools.agents.application.dtos.step_execution_dto import StepExecutionDTO
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
from core.agents_and_tools.agents.domain.ports.llm_client import LLMClientPort
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
        llm_client_port: LLMClientPort | None = None,
    ):
        """
        Initialize the use case with all dependencies (fail-fast).

        Args:
            tool_execution_port: Port for tool execution (required)
            step_mapper: Mapper for execution steps (required)
            artifact_mapper: Mapper for artifacts (required)
            llm_client_port: Port for LLM communication (optional)

        Note:
            All dependencies must be provided. This ensures full testability.
        """
        if not tool_execution_port:
            raise ValueError("tool_execution_port is required (fail-fast)")
        if not step_mapper:
            raise ValueError("step_mapper is required (fail-fast)")
        if not artifact_mapper:
            raise ValueError("artifact_mapper is required (fail-fast)")

        self.tool_execution_port = tool_execution_port
        self.llm_client_port = llm_client_port
        self.step_mapper = step_mapper
        self.artifact_mapper = artifact_mapper

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
            logger.info(f"Executing task (static): {task}")

            # Step 1: Generate execution plan
            # TODO: Call plan generation use case
            plan = ExecutionPlan(steps=[], reasoning="")
            logger.info(f"Generated plan with {len(plan.steps)} steps")

            # Step 2: Execute plan
            for i, step_dict in enumerate(plan.steps):
                logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step_dict}")

                # Convert dict to ExecutionStep entity (eliminates reflection)
                step = self.step_mapper.to_entity(step_dict)

                result = await self._execute_step(step, enable_write)

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
                    logger.error(f"Step {i+1} failed: {error_msg}")

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

            logger.info(f"Task completed: {success} ({operations.count()} operations)")

            return AgentResult(
                success=success,
                operations=operations,
                artifacts=artifacts,
                audit_trail=audit_trail,
                reasoning_log=reasoning_log,
            )

        except Exception as e:
            logger.exception(f"Task execution failed: {e}")
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

