"""TaskPlan domain entity - Planned task with estimation and dependencies."""

from dataclasses import dataclass

from .entity_ids.task_id import TaskId
from .task_type import TaskType


@dataclass(frozen=True)
class TaskPlan:
    """Planned task with estimation and dependencies (formerly SubtaskPlanDTO).

    This is a domain entity representing a task in the planning phase,
    including estimates, dependencies, and risk assessment.

    Moved from core/reports/dtos/dtos.py to proper domain layer.
    """

    task_id: TaskId
    title: str
    description: str
    role: str  # TODO: Should be Role enum (developer, architect, qa, etc.)
    type: TaskType
    suggested_tech: tuple[str, ...]  # Immutable tuple of technology suggestions
    depends_on: tuple[TaskId, ...]  # Immutable tuple of TaskId dependencies
    estimate_points: float
    priority: int
    risk_score: float  # 0.0 to 1.0
    notes: str

    def __post_init__(self) -> None:
        """Validate task plan."""
        if not self.title or not self.title.strip():
            raise ValueError("Task title cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("Task description cannot be empty")
        if self.estimate_points < 0:
            raise ValueError("estimate_points cannot be negative")
        if self.priority < 0:
            raise ValueError("priority cannot be negative")
        if self.risk_score < 0 or self.risk_score > 1:
            raise ValueError("risk_score must be between 0 and 1")

    def has_dependencies(self) -> bool:
        """Check if task has dependencies.

        Returns:
            True if task depends on other tasks
        """
        return len(self.depends_on) > 0

    def get_dependency_ids(self) -> list[str]:
        """Get list of dependency IDs as strings.

        Returns:
            List of task IDs this task depends on
        """
        return [dep.to_string() for dep in self.depends_on]

    def is_high_risk(self, threshold: float = 0.7) -> bool:
        """Check if task is high risk.

        Args:
            threshold: Risk threshold (default 0.7)

        Returns:
            True if risk_score >= threshold
        """
        return self.risk_score >= threshold

