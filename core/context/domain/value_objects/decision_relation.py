"""DecisionRelation Value Object - Relationship between decisions."""

from dataclasses import dataclass

from core.context.domain.entity_ids.decision_id import DecisionId
from core.context.domain.graph_relation_type import GraphRelationType


@dataclass(frozen=True)
class DecisionRelation:
    """Relationship between two decisions (e.g., dependency).

    Represents how decisions relate to each other:
    - Decision A depends on Decision B
    - Decision A supersedes Decision B
    - Decision A contradicts Decision B

    This is a Value Object - immutable and replaceable.
    DDD-compliant: Uses GraphRelationType instead of string.
    """

    source_decision_id: DecisionId
    target_decision_id: DecisionId
    relation_type: GraphRelationType

    def __post_init__(self) -> None:
        """Validate decision relation.

        Raises:
            ValueError: If validation fails
        """
        # Prevent self-references
        if self.source_decision_id.value == self.target_decision_id.value:
            raise ValueError("Decision cannot relate to itself")

    def is_dependency(self) -> bool:
        """Check if this is a dependency relationship.

        Returns:
            True if relation_type is DEPENDS_ON
        """
        return self.relation_type == GraphRelationType.DEPENDS_ON

    def __str__(self) -> str:
        """Return human-readable representation."""
        return (
            f"{self.source_decision_id.to_string()} "
            f"{self.relation_type.value} "
            f"{self.target_decision_id.to_string()}"
        )

