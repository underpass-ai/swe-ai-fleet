from dataclasses import dataclass

from core.context.domain.decision_status import DecisionStatus
from core.context.domain.entity_ids.actor_id import ActorId
from core.context.domain.entity_ids.decision_id import DecisionId


@dataclass(frozen=True)
class DecisionNode:
    """Decision node in decision graph.

    Represents a decision with its metadata for graph analytics and impact tracking.

    DDD-compliant: Uses DecisionId, ActorId, and DecisionStatus instead of primitives.
    """

    id: DecisionId
    title: str
    rationale: str
    status: DecisionStatus
    created_at_ms: int
    author_id: ActorId

    def __post_init__(self) -> None:
        """Validate decision node.

        Raises:
            ValueError: If validation fails
        """
        if not self.title:
            raise ValueError("Decision title cannot be empty")
        if self.created_at_ms < 0:
            raise ValueError(f"created_at_ms must be >= 0, got {self.created_at_ms}")
