"""ProjectCreatedEvent - Domain event for project creation."""

from dataclasses import dataclass
from datetime import datetime

from planning.domain.value_objects.project_id import ProjectId


@dataclass(frozen=True)
class ProjectCreatedEvent:
    """Domain event emitted when a Project is created.

    This event signals that a new project (root of hierarchy) has been created.
    Other bounded contexts can react to this event.

    Following DDD:
    - Events are immutable (frozen=True)
    - Events are facts (past tense naming)
    - NO serialization methods (use mappers)
    """

    project_id: ProjectId
    name: str
    description: str
    owner: str
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate event (fail-fast).

        NO REFLECTION: All fields are required and provided by use case.
        See .cursorrules Rule #4: NO object.__setattr__()

        Raises:
            ValueError: If validation fails
        """
        if not self.name or not self.name.strip():
            raise ValueError("Project name cannot be empty in event")

