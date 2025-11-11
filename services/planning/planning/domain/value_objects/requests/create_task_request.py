"""CreateTaskRequest value object."""

from dataclasses import dataclass

from planning.domain.value_objects.actors.role import Role
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_type import TaskType


@dataclass(frozen=True)
class CreateTaskRequest:
    """Request to create a task.

    Value Object (DDD):
    - Encapsulates task creation parameters
    - All fields are VOs (NO primitives)
    - Immutable
    - Type-safe

    Used to pass data from domain/application to use cases.
    Avoids primitive obsession anti-pattern.
    """

    plan_id: PlanId
    story_id: StoryId
    task_id: TaskId
    title: Title
    description: Brief
    task_type: TaskType
    assigned_to: Role
    estimated_hours: int  # TODO: Create Duration VO
    priority: int  # TODO: Create Priority VO

    def __post_init__(self) -> None:
        """Validate request.

        Raises:
            ValueError: If validation fails
        """
        if self.estimated_hours < 0:
            raise ValueError("estimated_hours cannot be negative")

        if self.priority < 1:
            raise ValueError("priority must be >= 1")

