"""StoryCreatedEvent - Domain event for story creation."""

from dataclasses import dataclass

from core.context.domain.domain_event import DomainEvent
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.event_type import EventType


@dataclass(frozen=True)
class StoryCreatedEvent(DomainEvent):
    """Event emitted when a Story is created (formerly CaseCreatedEvent).

    This event signals that a new user story has been created in the system.
    """

    story_id: StoryId
    name: str
    event_type: EventType = EventType.STORY_CREATED  # Fixed value

    def __post_init__(self) -> None:
        """Initialize event_type for frozen dataclass."""
