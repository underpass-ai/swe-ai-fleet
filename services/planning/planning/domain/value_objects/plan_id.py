"""PlanId value object for Planning Service."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanId:
    """Value Object for Plan identifier.

    Domain Invariant: PlanId cannot be empty.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate PlanId (fail-fast).

        Raises:
            ValueError: If plan ID is empty or whitespace
        """
        if not self.value or not self.value.strip():
            raise ValueError("PlanId cannot be empty")

    def __str__(self) -> str:
        """String representation.

        Returns:
            String value
        """
        return self.value

