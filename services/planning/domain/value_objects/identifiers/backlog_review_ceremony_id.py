"""BacklogReviewCeremonyId value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BacklogReviewCeremonyId:
    """Value Object for Backlog Review Ceremony identifier.

    Domain Invariant: BacklogReviewCeremonyId cannot be empty.
    Format: BRC-{uuid} (Backlog Review Ceremony)
    """

    value: str

    def __post_init__(self) -> None:
        """Validate BacklogReviewCeremonyId (fail-fast).

        Raises:
            ValueError: If ceremony ID is empty or whitespace
        """
        if not self.value or not self.value.strip():
            raise ValueError("BacklogReviewCeremonyId cannot be empty")

    def __str__(self) -> str:
        """String representation.

        Returns:
            String value
        """
        return self.value


