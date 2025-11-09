"""Task domain entity for Planning Service."""

from dataclasses import dataclass
from datetime import UTC, datetime

from planning.domain.value_objects.plan_id import PlanId
from planning.domain.value_objects.story_id import StoryId
from planning.domain.value_objects.task_id import TaskId
from planning.domain.value_objects.task_status import TaskStatus
from planning.domain.value_objects.task_type import TaskType


@dataclass(frozen=True)
class Task:
    """Task entity - Atomic unit of work.

    A Task represents a concrete work item that needs to be executed.
    Tasks are derived from Stories during planning and belong to a PlanVersion.

    Hierarchy: Project → Epic → Story → PlanVersion → Task

    DOMAIN INVARIANT: Task MUST belong to a PlanVersion (which belongs to a Story).
    NO orphan tasks allowed.

    Following DDD:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - No serialization methods (use mappers)
    """

    task_id: TaskId
    plan_id: PlanId  # REQUIRED - parent plan (domain invariant)
    story_id: StoryId  # Denormalized for fast lookups (derived from plan)
    title: str
    description: str = ""
    type: TaskType = TaskType.DEVELOPMENT
    status: TaskStatus = TaskStatus.TODO
    assigned_to: str = ""  # Agent or role assigned
    estimated_hours: int = 0
    priority: int = 1
    created_at: datetime  # REQUIRED - no defaults (use case provides)
    updated_at: datetime  # REQUIRED - no defaults (use case provides)

    def __post_init__(self) -> None:
        """Validate task entity (fail-fast).

        Domain Invariants:
        - title cannot be empty
        - story_id is already validated by StoryId value object
        - estimated_hours cannot be negative
        - priority must be >= 1
        - created_at and updated_at must be provided (NO auto-generation)

        NO REFLECTION: Use case MUST provide timestamps explicitly.
        See .cursorrules Rule #4: NO object.__setattr__()

        Raises:
            ValueError: If validation fails
        """
        if not self.title or not self.title.strip():
            raise ValueError("Task title cannot be empty")

        if self.estimated_hours < 0:
            raise ValueError(f"estimated_hours cannot be negative: {self.estimated_hours}")

        if self.priority < 1:
            raise ValueError(f"priority must be >= 1: {self.priority}")

    def is_completed(self) -> bool:
        """Check if task is completed.

        Returns:
            True if task status is COMPLETED
        """
        return self.status == TaskStatus.COMPLETED

    def is_terminal(self) -> bool:
        """Check if task is in terminal state.

        Returns:
            True if no further work expected
        """
        return self.status.is_terminal()

    def is_blocked(self) -> bool:
        """Check if task is blocked.

        Returns:
            True if task status is BLOCKED
        """
        return self.status == TaskStatus.BLOCKED

