"""TaskCreatedEvent - Domain event for task creation."""

from dataclasses import dataclass
from datetime import datetime

from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_type import TaskType


@dataclass(frozen=True)
class TaskCreatedEvent:
    """Domain event emitted when a Task is created.

    This event signals that a new task has been derived from a story's plan.
    Other bounded contexts can react to this event (e.g., Workflow Service).

    Following DDD:
    - Events are immutable (frozen=True)
    - Events are facts (past tense naming)
    - NO serialization methods (use mappers)
    """

    task_id: TaskId
    story_id: StoryId  # Denormalized for convenience
    title: str
    created_at: datetime
    plan_id: PlanId | None = None # Parent plan (optional)
    description: str = ""
    type: TaskType = TaskType.DEVELOPMENT
    assigned_to: str = ""
    estimated_hours: int = 0
    priority: int = 1

    def __post_init__(self) -> None:
        """Validate event (fail-fast).

        NO REFLECTION: All fields are required and provided by use case.
        See .cursorrules Rule #4: NO object.__setattr__()

        Raises:
            ValueError: If validation fails
        """
        if not self.title or not self.title.strip():
            raise ValueError("Task title cannot be empty in event")

        if self.estimated_hours < 0:
            raise ValueError("estimated_hours cannot be negative in event")

