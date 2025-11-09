"""Project domain entity for Planning Service."""

from dataclasses import dataclass
from datetime import UTC, datetime

from planning.domain.value_objects.project_id import ProjectId
from planning.domain.value_objects.project_status import ProjectStatus


@dataclass(frozen=True)
class Project:
    """Project entity - Root of work hierarchy.

    A Project represents the top-level container for organizing work.
    All Epics belong to a Project.

    Hierarchy: Project → Epic → Story → Task

    DOMAIN INVARIANT: Project is the root of the hierarchy.
    All work must trace back to a Project.

    Following DDD:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - No serialization methods (use mappers)
    """

    project_id: ProjectId
    name: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    owner: str = ""  # PO or project owner
    created_at: datetime  # REQUIRED - no defaults (use case provides)
    updated_at: datetime  # REQUIRED - no defaults (use case provides)

    def __post_init__(self) -> None:
        """Validate project entity (fail-fast).

        Domain Invariants:
        - name cannot be empty
        - project_id is already validated by ProjectId value object
        - created_at and updated_at must be provided (NO auto-generation)

        NO REFLECTION: Use case MUST provide timestamps explicitly.
        See .cursorrules Rule #4: NO object.__setattr__()

        Raises:
            ValueError: If validation fails
        """
        if not self.name or not self.name.strip():
            raise ValueError("Project name cannot be empty")

    def is_active(self) -> bool:
        """Check if project is active.

        Returns:
            True if project is actively being worked on
        """
        return self.status.is_active_work()

    def is_completed(self) -> bool:
        """Check if project is completed.

        Returns:
            True if project status is COMPLETED
        """
        return self.status == ProjectStatus.COMPLETED

    def is_terminal(self) -> bool:
        """Check if project is in terminal state.

        Returns:
            True if no further work expected
        """
        return self.status.is_terminal()

