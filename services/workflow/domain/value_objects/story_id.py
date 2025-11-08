"""Story identifier value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryId:
    """Story identifier value object.

    Represents a unique story identifier.
    Tasks belong to stories.
    Immutable following DDD principles.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Type validation is handled by type hints.
        """
        if not self.value or not self.value.strip():
            raise ValueError("StoryId cannot be empty")

    def __str__(self) -> str:
        """String representation."""
        return self.value

