"""DecisionSelector domain service - Selects relevant decisions for a role."""

from dataclasses import dataclass

from core.context.domain.task_plan import TaskPlan
from core.reports.domain.decision_node import DecisionNode
from core.reports.domain.task_node import TaskNode


@dataclass
class DecisionSelector:
    """Domain service for selecting decisions relevant to a role.

    This service encapsulates the business logic for determining which
    decisions are relevant to a role based on their task assignments.

    Pure domain logic with NO external dependencies.
    """

    fallback_count: int = 5  # Number of decisions to return if no specific matches

    def select_for_role(
        self,
        role_tasks: list[TaskPlan],
        impacts_by_decision: dict[str, list[TaskNode]],
        decisions_by_id: dict[str, DecisionNode],
        all_decisions: list[DecisionNode],
    ) -> list[DecisionNode]:
        """Select decisions relevant to a role's tasks.

        Algorithm:
        1. If role has tasks, find decisions that impact those tasks
        2. If no decisions found, return first N decisions as fallback

        Args:
            role_tasks: Tasks assigned to this role
            impacts_by_decision: Map of decision_id → impacted TaskNodes
            decisions_by_id: Map of decision_id → DecisionNode
            all_decisions: All available decisions (for fallback)

        Returns:
            List of relevant DecisionNode entities
        """
        relevant: list[DecisionNode] = []

        if role_tasks:
            # Build set of task IDs for this role
            task_ids = {task.task_id.to_string() for task in role_tasks}

            # Find decisions that impact any of these tasks
            for decision_id, impacted_subtasks in impacts_by_decision.items():
                if any(subtask.id in task_ids for subtask in impacted_subtasks):
                    decision = decisions_by_id.get(decision_id)
                    if decision:
                        relevant.append(decision)

        # Fallback: if no specific decisions, return first N
        if not relevant:
            return all_decisions[:self.fallback_count]

        return relevant

