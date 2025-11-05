"""Agent ID value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentId:
    """Value Object: Agent identifier.

    Represents a unique identifier for an agent in the system.

    Domain Invariants:
    - Agent ID cannot be empty
    - Agent ID is immutable

    Examples:
        >>> agent_id = AgentId(value="agent-dev-001")
        >>> agent_id.value
        'agent-dev-001'
    """

    value: str

    def __post_init__(self) -> None:
        """Validate agent ID (fail-fast).

        Raises:
            ValueError: If value is empty
        """
        if not self.value:
            raise ValueError("AgentId cannot be empty")

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value

