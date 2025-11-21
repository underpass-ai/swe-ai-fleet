"""NATS durable consumer names for Planning Service."""

from enum import Enum


class NATSDurable(str, Enum):
    """Enumeration of NATS durable consumer names.

    Following DDD:
    - Enum for fixed set of values
    - Type-safe durable names
    - NO magic strings
    - Ensures consumer name consistency
    """

    # Task derivation consumers
    PLAN_APPROVED_TASK_DERIVATION = "planning-task-derivation-consumer"
    TASK_DERIVATION_RESULT = "planning-task-derivation-result-consumer"

    def __str__(self) -> str:
        """String representation.

        Returns:
            Durable name
        """
        return self.value

