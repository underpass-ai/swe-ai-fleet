"""StoryTags value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryTags:
    """Value Object for story tags.

    Encapsulates validation and behavior for story categorization tags.
    """

    tags: tuple[str, ...]  # Tuple for immutability

    def __post_init__(self) -> None:
        """Validate tags."""
        for tag in self.tags:
            if not tag or not tag.strip():
                raise ValueError("Individual tag cannot be empty")

    @staticmethod
    def from_list(tags_list: list[str]) -> "StoryTags":
        """Create StoryTags from list.

        Args:
            tags_list: List of tag strings

        Returns:
            StoryTags value object
        """
        return StoryTags(tags=tuple(tags_list))

    @staticmethod
    def empty() -> "StoryTags":
        """Create empty tags.

        Returns:
            Empty StoryTags value object
        """
        return StoryTags(tags=())

    def to_list(self) -> list[str]:
        """Convert to list representation.

        Returns:
            List of tag strings
        """
        return list(self.tags)

    def count(self) -> int:
        """Get number of tags.

        Returns:
            Count of tags
        """
        return len(self.tags)

    def has_tag(self, tag: str) -> bool:
        """Check if tag exists.

        Args:
            tag: Tag to check

        Returns:
            True if tag exists
        """
        return tag in self.tags






