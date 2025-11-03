"""Application service for reasoning logging."""

from __future__ import annotations

import logging
from typing import Any

from core.agents_and_tools.agents.domain.entities import ExecutionStep, ReasoningLogs
from core.agents_and_tools.agents.domain.entities.rbac import Role

logger = logging.getLogger(__name__)


class LogReasoningApplicationService:
    """
    Application service for managing reasoning log entries.

    This service encapsulates all reasoning logging logic,
    reducing complexity in use cases that need observability.

    Following DDD principles:
    - Service operates on domain entities (ReasoningLogs, ExecutionStep)
    - No business rules, only logging coordination
    - Stateless (receives all context via parameters)
    """

    def __init__(self, agent_id: str, role: Role):
        """
        Initialize reasoning service with agent context.

        Args:
            agent_id: Agent identifier for all log entries
            role: Agent Role value object (domain entity)

        Note:
            This service is stateless except for agent context.

        Raises:
            ValueError: If agent_id is empty
        """
        if not agent_id:
            raise ValueError("agent_id cannot be empty (fail-fast)")

        self.agent_id = agent_id
        self.role = role

    def log_analysis(
        self,
        reasoning_log: ReasoningLogs,
        task: str,
        mode: str,
        iteration: int = 0,
    ) -> None:
        """
        Log initial task analysis.

        Args:
            reasoning_log: ReasoningLogs collection to append to
            task: Task being analyzed
            mode: Execution mode ("full execution" or "planning only")
            iteration: Iteration number (default 0)
        """
        self._log_thought(
            reasoning_log=reasoning_log,
            iteration=iteration,
            thought_type="analysis",
            content=f"[{self.role.get_name()}] Analyzing task: {task}. Mode: {mode}",
        )

    def log_plan_decision(
        self,
        reasoning_log: ReasoningLogs,
        plan_steps_count: int,
        plan_reasoning: str,
        steps: list[ExecutionStep],
        iteration: int = 0,
    ) -> None:
        """
        Log plan generation decision.

        Args:
            reasoning_log: ReasoningLogs collection
            plan_steps_count: Number of steps in plan
            plan_reasoning: LLM's reasoning for the plan
            steps: List of ExecutionStep entities
            iteration: Iteration number (default 0)
        """
        related_ops = [f"{s.tool}.{s.operation}" for s in steps]
        self._log_thought(
            reasoning_log=reasoning_log,
            iteration=iteration,
            thought_type="decision",
            content=f"Generated execution plan with {plan_steps_count} steps. Reasoning: {plan_reasoning}",
            related_operations=related_ops,
        )

    def log_action(
        self,
        reasoning_log: ReasoningLogs,
        step: ExecutionStep,
        iteration: int,
    ) -> None:
        """
        Log action about to be executed.

        Args:
            reasoning_log: ReasoningLogs collection
            step: ExecutionStep being executed
            iteration: Iteration number
        """
        self._log_thought(
            reasoning_log=reasoning_log,
            iteration=iteration,
            thought_type="action",
            content=f"Executing: {step.tool}.{step.operation}({step.params or {}})",
        )

    def log_success_observation(
        self,
        reasoning_log: ReasoningLogs,
        summary: str,
        iteration: int,
    ) -> None:
        """
        Log successful operation observation.

        Args:
            reasoning_log: ReasoningLogs collection
            summary: Human-readable summary of result
            iteration: Iteration number
        """
        self._log_thought(
            reasoning_log=reasoning_log,
            iteration=iteration,
            thought_type="observation",
            content=f"✅ Operation succeeded. {summary}",
            confidence=1.0,
        )

    def log_failure_observation(
        self,
        reasoning_log: ReasoningLogs,
        error: str,
        iteration: int,
    ) -> None:
        """
        Log failed operation observation.

        Args:
            reasoning_log: ReasoningLogs collection
            error: Error message
            iteration: Iteration number
        """
        self._log_thought(
            reasoning_log=reasoning_log,
            iteration=iteration,
            thought_type="observation",
            content=f"❌ Operation failed: {error or 'Unknown error'}",
            confidence=0.0,
        )

    def log_conclusion(
        self,
        reasoning_log: ReasoningLogs,
        success: bool,
        operations_count: int,
        artifacts_keys: list[str],
        iteration: int,
    ) -> None:
        """
        Log final conclusion.

        Args:
            reasoning_log: ReasoningLogs collection
            success: Whether task completed successfully
            operations_count: Number of operations executed
            artifacts_keys: List of artifact keys collected
            iteration: Final iteration number
        """
        self._log_thought(
            reasoning_log=reasoning_log,
            iteration=iteration,
            thought_type="conclusion",
            content=(
                f"Task {'completed successfully' if success else 'failed'}. "
                f"Executed {operations_count} operations. "
                f"Artifacts: {artifacts_keys}"
            ),
            confidence=1.0 if success else 0.5,
        )

    def log_error(
        self,
        reasoning_log: ReasoningLogs,
        error: str,
    ) -> None:
        """
        Log fatal error.

        Args:
            reasoning_log: ReasoningLogs collection
            error: Error message
        """
        self._log_thought(
            reasoning_log=reasoning_log,
            iteration=-1,
            thought_type="error",
            content=f"Fatal error: {error}",
            confidence=0.0,
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
        Internal helper to add thought to reasoning log.

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
            role=self.role.get_name(),  # Convert Role to string for entity
            iteration=iteration,
            thought_type=thought_type,
            content=content,
            related_operations=related_operations,
            confidence=confidence,
        )

        # Also log to standard logger for real-time observability
        logger.info(f"[{self.agent_id}] {thought_type.upper()}: {content}")

