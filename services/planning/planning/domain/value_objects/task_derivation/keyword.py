"""Keyword value object for task dependency analysis."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Keyword:
    """Value Object for technical keyword.

    Used in dependency analysis to infer task relationships.
    Domain Invariant: Keyword cannot be empty.
    Following DDD: No primitives - everything is a value object.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate Keyword (fail-fast).

        Raises:
            ValueError: If keyword is empty or whitespace
        """
        if not self.value or not self.value.strip():
            raise ValueError("Keyword cannot be empty")

    def __str__(self) -> str:
        """String representation.

        Returns:
            String value
        """
        return self.value

    def matches_in(self, text: str) -> bool:
        """Check if keyword matches in text (case-insensitive).

        Tell, Don't Ask: Keyword knows how to match itself.

        Args:
            text: Text to search in

        Returns:
            True if keyword found in text
        """
        if not text:
            return False
        return self.value.lower() in text.lower()

