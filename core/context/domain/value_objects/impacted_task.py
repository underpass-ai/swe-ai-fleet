"""ImpactedTask Value Object - Task impacted by a decision."""

from dataclasses import dataclass

from core.context.domain.entity_ids.decision_id import DecisionId
from core.context.domain.entity_ids.task_id import TaskId


@dataclass(frozen=True)
class ImpactedTask:
    """Represents a task that is impacted by a decision.

    This Value Object captures the impact relationship between
    a decision and a task, including context about the impact.

    Example: "Decision D-001 (Use Neo4j) impacts Task T-005 (Database migration)"

    This is a Value Object - immutable and replaceable.
    """

    decision_id: DecisionId
    task_id: TaskId
    title: str
    impact_description: str = ""

    def __post_init__(self) -> None:
        """Validate impacted task.

        Raises:
            ValueError: If validation fails
        """
        if not self.title or not self.title.strip():
            raise ValueError("Task title cannot be empty")

    def has_description(self) -> bool:
        """Check if impact has a description.

        Returns:
            True if impact_description is not empty
        """
        return bool(self.impact_description and self.impact_description.strip())

    def __str__(self) -> str:
        """Return human-readable representation."""
        base = (
            f"Decision {self.decision_id.to_string()} impacts "
            f"Task {self.task_id.to_string()} ({self.title})"
        )
        if self.has_description():
            return f"{base}: {self.impact_description}"
        return base

