"""Domain event emitted when task derivation succeeds."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..value_objects.identifiers.plan_id import PlanId
from ..value_objects.identifiers.story_id import StoryId
from ..value_objects.task_derivation.status.task_derivation_status import (
    TaskDerivationStatus,
)


@dataclass(frozen=True)
class TaskDerivationCompletedEvent:
    """Immutable event describing a successful derivation run.

    Following DDD and project rules:
    - Events are immutable facts (past tense naming)
    - No reflection, no dynamic mutation
    - Validation happens in __post_init__ (fail-fast)
    """

    plan_id: PlanId
    story_id: StoryId
    task_count: int
    occurred_at: datetime
    status: TaskDerivationStatus = TaskDerivationStatus.SUCCESS

    def __post_init__(self) -> None:
        """Validate invariants."""
        if self.task_count < 0:
            raise ValueError("task_count cannot be negative")

        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")

        if self.status is not TaskDerivationStatus.SUCCESS:
            raise ValueError("status must be SUCCESS for completion events")

