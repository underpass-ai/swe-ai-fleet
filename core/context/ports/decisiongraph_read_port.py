from typing import Protocol

from core.context.domain.epic import Epic
from core.reports.domain.decision_edges import DecisionEdges
from core.reports.domain.decision_node import DecisionNode
from core.reports.domain.task_node import TaskNode
from core.reports.dtos.dtos import PlanVersionDTO


class DecisionGraphReadPort(Protocol):
    """Port for reading decision graph data from Neo4j.

    DOMAIN INVARIANT: Every Story must belong to an Epic.
    """

    def get_epic_by_story(self, story_id: str) -> Epic:
        """Get the Epic that contains this Story.

        DOMAIN INVARIANT: Every story MUST have an epic.

        Args:
            story_id: Story identifier

        Returns:
            Epic entity (NEVER None - fail-fast if not found)

        Raises:
            ValueError: If epic not found (violates domain invariant)
        """
        ...

    def get_plan_by_case(self, case_id: str) -> PlanVersionDTO | None: ...
    def list_decisions(self, case_id: str) -> list[DecisionNode]: ...
    def list_decision_dependencies(self, case_id: str) -> list[DecisionEdges]: ...
    def list_decision_impacts(self, case_id: str) -> list[tuple[str, TaskNode]]: ...
