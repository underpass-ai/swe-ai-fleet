"""NATS subject enumeration for Task Extraction Service."""

from enum import Enum


class NATSSubject(str, Enum):
    """Enumeration of NATS subjects used by Task Extraction Service.

    Following DDD:
    - Enum for fixed set of values
    - Type-safe subject names
    - NO magic strings
    - Centralized subject registry
    """

    # Events consumed by Task Extraction Service
    DELIBERATIONS_COMPLETE = "planning.backlog_review.deliberations.complete"
    TASKS_COMPLETE = "planning.backlog_review.tasks.complete"

    # Agent response subjects (specific for filtering)
    AGENT_RESPONSE_COMPLETED = "agent.response.completed"  # Legacy/generic (for backward compatibility)
    AGENT_RESPONSE_COMPLETED_BACKLOG_REVIEW_ROLE = "agent.response.completed.backlog-review.role"
    AGENT_RESPONSE_COMPLETED_TASK_EXTRACTION = "agent.response.completed.task-extraction"

    def __str__(self) -> str:
        """String representation.

        Returns:
            Subject value
        """
        return self.value

