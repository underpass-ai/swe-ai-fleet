"""Use case for logging agent reasoning thoughts."""

import logging

from core.agents_and_tools.agents.domain.entities import ReasoningLogs

logger = logging.getLogger(__name__)


class LogReasoningUseCase:
    """
    Use case for logging agent reasoning thoughts.

    This use case handles the business logic for:
    - Capturing agent's internal thoughts
    - Logging to ReasoningLogs entity
    - Providing observability for agent decision-making

    Following DDD + Hexagonal Architecture:
    - No infrastructure dependencies (pure domain logic)
    - Logs to ReasoningLogs entity (domain abstraction)
    - Can be extended to log to external systems via port
    """

    def __init__(
        self,
        agent_id: str,
        role: str,
    ):
        """
        Initialize the use case with agent context (fail-fast).

        Args:
            agent_id: Agent identifier (required)
            role: Agent role (required)

        Note:
            All dependencies must be provided. This ensures full testability.
        """
        if not agent_id:
            raise ValueError("agent_id is required (fail-fast)")
        if not role:
            raise ValueError("role is required (fail-fast)")

        self.agent_id = agent_id
        self.role = role

    def execute(
        self,
        reasoning_log: ReasoningLogs,
        iteration: int,
        thought_type: str,
        content: str,
        related_operations: list[str] | None = None,
        confidence: float | None = None,
    ) -> None:
        """
        Log an agent thought to the reasoning log.

        Args:
            reasoning_log: ReasoningLogs entity to append to (required)
            iteration: Iteration/step number (required)
            thought_type: Type of thought (analysis, decision, action, observation,
                conclusion, error) (required)
            content: Thought content (required)
            related_operations: Related tool operations (optional)
            confidence: Confidence level 0.0-1.0 (optional)

        Note:
            This method modifies the reasoning_log entity in place.
        """
        if not reasoning_log:
            raise ValueError("reasoning_log is required (fail-fast)")
        if not thought_type:
            raise ValueError("thought_type is required (fail-fast)")
        if not content:
            raise ValueError("content is required (fail-fast)")

        # Log to ReasoningLogs entity
        reasoning_log.add(
            agent_id=self.agent_id,
            role=self.role.get_name(),  # Convert Role object to string for logging
            iteration=iteration,
            thought_type=thought_type,
            content=content,
            related_operations=related_operations,
            confidence=confidence,
        )

        # Also log to standard logger for real-time observability
        logger.info(f"[{self.agent_id}] {thought_type.upper()}: {content}")
