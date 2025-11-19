"""Value object describing a task creation command for Planning Service."""

from __future__ import annotations

from dataclasses import dataclass

from core.shared.domain.value_objects.content.task_description import TaskDescription
from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)


@dataclass(frozen=True)
class TaskCreationCommand:
    """Immutable VO representing a request to persist a derived task."""

    plan_id: PlanId
    story_id: StoryId
    title: Title
    description: TaskDescription
    estimated_hours: Duration
    priority: Priority
    assigned_role: ContextRole

