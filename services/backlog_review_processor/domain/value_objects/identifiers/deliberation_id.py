"""DeliberationId value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeliberationId:
    """Value Object for Deliberation identifier.

    Domain Invariant: DeliberationId cannot be empty.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate DeliberationId (fail-fast).

        Raises:
            ValueError: If deliberation ID is empty or whitespace
        """
        if not self.value or not self.value.strip():
            raise ValueError("DeliberationId cannot be empty")

    def __str__(self) -> str:
        """String representation.

        Returns:
            String value
        """
        return self.value

