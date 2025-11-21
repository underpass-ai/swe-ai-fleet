"""EpicId value object for Planning Service."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EpicId:
    """Value Object for Epic identifier.

    Domain Invariant: EpicId cannot be empty.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate EpicId (fail-fast).

        Raises:
            ValueError: If epic ID is empty or whitespace
        """
        if not self.value or not self.value.strip():
            raise ValueError("EpicId cannot be empty")

    def __str__(self) -> str:
        """String representation.

        Returns:
            String value
        """
        return self.value

