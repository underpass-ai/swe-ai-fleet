"""DataIndexer domain service - Indexes story data for fast lookups."""

from typing import Any

from core.context.domain.epic import Epic
from core.context.domain.story import Story
from core.context.domain.task_plan import TaskPlan
from core.context.domain.value_objects.indexed_story_data import IndexedStoryData
from core.reports.domain.decision_edges import DecisionEdges
from core.reports.domain.decision_node import DecisionNode
from core.reports.domain.task_node import TaskNode


class DataIndexer:
    """Domain service for indexing story data.

    This service builds efficient index structures for fast lookups
    during context assembly.

    Supports full hierarchy: Epic → Story → Task

    Pure domain logic with NO external dependencies.
    """

    def index(
        self,
        epic: Epic,
        story: Story,
        redis_plan: Any,  # PlanVersion (if None, there are no tasks)
        decisions: list[DecisionNode],
        decision_dependencies: list[DecisionEdges],
        decision_impacts: list[tuple[str, TaskNode]],
    ) -> IndexedStoryData:
        """Index story data for fast lookups.

        DOMAIN INVARIANTS:
        - Every Story MUST belong to an Epic
        - Every Task MUST belong to a Story (via PlanVersion)
        - If no Plan exists, there are no Tasks (empty dict)

        Args:
            epic: Parent epic (REQUIRED - every story must have an epic)
            story: The story entity (center of context - REQUIRED)
            redis_plan: Plan version from Redis (may be None if not planned yet)
            decisions: All decisions for this story
            decision_dependencies: Decision dependency edges
            decision_impacts: Decision impact relationships

        Returns:
            IndexedStoryData with REQUIRED hierarchy: Epic → Story → Tasks

        Raises:
            ValueError: If epic or story is None (violates domain invariant)
        """
        # Fail-fast validation (enforce domain invariants)
        if epic is None:
            raise ValueError("Epic is required - every story must belong to an epic")
        if story is None:
            raise ValueError("Story is required")
        # Index tasks by role
        subtasks_by_role = self._index_tasks_by_role(redis_plan)

        # Index decisions by ID
        decisions_by_id = {d.id: d for d in decisions}

        # Index dependencies by source
        dependencies_by_source: dict[str, list[DecisionEdges]] = {}
        for edge in decision_dependencies:
            dependencies_by_source.setdefault(edge.src_id, []).append(edge)

        # Index impacts by decision
        impacts_by_decision: dict[str, list[TaskNode]] = {}
        for decision_id, task_node in decision_impacts:
            impacts_by_decision.setdefault(decision_id, []).append(task_node)

        return IndexedStoryData(
            epic=epic,
            story=story,
            subtasks_by_role=subtasks_by_role,
            decisions_by_id=decisions_by_id,
            dependencies_by_source=dependencies_by_source,
            impacts_by_decision=impacts_by_decision,
            all_decisions=decisions,
        )

    @staticmethod
    def _index_tasks_by_role(plan: Any | None) -> dict[str, list[TaskPlan]]:
        """Group plan tasks by role for quick lookup.

        DOMAIN INVARIANT: Tasks can only exist if there's a Plan.
        If plan is None, returns empty dict (no tasks yet).

        Args:
            plan: PlanVersion or None (None = story not planned yet, no tasks)

        Returns:
            Dictionary mapping role → list of tasks (empty if no plan)

        Raises:
            ValueError: If plan exists but doesn't have 'tasks' attribute
        """
        # If no plan exists, there are no tasks (domain invariant)
        if plan is None:
            return {}

        # Build index: role → list of tasks
        tasks_by_role: dict[str, list[TaskPlan]] = {}

        # PlanVersion.tasks is a tuple[TaskPlan, ...]
        if not hasattr(plan, 'tasks'):
            raise ValueError(
                "PlanVersion must have 'tasks' attribute. "
                "Domain model violation or incorrect adapter response."
            )

        for task in plan.tasks:
            tasks_by_role.setdefault(task.role, []).append(task)

        return tasks_by_role

