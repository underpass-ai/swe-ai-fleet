"""Data Transfer Object for State Transition.

DTO for Neo4j persistence and API responses.
Following DDD + Hexagonal Architecture principles.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StateTransitionDTO:
    """DTO for state transition (audit trail record).

    Represents a workflow state transition for persistence/serialization.
    Used by:
    - Neo4j adapter (persistence)
    - Valkey adapter (cache)
    - API responses (audit trail)

    Following DDD:
    - DTO does NOT implement to_dict() / from_dict()
    - Conversion handled by mappers in infrastructure layer
    - Immutable (frozen=True)
    - Fail-fast validation

    Domain Invariants:
    - from_state and to_state cannot be empty
    - action cannot be empty
    - actor_role cannot be empty
    - timestamp must be ISO format string
    """

    from_state: str
    to_state: str
    action: str
    actor_role: str
    timestamp: str
    feedback: str | None

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If any invariant is violated
        """
        if not self.from_state:
            raise ValueError("from_state cannot be empty")

        if not self.to_state:
            raise ValueError("to_state cannot be empty")

        if not self.action:
            raise ValueError("action cannot be empty")

        if not self.actor_role:
            raise ValueError("actor_role cannot be empty")

        if not self.timestamp:
            raise ValueError("timestamp cannot be empty")

