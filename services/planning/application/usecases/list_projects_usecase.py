"""Use case to list all projects."""

import logging

from planning.application.ports.storage_port import StoragePort
from planning.domain.entities.project import Project

logger = logging.getLogger(__name__)


class ListProjectsUseCase:
    """List all projects with pagination.

    Following Hexagonal Architecture + DDD.
    """

    def __init__(self, storage: StoragePort):
        """Initialize with storage port (DI)."""
        self._storage = storage

    async def execute(self, limit: int = 100, offset: int = 0) -> list[Project]:
        """List projects with pagination.

        Args:
            limit: Maximum number of projects to return
            offset: Number of projects to skip

        Returns:
            List of Project entities
        """
        logger.info(
            f"Listing projects: limit={limit}, offset={offset}",
            extra={"limit": limit, "offset": offset, "use_case": "ListProjects"},
        )

        projects = await self._storage.list_projects(limit=limit, offset=offset)

        # Fail-fast: Ensure projects is never None (defensive programming)
        if projects is None:
            logger.warning("Storage returned None for list_projects, returning empty list")
            projects = []

        logger.info(f"✓ Found {len(projects)} projects")

        return projects

