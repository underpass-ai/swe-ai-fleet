"""TaskImpact Value Object - Impact relationship between decision and task."""

from dataclasses import dataclass

from core.context.domain.entity_ids.decision_id import DecisionId
from core.context.domain.entity_ids.task_id import TaskId


@dataclass(frozen=True)
class TaskImpact:
    """Task impact result from decision.

    Represents the relationship where a decision impacts/influences a task.

    This is a Value Object - immutable and replaceable.
    DDD-compliant: Uses DecisionId and TaskId instead of primitives.
    """

    decision_id: DecisionId
    task_id: TaskId
    title: str

    def __post_init__(self) -> None:
        """Validate task impact.

        Raises:
            ValueError: If validation fails
        """
        if not self.title:
            raise ValueError("Task title cannot be empty")

    def __str__(self) -> str:
        """Return human-readable representation."""
        return (
            f"Decision {self.decision_id.to_string()} impacts "
            f"Task {self.task_id.to_string()} ({self.title})"
        )

