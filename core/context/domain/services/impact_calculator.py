"""ImpactCalculator domain service - Calculates task impacts from decisions."""

from dataclasses import dataclass

from core.context.domain.entity_ids.decision_id import DecisionId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.value_objects.task_impact import TaskImpact
from core.reports.domain.decision_node import DecisionNode
from core.reports.domain.task_node import TaskNode


@dataclass
class ImpactCalculator:
    """Domain service for calculating which tasks are impacted by decisions.

    This service encapsulates the business logic for determining impact
    relationships between decisions and tasks.

    Pure domain logic with NO external dependencies.
    """

    def calculate_for_role(
        self,
        relevant_decisions: list[DecisionNode],
        impacts_by_decision: dict[str, list[TaskNode]],
        role: str,
    ) -> list[TaskImpact]:
        """Calculate which tasks are impacted by decisions for a specific role.

        Args:
            relevant_decisions: Decisions relevant to this role
            impacts_by_decision: Map of decision_id → impacted tasks
            role: Role identifier (string for now, will use Role enum later)

        Returns:
            List of TaskImpact results (typed, not dicts)
        """
        impacted: list[TaskImpact] = []

        for decision in relevant_decisions:
            decision_id_str = decision.id.to_string()
            for task_node in impacts_by_decision.get(decision_id_str, []):
                if task_node.role.value == role:
                    impacted.append(
                        TaskImpact(
                            decision_id=decision.id,  # DecisionId VO
                            task_id=task_node.id,     # TaskId VO
                            title=task_node.title,
                        )
                    )

        return impacted

    def calculate_total_impacts(
        self,
        impacts_by_decision: dict[str, list[TaskNode]],
    ) -> int:
        """Calculate total number of impact relationships.

        Args:
            impacts_by_decision: Map of decision_id → impacted tasks

        Returns:
            Total count of impact relationships
        """
        return sum(len(tasks) for tasks in impacts_by_decision.values())

