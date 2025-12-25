"""Unit tests for StoryPoApproval value object."""

import pytest
from datetime import datetime, UTC

from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.po_concerns import PoConcerns
from planning.domain.value_objects.review.po_notes import PoNotes
from planning.domain.value_objects.review.story_po_approval import StoryPoApproval
from planning.domain.value_objects.statuses.priority_adjustment import (
    PriorityAdjustment,
    PriorityAdjustmentEnum,
)


def test_story_po_approval_creation_minimal() -> None:
    """Test creating StoryPoApproval with only required fields."""
    # Arrange
    ceremony_id = BacklogReviewCeremonyId("BRC-123")
    story_id = StoryId("STORY-456")
    approved_by = UserName("john.doe")
    approved_at = datetime.now(UTC)
    po_notes = PoNotes("This plan aligns with business goals.")

    # Act
    approval = StoryPoApproval(
        ceremony_id=ceremony_id,
        story_id=story_id,
        approved_by=approved_by,
        approved_at=approved_at,
        po_notes=po_notes,
    )

    # Assert
    assert approval.ceremony_id == ceremony_id
    assert approval.story_id == story_id
    assert approval.approved_by == approved_by
    assert approval.approved_at == approved_at
    assert approval.po_notes == po_notes
    assert approval.po_concerns is None
    assert approval.priority_adjustment is None


def test_story_po_approval_creation_with_all_fields() -> None:
    """Test creating StoryPoApproval with all optional fields."""
    # Arrange
    ceremony_id = BacklogReviewCeremonyId("BRC-123")
    story_id = StoryId("STORY-456")
    approved_by = UserName("jane.smith")
    approved_at = datetime.now(UTC)
    po_notes = PoNotes("Plan is solid and well-structured.")
    po_concerns = PoConcerns("Watch out for API rate limits.")
    priority_adjustment = PriorityAdjustment(value=PriorityAdjustmentEnum.HIGH)

    # Act
    approval = StoryPoApproval(
        ceremony_id=ceremony_id,
        story_id=story_id,
        approved_by=approved_by,
        approved_at=approved_at,
        po_notes=po_notes,
        po_concerns=po_concerns,
        priority_adjustment=priority_adjustment,
    )

    # Assert
    assert approval.ceremony_id == ceremony_id
    assert approval.story_id == story_id
    assert approval.approved_by == approved_by
    assert approval.approved_at == approved_at
    assert approval.po_notes == po_notes
    assert approval.po_concerns == po_concerns
    assert approval.priority_adjustment == priority_adjustment


def test_story_po_approval_is_immutable() -> None:
    """Test that StoryPoApproval is frozen (immutable)."""
    # Arrange
    approval = StoryPoApproval(
        ceremony_id=BacklogReviewCeremonyId("BRC-123"),
        story_id=StoryId("STORY-456"),
        approved_by=UserName("john.doe"),
        approved_at=datetime.now(UTC),
        po_notes=PoNotes("Approved"),
    )

    # Act & Assert
    with pytest.raises(Exception):  # FrozenInstanceError
        approval.po_notes = PoNotes("Changed")  # type: ignore


def test_story_po_approval_has_priority_adjustment_true() -> None:
    """Test has_priority_adjustment returns True when adjustment present."""
    # Arrange
    approval = StoryPoApproval(
        ceremony_id=BacklogReviewCeremonyId("BRC-123"),
        story_id=StoryId("STORY-456"),
        approved_by=UserName("john.doe"),
        approved_at=datetime.now(UTC),
        po_notes=PoNotes("Approved"),
        priority_adjustment=PriorityAdjustment(value=PriorityAdjustmentEnum.HIGH),
    )

    # Act & Assert
    assert approval.has_priority_adjustment is True


def test_story_po_approval_has_priority_adjustment_false() -> None:
    """Test has_priority_adjustment returns False when no adjustment."""
    # Arrange
    approval = StoryPoApproval(
        ceremony_id=BacklogReviewCeremonyId("BRC-123"),
        story_id=StoryId("STORY-456"),
        approved_by=UserName("john.doe"),
        approved_at=datetime.now(UTC),
        po_notes=PoNotes("Approved"),
    )

    # Act & Assert
    assert approval.has_priority_adjustment is False


def test_story_po_approval_has_concerns_true() -> None:
    """Test has_concerns returns True when concerns present."""
    # Arrange
    approval = StoryPoApproval(
        ceremony_id=BacklogReviewCeremonyId("BRC-123"),
        story_id=StoryId("STORY-456"),
        approved_by=UserName("john.doe"),
        approved_at=datetime.now(UTC),
        po_notes=PoNotes("Approved"),
        po_concerns=PoConcerns("Monitor API usage"),
    )

    # Act & Assert
    assert approval.has_concerns is True


def test_story_po_approval_has_concerns_false() -> None:
    """Test has_concerns returns False when no concerns."""
    # Arrange
    approval = StoryPoApproval(
        ceremony_id=BacklogReviewCeremonyId("BRC-123"),
        story_id=StoryId("STORY-456"),
        approved_by=UserName("john.doe"),
        approved_at=datetime.now(UTC),
        po_notes=PoNotes("Approved"),
    )

    # Act & Assert
    assert approval.has_concerns is False


def test_story_po_approval_equality() -> None:
    """Test that two StoryPoApprovals with same values are equal."""
    # Arrange
    ceremony_id = BacklogReviewCeremonyId("BRC-123")
    story_id = StoryId("STORY-456")
    approved_by = UserName("john.doe")
    approved_at = datetime.now(UTC)
    po_notes = PoNotes("Approved")

    approval1 = StoryPoApproval(
        ceremony_id=ceremony_id,
        story_id=story_id,
        approved_by=approved_by,
        approved_at=approved_at,
        po_notes=po_notes,
    )

    approval2 = StoryPoApproval(
        ceremony_id=ceremony_id,
        story_id=story_id,
        approved_by=approved_by,
        approved_at=approved_at,
        po_notes=po_notes,
    )

    # Act & Assert
    assert approval1 == approval2


def test_story_po_approval_inequality_different_notes() -> None:
    """Test that StoryPoApprovals with different notes are not equal."""
    # Arrange
    ceremony_id = BacklogReviewCeremonyId("BRC-123")
    story_id = StoryId("STORY-456")
    approved_by = UserName("john.doe")
    approved_at = datetime.now(UTC)

    approval1 = StoryPoApproval(
        ceremony_id=ceremony_id,
        story_id=story_id,
        approved_by=approved_by,
        approved_at=approved_at,
        po_notes=PoNotes("Approved A"),
    )

    approval2 = StoryPoApproval(
        ceremony_id=ceremony_id,
        story_id=story_id,
        approved_by=approved_by,
        approved_at=approved_at,
        po_notes=PoNotes("Approved B"),
    )

    # Act & Assert
    assert approval1 != approval2


def test_story_po_approval_inequality_different_ceremony() -> None:
    """Test that StoryPoApprovals with different ceremony_id are not equal."""
    # Arrange
    story_id = StoryId("STORY-456")
    approved_by = UserName("john.doe")
    approved_at = datetime.now(UTC)
    po_notes = PoNotes("Approved")

    approval1 = StoryPoApproval(
        ceremony_id=BacklogReviewCeremonyId("BRC-123"),
        story_id=story_id,
        approved_by=approved_by,
        approved_at=approved_at,
        po_notes=po_notes,
    )

    approval2 = StoryPoApproval(
        ceremony_id=BacklogReviewCeremonyId("BRC-789"),
        story_id=story_id,
        approved_by=approved_by,
        approved_at=approved_at,
        po_notes=po_notes,
    )

    # Act & Assert
    assert approval1 != approval2


def test_story_po_approval_hash_consistency() -> None:
    """Test that StoryPoApproval can be hashed (for use in sets/dicts)."""
    # Arrange
    ceremony_id = BacklogReviewCeremonyId("BRC-123")
    story_id = StoryId("STORY-456")
    approved_by = UserName("john.doe")
    approved_at = datetime.now(UTC)
    po_notes = PoNotes("Approved")

    approval1 = StoryPoApproval(
        ceremony_id=ceremony_id,
        story_id=story_id,
        approved_by=approved_by,
        approved_at=approved_at,
        po_notes=po_notes,
    )

    approval2 = StoryPoApproval(
        ceremony_id=ceremony_id,
        story_id=story_id,
        approved_by=approved_by,
        approved_at=approved_at,
        po_notes=po_notes,
    )

    # Act & Assert: Same values = same hash
    assert hash(approval1) == hash(approval2)

    # Can be used in set
    approval_set = {approval1, approval2}
    assert len(approval_set) == 1  # Only one unique approval


def test_story_po_approval_with_all_priority_levels() -> None:
    """Test StoryPoApproval with all priority adjustment levels."""
    # Arrange
    base_approval = {
        "ceremony_id": BacklogReviewCeremonyId("BRC-123"),
        "story_id": StoryId("STORY-456"),
        "approved_by": UserName("john.doe"),
        "approved_at": datetime.now(UTC),
        "po_notes": PoNotes("Approved"),
    }

    # Test HIGH
    approval_high = StoryPoApproval(
        **base_approval,
        priority_adjustment=PriorityAdjustment(value=PriorityAdjustmentEnum.HIGH),
    )
    assert approval_high.priority_adjustment.value == PriorityAdjustmentEnum.HIGH

    # Test MEDIUM
    approval_medium = StoryPoApproval(
        **base_approval,
        priority_adjustment=PriorityAdjustment(value=PriorityAdjustmentEnum.MEDIUM),
    )
    assert approval_medium.priority_adjustment.value == PriorityAdjustmentEnum.MEDIUM

    # Test LOW
    approval_low = StoryPoApproval(
        **base_approval,
        priority_adjustment=PriorityAdjustment(value=PriorityAdjustmentEnum.LOW),
    )
    assert approval_low.priority_adjustment.value == PriorityAdjustmentEnum.LOW


def test_story_po_approval_validation_delegated_to_value_objects() -> None:
    """Test that validation is delegated to value objects."""
    # Act & Assert - PoNotes validation
    with pytest.raises(ValueError, match="PoNotes cannot be empty"):
        StoryPoApproval(
            ceremony_id=BacklogReviewCeremonyId("BRC-123"),
            story_id=StoryId("STORY-456"),
            approved_by=UserName("john.doe"),
            approved_at=datetime.now(UTC),
            po_notes=PoNotes(""),  # This will fail in PoNotes.__post_init__
        )


def test_story_po_approval_with_concerns_validation() -> None:
    """Test that PoConcerns validation is enforced if provided."""
    # Act & Assert - PoConcerns validation
    with pytest.raises(ValueError, match="PoConcerns cannot be empty"):
        StoryPoApproval(
            ceremony_id=BacklogReviewCeremonyId("BRC-123"),
            story_id=StoryId("STORY-456"),
            approved_by=UserName("john.doe"),
            approved_at=datetime.now(UTC),
            po_notes=PoNotes("Approved"),
            po_concerns=PoConcerns(""),  # This will fail in PoConcerns.__post_init__
        )


def test_story_po_approval_with_priority_adjustment_validation() -> None:
    """Test that PriorityAdjustment validation is enforced if provided."""
    # Act & Assert - PriorityAdjustment validation
    with pytest.raises(ValueError, match="Invalid priority adjustment"):
        StoryPoApproval(
            ceremony_id=BacklogReviewCeremonyId("BRC-123"),
            story_id=StoryId("STORY-456"),
            approved_by=UserName("john.doe"),
            approved_at=datetime.now(UTC),
            po_notes=PoNotes("Approved"),
            priority_adjustment=PriorityAdjustment.from_string("INVALID"),  # This will fail
        )

