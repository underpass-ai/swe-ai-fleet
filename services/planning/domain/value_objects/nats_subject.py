"""NATS subject enumeration for Planning Service."""

from enum import Enum


class NATSSubject(str, Enum):
    """Enumeration of NATS subjects used by Planning Service.

    Following DDD:
    - Enum for fixed set of values
    - Type-safe subject names
    - NO magic strings
    - Centralized subject registry
    """

    # Planning events (published by Planning)
    STORY_TRANSITIONED = "planning.story.transitioned"
    PLAN_APPROVED = "planning.plan.approved"
    TASK_CREATED = "planning.task.created"
    TASKS_DERIVED = "planning.tasks.derived"

    # Backlog Review events (published by Planning)
    BACKLOG_REVIEW_CEREMONY_STARTED = "planning.backlog_review.ceremony.started"
    BACKLOG_REVIEW_CEREMONY_COMPLETED = "planning.backlog_review.ceremony.completed"

    # Agent responses (consumed by Planning for backlog review results)
    # These events are published by Ray Workers after vLLM completes deliberation
    AGENT_RESPONSE_COMPLETED = "agent.response.completed"
    AGENT_RESPONSE_FAILED = "agent.response.failed"

    # Agent responses (consumed by Planning for task derivation)
    # Same events, different use case
    # AGENT_RESPONSE_COMPLETED = "agent.response.completed"  # Already defined above
    # AGENT_RESPONSE_FAILED = "agent.response.failed"  # Already defined above

    def __str__(self) -> str:
        """String representation.

        Returns:
            Subject value
        """
        return self.value

