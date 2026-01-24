"""Unit tests for StepResult value object."""

import pytest

from core.ceremony_engine.domain.value_objects.step_result import StepResult
from core.ceremony_engine.domain.value_objects.step_status import StepStatus


class TestStepResult:
    """Test cases for StepResult value object."""

    def test_step_result_completed_happy_path(self) -> None:
        """Test creating a successful StepResult."""
        result = StepResult(
            status=StepStatus.COMPLETED,
            output={"result": "success", "data": {"key": "value"}},
        )

        assert result.status == StepStatus.COMPLETED
        assert result.output == {"result": "success", "data": {"key": "value"}}
        assert result.error_message is None
        assert result.metadata is None
        assert result.is_success() is True
        assert result.is_failure() is False

    def test_step_result_failed_happy_path(self) -> None:
        """Test creating a failed StepResult."""
        result = StepResult(
            status=StepStatus.FAILED,
            output={},
            error_message="Step execution failed: timeout",
        )

        assert result.status == StepStatus.FAILED
        assert result.output == {}
        assert result.error_message == "Step execution failed: timeout"
        assert result.is_success() is False
        assert result.is_failure() is True

    def test_step_result_with_metadata(self) -> None:
        """Test StepResult with metadata."""
        result = StepResult(
            status=StepStatus.COMPLETED,
            output={"result": "ok"},
            metadata={"execution_time_ms": 150, "retry_count": 0},
        )

        assert result.metadata == {"execution_time_ms": 150, "retry_count": 0}

    def test_step_result_rejects_pending_status(self) -> None:
        """Test that PENDING status is rejected."""
        with pytest.raises(ValueError, match="StepResult cannot have status.*PENDING"):
            StepResult(status=StepStatus.PENDING, output={})

    def test_step_result_rejects_in_progress_status(self) -> None:
        """Test that IN_PROGRESS status is rejected."""
        with pytest.raises(ValueError, match="StepResult cannot have status.*IN_PROGRESS"):
            StepResult(status=StepStatus.IN_PROGRESS, output={})

    def test_step_result_rejects_failed_without_error_message(self) -> None:
        """Test that FAILED status requires error_message."""
        with pytest.raises(ValueError, match="FAILED StepResult must have error_message"):
            StepResult(status=StepStatus.FAILED, output={})

    def test_step_result_rejects_completed_with_error_message(self) -> None:
        """Test that COMPLETED status should not have error_message."""
        with pytest.raises(ValueError, match="COMPLETED StepResult should not have error_message"):
            StepResult(
                status=StepStatus.COMPLETED,
                output={},
                error_message="should not be here",
            )

    def test_step_result_rejects_invalid_status_type(self) -> None:
        """Test that invalid status type is rejected."""
        with pytest.raises(ValueError, match="status must be a StepStatus"):
            StepResult(status="INVALID", output={})  # type: ignore[arg-type]

    def test_step_result_rejects_invalid_output_type(self) -> None:
        """Test that invalid output type is rejected."""
        with pytest.raises(ValueError, match="output must be a dict"):
            StepResult(status=StepStatus.COMPLETED, output="not a dict")  # type: ignore[arg-type]

    def test_step_result_immutable(self) -> None:
        """Test that StepResult is immutable."""
        result = StepResult(status=StepStatus.COMPLETED, output={})

        with pytest.raises(Exception):  # Frozen dataclass raises exception
            result.status = StepStatus.FAILED  # type: ignore[misc]

    def test_step_result_cancelled(self) -> None:
        """Test CANCELLED status."""
        result = StepResult(status=StepStatus.CANCELLED, output={})

        assert result.status == StepStatus.CANCELLED
        assert result.is_success() is False
        assert result.is_failure() is True

    def test_step_result_waiting_for_human(self) -> None:
        """Test WAITING_FOR_HUMAN status."""
        result = StepResult(status=StepStatus.WAITING_FOR_HUMAN, output={})

        assert result.status == StepStatus.WAITING_FOR_HUMAN
        assert result.is_success() is False
        assert result.is_failure() is False
