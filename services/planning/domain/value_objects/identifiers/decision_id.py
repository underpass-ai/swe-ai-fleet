"""DecisionId value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionId:
    """
    Value Object: Decision identifier.

    Domain Invariants:
    - Decision ID must not be empty
    - Immutable (frozen=True)

    Immutability: frozen=True ensures no mutation after creation.
    """

    value: str

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If decision ID is empty.
        """
        if not self.value or not self.value.strip():
            raise ValueError("DecisionId cannot be empty")

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value

