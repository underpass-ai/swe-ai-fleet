"""DTO for task derivation failed event payload."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaskDerivationFailedPayload:
    """Payload DTO for task.derivation.failed NATS event.

    This DTO represents the structured data published to NATS when
    task derivation fails. It conforms to AsyncAPI specification:
    task.derivation.failed schema.

    Attributes:
        plan_id: Plan identifier
        story_id: Story identifier
        status: Always "failed"
        reason: Human-readable failure reason
        requires_manual_review: Whether Planning must mark story as not planned
        occurred_at: ISO 8601 UTC timestamp
        derivation_request_id: Optional Ray Executor job ID (if available)
    """

    plan_id: str
    story_id: str
    status: str
    reason: str
    requires_manual_review: bool
    occurred_at: str
    derivation_request_id: str | None = None

    def __post_init__(self) -> None:
        """Validate payload fields."""
        if not self.plan_id:
            raise ValueError("plan_id cannot be empty")
        if not self.story_id:
            raise ValueError("story_id cannot be empty")
        if not self.status:
            raise ValueError("status cannot be empty")
        if self.status != "failed":
            raise ValueError(f"Invalid status: {self.status} (must be 'failed')")
        if not self.reason:
            raise ValueError("reason cannot be empty")
        if not self.occurred_at:
            raise ValueError("occurred_at cannot be empty")

