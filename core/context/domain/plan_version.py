# core/context/domain/plan_version.py
from __future__ import annotations

from dataclasses import dataclass

from .entity_ids.actor_id import ActorId
from .entity_ids.plan_id import PlanId
from .entity_ids.story_id import StoryId
from .graph_label import GraphLabel
from .graph_relation_type import GraphRelationType
from .graph_relationship import GraphRelationship
from .task_plan import TaskPlan


@dataclass(frozen=True)
class PlanVersion:
    """Domain model representing a PlanVersion entity in the context graph.

    A PlanVersion represents a specific version of a plan for completing a Story.
    It serves as an intermediate entity connecting Stories to their Tasks (formerly Case/Subtasks).

    This is a pure domain entity with NO serialization methods.
    Use PlanVersionMapper in infrastructure layer for conversions.
    """

    plan_id: PlanId
    version: int
    story_id: StoryId
    status: str = "draft"  # draft, approved, rejected, archived
    author_id: ActorId | None = None
    rationale: str = ""
    tasks: tuple[TaskPlan, ...] = ()  # Immutable tuple of tasks
    created_at_ms: int = 0

    def __post_init__(self) -> None:
        """Validate plan version."""
        if self.version < 1:
            raise ValueError("Plan version must be >= 1")
        if self.status not in {"draft", "approved", "rejected", "archived"}:
            raise ValueError(f"Invalid status: {self.status}")

    def get_task_count(self) -> int:
        """Get number of tasks in this plan.

        Returns:
            Number of tasks
        """
        return len(self.tasks)

    def is_draft(self) -> bool:
        """Check if plan is still in draft status.

        Returns:
            True if status is draft
        """
        return self.status == "draft"

    def is_approved(self) -> bool:
        """Check if plan has been approved.

        Returns:
            True if status is approved
        """
        return self.status == "approved"

    def get_relationship_to_story(self) -> GraphRelationship:
        """Get the relationship details to connect this plan to its Story (formerly case).

        Returns:
            GraphRelationship connecting Story to PlanVersion with HAS_PLAN type
        """
        return GraphRelationship(
            src_id=self.story_id.to_string(),
            rel_type=GraphRelationType.HAS_PLAN,
            dst_id=self.plan_id.to_string(),
            src_labels=[GraphLabel.STORY],
            dst_labels=[GraphLabel.PLAN_VERSION],
        )
