"""Backlog Review Ceremony Status value object."""

from dataclasses import dataclass
from enum import Enum


class BacklogReviewCeremonyStatusEnum(str, Enum):
    """
    FSM States for a Backlog Review Ceremony lifecycle.

    State Machine:
    DRAFT → IN_PROGRESS → REVIEWING → COMPLETED
    Any state → CANCELLED

    Key States:
    - DRAFT: Ceremony created but not started
    - IN_PROGRESS: Ceremony started, orchestrating reviews
    - REVIEWING: Reviews completed, awaiting PO approval
    - COMPLETED: All plans approved/rejected, ceremony finished
    - CANCELLED: Ceremony cancelled by PO
    """

    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEWING = "REVIEWING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class BacklogReviewCeremonyStatus:
    """
    Value Object: Current status of a Backlog Review Ceremony.

    Domain Invariants:
    - Status must be one of the valid BacklogReviewCeremonyStatusEnum values

    Immutability: frozen=True ensures no mutation after creation.
    """

    value: BacklogReviewCeremonyStatusEnum

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If status is not a valid BacklogReviewCeremonyStatusEnum.
        """
        if not isinstance(self.value, BacklogReviewCeremonyStatusEnum):
            raise ValueError(
                f"Invalid status: {self.value}. Must be BacklogReviewCeremonyStatusEnum."
            )

    def to_string(self) -> str:
        """
        Convert status to string representation.

        Tell, Don't Ask: Instead of accessing .value.value externally.

        Returns:
            String representation of the status.
        """
        return self.value.value

    def is_draft(self) -> bool:
        """Check if status is DRAFT."""
        return self.value == BacklogReviewCeremonyStatusEnum.DRAFT

    def is_in_progress(self) -> bool:
        """Check if status is IN_PROGRESS."""
        return self.value == BacklogReviewCeremonyStatusEnum.IN_PROGRESS

    def is_reviewing(self) -> bool:
        """Check if status is REVIEWING."""
        return self.value == BacklogReviewCeremonyStatusEnum.REVIEWING

    def is_completed(self) -> bool:
        """Check if status is COMPLETED."""
        return self.value == BacklogReviewCeremonyStatusEnum.COMPLETED

    def is_cancelled(self) -> bool:
        """Check if status is CANCELLED."""
        return self.value == BacklogReviewCeremonyStatusEnum.CANCELLED

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value.value


