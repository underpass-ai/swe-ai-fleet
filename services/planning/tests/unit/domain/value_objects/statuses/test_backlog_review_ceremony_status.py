"""Unit tests for BacklogReviewCeremonyStatus value object."""

import pytest
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)


class TestBacklogReviewCeremonyStatusEnum:
    """Test suite for BacklogReviewCeremonyStatusEnum."""

    def test_all_states_defined(self) -> None:
        """Test that all expected states are defined."""
        assert BacklogReviewCeremonyStatusEnum.DRAFT == "DRAFT"
        assert BacklogReviewCeremonyStatusEnum.IN_PROGRESS == "IN_PROGRESS"
        assert BacklogReviewCeremonyStatusEnum.REVIEWING == "REVIEWING"
        assert BacklogReviewCeremonyStatusEnum.COMPLETED == "COMPLETED"
        assert BacklogReviewCeremonyStatusEnum.CANCELLED == "CANCELLED"

    def test_enum_count(self) -> None:
        """Test that enum has exactly 5 states."""
        assert len(BacklogReviewCeremonyStatusEnum) == 5


class TestBacklogReviewCeremonyStatus:
    """Test suite for BacklogReviewCeremonyStatus value object."""

    def test_create_draft_status(self) -> None:
        """Test creating DRAFT status."""
        status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)

        assert status.value == BacklogReviewCeremonyStatusEnum.DRAFT
        assert status.to_string() == "DRAFT"

    def test_create_in_progress_status(self) -> None:
        """Test creating IN_PROGRESS status."""
        status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS)

        assert status.value == BacklogReviewCeremonyStatusEnum.IN_PROGRESS
        assert status.to_string() == "IN_PROGRESS"

    def test_create_reviewing_status(self) -> None:
        """Test creating REVIEWING status."""
        status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING)

        assert status.value == BacklogReviewCeremonyStatusEnum.REVIEWING
        assert status.to_string() == "REVIEWING"

    def test_create_completed_status(self) -> None:
        """Test creating COMPLETED status."""
        status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED)

        assert status.value == BacklogReviewCeremonyStatusEnum.COMPLETED
        assert status.to_string() == "COMPLETED"

    def test_create_cancelled_status(self) -> None:
        """Test creating CANCELLED status."""
        status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.CANCELLED)

        assert status.value == BacklogReviewCeremonyStatusEnum.CANCELLED
        assert status.to_string() == "CANCELLED"

    def test_invalid_status_raises_value_error(self) -> None:
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            BacklogReviewCeremonyStatus("INVALID_STATUS")  # type: ignore

    def test_is_draft(self) -> None:
        """Test is_draft() method."""
        draft_status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)
        other_status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS)

        assert draft_status.is_draft() is True
        assert other_status.is_draft() is False

    def test_is_in_progress(self) -> None:
        """Test is_in_progress() method."""
        in_progress_status = BacklogReviewCeremonyStatus(
            BacklogReviewCeremonyStatusEnum.IN_PROGRESS
        )
        other_status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)

        assert in_progress_status.is_in_progress() is True
        assert other_status.is_in_progress() is False

    def test_is_reviewing(self) -> None:
        """Test is_reviewing() method."""
        reviewing_status = BacklogReviewCeremonyStatus(
            BacklogReviewCeremonyStatusEnum.REVIEWING
        )
        other_status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)

        assert reviewing_status.is_reviewing() is True
        assert other_status.is_reviewing() is False

    def test_is_completed(self) -> None:
        """Test is_completed() method."""
        completed_status = BacklogReviewCeremonyStatus(
            BacklogReviewCeremonyStatusEnum.COMPLETED
        )
        other_status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)

        assert completed_status.is_completed() is True
        assert other_status.is_completed() is False

    def test_is_cancelled(self) -> None:
        """Test is_cancelled() method."""
        cancelled_status = BacklogReviewCeremonyStatus(
            BacklogReviewCeremonyStatusEnum.CANCELLED
        )
        other_status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)

        assert cancelled_status.is_cancelled() is True
        assert other_status.is_cancelled() is False

    def test_str_representation(self) -> None:
        """Test __str__ returns the status value."""
        status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)

        assert str(status) == "DRAFT"

    def test_equality(self) -> None:
        """Test equality between two statuses with same value."""
        status1 = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)
        status2 = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)

        assert status1 == status2

    def test_inequality(self) -> None:
        """Test inequality between two statuses with different values."""
        status1 = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)
        status2 = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED)

        assert status1 != status2

    def test_immutability(self) -> None:
        """Test that status is immutable (frozen dataclass)."""
        status = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)

        with pytest.raises(AttributeError):
            status.value = BacklogReviewCeremonyStatusEnum.COMPLETED  # type: ignore

    def test_hash_consistency(self) -> None:
        """Test that statuses with same value have same hash."""
        status1 = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)
        status2 = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)

        assert hash(status1) == hash(status2)

    def test_can_be_used_in_set(self) -> None:
        """Test that statuses can be used in sets."""
        status1 = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)
        status2 = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED)
        status3 = BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT)

        status_set = {status1, status2, status3}

        assert len(status_set) == 2  # status1 and status3 are same

