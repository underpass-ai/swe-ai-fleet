"""Messaging port for Task Extraction Service.

Port (interface) for NATS messaging.
Task Extraction Service uses NATS to publish events.
"""

from typing import Protocol


class MessagingPort(Protocol):
    """Port for NATS messaging.

    Following Hexagonal Architecture:
    - Port defines interface (application layer)
    - Adapter implements NATS calls (infrastructure layer)
    """

    async def publish_event(self, subject: str, payload: dict) -> None:
        """Publish an event to NATS.

        Args:
            subject: NATS subject (e.g., "planning.backlog_review.deliberations.complete")
            payload: Event payload (dict)

        Raises:
            MessagingError: If publish fails
        """
        ...
