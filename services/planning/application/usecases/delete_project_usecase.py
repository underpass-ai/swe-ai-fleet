"""DeleteProjectUseCase - Delete a project."""

import logging

from planning.application.ports.storage_port import StoragePort
from planning.domain.value_objects.identifiers.project_id import ProjectId

logger = logging.getLogger(__name__)


class DeleteProjectUseCase:
    """Delete a project by ID.

    This use case:
    1. Validates project_id is not empty
    2. Deletes project from dual storage (Neo4j + Valkey)

    Following Hexagonal Architecture:
    - Depends on StoragePort only
    - No infrastructure dependencies
    """

    def __init__(self, storage: StoragePort) -> None:
        """Initialize with storage port (DI)."""
        self._storage = storage

    async def execute(self, project_id: ProjectId) -> None:
        """Execute project deletion.

        Args:
            project_id: Project ID to delete

        Raises:
            ValueError: If project_id is empty
        """
        if not project_id or not project_id.value:
            raise ValueError("project_id cannot be empty")

        logger.info(f"Deleting project: {project_id.value}")

        await self._storage.delete_project(project_id)

        logger.info(f"Project deleted: {project_id.value}")
