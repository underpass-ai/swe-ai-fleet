"""Use case for executing tasks iteratively (ReAct-style)."""

from __future__ import annotations

import logging
from typing import Any

from core.agents_and_tools.agents.application.dtos.next_action_dto import NextActionDTO
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
            generate_next_action_usecase: Use case for deciding next action (required)
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
        if not generate_next_action_usecase:
            raise ValueError("generate_next_action_usecase is required (fail-fast)")
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
        self.generate_next_action_usecase = generate_next_action_usecase
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
            logger.info(f"[{self.agent_id}:{self.role.get_name()}] Executing task (iterative): {task}")

            # Log initial analysis
            mode = "iterative execution"
            self.log_reasoning_service.log_analysis(reasoning_log, task, mode)

            max_iterations = constraints.max_iterations
            max_operations = constraints.max_operations

            # Execute ReAct loop
            early_result = await self._execute_react_loop(
                task, context, operations, artifacts, observation_history,
                reasoning_log, constraints, enable_write, max_iterations
            )
            if early_result:  # Early abort due to error
                return early_result

            # Verify completion
            success = all(op.success for op in operations.get_all())

            logger.info(
                f"[{self.agent_id}] Task {'completed successfully' if success else 'failed'}. "
                f"Executed {operations.count()} operations in {observation_history.count()} iterations."
            )

            # Log final conclusion
            self.log_reasoning_service.log_conclusion(
                reasoning_log,
                success,
                operations.count(),
                list(artifacts.get_all().keys()),
                iteration=observation_history.count() + 1,
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
        Execute a single step.

        Delegates to StepExecutionApplicationService.

        Args:
            step: The execution step
            enable_write: Whether write operations are allowed

        Returns:
            StepExecutionDTO with execution results
        """
        return await self.step_execution_service.execute(step, enable_write)

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

    async def _execute_react_loop(
        self,
        task: str,
        context: str,
        operations: Operations,
        artifacts: Artifacts,
        observation_history: ObservationHistories,
        reasoning_log: ReasoningLogs,
        constraints: ExecutionConstraints,
        enable_write: bool,
        max_iterations: int,
    ) -> AgentResult | None:
        """
        Execute ReAct (Reasoning + Acting) loop.

        Extracted to reduce cognitive complexity of execute() method.

        Returns:
            AgentResult if early abort needed, None otherwise
        """
        for iteration in range(max_iterations):
            logger.info(f"[{self.agent_id}] Iteration {iteration + 1}/{max_iterations}")

            # Decide next action
            next_action = await self._decide_next_action(
                task=task,
                context=context,
                observation_history=observation_history,
                constraints=constraints,
            )

            # Check if complete or should stop
            should_stop, stop_result = self._check_iteration_completion(
                next_action, iteration, reasoning_log
            )
            if should_stop:
                return stop_result

            # Execute step and check for early abort
            early_abort = await self._execute_iteration_step(
                next_action, iteration, operations, artifacts,
                observation_history, reasoning_log, constraints, enable_write
            )
            if early_abort:
                return early_abort

            # Check limits
            if operations.count() >= constraints.max_operations:
                logger.warning("Max operations limit reached")
                break

        return None  # Continue to completion

    def _check_iteration_completion(
        self,
        next_action: NextActionDTO,
        iteration: int,
        reasoning_log: ReasoningLogs,
    ) -> tuple[bool, AgentResult | None]:
        """
        Check if iteration should stop (task done or no step).

        Returns:
            (should_stop, result_if_stopping)
        """
        if next_action.done:
            logger.info("Task complete")
            self.log_reasoning_service._log_thought(
                reasoning_log,
                iteration=iteration + 1,
                thought_type="decision",
                content=f"Decision: Task complete. Reasoning: {next_action.reasoning}",
            )
            return (True, None)

        if not next_action.step:
            logger.warning("No step decided")
            self.log_reasoning_service._log_thought(
                reasoning_log,
                iteration=iteration + 1,
                thought_type="decision",
                content=f"Decision: No step. Reasoning: {next_action.reasoning}",
            )
            return (True, None)

        return (False, None)

    async def _execute_iteration_step(
        self,
        next_action: NextActionDTO,
        iteration: int,
        operations: Operations,
        artifacts: Artifacts,
        observation_history: ObservationHistories,
        reasoning_log: ReasoningLogs,
        constraints: ExecutionConstraints,
        enable_write: bool,
    ) -> AgentResult | None:
        """
        Execute a single iteration step.

        Returns:
            AgentResult if abort needed, None to continue
        """
        # Convert step to ExecutionStep entity (if it's a dict)
        step = self._convert_to_execution_step(next_action.step)

        # Log decision
        self.log_reasoning_service._log_thought(
            reasoning_log,
            iteration=iteration + 1,
            thought_type="decision",
            content=f"Decision: Execute {step.tool}.{step.operation}. Reasoning: {next_action.reasoning}",
        )

        logger.info(f"[{self.agent_id}] Executing: {step.tool}.{step.operation}")

        # Log action
        self.log_reasoning_service.log_action(reasoning_log, step, iteration=iteration + 1)

        # Execute step
        result = await self._execute_step(step, enable_write)

        # Process result
        return await self._process_iteration_result(
            step, result, iteration, operations, artifacts,
            observation_history, reasoning_log, constraints
        )

    def _convert_to_execution_step(self, step: ExecutionStep | dict | None) -> ExecutionStep:
        """Convert step to ExecutionStep entity if needed."""
        if isinstance(step, dict):
            return self.step_mapper.to_entity(step)
        return step  # type: ignore

    async def _process_iteration_result(
        self,
        step: ExecutionStep,
        result: StepExecutionDTO,
        iteration: int,
        operations: Operations,
        artifacts: Artifacts,
        observation_history: ObservationHistories,
        reasoning_log: ReasoningLogs,
        constraints: ExecutionConstraints,
    ) -> AgentResult | None:
        """
        Process result from iteration step execution.

        Returns:
            AgentResult if abort needed, None to continue
        """
        # Log observation
        self._log_step_observation(step, result, reasoning_log, iteration)

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

        # Collect artifacts on success
        if result.success:
            new_artifacts = self._collect_artifacts(step, result)
            for name, artifact_entity in new_artifacts.items():
                artifacts.items[name] = artifact_entity
        elif constraints.abort_on_error:
            # Abort on error if configured
            return AgentResult(
                success=False,
                operations=operations,
                artifacts=artifacts,
                audit_trail=AuditTrails(),
                reasoning_log=reasoning_log,
                error=f"Iteration {iteration + 1} failed: {result.error}",
            )

        return None

    def _log_step_observation(
        self,
        step: ExecutionStep,
        result: StepExecutionDTO,
        reasoning_log: ReasoningLogs,
        iteration: int,
    ) -> None:
        """Log step observation (success or failure)."""
        if result.success:
            summary = self._summarize_result(step, result.result, step.params or {})
            self.log_reasoning_service.log_success_observation(
                reasoning_log, summary, iteration=iteration + 1
            )
        else:
            self.log_reasoning_service.log_failure_observation(
                reasoning_log, result.error or "Unknown error", iteration=iteration + 1
            )

