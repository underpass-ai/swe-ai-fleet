"""ContextSection Value Object - Single section of agent context."""

from dataclasses import dataclass

from core.context.domain.context_section_type import ContextSectionType


@dataclass(frozen=True)
class ContextSection:
    """Represents a single section of context information.

    This Value Object encapsulates a piece of context information
    that will be presented to agents, following DDD principles.

    DDD-compliant: Uses ContextSectionType enum instead of string.
    Immutable by design (frozen=True).
    """

    content: str
    section_type: ContextSectionType
    priority: int = 0  # Higher priority sections appear first

    def __post_init__(self) -> None:
        """Validate context section.

        Raises:
            ValueError: If validation fails
        """
        if not self.content:
            raise ValueError("Context section content cannot be empty")
        if self.priority < 0:
            raise ValueError(f"Priority must be >= 0, got {self.priority}")

    def __str__(self) -> str:
        """Return the content of this section."""
        return self.content

    def is_high_priority(self) -> bool:
        """Check if this is a high-priority section.

        Returns:
            True if priority >= 70
        """
        return self.priority >= 70

    def is_identity_section(self) -> bool:
        """Check if this section identifies the story/epic.

        Returns:
            True if this is an identity section
        """
        return self.section_type.is_identity_section()

