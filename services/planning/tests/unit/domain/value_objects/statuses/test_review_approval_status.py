"""Unit tests for ReviewApprovalStatus value object."""

import pytest
from planning.domain.value_objects.statuses.review_approval_status import (
    ReviewApprovalStatus,
    ReviewApprovalStatusEnum,
)


class TestReviewApprovalStatusEnum:
    """Test suite for ReviewApprovalStatusEnum."""

    def test_all_states_defined(self) -> None:
        """Test that all expected states are defined."""
        assert ReviewApprovalStatusEnum.PENDING == "PENDING"
        assert ReviewApprovalStatusEnum.APPROVED == "APPROVED"
        assert ReviewApprovalStatusEnum.REJECTED == "REJECTED"

    def test_enum_count(self) -> None:
        """Test that enum has exactly 3 states."""
        assert len(ReviewApprovalStatusEnum) == 3


class TestReviewApprovalStatus:
    """Test suite for ReviewApprovalStatus value object."""

    def test_create_pending_status(self) -> None:
        """Test creating PENDING status."""
        status = ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING)

        assert status.value == ReviewApprovalStatusEnum.PENDING
        assert status.to_string() == "PENDING"

    def test_create_approved_status(self) -> None:
        """Test creating APPROVED status."""
        status = ReviewApprovalStatus(ReviewApprovalStatusEnum.APPROVED)

        assert status.value == ReviewApprovalStatusEnum.APPROVED
        assert status.to_string() == "APPROVED"

    def test_create_rejected_status(self) -> None:
        """Test creating REJECTED status."""
        status = ReviewApprovalStatus(ReviewApprovalStatusEnum.REJECTED)

        assert status.value == ReviewApprovalStatusEnum.REJECTED
        assert status.to_string() == "REJECTED"

    def test_invalid_status_raises_value_error(self) -> None:
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            ReviewApprovalStatus("INVALID")  # type: ignore

    def test_is_pending(self) -> None:
        """Test is_pending() method."""
        pending_status = ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING)
        other_status = ReviewApprovalStatus(ReviewApprovalStatusEnum.APPROVED)

        assert pending_status.is_pending() is True
        assert other_status.is_pending() is False

    def test_is_approved(self) -> None:
        """Test is_approved() method."""
        approved_status = ReviewApprovalStatus(ReviewApprovalStatusEnum.APPROVED)
        other_status = ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING)

        assert approved_status.is_approved() is True
        assert other_status.is_approved() is False

    def test_is_rejected(self) -> None:
        """Test is_rejected() method."""
        rejected_status = ReviewApprovalStatus(ReviewApprovalStatusEnum.REJECTED)
        other_status = ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING)

        assert rejected_status.is_rejected() is True
        assert other_status.is_rejected() is False

    def test_str_representation(self) -> None:
        """Test __str__ returns the status value."""
        status = ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING)

        assert str(status) == "PENDING"

    def test_equality(self) -> None:
        """Test equality between two statuses with same value."""
        status1 = ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING)
        status2 = ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING)

        assert status1 == status2

    def test_inequality(self) -> None:
        """Test inequality between two statuses with different values."""
        status1 = ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING)
        status2 = ReviewApprovalStatus(ReviewApprovalStatusEnum.APPROVED)

        assert status1 != status2

    def test_immutability(self) -> None:
        """Test that status is immutable (frozen dataclass)."""
        status = ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING)

        with pytest.raises(AttributeError):
            status.value = ReviewApprovalStatusEnum.APPROVED  # type: ignore

    def test_hash_consistency(self) -> None:
        """Test that statuses with same value have same hash."""
        status1 = ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING)
        status2 = ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING)

        assert hash(status1) == hash(status2)

