"""TaskStatusChangedEvent - Domain event for task status changes."""

from dataclasses import dataclass

from core.context.domain.domain_event import DomainEvent
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.plan_id import PlanId
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.event_type import EventType
from core.context.domain.task_status import TaskStatus


@dataclass(frozen=True)
class TaskStatusChangedEvent(DomainEvent):
    """Event emitted when a Task status changes (formerly SubtaskStatusChangedEvent).

    This event signals that a task has transitioned to a new status.
    Includes complete hierarchy for traceability: Project → Epic → Story → Plan → Task.

    Note: event_type inherited from DomainEvent, pass explicitly in constructor.
    """

    task_id: TaskId
    plan_id: PlanId  # Parent plan (traceability)
    story_id: StoryId  # Parent story (traceability)
    epic_id: EpicId  # Parent epic (traceability)
    project_id: ProjectId  # Root project (traceability)
    status: TaskStatus  # REQUIRED - new status
