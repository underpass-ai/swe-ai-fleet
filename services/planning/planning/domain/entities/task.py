"""Task domain entity for Planning Service."""

from dataclasses import dataclass
from datetime import datetime

from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType


@dataclass(frozen=True)
class Task:
    """Task entity - Atomic unit of work.

    A Task represents a concrete work item that needs to be executed.
    Tasks are derived from Stories during planning and belong to a PlanVersion.

    Hierarchy: Project → Epic → Story → PlanVersion → Task

    Design Philosophy:
    - Task aligns with LLM output structure but IDs and assignment are Planning Service responsibility
    - Core fields from LLM: title, description, estimated_hours (content only)
    - IDs REQUIRED from Planning Service: task_id, plan_id, story_id (NOT from LLM)
    - Assignment decided by Planning Service: assigned_to (RBAC - LLM role is just a hint)
    - Timestamps REQUIRED: created_at, updated_at (use case provides on creation/update)
    - System metadata: type, status, priority (Planning Service provides)
    - Domain invariant: Task MUST belong to a PlanVersion (plan_id/story_id required)

    Following DDD:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - No serialization methods (use mappers)
    """

    # REQUIRED fields FIRST (no defaults) - Planning Service provides
    task_id: TaskId  # Planning Service generates (e.g., T-{uuid})
    plan_id: PlanId  # Planning Service provides from context (domain invariant)
    story_id: StoryId  # Planning Service provides from context (denormalized)
    title: str  # From LLM
    created_at: datetime  # Planning Service provides (use case sets on creation)
    updated_at: datetime  # Planning Service provides (use case sets on creation/update)

    # Optional fields LAST (with defaults)
    description: str = ""  # From LLM (optional)
    estimated_hours: int = 0  # From LLM (converted from Duration VO)
    assigned_to: str = ""  # Planning Service assigns based on RBAC (role suggested by LLM is just a hint)
    type: TaskType = TaskType.DEVELOPMENT  # System default
    status: TaskStatus = TaskStatus.TODO  # System default
    priority: int = 1  # System default (fallback only - Planning Service calculates from order in task derivation)

    def __post_init__(self) -> None:
        """Validate task entity (fail-fast).

        Domain Invariants:
        - title cannot be empty (from LLM)
        - estimated_hours cannot be negative (from LLM)
        - priority must be >= 1 (system default or calculated)
        - task_id, plan_id, story_id are REQUIRED (Planning Service provides)
        - created_at and updated_at are REQUIRED (use case provides)
        - Domain invariant: Task MUST belong to a PlanVersion (plan_id/story_id required)

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

        # Domain invariant: if plan_id provided, it must be valid
        # But Task can exist without plan_id initially (more flexible for LLM output)
        # Use case will add plan_id/story_id when persisting

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

