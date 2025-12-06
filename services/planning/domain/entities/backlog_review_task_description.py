"""BacklogReviewTaskDescription domain entity.

Represents a task description for backlog review deliberations.
Encapsulates the construction of task descriptions with or without context.
"""

from dataclasses import dataclass

from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)


@dataclass(frozen=True)
class BacklogReviewTaskDescription:
    """
    Task description for backlog review deliberation.

    This entity encapsulates the task description that will be sent to
    the Orchestrator for deliberation. It includes metadata (task_id)
    and the actual description text.

    Domain Invariants:
    - task_id must follow format: "ceremony-{id}:story-{id}:role-{role}"
    - description must not be empty
    - ceremony_id, story_id, and role must be valid

    Immutability: frozen=True ensures no mutation after creation.
    """

    task_id: str  # Format: "ceremony-{id}:story-{id}:role-{role}"
    description: str

    def __post_init__(self) -> None:
        """Validate task description (fail-fast).

        Raises:
            ValueError: If any parameter is invalid
        """
        if not self.task_id or not self.task_id.strip():
            raise ValueError("task_id cannot be empty")

        if not self.description or not self.description.strip():
            raise ValueError("description cannot be empty")

        # Validate task_id format
        if not self.task_id.startswith("ceremony-"):
            raise ValueError(
                f"task_id must start with 'ceremony-', got {self.task_id}"
            )

    @classmethod
    def build_with_context(
        cls,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        role: BacklogReviewRole,
        context_text: str,
    ) -> "BacklogReviewTaskDescription":
        """
        Build task description with context (builder method).

        Creates a task description that includes context from Context Service.
        This provides richer information for the deliberation.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier
            role: Review role (BacklogReviewRole enum)
            context_text: Context string from Context Service

        Returns:
            BacklogReviewTaskDescription with context included

        Raises:
            ValueError: If any parameter is invalid
        """
        if not context_text or not context_text.strip():
            raise ValueError("context_text cannot be empty for build_with_context")

        if not isinstance(role, BacklogReviewRole):
            raise ValueError(f"role must be a BacklogReviewRole enum, got {type(role)}")

        # Build task_id with metadata for NATS callback
        # Format: "ceremony-{id}:story-{id}:role-{role}"
        role_str = role.value
        task_id = (
            f"ceremony-{ceremony_id.value}:story-{story_id.value}:role-{role_str}"
        )

        # Build description with context
        description = (
            f"[{task_id}] Review story {story_id.value} from {role_str} perspective.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Please provide a comprehensive review from the {role_str} perspective, "
            f"considering the context provided above."
        )

        return cls(task_id=task_id, description=description)

    @classmethod
    def build_without_context(
        cls,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        role: BacklogReviewRole,
    ) -> "BacklogReviewTaskDescription":
        """
        Build task description without context (builder method).

        Creates a basic task description when context is unavailable.
        This is a fallback when Context Service is unavailable.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier
            role: Review role (BacklogReviewRole enum)

        Returns:
            BacklogReviewTaskDescription without context

        Raises:
            ValueError: If any parameter is invalid
        """
        if not isinstance(role, BacklogReviewRole):
            raise ValueError(f"role must be a BacklogReviewRole enum, got {type(role)}")

        # Build task_id with metadata for NATS callback
        # Format: "ceremony-{id}:story-{id}:role-{role}"
        role_str = role.value
        task_id = (
            f"ceremony-{ceremony_id.value}:story-{story_id.value}:role-{role_str}"
        )

        # Build basic description without context
        description = (
            f"[{task_id}] Review story {story_id.value} from {role_str} perspective"
        )

        return cls(task_id=task_id, description=description)

    def to_string(self) -> str:
        """Get description as string.

        Returns:
            Task description string
        """
        return self.description
