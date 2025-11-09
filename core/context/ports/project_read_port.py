"""ProjectReadPort - Port for reading Project entities."""

from typing import Protocol

from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.project import Project


class ProjectReadPort(Protocol):
    """Port for reading Project entities from persistence.

    This port abstracts project data retrieval for the application layer.
    Implementation can be Neo4j, Valkey, or any other storage.

    Following Hexagonal Architecture:
    - Application layer depends on this port (interface)
    - Infrastructure adapter implements this port
    - Port works with domain entities, NOT primitives
    """

    def get_project(self, project_id: ProjectId) -> Project | None:
        """Get project by ID.

        Args:
            project_id: Project identifier

        Returns:
            Project domain entity or None if not found
        """
        ...

    def list_projects(self, status: str | None = None) -> list[Project]:
        """List all projects, optionally filtered by status.

        Args:
            status: Optional status filter (ACTIVE, PLANNING, etc.)

        Returns:
            List of Project domain entities
        """
        ...

    def get_active_projects(self) -> list[Project]:
        """Get all active projects (convenience method).

        Returns:
            List of active Project entities
        """
        ...

