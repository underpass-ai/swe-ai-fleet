"""DTO for task derivation completed event payload."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaskDerivationCompletedPayload:
    """Payload DTO for task.derivation.completed NATS event.
    
    This DTO represents the structured data published to NATS when
    task derivation completes successfully. It's infrastructure-layer
    only and has no business logic.
    
    Attributes:
        event_type: Always "task.derivation.completed"
        plan_id: Plan identifier
        story_id: Story identifier
        role: Executor role that completed the task
        task_count: Number of tasks derived
        timestamp: ISO 8601 timestamp of event
    """

    event_type: str
    plan_id: str
    story_id: str
    role: str
    task_count: int
    timestamp: str

    def __post_init__(self) -> None:
        """Validate payload fields."""
        if not self.event_type:
            raise ValueError("event_type cannot be empty")
        if self.event_type != "task.derivation.completed":
            raise ValueError(f"Invalid event_type: {self.event_type}")
        if not self.plan_id:
            raise ValueError("plan_id cannot be empty")
        if not self.story_id:
            raise ValueError("story_id cannot be empty")
        if not self.role:
            raise ValueError("role cannot be empty")
        if self.task_count < 0:
            raise ValueError("task_count cannot be negative")
        if not self.timestamp:
            raise ValueError("timestamp cannot be empty")

