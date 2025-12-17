"""NATS durable consumer names for Backlog Review Processor Service."""

from enum import Enum


class NATSDurable(str, Enum):
    """Enumeration of NATS durable consumer names.

    Following DDD:
    - Enum for fixed set of values
    - Type-safe durable names
    - NO magic strings
    - Ensures consumer name consistency
    """

    DELIBERATIONS_COMPLETE = "backlog-review-processor-deliberations-complete-consumer"
    TASK_EXTRACTION_RESULT = "backlog-review-processor-result-consumer"

    def __str__(self) -> str:
        """String representation.

        Returns:
            Durable name
        """
        return self.value

