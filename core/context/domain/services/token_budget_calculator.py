"""TokenBudgetCalculator domain service - Calculates token budgets for roles."""

from dataclasses import dataclass

from core.context.domain.role import Role


@dataclass
class TokenBudgetCalculator:
    """Domain service for calculating token budgets based on role and context size.

    This is a pure domain service with NO external dependencies.
    It encapsulates the business logic for token allocation.
    """

    # Configuration (can be injected or defaulted)
    base_architect: int = 8192
    base_default: int = 4096
    bump_per_task: int = 256
    bump_per_decision: int = 128
    bump_max: int = 4096

    def calculate(
        self,
        role: Role,
        task_count: int,
        decision_count: int,
    ) -> int:
        """Calculate suggested token budget for a role.

        Architects get more tokens because they need broader context.
        Budget increases with number of tasks and decisions.

        Args:
            role: Role enum
            task_count: Number of tasks in role's context
            decision_count: Number of relevant decisions

        Returns:
            Suggested token budget

        Raises:
            ValueError: If counts are negative
        """
        if task_count < 0:
            raise ValueError("task_count cannot be negative")
        if decision_count < 0:
            raise ValueError("decision_count cannot be negative")

        # Base budget depends on role
        base = self.base_architect if role == Role.ARCHITECT else self.base_default

        # Calculate bump based on context size
        bump = min(
            self.bump_max,
            task_count * self.bump_per_task + decision_count * self.bump_per_decision,
        )

        return base + bump

    def calculate_for_full_access_role(self, total_tasks: int, total_decisions: int) -> int:
        """Calculate token budget for roles with full context access (PO, Admin).

        Args:
            total_tasks: Total number of tasks across all roles
            total_decisions: Total number of decisions

        Returns:
            Suggested token budget (typically higher)
        """
        # Full access roles get architect-level base + full bump
        base = self.base_architect
        bump = min(
            self.bump_max,
            total_tasks * self.bump_per_task + total_decisions * self.bump_per_decision,
        )
        return base + bump

