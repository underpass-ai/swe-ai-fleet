"""StoryList domain collection."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from planning.domain.entities.story import Story
from planning.domain.value_objects.story_state import StoryState


@dataclass(frozen=True)
class StoryList:
    """
    Domain Collection: Immutable collection of Story entities.

    Domain Collection Responsibilities:
    - Encapsulate list behavior with domain semantics
    - Provide domain-specific queries (filter by state, etc.)
    - Enforce immutability (frozen=True)
    - Type safety delegated to type checker (mypy/pyright)

    Note: This is a COLLECTION, not a Value Object.
    Collections can depend on Entities without violating DDD principles.

    Type Safety: Trust the type system. No runtime isinstance() checks.
    """

    stories: tuple[Story, ...]

    @classmethod
    def from_list(cls, stories: list[Story]) -> StoryList:
        """
        Create StoryList from a list.

        Args:
            stories: List of Story entities.

        Returns:
            StoryList instance.
        """
        return cls(stories=tuple(stories))

    @classmethod
    def empty(cls) -> StoryList:
        """
        Create empty StoryList.

        Returns:
            Empty StoryList instance.
        """
        return cls(stories=())

    def count(self) -> int:
        """
        Get number of stories.

        Returns:
            Count of stories.
        """
        return len(self.stories)

    def is_empty(self) -> bool:
        """
        Check if collection is empty.

        Returns:
            True if empty, False otherwise.
        """
        return len(self.stories) == 0

    def filter_by_state(self, state: StoryState) -> StoryList:
        """
        Filter stories by state (domain operation).

        Args:
            state: State to filter by.

        Returns:
            New StoryList with filtered stories.
        """
        filtered = [s for s in self.stories if s.state == state]
        return StoryList.from_list(filtered)

    def __iter__(self) -> Iterator[Story]:
        """Iterate over stories."""
        return iter(self.stories)

    def __len__(self) -> int:
        """Get length."""
        return len(self.stories)

    def __getitem__(self, index: int) -> Story:
        """Get story by index."""
        return self.stories[index]

    def __str__(self) -> str:
        """String representation for logging."""
        return f"StoryList(count={self.count()})"

