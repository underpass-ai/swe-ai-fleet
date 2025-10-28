"""Use case for executing tasks iteratively (ReAct-style)."""

from __future__ import annotations

import logging

from core.agents_and_tools.agents.application.dtos.next_action_dto import NextActionDTO
from core.agents_and_tools.agents.application.dtos.step_execution_dto import StepExecutionDTO
from core.agents_and_tools.agents.domain.entities.agent_result import AgentResult
from core.agents_and_tools.agents.domain.entities.artifact import Artifact
from core.agents_and_tools.agents.domain.entities.artifacts import Artifacts
from core.agents_and_tools.agents.domain.entities.audit_trails import AuditTrails
from core.agents_and_tools.agents.domain.entities.execution_constraints import ExecutionConstraints
from core.agents_and_tools.agents.domain.entities.execution_step import ExecutionStep
from core.agents_and_tools.agents.domain.entities.observation_histories import ObservationHistories
from core.agents_and_tools.agents.domain.entities.operations import Operations
from core.agents_and_tools.agents.domain.entities.reasoning_logs import ReasoningLogs
from core.agents_and_tools.agents.domain.ports.tool_execution_port import ToolExecutionPort
from core.agents_and_tools.agents.infrastructure.mappers.artifact_mapper import ArtifactMapper
from core.agents_and_tools.agents.infrastructure.mappers.execution_step_mapper import ExecutionStepMapper

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

    def __init__(self, tool_execution_port: ToolExecutionPort):
        """
        Initialize the use case.

        Args:
            tool_execution_port: Port for tool execution
        """
        self.tool_execution_port = tool_execution_port
        self.step_mapper = ExecutionStepMapper()
        self.artifact_mapper = ArtifactMapper()

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
            logger.info(f"Executing task (iterative): {task}")

            max_iterations = constraints.max_iterations
            max_operations = constraints.max_operations

            for iteration in range(max_iterations):
                logger.info(f"Iteration {iteration + 1}/{max_iterations}")

                # TODO: Decide next action based on history
                next_action = await self._decide_next_action(
                    task=task,
                    context=context,
                    observation_history=observation_history,
                    constraints=constraints,
                )

                # Check if done
                if next_action.done:
                    logger.info("Task complete")
                    break

                # Execute next action
                if not next_action.step:
                    logger.warning("No step decided")
                    break

                # Convert step dict to ExecutionStep entity
                step = self.step_mapper.to_entity(next_action.step)

                logger.info(f"Executing: {step.tool}.{step.operation}")
                result = await self._execute_step(step, enable_write)

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
                        artifacts.artifacts[name] = artifact_entity
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
            logger.exception(f"Iterative execution failed: {e}")
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
        Decide next action based on history.

        Simple heuristic logic for now:
        - If history is empty, start with read operation
        - If last operation failed, mark as done
        - Otherwise, decide based on task type

        TODO: Replace with GenerateNextActionUseCase for intelligent decisions

        Args:
            task: Task description
            context: Project context
            observation_history: History of previous observations
            constraints: Execution constraints

        Returns:
            NextActionDTO with decision
        """
        # Check constraints
        max_iterations = constraints.max_iterations

        # If no history yet, start with initial read operation
        if observation_history.count() == 0:
            initial_step = {
                "tool": "files",
                "operation": "list_files",
                "params": {"path": ".", "recursive": False}
            }
            return NextActionDTO(
                done=False,
                step=initial_step,
                reasoning=f"Starting execution of task: {task}"
            )

        # Get last observation
        last_obs = observation_history.get_last()
        if last_obs and not last_obs.success:
            # Last operation failed
            return NextActionDTO(
                done=True,
                step=None,
                reasoning=f"Task failed: {last_obs.error or 'Unknown error'}"
            )

        # If we've reached max iterations, mark as done
        if observation_history.count() >= max_iterations:
            return NextActionDTO(
                done=True,
                step=None,
                reasoning=f"Reached max iterations ({max_iterations})"
            )

        # Default: mark as done (implement actual logic via GenerateNextActionUseCase)
        return NextActionDTO(
            done=True,
            step=None,
            reasoning="Task evaluation complete (fallback logic)"
        )

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

