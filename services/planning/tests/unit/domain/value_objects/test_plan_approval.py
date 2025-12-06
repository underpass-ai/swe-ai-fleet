"""Unit tests for PlanApproval value object."""

import pytest
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.plan_approval import PlanApproval


def test_plan_approval_creation_with_minimal_fields() -> None:
    """Test creating PlanApproval with only required fields."""
    # Arrange & Act
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="This plan aligns with business goals and has clear acceptance criteria.",
    )

    # Assert
    assert approval.approved_by.value == "john.doe"
    assert "business goals" in approval.po_notes
    assert approval.po_concerns is None
    assert approval.priority_adjustment is None
    assert approval.po_priority_reason is None


def test_plan_approval_creation_with_all_fields() -> None:
    """Test creating PlanApproval with all optional fields."""
    # Arrange & Act
    approval = PlanApproval(
        approved_by=UserName("jane.smith"),
        po_notes="Plan is solid and well-structured.",
        po_concerns="Watch out for API rate limits in third-party integration.",
        priority_adjustment="HIGH",
        po_priority_reason="Critical for Q4 release milestone.",
    )

    # Assert
    assert approval.approved_by.value == "jane.smith"
    assert approval.po_notes == "Plan is solid and well-structured."
    assert approval.po_concerns == "Watch out for API rate limits in third-party integration."
    assert approval.priority_adjustment == "HIGH"
    assert approval.po_priority_reason == "Critical for Q4 release milestone."


def test_plan_approval_is_immutable() -> None:
    """Test that PlanApproval is frozen (immutable)."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
    )

    # Act & Assert
    with pytest.raises(Exception):  # FrozenInstanceError
        approval.po_notes = "Changed"  # type: ignore


def test_plan_approval_rejects_empty_po_notes() -> None:
    """Test that PlanApproval rejects empty po_notes."""
    # Act & Assert
    with pytest.raises(ValueError, match="po_notes is required"):
        PlanApproval(
            approved_by=UserName("john.doe"),
            po_notes="",
        )


def test_plan_approval_rejects_whitespace_only_po_notes() -> None:
    """Test that PlanApproval rejects whitespace-only po_notes."""
    # Act & Assert
    with pytest.raises(ValueError, match="po_notes is required"):
        PlanApproval(
            approved_by=UserName("john.doe"),
            po_notes="   \n\t  ",
        )


def test_plan_approval_rejects_priority_adjustment_without_reason() -> None:
    """Test that priority adjustment requires po_priority_reason."""
    # Act & Assert
    with pytest.raises(ValueError, match="po_priority_reason is required when priority_adjustment"):
        PlanApproval(
            approved_by=UserName("john.doe"),
            po_notes="Approved",
            priority_adjustment="HIGH",
            po_priority_reason=None,
        )


def test_plan_approval_rejects_priority_adjustment_with_empty_reason() -> None:
    """Test that priority adjustment rejects empty po_priority_reason."""
    # Act & Assert
    with pytest.raises(ValueError, match="po_priority_reason is required when priority_adjustment"):
        PlanApproval(
            approved_by=UserName("john.doe"),
            po_notes="Approved",
            priority_adjustment="HIGH",
            po_priority_reason="",
        )


def test_plan_approval_rejects_invalid_priority_high_case() -> None:
    """Test that PlanApproval rejects invalid priority values."""
    # Act & Assert
    with pytest.raises(ValueError, match="Invalid priority_adjustment.*Must be one of"):
        PlanApproval(
            approved_by=UserName("john.doe"),
            po_notes="Approved",
            priority_adjustment="CRITICAL",
            po_priority_reason="Very important",
        )


def test_plan_approval_rejects_invalid_priority_lowercase() -> None:
    """Test that PlanApproval rejects lowercase invalid priorities."""
    # Act & Assert
    with pytest.raises(ValueError, match="Invalid priority_adjustment"):
        PlanApproval(
            approved_by=UserName("john.doe"),
            po_notes="Approved",
            priority_adjustment="urgent",
            po_priority_reason="Needed ASAP",
        )


def test_plan_approval_accepts_high_priority() -> None:
    """Test that PlanApproval accepts HIGH priority."""
    # Arrange & Act
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        priority_adjustment="HIGH",
        po_priority_reason="Critical for release",
    )

    # Assert
    assert approval.priority_adjustment == "HIGH"
    assert approval.has_priority_adjustment is True


def test_plan_approval_accepts_medium_priority() -> None:
    """Test that PlanApproval accepts MEDIUM priority."""
    # Arrange & Act
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        priority_adjustment="MEDIUM",
        po_priority_reason="Standard priority",
    )

    # Assert
    assert approval.priority_adjustment == "MEDIUM"


def test_plan_approval_accepts_low_priority() -> None:
    """Test that PlanApproval accepts LOW priority."""
    # Arrange & Act
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        priority_adjustment="LOW",
        po_priority_reason="Can wait",
    )

    # Assert
    assert approval.priority_adjustment == "LOW"


def test_plan_approval_accepts_lowercase_priority() -> None:
    """Test that PlanApproval accepts lowercase priority (normalized in validation)."""
    # Arrange & Act
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        priority_adjustment="high",
        po_priority_reason="Important",
    )

    # Assert
    assert approval.priority_adjustment == "high"  # Stores as-is
    assert approval.normalized_priority == "HIGH"  # But normalizes via property


def test_plan_approval_accepts_mixed_case_priority() -> None:
    """Test that PlanApproval accepts mixed case priority."""
    # Arrange & Act
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        priority_adjustment="MeDiUm",
        po_priority_reason="Standard",
    )

    # Assert
    assert approval.normalized_priority == "MEDIUM"


def test_has_priority_adjustment_returns_true_when_present() -> None:
    """Test has_priority_adjustment property when adjustment present."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        priority_adjustment="HIGH",
        po_priority_reason="Important",
    )

    # Act & Assert
    assert approval.has_priority_adjustment is True


def test_has_priority_adjustment_returns_false_when_absent() -> None:
    """Test has_priority_adjustment property when no adjustment."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
    )

    # Act & Assert
    assert approval.has_priority_adjustment is False


def test_has_concerns_returns_true_when_present() -> None:
    """Test has_concerns property when concerns present."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        po_concerns="Monitor API usage carefully.",
    )

    # Act & Assert
    assert approval.has_concerns is True


def test_has_concerns_returns_false_when_absent() -> None:
    """Test has_concerns property when no concerns."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
    )

    # Act & Assert
    assert approval.has_concerns is False


def test_has_concerns_returns_false_when_empty_string() -> None:
    """Test has_concerns property when concerns is empty string."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        po_concerns="",
    )

    # Act & Assert
    assert approval.has_concerns is False


def test_has_concerns_returns_false_when_whitespace_only() -> None:
    """Test has_concerns property when concerns is whitespace only."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        po_concerns="   \n\t  ",
    )

    # Act & Assert
    assert approval.has_concerns is False


def test_normalized_priority_returns_none_when_no_adjustment() -> None:
    """Test normalized_priority returns None when no adjustment."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
    )

    # Act & Assert
    assert approval.normalized_priority is None


def test_normalized_priority_returns_uppercase() -> None:
    """Test normalized_priority returns uppercase value."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        priority_adjustment="low",
        po_priority_reason="Can wait",
    )

    # Act & Assert
    assert approval.normalized_priority == "LOW"


def test_normalized_priority_strips_whitespace() -> None:
    """Test normalized_priority strips whitespace."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        priority_adjustment="  HIGH  ",
        po_priority_reason="Important",
    )

    # Act & Assert
    assert approval.normalized_priority == "HIGH"


def test_format_for_audit_log_minimal() -> None:
    """Test format_for_audit_log with minimal approval."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Plan looks good.",
    )

    # Act
    result = approval.format_for_audit_log()

    # Assert
    assert "Approved by: john.doe" in result
    assert "Notes: Plan looks good." in result
    assert "Concerns:" not in result
    assert "Priority adjusted" not in result


def test_format_for_audit_log_with_concerns() -> None:
    """Test format_for_audit_log with concerns."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("jane.smith"),
        po_notes="Approved with monitoring.",
        po_concerns="Watch database performance.",
    )

    # Act
    result = approval.format_for_audit_log()

    # Assert
    assert "Approved by: jane.smith" in result
    assert "Notes: Approved with monitoring." in result
    assert "Concerns: Watch database performance." in result


def test_format_for_audit_log_with_priority_adjustment() -> None:
    """Test format_for_audit_log with priority adjustment."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("admin"),
        po_notes="Approved",
        priority_adjustment="HIGH",
        po_priority_reason="Q4 deadline",
    )

    # Act
    result = approval.format_for_audit_log()

    # Assert
    assert "Priority adjusted to HIGH" in result
    assert "Q4 deadline" in result


def test_format_for_audit_log_complete() -> None:
    """Test format_for_audit_log with all fields."""
    # Arrange
    approval = PlanApproval(
        approved_by=UserName("product.owner"),
        po_notes="Excellent plan with clear structure.",
        po_concerns="Monitor third-party API limits.",
        priority_adjustment="MEDIUM",
        po_priority_reason="Standard business priority.",
    )

    # Act
    result = approval.format_for_audit_log()

    # Assert
    assert "Approved by: product.owner" in result
    assert "Notes: Excellent plan" in result
    assert "Concerns: Monitor third-party" in result
    assert "Priority adjusted to MEDIUM" in result
    assert "Standard business priority" in result
    assert "|" in result  # Check separator


def test_plan_approval_with_multiline_po_notes() -> None:
    """Test PlanApproval accepts multiline po_notes."""
    # Arrange & Act
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Line 1: Good structure\nLine 2: Clear acceptance criteria\nLine 3: Ready to proceed",
    )

    # Assert
    assert "Line 1" in approval.po_notes
    assert "Line 2" in approval.po_notes
    assert "Line 3" in approval.po_notes


def test_plan_approval_with_special_characters_in_notes() -> None:
    """Test PlanApproval accepts special characters in notes."""
    # Arrange & Act
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved! Plan has 100% clarity & good structure. Cost: $5k-$10k.",
    )

    # Assert
    assert "Approved!" in approval.po_notes
    assert "100%" in approval.po_notes
    assert "&" in approval.po_notes
    assert "$5k-$10k" in approval.po_notes


def test_plan_approval_priority_adjustment_with_whitespace() -> None:
    """Test PlanApproval handles whitespace in priority_adjustment."""
    # Arrange & Act
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        priority_adjustment="  MEDIUM  ",
        po_priority_reason="Standard",
    )

    # Assert
    assert approval.priority_adjustment == "  MEDIUM  "  # Preserves original
    assert approval.normalized_priority == "MEDIUM"  # Normalizes


def test_plan_approval_equality() -> None:
    """Test that two PlanApprovals with same values are equal."""
    # Arrange
    approval1 = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
    )
    approval2 = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
    )

    # Act & Assert
    assert approval1 == approval2


def test_plan_approval_inequality_different_notes() -> None:
    """Test that PlanApprovals with different notes are not equal."""
    # Arrange
    approval1 = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved A",
    )
    approval2 = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved B",
    )

    # Act & Assert
    assert approval1 != approval2


def test_plan_approval_hash_consistency() -> None:
    """Test that PlanApproval can be hashed (for use in sets/dicts)."""
    # Arrange
    approval1 = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
    )
    approval2 = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
    )

    # Act & Assert: Same values = same hash
    assert hash(approval1) == hash(approval2)

    # Can be used in set
    approval_set = {approval1, approval2}
    assert len(approval_set) == 1  # Only one unique approval


def test_plan_approval_semantic_traceability_message() -> None:
    """Test that error messages emphasize semantic traceability."""
    # Act & Assert
    try:
        PlanApproval(
            approved_by=UserName("john.doe"),
            po_notes="",
        )
        pytest.fail("Should have raised ValueError")
    except ValueError as e:
        # Check that error message mentions semantic traceability
        assert "semantic traceability" in str(e).lower()
        assert "accountability" in str(e).lower()


def test_plan_approval_priority_reason_semantic_traceability() -> None:
    """Test that priority reason error emphasizes semantic traceability."""
    # Act & Assert
    try:
        PlanApproval(
            approved_by=UserName("john.doe"),
            po_notes="Approved",
            priority_adjustment="HIGH",
            po_priority_reason=None,
        )
        pytest.fail("Should have raised ValueError")
    except ValueError as e:
        # Check that error message mentions semantic traceability
        assert "semantic traceability" in str(e).lower()


def test_plan_approval_with_long_po_notes() -> None:
    """Test PlanApproval with very long po_notes."""
    # Arrange
    long_notes = "A" * 10000  # 10k characters

    # Act
    approval = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes=long_notes,
    )

    # Assert
    assert len(approval.po_notes) == 10000


def test_plan_approval_normalized_priority_with_all_valid_values() -> None:
    """Test normalized_priority with all valid priority values."""
    # Test HIGH
    approval_high = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        priority_adjustment="high",
        po_priority_reason="Reason",
    )
    assert approval_high.normalized_priority == "HIGH"

    # Test MEDIUM
    approval_medium = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        priority_adjustment="medium",
        po_priority_reason="Reason",
    )
    assert approval_medium.normalized_priority == "MEDIUM"

    # Test LOW
    approval_low = PlanApproval(
        approved_by=UserName("john.doe"),
        po_notes="Approved",
        priority_adjustment="low",
        po_priority_reason="Reason",
    )
    assert approval_low.normalized_priority == "LOW"
