from dataclasses import dataclass

from core.context.domain.plan_header import PlanHeader
from core.context.domain.role import Role
from core.context.domain.story_header import StoryHeader
from core.context.domain.task_plan import TaskPlan
from core.context.domain.value_objects.decision_relation import DecisionRelation
from core.context.domain.value_objects.impacted_task import ImpactedTask
from core.context.domain.value_objects.milestone import Milestone
from core.reports.domain.decision_node import DecisionNode


@dataclass(frozen=True)
class RoleContextFields:
    """Context fields for a specific role.

    Contains all the information needed by an agent or user in a specific role
    to understand the current state of work.

    This is an aggregate that brings together:
    - Story context (what we're building)
    - Plan context (how we're building it)
    - Role-specific tasks
    - Relevant decisions and their impacts
    - Recent milestones and summaries

    DDD-compliant: Uses domain entities and Value Objects (NO dicts).
    Immutable by design (frozen=True).
    """

    role: Role
    story_header: StoryHeader
    plan_header: PlanHeader
    role_tasks: tuple[TaskPlan, ...]
    decisions_relevant: list[DecisionNode]
    decision_dependencies: tuple[DecisionRelation, ...]
    impacted_tasks: tuple[ImpactedTask, ...]
    recent_milestones: tuple[Milestone, ...]
    last_summary: str | None
    token_budget_hint: int

    def has_story_header(self) -> bool:
        """Check if story header is present."""
        return self.story_header is not None

    def has_plan(self) -> bool:
        """Check if plan exists."""
        return self.plan_header is not None

    def get_task_count(self) -> int:
        """Get total number of tasks for this role."""
        return len(self.role_tasks)

    def get_decision_count(self) -> int:
        """Get total number of relevant decisions."""
        return len(self.decisions_relevant)

    def get_recent_milestones(self, limit: int = 10) -> tuple[Milestone, ...]:
        """Return the last N recent milestones.

        Args:
            limit: Number of milestones to return (non-positive returns empty)

        Returns:
            Tuple of recent milestones (ordered by timestamp)
        """
        if limit <= 0:
            return ()
        return self.recent_milestones[-limit:]
