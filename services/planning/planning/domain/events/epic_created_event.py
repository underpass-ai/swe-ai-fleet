"""EpicCreatedEvent - Domain event for epic creation."""

from dataclasses import dataclass
from datetime import datetime

from planning.domain.value_objects.epic_id import EpicId
from planning.domain.value_objects.project_id import ProjectId


@dataclass(frozen=True)
class EpicCreatedEvent:
    """Domain event emitted when an Epic is created.

    This event signals that a new epic has been created within a project.
    Other bounded contexts can react to this event.

    Following DDD:
    - Events are immutable (frozen=True)
    - Events are facts (past tense naming)
    - NO serialization methods (use mappers)
    """

    epic_id: EpicId
    project_id: ProjectId  # Parent project (domain invariant)
    title: str
    description: str
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate event (fail-fast).

        NO REFLECTION: All fields are required and provided by use case.
        See .cursorrules Rule #4: NO object.__setattr__()

        Raises:
            ValueError: If validation fails
        """
        if not self.title or not self.title.strip():
            raise ValueError("Epic title cannot be empty in event")

