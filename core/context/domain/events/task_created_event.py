"""TaskCreatedEvent - Domain event for task creation."""

from dataclasses import dataclass

from core.context.domain.domain_event import DomainEvent
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.plan_id import PlanId
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.event_type import EventType
from core.context.domain.task_type import TaskType


@dataclass(frozen=True)
class TaskCreatedEvent(DomainEvent):
    """Event emitted when a Task is created (formerly SubtaskCreatedEvent).

    This event signals that a new task has been created within a plan.
    Includes complete hierarchy for traceability: Project → Epic → Story → Plan → Task.

    Note: event_type inherited from DomainEvent, pass explicitly in constructor.
    """

    task_id: TaskId
    plan_id: PlanId  # Parent plan (REQUIRED - domain invariant)
    story_id: StoryId  # Parent story (traceability)
    epic_id: EpicId  # Parent epic (traceability)
    project_id: ProjectId  # Root project (traceability)
    title: str
    type: TaskType
