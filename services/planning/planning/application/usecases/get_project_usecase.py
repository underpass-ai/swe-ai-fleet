"""Use case to get a project by ID."""

import logging

from planning.application.ports.storage_port import StoragePort
from planning.domain.entities.project import Project
from planning.domain.value_objects.project_id import ProjectId

logger = logging.getLogger(__name__)


class GetProjectUseCase:
    """Get a project by ID.

    Following Hexagonal Architecture + DDD.
    """

    def __init__(self, storage: StoragePort):
        """Initialize with storage port (DI)."""
        self._storage = storage

    async def execute(self, project_id: ProjectId) -> Project | None:
        """Get project by ID.

        Args:
            project_id: ProjectId value object

        Returns:
            Project entity or None if not found
        """
        logger.info(
            f"Getting project: {project_id.value}",
            extra={"project_id": project_id.value, "use_case": "GetProject"},
        )

        project = await self._storage.get_project(project_id)

        if project:
            logger.info(f"✓ Project found: {project_id.value}")
        else:
            logger.warning(f"Project not found: {project_id.value}")

        return project

