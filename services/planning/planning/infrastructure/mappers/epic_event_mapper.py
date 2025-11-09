"""EpicEventMapper - Infrastructure layer mapper for Epic events."""

from typing import Any

from planning.domain.entities.epic import Epic
from planning.domain.events.epic_created_event import EpicCreatedEvent


class EpicEventMapper:
    """Mapper for Epic domain events to dict/JSON.

    Following Hexagonal Architecture:
    - Mappers live in infrastructure layer
    - Handle conversions: DomainEvent → dict (for NATS/JSON)
    - Domain entities → Events happen in use cases
    """

    @staticmethod
    def epic_to_created_event(epic: Epic) -> EpicCreatedEvent:
        """Convert Epic entity to EpicCreatedEvent.

        Args:
            epic: Epic domain entity

        Returns:
            EpicCreatedEvent (domain event)
        """
        return EpicCreatedEvent(
            epic_id=epic.epic_id,
            project_id=epic.project_id,
            title=epic.title,
            description=epic.description,
            created_at=epic.created_at,
        )

    @staticmethod
    def created_event_to_payload(event: EpicCreatedEvent) -> dict[str, Any]:
        """Convert EpicCreatedEvent to event payload dict.

        Args:
            event: EpicCreatedEvent

        Returns:
            Dictionary for NATS/JSON serialization
        """
        return {
            "epic_id": str(event.epic_id),
            "project_id": str(event.project_id),
            "title": event.title,
            "description": event.description,
            "created_at": event.created_at.isoformat(),
        }

