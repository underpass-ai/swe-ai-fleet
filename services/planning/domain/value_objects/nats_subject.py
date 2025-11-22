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

    # Agent responses (consumed by Planning for task derivation)
    AGENT_RESPONSE_COMPLETED = "agent.response.completed"
    AGENT_RESPONSE_FAILED = "agent.response.failed"

    def __str__(self) -> str:
        """String representation.

        Returns:
            Subject value
        """
        return self.value

