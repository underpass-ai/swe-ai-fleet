"""TaskNode value object for dependency analysis.

Value Object (DDD):
- Defined by its values, not identity
- Immutable (frozen=True)
- NO primitives - all typed with VOs
"""

from dataclasses import dataclass

from core.shared.domain.value_objects.content.task_description import TaskDescription
from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.task_id import TaskId
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority

from core.shared.domain.value_objects.task_derivation.keyword import Keyword


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

    Note: Role is NOT part of TaskNode - Planning Service assigns roles based on RBAC
    and event context (planning.plan.approved event), NOT from LLM output.
    """

    task_id: TaskId
    title: Title
    description: TaskDescription  # Task description (required for task creation)
    keywords: tuple[Keyword, ...]  # Immutable tuple of Keyword VOs
    estimated_hours: Duration  # Estimated effort in hours (from LLM or default)
    priority: Priority  # Priority decided by LLM (vLLM or superior LLM) - 1-10 (1 = highest)

    def __post_init__(self) -> None:
        """Validate task node (fail-fast).

        Note: Individual VOs already validate themselves.
        This validates collection-level invariants.

        Raises:
            ValueError: If validation fails
        """
        # Individual VOs validate themselves (TaskId, Title, etc.)
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

