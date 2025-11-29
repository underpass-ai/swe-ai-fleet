"""Use case to list all projects."""

import logging

from planning.application.ports.storage_port import StoragePort
from planning.domain.entities.project import Project
from planning.domain.value_objects.statuses.project_status import ProjectStatus

logger = logging.getLogger(__name__)


class ListProjectsUseCase:
    """List all projects with pagination.

    Following Hexagonal Architecture + DDD.
    """

    def __init__(self, storage: StoragePort):
        """Initialize with storage port (DI)."""
        self._storage = storage

    async def execute(
        self,
        status_filter: ProjectStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Project]:
        """List projects with optional status filtering and pagination.

        Args:
            status_filter: Filter by status (optional)
            limit: Maximum number of projects to return
            offset: Number of projects to skip

        Returns:
            List of Project entities
        """
        logger.info(
            f"Listing projects: status_filter={status_filter}, limit={limit}, offset={offset}",
            extra={
                "status_filter": status_filter.value if status_filter else None,
                "limit": limit,
                "offset": offset,
                "use_case": "ListProjects",
            },
        )

        projects = await self._storage.list_projects(
            status_filter=status_filter,
            limit=limit,
            offset=offset,
        )

        # Fail-fast: Ensure projects is never None (defensive programming)
        if projects is None:
            logger.warning("Storage returned None for list_projects, returning empty list")
            projects = []

        logger.info(f"✓ Found {len(projects)} projects")

        return projects

