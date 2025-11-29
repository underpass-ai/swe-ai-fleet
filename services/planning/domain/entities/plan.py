"""Plan entity for Planning Service."""

from dataclasses import dataclass

from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId


@dataclass(frozen=True)
class Plan:
    """Plan entity - Implementation plan for one or more Stories.

    A Plan represents the technical approach for implementing Stories.
    It contains acceptance criteria, technical notes, and can be decomposed
    into atomic Tasks.

    Hierarchy: Project → Epic → Story → Task (Plan is separate aggregate)

    DOMAIN INVARIANT: Plan MUST cover at least one Story.
    NO orphan plans allowed.

    Following DDD:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - No serialization methods (use mappers)
    - Tell, Don't Ask: Plan provides its content for decomposition
    """

    plan_id: PlanId
    story_ids: tuple[StoryId, ...]  # REQUIRED - covered stories (domain invariant)
    title: Title
    description: Brief  # Detailed plan description
    acceptance_criteria: tuple[str, ...]  # Immutable tuple of criteria
    technical_notes: str = ""  # Optional technical details
    roles: tuple[str, ...] = ()  # Roles needed for execution

    def __post_init__(self) -> None:
        """Validate plan entity (fail-fast).

        Domain Invariants:
        - plan_id is already validated by PlanId value object
        - story_ids cannot be empty (must cover at least one story)
        - title is already validated by Title value object
        - description is already validated by Brief value object
        - acceptance_criteria cannot be empty

        Raises:
            ValueError: If validation fails
        """
        if not self.story_ids:
            raise ValueError("Plan must cover at least one Story (story_ids cannot be empty)")

        if not self.acceptance_criteria:
            raise ValueError("Plan must have at least one acceptance criterion")

    def get_description_for_decomposition(self) -> str:
        """Get plan description for LLM task decomposition.

        Tell, Don't Ask: Plan knows how to provide its content.

        Returns:
            Formatted description for LLM
        """
        return str(self.description)

    def get_acceptance_criteria_text(self) -> str:
        """Get formatted acceptance criteria.

        Tell, Don't Ask: Plan knows how to format its criteria.

        Returns:
            Formatted acceptance criteria (newline-separated)
        """
        return "\n".join(f"- {criterion}" for criterion in self.acceptance_criteria)

    def get_technical_notes_text(self) -> str:
        """Get technical notes or default message.

        Tell, Don't Ask: Plan provides its technical notes.

        Returns:
            Technical notes or "Not specified"
        """
        return self.technical_notes if self.technical_notes else "Not specified"
