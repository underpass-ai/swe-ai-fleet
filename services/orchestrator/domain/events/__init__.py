"""Domain events for orchestrator.

Events represent facts that have occurred in the orchestration domain.
They follow Domain-Driven Design and Event-Driven Architecture principles.

All events:
- Are immutable (frozen dataclasses)
- Inherit from DomainEvent base class
- Have a clear event_type identifier
- Can be serialized to dict for messaging
"""

from .deliberation_completed_event import DeliberationCompletedEvent
from .domain_event import DomainEvent
from .phase_changed_event import PhaseChangedEvent
from .plan_approved_event import PlanApprovedEvent
from .task_completed_event import TaskCompletedEvent
from .task_dispatched_event import TaskDispatchedEvent
from .task_failed_event import TaskFailedEvent

__all__ = [
    "DeliberationCompletedEvent",
    "DomainEvent",
    "PhaseChangedEvent",
    "PlanApprovedEvent",
    "TaskCompletedEvent",
    "TaskDispatchedEvent",
    "TaskFailedEvent",
]

