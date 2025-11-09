"""DecisionMadeEvent - Domain event for technical decisions."""

from dataclasses import dataclass

from core.context.domain.decision_kind import DecisionKind
from core.context.domain.domain_event import DomainEvent
from core.context.domain.entity_ids.decision_id import DecisionId
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.event_type import EventType


@dataclass(frozen=True)
class DecisionMadeEvent(DomainEvent):
    """Event emitted when a technical Decision is made.

    This event signals that an architectural or technical decision has been recorded.
    Includes complete hierarchy for traceability: Project → Epic → Story → Task.

    Note: event_type is inherited from DomainEvent and must be passed explicitly
    in constructor: DecisionMadeEvent(..., event_type=EventType.DECISION_MADE)
    """

    decision_id: DecisionId
    project_id: ProjectId  # Root of hierarchy (traceability)
    epic_id: EpicId  # Epic context (traceability)
    story_id: StoryId  # Story context (traceability)
    task_id: TaskId  # Related task (REQUIRED - no orphan decisions)
    kind: DecisionKind
    summary: str

