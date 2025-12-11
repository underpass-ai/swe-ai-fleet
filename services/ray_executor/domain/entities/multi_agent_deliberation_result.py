"""Multi-agent deliberation result entity."""

from dataclasses import dataclass, field

from .deliberation_result import DeliberationResult


@dataclass(frozen=True)
class MultiAgentDeliberationResult:
    """Represents the aggregated result of a multi-agent deliberation.

    This entity contains results from all agents that participated in the deliberation,
    allowing comparison and aggregation of multiple perspectives.

    Attributes:
        agent_results: List of individual agent results
        best_result: The result with the highest score (for backward compatibility)
        total_agents: Total number of agents that participated
        completed_agents: Number of agents that successfully completed
        failed_agents: Number of agents that failed
    """

    agent_results: list[DeliberationResult] = field(default_factory=list)
    total_agents: int = 0
    completed_agents: int = 0
    failed_agents: int = 0

    def __post_init__(self) -> None:
        """Validate multi-agent deliberation result invariants."""
        if self.total_agents < 0:
            raise ValueError("total_agents cannot be negative")

        if self.completed_agents < 0:
            raise ValueError("completed_agents cannot be negative")

        if self.failed_agents < 0:
            raise ValueError("failed_agents cannot be negative")

        if self.completed_agents + self.failed_agents > self.total_agents:
            raise ValueError(
                f"completed_agents ({self.completed_agents}) + failed_agents ({self.failed_agents}) "
                f"cannot exceed total_agents ({self.total_agents})"
            )

        if len(self.agent_results) != self.completed_agents:
            raise ValueError(
                f"agent_results count ({len(self.agent_results)}) must match "
                f"completed_agents ({self.completed_agents})"
            )

    @property
    def best_result(self) -> DeliberationResult | None:
        """Get the result with the highest score.

        Returns:
            DeliberationResult with highest score, or None if no results
        """
        if not self.agent_results:
            return None

        return max(self.agent_results, key=lambda r: r.score)

    @property
    def all_completed(self) -> bool:
        """Check if all agents completed successfully."""
        return self.completed_agents == self.total_agents

    @property
    def has_failures(self) -> bool:
        """Check if any agents failed."""
        return self.failed_agents > 0

    @property
    def average_score(self) -> float:
        """Calculate average score across all completed agents.

        Returns:
            Average score, or 0.0 if no results
        """
        if not self.agent_results:
            return 0.0

        total_score = sum(r.score for r in self.agent_results)
        return total_score / len(self.agent_results)


