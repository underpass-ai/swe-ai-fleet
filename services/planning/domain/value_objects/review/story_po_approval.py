"""StoryPoApproval - Value Object for PO approval of a story in a ceremony.

Domain Layer (Value Object):
- Encapsulates PO's approval decision for a story within a ceremony
- WHY the PO approved (required for traceability)
- Concerns and priority adjustments (optional)
- Immutable record of approval decision with ceremony context
"""

from dataclasses import dataclass
from datetime import datetime

from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.po_concerns import PoConcerns
from planning.domain.value_objects.review.po_notes import PoNotes
from planning.domain.value_objects.statuses.priority_adjustment import (
    PriorityAdjustment,
)


@dataclass(frozen=True)
class StoryPoApproval:
    """
    Value object representing a PO's approval of a story plan in a ceremony.

    This captures the semantic context of the approval decision:
    - WHICH ceremony (ceremony_id)
    - WHICH story (story_id)
    - WHO approved (approved_by)
    - WHEN approved (approved_at)
    - WHY they approved (po_notes) - REQUIRED for traceability
    - Any concerns to monitor (po_concerns) - optional
    - Priority adjustments (optional)

    Following DDD:
    - Immutable value object (@dataclass(frozen=True))
    - Rich validation in __post_init__
    - Business rules enforced at construction
    - Self-documenting domain concept

    Semantic Traceability:
    - PO notes explain WHY plan was approved (decision rationale)
    - This enables future agents/humans to understand the approval context
    - Supports accountability and auditability
    - Links approval to specific ceremony and story for full context
    """

    ceremony_id: BacklogReviewCeremonyId
    story_id: StoryId
    approved_by: UserName
    approved_at: datetime
    po_notes: PoNotes
    po_concerns: PoConcerns | None = None
    priority_adjustment: PriorityAdjustment | None = None

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Validation rules:
        1. po_notes is validated by PoNotes value object (required, non-empty)
        2. po_concerns is validated by PoConcerns value object if provided
        3. priority_adjustment is validated by PriorityAdjustment value object if provided
        4. approved_at must be a valid datetime (not None) - validated by type system

        Raises:
            ValueError: If validation fails (from value objects)
        """
        # All validation is delegated to value objects:
        # - PoNotes validates that notes are non-empty
        # - PoConcerns validates that concerns are non-empty if provided
        # - PriorityAdjustment validates enum value if provided
        # No additional validation needed here

    @property
    def has_priority_adjustment(self) -> bool:
        """Check if PO adjusted priority from plan preliminary.

        Returns:
            True if priority was adjusted, False otherwise
        """
        return self.priority_adjustment is not None

    @property
    def has_concerns(self) -> bool:
        """Check if PO has concerns to monitor.

        Returns:
            True if po_concerns is provided, False otherwise
        """
        return self.po_concerns is not None

