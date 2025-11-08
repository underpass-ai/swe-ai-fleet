from dataclasses import dataclass

from core.context.domain.entity_ids.decision_id import DecisionId
from core.context.domain.graph_relation_type import GraphRelationType


@dataclass(frozen=True)
class DecisionEdges:
    """Edge between two decisions in the decision graph.

    Represents relationships like DEPENDS_ON, GOVERNS, REFINES, etc.

    DDD-compliant: Uses DecisionId and GraphRelationType instead of primitives.
    """

    src_id: DecisionId
    rel_type: GraphRelationType
    dst_id: DecisionId

    def __post_init__(self) -> None:
        """Validate decision edge.

        Raises:
            ValueError: If validation fails
        """
        if self.src_id == self.dst_id:
            raise ValueError("Decision cannot have edge to itself")
