"""Milestone Value Object - Represents a significant event in project timeline."""

from dataclasses import dataclass

from core.context.domain.milestone_event_type import MilestoneEventType


@dataclass(frozen=True)
class Milestone:
    """Milestone event in project timeline.

    Represents a significant event (planning started, first decision, etc.)
    with its timestamp and optional metadata.

    Immutable by design (frozen=True).
    """

    event_type: MilestoneEventType
    timestamp_ms: int
    event_id: str
    metadata: str = ""

    def __post_init__(self) -> None:
        """Validate milestone data.

        Raises:
            ValueError: If validation fails
        """
        if self.timestamp_ms < 0:
            raise ValueError(f"timestamp_ms must be >= 0, got {self.timestamp_ms}")
        if not self.event_id:
            raise ValueError("event_id cannot be empty")

    def is_planning_milestone(self) -> bool:
        """Check if this is a planning-related milestone.

        Returns:
            True if milestone is planning-related
        """
        return self.event_type in {
            MilestoneEventType.PLANNING_STARTED,
            MilestoneEventType.FIRST_PLAN_VERSION,
        }

    def is_decision_milestone(self) -> bool:
        """Check if this is a decision-related milestone.

        Returns:
            True if milestone is decision-related
        """
        return self.event_type in {
            MilestoneEventType.FIRST_DECISION,
            MilestoneEventType.DECISION_APPROVED,
        }

    def get_display_text(self) -> str:
        """Get human-readable display text for this milestone.

        Returns:
            Display text describing the milestone
        """
        if self.metadata:
            return f"{self.event_type.value}: {self.metadata}"
        return self.event_type.value

