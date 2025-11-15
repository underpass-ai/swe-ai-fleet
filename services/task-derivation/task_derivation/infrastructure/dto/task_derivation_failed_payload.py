"""DTO for task derivation failed event payload."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaskDerivationFailedPayload:
    """Payload DTO for task.derivation.failed NATS event.
    
    This DTO represents the structured data published to NATS when
    task derivation fails. It's infrastructure-layer only and has
    no business logic.
    
    Attributes:
        event_type: Always "task.derivation.failed"
        plan_id: Plan identifier
        story_id: Story identifier
        reason: Human-readable failure reason
        requires_manual_review: Whether manual intervention is needed
        timestamp: ISO 8601 timestamp of event
    """

    event_type: str
    plan_id: str
    story_id: str
    reason: str
    requires_manual_review: bool
    timestamp: str

    def __post_init__(self) -> None:
        """Validate payload fields."""
        if not self.event_type:
            raise ValueError("event_type cannot be empty")
        if self.event_type != "task.derivation.failed":
            raise ValueError(f"Invalid event_type: {self.event_type}")
        if not self.plan_id:
            raise ValueError("plan_id cannot be empty")
        if not self.story_id:
            raise ValueError("story_id cannot be empty")
        if not self.reason:
            raise ValueError("reason cannot be empty")
        if not self.timestamp:
            raise ValueError("timestamp cannot be empty")

