"""Unit tests for StepStatus enum."""

import pytest

from core.ceremony_engine.domain.value_objects.step_status import StepStatus


class TestStepStatus:
    """Test cases for StepStatus enum."""

    def test_status_values(self) -> None:
        """Test that all status values are defined."""
        assert StepStatus.PENDING == "PENDING"
        assert StepStatus.IN_PROGRESS == "IN_PROGRESS"
        assert StepStatus.COMPLETED == "COMPLETED"
        assert StepStatus.FAILED == "FAILED"
        assert StepStatus.WAITING_FOR_HUMAN == "WAITING_FOR_HUMAN"
        assert StepStatus.CANCELLED == "CANCELLED"

    def test_is_terminal(self) -> None:
        """Test is_terminal method."""
        assert StepStatus.COMPLETED.is_terminal() is True
        assert StepStatus.FAILED.is_terminal() is True
        assert StepStatus.CANCELLED.is_terminal() is True
        assert StepStatus.PENDING.is_terminal() is False
        assert StepStatus.IN_PROGRESS.is_terminal() is False
        assert StepStatus.WAITING_FOR_HUMAN.is_terminal() is False

    def test_is_executable(self) -> None:
        """Test is_executable method."""
        assert StepStatus.PENDING.is_executable() is True
        assert StepStatus.FAILED.is_executable() is True  # Can retry
        assert StepStatus.WAITING_FOR_HUMAN.is_executable() is True  # Re-exec with approval
        assert StepStatus.IN_PROGRESS.is_executable() is False
        assert StepStatus.COMPLETED.is_executable() is False
        assert StepStatus.CANCELLED.is_executable() is False

    def test_is_success(self) -> None:
        """Test is_success method."""
        assert StepStatus.COMPLETED.is_success() is True
        assert StepStatus.PENDING.is_success() is False
        assert StepStatus.IN_PROGRESS.is_success() is False
        assert StepStatus.FAILED.is_success() is False
        assert StepStatus.WAITING_FOR_HUMAN.is_success() is False
        assert StepStatus.CANCELLED.is_success() is False

    def test_is_failure(self) -> None:
        """Test is_failure method."""
        assert StepStatus.FAILED.is_failure() is True
        assert StepStatus.CANCELLED.is_failure() is True
        assert StepStatus.COMPLETED.is_failure() is False
        assert StepStatus.PENDING.is_failure() is False
        assert StepStatus.IN_PROGRESS.is_failure() is False
        assert StepStatus.WAITING_FOR_HUMAN.is_failure() is False
