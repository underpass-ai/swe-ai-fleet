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
    event_type: EventType = EventType.DECISION_MADE  # Fixed value - no reflection needed

    def __post_init__(self) -> None:
        """Validate event (fail-fast).

        NO REFLECTION: event_type has default value.
        See .cursorrules Rule #4: NO object.__setattr__()
        """
        # Validation only - no mutation
        pass

