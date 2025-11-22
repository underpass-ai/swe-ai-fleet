"""StoryCreatedEvent - Domain event for story creation."""

from dataclasses import dataclass

from core.context.domain.domain_event import DomainEvent
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.entity_ids.story_id import StoryId


@dataclass(frozen=True)
class StoryCreatedEvent(DomainEvent):
    """Event emitted when a Story is created (formerly CaseCreatedEvent).

    This event signals that a new user story has been created in the system.
    Includes complete hierarchy for traceability: Project → Epic → Story.

    Note: event_type inherited from DomainEvent, pass explicitly in constructor.
    """

    story_id: StoryId
    epic_id: EpicId  # Parent epic (REQUIRED - domain invariant)
    project_id: ProjectId  # Root project (traceability)
    name: str
