"""Value object describing an existing task snapshot in Planning Service."""

from dataclasses import dataclass

from core.shared.domain.value_objects.task_attributes.priority import Priority

from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.task_id import TaskId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)


@dataclass(frozen=True)
class TaskSummary:
    """Immutable representation of an existing task used for deduplication."""

    task_id: TaskId
    title: Title
    priority: Priority
    assigned_role: ContextRole

