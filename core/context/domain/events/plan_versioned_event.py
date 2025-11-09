"""PlanVersionedEvent - Domain event for plan versioning."""

from dataclasses import dataclass

from core.context.domain.domain_event import DomainEvent
from core.context.domain.entity_ids.plan_id import PlanId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.event_type import EventType


@dataclass(frozen=True)
class PlanVersionedEvent(DomainEvent):
    """Event emitted when a Plan version is created/updated.

    This event signals that a new plan version has been created for a story.
    """

    story_id: StoryId
    plan_id: PlanId
    version: int
    event_type: EventType = EventType.PLAN_VERSIONED

    def __post_init__(self) -> None:
        """Validate version (fail-fast)."""
        if self.version < 1:
            raise ValueError("Plan version must be >= 1")

