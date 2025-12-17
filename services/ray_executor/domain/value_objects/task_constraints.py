"""Task constraints value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskConstraints:
    """Constraints for task execution.

    Value object representing the constraints and limits for a task execution.

    Attributes:
        story_id: ID of the story/case this task belongs to
        plan_id: ID of the plan this task is part of
        timeout_seconds: Maximum execution time in seconds
        max_retries: Maximum number of retry attempts
        metadata: Additional metadata (e.g., original task_id from planning)
    """

    story_id: str
    plan_id: str
    timeout_seconds: int = 300  # 5 minutes default
    max_retries: int = 3
    metadata: dict[str, str] | None = None

    def __post_init__(self) -> None:
        """Validate task constraints invariants."""
        if not self.story_id:
            raise ValueError("story_id cannot be empty")

        # plan_id is optional (can be empty for backlog review ceremonies)
        # Only story_id is required for backlog review, plan_id is required for task derivation

        if self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be positive, got {self.timeout_seconds}")

        if self.max_retries < 0:
            raise ValueError(f"max_retries cannot be negative, got {self.max_retries}")

