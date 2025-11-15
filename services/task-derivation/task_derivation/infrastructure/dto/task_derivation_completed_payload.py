"""DTO for task derivation completed event payload."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaskDerivationCompletedPayload:
    """Payload DTO for task.derivation.completed NATS event.

    This DTO represents the structured data published to NATS when
    task derivation completes successfully. It conforms to AsyncAPI
    specification: task.derivation.completed schema.

    Attributes:
        plan_id: Plan identifier
        story_id: Story identifier
        task_count: Number of tasks derived
        status: Always "success"
        occurred_at: ISO 8601 UTC timestamp
        derivation_request_id: Optional Ray Executor job ID
    """

    plan_id: str
    story_id: str
    task_count: int
    status: str
    occurred_at: str
    derivation_request_id: str | None = None

    def __post_init__(self) -> None:
        """Validate payload fields."""
        if not self.plan_id:
            raise ValueError("plan_id cannot be empty")
        if not self.story_id:
            raise ValueError("story_id cannot be empty")
        if self.task_count < 0:
            raise ValueError("task_count cannot be negative")
        if not self.status:
            raise ValueError("status cannot be empty")
        if self.status != "success":
            raise ValueError(f"Invalid status: {self.status} (must be 'success')")
        if not self.occurred_at:
            raise ValueError("occurred_at cannot be empty")

