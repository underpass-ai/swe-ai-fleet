"""Domain entity for agent reasoning thoughts."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentThought:
    """
    Captures agent's internal reasoning (for observability and debugging).

    This is logged to show HOW the agent thinks and decides.
    Useful for:
    - Debugging why agent made a decision
    - Demo to investors (show intelligence)
    - Audit trail of reasoning
    - Training data for future models
    """

    iteration: int
    thought_type: str  # "analysis", "decision", "observation", "conclusion"
    content: str  # What the agent is thinking
    related_operations: list[str] = field(default_factory=list)  # Tool operations related
    confidence: float | None = None  # How confident (0.0-1.0)
    timestamp: str | None = None

