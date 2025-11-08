"""DecisionMadeEvent - Domain event for technical decisions."""

from dataclasses import dataclass

from core.context.domain.decision_kind import DecisionKind
from core.context.domain.domain_event import DomainEvent
from core.context.domain.entity_ids.decision_id import DecisionId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.event_type import EventType


@dataclass(frozen=True)
class DecisionMadeEvent(DomainEvent):
    """Event emitted when a technical Decision is made.

    This event signals that an architectural or technical decision has been recorded.
    """

    decision_id: DecisionId
    kind: DecisionKind
    summary: str
    related_task_id: TaskId | None = None

    def __post_init__(self) -> None:
        """Initialize event_type for frozen dataclass."""
        object.__setattr__(self, 'event_type', EventType.DECISION_MADE)

