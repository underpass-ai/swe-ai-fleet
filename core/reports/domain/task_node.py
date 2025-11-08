from dataclasses import dataclass

from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.role import Role


@dataclass(frozen=True)
class TaskNode:
    """Task node representation for impact analysis (formerly SubtaskNode).

    This is a simplified view of a task used for decision impact tracking.

    DDD-compliant: Uses TaskId and Role instead of primitives.
    """

    id: TaskId
    title: str
    role: Role

    def __post_init__(self) -> None:
        """Validate task node.

        Raises:
            ValueError: If validation fails
        """
        if not self.title:
            raise ValueError("Task title cannot be empty")
