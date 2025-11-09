"""Epic domain entity for Planning Service."""

from dataclasses import dataclass
from datetime import UTC, datetime

from planning.domain.value_objects.epic_id import EpicId
from planning.domain.value_objects.epic_status import EpicStatus
from planning.domain.value_objects.project_id import ProjectId


@dataclass(frozen=True)
class Epic:
    """Epic entity - Groups related User Stories.

    An Epic represents a large body of work that spans multiple Stories.

    Hierarchy: Project → Epic → Story → Task

    DOMAIN INVARIANT: Epic MUST belong to a Project.
    NO orphan epics allowed.

    Following DDD:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - No serialization methods (use mappers)
    """

    # REQUIRED fields FIRST (no defaults)
    epic_id: EpicId
    project_id: ProjectId  # REQUIRED - enforces domain invariant
    title: str
    created_at: datetime  # REQUIRED - use case provides
    updated_at: datetime  # REQUIRED - use case provides
    # Optional fields LAST (with defaults)
    description: str = ""
    status: EpicStatus = EpicStatus.ACTIVE

    def __post_init__(self) -> None:
        """Validate epic entity (fail-fast).

        Domain Invariants:
        - title cannot be empty
        - project_id is already validated by ProjectId value object
        - created_at and updated_at must be provided (NO auto-generation)

        NO REFLECTION: Use case MUST provide timestamps explicitly.
        See .cursorrules Rule #4: NO object.__setattr__()

        Raises:
            ValueError: If validation fails
        """
        if not self.title or not self.title.strip():
            raise ValueError("Epic title cannot be empty")

    def is_active(self) -> bool:
        """Check if epic is active.

        Returns:
            True if epic is actively being worked on
        """
        return self.status.is_active_work()

    def is_completed(self) -> bool:
        """Check if epic is completed.

        Returns:
            True if epic status is COMPLETED
        """
        return self.status == EpicStatus.COMPLETED

    def is_terminal(self) -> bool:
        """Check if epic is in terminal state.

        Returns:
            True if no further work expected
        """
        return self.status.is_terminal()

