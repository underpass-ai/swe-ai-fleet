"""ProjectEventMapper - Infrastructure layer mapper for Project events."""

import logging
from typing import Any

from planning.domain.entities.project import Project
from planning.domain.events.project_created_event import ProjectCreatedEvent

logger = logging.getLogger(__name__)


class ProjectEventMapper:
    """Mapper for Project domain events to dict/JSON.

    Following Hexagonal Architecture:
    - Mappers live in infrastructure layer
    - Handle conversions: DomainEvent → dict (for NATS/JSON)
    - Domain entities → Events happen in use cases
    """

    @staticmethod
    def project_to_created_event(project: Project) -> ProjectCreatedEvent:
        """Convert Project entity to ProjectCreatedEvent.

        Args:
            project: Project domain entity

        Returns:
            ProjectCreatedEvent (domain event)
        """
        event = ProjectCreatedEvent(
            project_id=project.project_id,
            name=project.name,
            description=project.description,
            owner=project.owner,
            created_at=project.created_at,
        )

        logger.info(
            f"ProjectCreatedEvent mapped: project_id={project.project_id}, "
            f"name={project.name}, owner={project.owner}"
        )

        return event

    @staticmethod
    def created_event_to_payload(event: ProjectCreatedEvent) -> dict[str, Any]:
        """Convert ProjectCreatedEvent to event payload dict.

        Args:
            event: ProjectCreatedEvent

        Returns:
            Dictionary for NATS/JSON serialization
        """
        payload = {
            "project_id": str(event.project_id),
            "name": event.name,
            "description": event.description,
            "owner": event.owner,
            "created_at": event.created_at.isoformat(),
        }

        logger.debug(
            f"Event serialized to payload: project_id={event.project_id}, "
            f"payload_size={len(str(payload))} bytes"
        )

        return payload

