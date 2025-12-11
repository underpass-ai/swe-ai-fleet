"""NATS stream enumeration for Task Extraction Service."""

from enum import Enum


class NATSStream(str, Enum):
    """Enumeration of NATS JetStream streams.

    Following DDD:
    - Enum for fixed set of values
    - Type-safe stream names
    - NO magic strings
    """

    PLANNING_EVENTS = "PLANNING_EVENTS"
    AGENT_RESPONSES = "AGENT_RESPONSES"

    def __str__(self) -> str:
        """String representation.

        Returns:
            Stream name
        """
        return self.value

