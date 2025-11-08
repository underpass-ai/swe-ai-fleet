"""Acceptance Criteria value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AcceptanceCriteria:
    """Value Object for acceptance criteria list.

    Encapsulates validation and behavior for story acceptance criteria.
    """

    criteria: tuple[str, ...]  # Tuple for immutability

    def __post_init__(self) -> None:
        """Validate acceptance criteria."""
        if not self.criteria:
            raise ValueError("AcceptanceCriteria cannot be empty")

        for criterion in self.criteria:
            if not criterion or not criterion.strip():
                raise ValueError("Individual criterion cannot be empty")

    @staticmethod
    def from_list(criteria_list: list[str]) -> "AcceptanceCriteria":
        """Create AcceptanceCriteria from list.

        Args:
            criteria_list: List of criteria strings

        Returns:
            AcceptanceCriteria value object
        """
        return AcceptanceCriteria(criteria=tuple(criteria_list))

    def to_list(self) -> list[str]:
        """Convert to list representation.

        Returns:
            List of criteria strings
        """
        return list(self.criteria)

    def count(self) -> int:
        """Get number of criteria.

        Returns:
            Count of criteria
        """
        return len(self.criteria)






