"""CreateEpicUseCase - Create new epic within a project."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from planning.application.ports import MessagingPort, StoragePort
from planning.domain.entities.epic import Epic
from planning.domain.value_objects.epic_id import EpicId
from planning.domain.value_objects.epic_status import EpicStatus
from planning.domain.value_objects.project_id import ProjectId

logger = logging.getLogger(__name__)


@dataclass
class CreateEpicUseCase:
    """Create a new epic within a project.

    This use case:
    1. Validates that parent project exists
    2. Creates Epic domain entity
    3. Persists to dual storage (Neo4j + Valkey)
    4. Creates Project→Epic relationship in Neo4j
    5. Publishes planning.epic.created event

    Following Hexagonal Architecture:
    - Depends on ports (StoragePort, MessagingPort)
    - Returns domain entity (Epic)
    - No infrastructure dependencies
    """

    storage: StoragePort
    messaging: MessagingPort

    async def execute(
        self,
        project_id: ProjectId,
        title: str,
        description: str = "",
    ) -> Epic:
        """Execute epic creation.

        Args:
            project_id: Parent project ID (REQUIRED - domain invariant)
            title: Epic title (REQUIRED)
            description: Optional epic description

        Returns:
            Created Epic entity

        Raises:
            ValueError: If project_id is empty or parent project not found
        """
        # Step 1: Validate parent project exists (domain invariant enforcement)
        parent_project = await self.storage.get_project(project_id)
        if not parent_project:
            raise ValueError(
                f"Cannot create Epic: Project {project_id} not found. "
                "Domain Invariant: Epic MUST belong to an existing Project."
            )

        # Step 2: Generate epic ID using UUID for guaranteed uniqueness
        epic_id = EpicId(f"E-{uuid4()}")

        # Step 3: Create Epic domain entity (validation in __post_init__)
        epic = Epic(
            epic_id=epic_id,
            project_id=project_id,  # REQUIRED parent reference
            title=title,
            description=description,
            status=EpicStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Step 4: Persist to dual storage (Neo4j + Valkey)
        # Neo4j will also create Project→Epic relationship
        await self.storage.save_epic(epic)

        logger.info(f"Epic created: {epic_id} - {title} (project: {project_id})")

        # Step 5: Publish event (other services react)
        # Use case creates domain event, mapper handles serialization
        from planning.domain.events.epic_created_event import EpicCreatedEvent
        from planning.infrastructure.mappers.epic_event_mapper import EpicEventMapper

        # Create domain event
        event = EpicEventMapper.epic_to_created_event(epic)

        # Convert to payload (infrastructure mapper)
        payload = EpicEventMapper.created_event_to_payload(event)

        # Publish via port
        await self.messaging.publish_event(
            topic="planning.epic.created",
            payload=payload,
        )

        return epic

