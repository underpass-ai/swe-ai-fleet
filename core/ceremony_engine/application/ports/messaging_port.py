"""MessagingPort: Port for publishing events (NATS).

Following Hexagonal Architecture:
- This is a PORT (interface) in the application layer
- Infrastructure adapters implement this port
- Application services depend on this port, not concrete adapters
"""

from typing import Protocol

from core.shared.events.event_envelope import EventEnvelope


class MessagingPort(Protocol):
    """Port for publishing events to messaging infrastructure (NATS).

    Provides event publishing capabilities:
    - Publish events with EventEnvelope (idempotency, correlation)
    - All events must include idempotency_key and correlation_id

    Following Hexagonal Architecture:
    - This is a PORT (interface)
    - Infrastructure provides ADAPTERS (NATSMessagingAdapter, etc.)
    - Application depends on PORT, not concrete implementation
    """

    async def publish_event(
        self,
        subject: str,
        envelope: EventEnvelope,
    ) -> None:
        """Publish an event with EventEnvelope to messaging infrastructure.

        Args:
            subject: Subject/topic name (e.g., "planning.sprint_planning.started")
            envelope: Event envelope with idempotency_key, correlation_id, etc.

        Raises:
            Exception: If publishing fails
        """
        ...
