"""Unit tests for StepStatusEntry value object."""

import pytest

from core.ceremony_engine.domain.value_objects.step_id import StepId
from core.ceremony_engine.domain.value_objects.step_status import StepStatus
from core.ceremony_engine.domain.value_objects.step_status_entry import StepStatusEntry


class TestStepStatusEntry:
    """Test cases for StepStatusEntry."""

    def test_step_status_entry_happy_path(self) -> None:
        """Test creating a valid StepStatusEntry."""
        entry = StepStatusEntry(step_id=StepId("step_1"), status=StepStatus.PENDING)

        assert entry.step_id == StepId("step_1")
        assert entry.status == StepStatus.PENDING

    def test_step_status_entry_rejects_invalid_step_id_type(self) -> None:
        """Test that invalid step_id type is rejected."""
        with pytest.raises(ValueError, match="step_id must be StepId"):
            StepStatusEntry(step_id="step_1", status=StepStatus.PENDING)  # type: ignore[arg-type]

    def test_step_status_entry_rejects_invalid_status_type(self) -> None:
        """Test that invalid status type is rejected."""
        with pytest.raises(ValueError, match="status must be StepStatus"):
            StepStatusEntry(step_id=StepId("step_1"), status="PENDING")  # type: ignore[arg-type]
