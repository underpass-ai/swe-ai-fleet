"""IndexedStoryData Value Object - Pre-indexed data for fast lookups."""

from dataclasses import dataclass

from core.context.domain.task_plan import TaskPlan
from core.context.domain.story import Story
from core.context.domain.epic import Epic
from core.reports.domain.decision_node import DecisionNode
from core.reports.domain.decision_edges import DecisionEdges
from core.reports.domain.task_node import TaskNode


@dataclass(frozen=True)
class IndexedStoryData:
    """Indexed story data for fast lookups.

    This is a Value Object that holds pre-indexed data structures
    for efficient querying during rehydration.

    Supports the REQUIRED hierarchy: Epic → Story → Task

    DOMAIN INVARIANTS (Business Rules):
    - Every Story MUST belong to an Epic (epic is NOT optional)
    - Every Task MUST belong to a Story (via plan)
    - No orphan stories or tasks allowed

    Immutable by design (frozen=True) to prevent accidental modification.
    """

    # Hierarchy data (Epic → Story → Tasks)
    epic: Epic  # Parent epic (REQUIRED - every story belongs to an epic)
    story: Story  # The story itself (center of context)

    # Indexed collections (all O(1) or O(k) lookups)
    subtasks_by_role: dict[str, list[TaskPlan]]
    decisions_by_id: dict[str, DecisionNode]
    dependencies_by_source: dict[str, list[DecisionEdges]]
    impacts_by_decision: dict[str, list[TaskNode]]

    # Raw collections (for fallback)
    all_decisions: list[DecisionNode]

    def get_tasks_for_role(self, role: str) -> list[TaskPlan]:
        """Get all tasks assigned to a specific role.

        Args:
            role: Role identifier

        Returns:
            List of TaskPlan entities for this role
        """
        return self.subtasks_by_role.get(role, [])

    def get_decision(self, decision_id: str) -> DecisionNode | None:
        """Get decision by ID.

        Args:
            decision_id: Decision identifier

        Returns:
            DecisionNode or None if not found
        """
        return self.decisions_by_id.get(decision_id)

    def get_dependencies_for_decision(self, decision_id: str) -> list[DecisionEdges]:
        """Get dependencies for a decision.

        Args:
            decision_id: Source decision identifier

        Returns:
            List of DecisionEdges where this decision is the source
        """
        return self.dependencies_by_source.get(decision_id, [])

    def get_impacts_for_decision(self, decision_id: str) -> list[TaskNode]:
        """Get tasks impacted by a decision.

        Args:
            decision_id: Decision identifier

        Returns:
            List of TaskNode entities impacted by this decision
        """
        return self.impacts_by_decision.get(decision_id, [])

    def get_epic_title(self) -> str:
        """Get epic title.

        Returns:
            Epic title (always present)
        """
        return self.epic.title

    def get_story_title(self) -> str:
        """Get story title.

        Returns:
            Story title
        """
        return self.story.name

