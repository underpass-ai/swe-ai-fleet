"""StoryTasksNotReadyEvent - Domain event for story tasks not ready for execution."""

from dataclasses import dataclass
from datetime import datetime

from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId


@dataclass(frozen=True)
class StoryTasksNotReadyEvent:
    """Domain event emitted when story cannot transition to READY_FOR_EXECUTION.

    This event implements HUMAN-IN-THE-LOOP pattern:
    - Notifies the Product Owner (HUMAN) that a story has tasks without priorities
    - PO receives notification in UI and can intervene to fix the issue
    - PO can reformulate the story or request re-derivation of tasks

    Business Rule:
    - All tasks must have priorities (>= 1) defined by LLM before story can be ready
    - PO (Product Owner) is HUMAN in swe-ai-fleet (human-in-the-loop)
    - PO receives this event notification in the UI
    - PO can reformulate the story or fix tasks based on the notification
    - This is a human gate: PO must approve/fix before story can proceed

    Following DDD:
    - Events are immutable (frozen=True)
    - Events are facts (past tense naming)
    - NO serialization methods (use mappers)
    """

    story_id: StoryId
    reason: str  # Reason why tasks are not ready (e.g., "No tasks defined", "Tasks without priority")
    task_ids_without_priority: tuple[TaskId, ...]  # Tasks that need priority
    total_tasks: int  # Total number of tasks for the story
    occurred_at: datetime  # When the event occurred

    def __post_init__(self) -> None:
        """Validate event (fail-fast).

        Raises:
            ValueError: If validation fails
        """
        if not self.reason or not self.reason.strip():
            raise ValueError("reason cannot be empty")

        if self.total_tasks < 0:
            raise ValueError(f"total_tasks cannot be negative: {self.total_tasks}")

        if len(self.task_ids_without_priority) > self.total_tasks:
            raise ValueError(
                f"task_ids_without_priority ({len(self.task_ids_without_priority)}) "
                f"cannot exceed total_tasks ({self.total_tasks})"
            )

