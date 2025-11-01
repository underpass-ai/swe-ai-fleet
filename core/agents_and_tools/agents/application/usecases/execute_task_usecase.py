"""Use case for executing tasks with tools."""

from __future__ import annotations

import logging
from typing import Any

from core.agents_and_tools.agents.application.dtos.step_execution_dto import StepExecutionDTO
from core.agents_and_tools.agents.application.services.artifact_collection_service import (
    ArtifactCollectionApplicationService,
)
from core.agents_and_tools.agents.application.services.log_reasoning_service import (
    LogReasoningApplicationService,
)
from core.agents_and_tools.agents.application.services.result_summarization_service import (
    ResultSummarizationApplicationService,
)
from core.agents_and_tools.agents.application.services.step_execution_service import (
    StepExecutionApplicationService,
)
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
        log_reasoning_service: LogReasoningApplicationService,
        result_summarization_service: ResultSummarizationApplicationService,
        artifact_collection_service: ArtifactCollectionApplicationService,
        step_execution_service: StepExecutionApplicationService,
        agent_id: str,
    ):
        """
        Initialize the use case with all dependencies (fail-fast).

        Args:
            tool_execution_port: Port for tool execution (required)
            step_mapper: Mapper for execution steps (required)
            artifact_mapper: Mapper for artifacts (required)
            generate_plan_usecase: Use case for generating execution plans (required)
            log_reasoning_service: Service for reasoning logging (required)
            result_summarization_service: Service for summarizing results (required)
            artifact_collection_service: Service for collecting artifacts (required)
            step_execution_service: Service for executing individual steps (required)
            agent_id: Agent identifier for logging context (required)

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
        if not log_reasoning_service:
            raise ValueError("log_reasoning_service is required (fail-fast)")
        if not result_summarization_service:
            raise ValueError("result_summarization_service is required (fail-fast)")
        if not artifact_collection_service:
            raise ValueError("artifact_collection_service is required (fail-fast)")
        if not step_execution_service:
            raise ValueError("step_execution_service is required (fail-fast)")
        if not agent_id:
            raise ValueError("agent_id is required (fail-fast)")

        self.tool_execution_port = tool_execution_port
        self.step_mapper = step_mapper
        self.artifact_mapper = artifact_mapper
        self.generate_plan_usecase = generate_plan_usecase
        self.log_reasoning_service = log_reasoning_service
        self.result_summarization_service = result_summarization_service
        self.artifact_collection_service = artifact_collection_service
        self.step_execution_service = step_execution_service
        self.agent_id = agent_id
        self.role = log_reasoning_service.role  # Get role from service

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
            logger.info(f"[{self.agent_id}] Executing task (static): {task}")

            # Log initial analysis
            mode = "full execution" if enable_write else "planning only"
            self.log_reasoning_service.log_analysis(reasoning_log, task, mode)

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

            # Log plan decision
            self.log_reasoning_service.log_plan_decision(
                reasoning_log, len(plan.steps), plan.reasoning, plan.steps
            )

            # Step 2: Execute plan
            for i, step in enumerate(plan.steps):
                logger.info(
                    f"[{self.agent_id}] Executing step {i+1}/{len(plan.steps)}: "
                    f"{step.tool}.{step.operation}"
                )

                # Log action
                self.log_reasoning_service.log_action(reasoning_log, step, iteration=i + 1)

                result = await self._execute_step(step, enable_write)

                # Log observation
                if result.success:
                    summary = self._summarize_result(step, result.result, step.params or {})
                    self.log_reasoning_service.log_success_observation(
                        reasoning_log, summary, iteration=i + 1
                    )
                else:
                    self.log_reasoning_service.log_failure_observation(
                        reasoning_log, result.error or "Unknown error", iteration=i + 1
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
            self.log_reasoning_service.log_conclusion(
                reasoning_log,
                success,
                operations.count(),
                list(artifacts.get_all().keys()),
                iteration=len(plan.steps) + 1,
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
            self.log_reasoning_service.log_error(reasoning_log, str(e))
            return AgentResult(
                success=False,
                operations=operations,
                artifacts=artifacts,
                audit_trail=audit_trail,
                reasoning_log=reasoning_log,
                error=str(e),
            )

    async def _execute_step(self, step: ExecutionStep, enable_write: bool) -> StepExecutionDTO:
        """
        Execute a single plan step.

        Delegates to StepExecutionApplicationService.

        Args:
            step: The execution step
            enable_write: Whether write operations are allowed

        Returns:
            StepExecutionDTO with execution results
        """
        return await self.step_execution_service.execute(step, enable_write)

    def _collect_artifacts(self, step: ExecutionStep, result: StepExecutionDTO) -> dict[str, Artifact]:
        """
        Collect artifacts from step execution.

        Delegates to ArtifactCollectionApplicationService.

        Args:
            step: The execution step
            result: The step execution result

        Returns:
            Dictionary mapping artifact names to Artifact entities
        """
        return self.artifact_collection_service.collect(step, result)

    def _summarize_result(self, step: ExecutionStep, tool_result: Any, params: dict[str, Any]) -> str:
        """
        Summarize tool operation result for logging.

        Delegates to ResultSummarizationApplicationService.

        Args:
            step: The step that was executed
            tool_result: The actual result domain entity from the tool
            params: Operation parameters

        Returns:
            Human-readable summary
        """
        return self.result_summarization_service.summarize(step, tool_result, params)

