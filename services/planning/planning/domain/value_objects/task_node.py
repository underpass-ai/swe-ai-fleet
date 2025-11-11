"""TaskNode value object for dependency analysis.

Value Object (DDD):
- Defined by its values, not identity
- Immutable (frozen=True)
- NO primitives - all typed with VOs
"""

from dataclasses import dataclass

from .keyword import Keyword
from .role import Role
from .task_id import TaskId
from .title import Title


@dataclass(frozen=True)
class TaskNode:
    """Task node for dependency analysis.

    Immutable representation of a task in dependency graph.
    NO serialization methods (use mappers in infrastructure).

    Following DDD:
    - Value object (no identity)
    - Immutable
    - NO primitives - all fields are Value Objects
    - Fail-fast validation in __post_init__
    """

    task_id: TaskId
    title: Title
    role: Role
    keywords: tuple[Keyword, ...]  # Immutable tuple of Keyword VOs

    def __post_init__(self) -> None:
        """Validate task node (fail-fast).

        Note: Individual VOs already validate themselves.
        This validates collection-level invariants.

        Raises:
            ValueError: If validation fails
        """
        # Individual VOs validate themselves (TaskId, Title, Role)
        # We just validate tuple is properly typed
        if not isinstance(self.keywords, tuple):
            raise ValueError("keywords must be a tuple")

    def has_keyword_matching(self, text: str) -> bool:
        """Check if any keyword matches in text.

        Tell, Don't Ask: TaskNode knows how to match its keywords.

        Args:
            text: Text to search in

        Returns:
            True if any keyword matches
        """
        return any(keyword.matches_in(text) for keyword in self.keywords)

