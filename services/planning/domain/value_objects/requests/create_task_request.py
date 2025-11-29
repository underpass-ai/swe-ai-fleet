"""CreateTaskRequest value object."""

from dataclasses import dataclass

from core.shared.domain.value_objects.content.task_description import TaskDescription
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority
from planning.domain.value_objects.actors.role import Role
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

    story_id: StoryId
    task_id: TaskId
    title: Title
    description: TaskDescription
    task_type: TaskType
    assigned_to: Role
    estimated_hours: Duration
    priority: Priority
    plan_id: PlanId | None = None

    def __post_init__(self) -> None:
        """Validate request.

        Note: Individual VOs already validate themselves.
        This validates request-level invariants if needed.

        Raises:
            ValueError: If validation fails
        """
        # Duration and Priority VOs validate themselves in __post_init__
        # No additional validation needed here
