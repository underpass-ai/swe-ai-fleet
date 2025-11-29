"""CreateProjectUseCase - Create new project (root of hierarchy)."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from planning.application.ports import MessagingPort, StoragePort
from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus

logger = logging.getLogger(__name__)


@dataclass
class CreateProjectUseCase:
    """Create a new project (root of work hierarchy).

    This use case:
    1. Validates input data
    2. Creates Project domain entity
    3. Persists to dual storage (Neo4j + Valkey)
    4. Publishes planning.project.created event

    Following Hexagonal Architecture:
    - Depends on ports (StoragePort, MessagingPort)
    - Returns domain entity (Project)
    - No infrastructure dependencies
    """

    storage: StoragePort
    messaging: MessagingPort

    async def execute(
        self,
        name: str,
        description: str = "",
        owner: str = "",
    ) -> Project:
        """Execute project creation.

        Args:
            name: Project name (REQUIRED)
            description: Optional project description
            owner: PO or project owner

        Returns:
            Created Project entity

        Raises:
            ValueError: If name is empty (domain invariant)
        """
        # Step 1: Generate project ID using UUID for guaranteed uniqueness
        project_id = ProjectId(f"PROJ-{uuid4()}")

        # Step 2: Create Project domain entity (validation in __post_init__)
        project = Project(
            project_id=project_id,
            name=name,
            description=description,
            status=ProjectStatus.ACTIVE,
            owner=owner,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Step 3: Persist to dual storage (Neo4j + Valkey)
        await self.storage.save_project(project)

        logger.info(f"Project created: {project_id} - {name}")

        # Step 4: Publish event (other services react)
        # Use case creates domain event, mapper handles serialization
        from planning.infrastructure.mappers.project_event_mapper import ProjectEventMapper

        # Create domain event
        event = ProjectEventMapper.project_to_created_event(project)

        # Convert to payload (infrastructure mapper)
        payload = ProjectEventMapper.created_event_to_payload(event)

        # Publish via port
        await self.messaging.publish_event(
            subject="planning.project.created",
            payload=payload,
        )

        return project

