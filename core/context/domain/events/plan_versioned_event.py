"""PlanVersionedEvent - Domain event for plan versioning."""

from dataclasses import dataclass

from core.context.domain.domain_event import DomainEvent
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.plan_id import PlanId
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.entity_ids.story_id import StoryId


@dataclass(frozen=True)
class PlanVersionedEvent(DomainEvent):
    """Event emitted when a Plan version is created/updated.

    This event signals that a new plan version has been created for a story.
    Includes complete hierarchy for traceability: Project → Epic → Story → Plan.

    Note: event_type inherited from DomainEvent, pass explicitly in constructor.
    """

    plan_id: PlanId
    story_id: StoryId  # Parent story (traceability)
    epic_id: EpicId  # Parent epic (traceability)
    project_id: ProjectId  # Root project (traceability)
    version: int

    def __post_init__(self) -> None:
        """Validate version (fail-fast)."""
        if self.version < 1:
            raise ValueError(f"Plan version must be >= 1, got {self.version}")

