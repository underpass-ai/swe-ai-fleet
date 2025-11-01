"""Deliberation result entity."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeliberationResult:
    """Represents the result of a completed deliberation.

    This entity contains the output from an agent's deliberation process,
    including the proposal, reasoning, and score.

    Attributes:
        agent_id: ID of the agent that produced this result
        proposal: The agent's proposal/solution
        reasoning: Explanation of why this proposal was made
        score: Quality score of the proposal (0.0-1.0)
        metadata: Additional metadata (execution time, tokens used, etc.)
    """

    agent_id: str
    proposal: str
    reasoning: str
    score: float
    metadata: dict[str, str]

    def __post_init__(self) -> None:
        """Validate deliberation result invariants."""
        if not self.agent_id:
            raise ValueError("agent_id cannot be empty")

        if not self.proposal:
            raise ValueError("proposal cannot be empty")

        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"score must be between 0.0 and 1.0, got {self.score}")

