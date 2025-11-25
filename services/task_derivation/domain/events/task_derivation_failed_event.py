"""Domain event emitted when task derivation fails."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..value_objects.identifiers.plan_id import PlanId
from ..value_objects.identifiers.story_id import StoryId
from ..value_objects.task_derivation.status.task_derivation_status import (
    TaskDerivationStatus,
)


@dataclass(frozen=True)
class TaskDerivationFailedEvent:
    """Immutable event describing a failed derivation attempt."""

    plan_id: PlanId
    story_id: StoryId
    reason: str
    requires_manual_review: bool
    occurred_at: datetime
    status: TaskDerivationStatus = TaskDerivationStatus.FAILED

    def __post_init__(self) -> None:
        """Validate invariants."""
        if not self.reason or not self.reason.strip():
            raise ValueError("reason cannot be empty")

        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")

        if self.status is not TaskDerivationStatus.FAILED:
            raise ValueError("status must be FAILED for failure events")

