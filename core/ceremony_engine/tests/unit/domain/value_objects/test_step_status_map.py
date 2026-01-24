"""Unit tests for StepStatusMap value object."""

import pytest

from core.ceremony_engine.domain.value_objects.step_id import StepId
from core.ceremony_engine.domain.value_objects.step_status import StepStatus
from core.ceremony_engine.domain.value_objects.step_status_entry import StepStatusEntry
from core.ceremony_engine.domain.value_objects.step_status_map import StepStatusMap


class TestStepStatusMap:
    """Test cases for StepStatusMap."""

    def test_step_status_map_happy_path(self) -> None:
        """Test creating a valid StepStatusMap."""
        mapping = StepStatusMap(
            entries=(StepStatusEntry(step_id=StepId("step_1"), status=StepStatus.PENDING),)
        )

        assert mapping.get(StepId("step_1"), StepStatus.COMPLETED) == StepStatus.PENDING
        assert mapping.get(StepId("missing"), StepStatus.PENDING) == StepStatus.PENDING

    def test_step_status_map_rejects_empty_step_id(self) -> None:
        """Test that empty step_id is rejected."""
        with pytest.raises(ValueError, match="StepId value cannot be empty"):
            StepStatusMap(
                entries=(StepStatusEntry(step_id=StepId(""), status=StepStatus.PENDING),)
            )

    def test_step_status_map_rejects_duplicate_step_id(self) -> None:
        """Test that duplicate step_id is rejected."""
        with pytest.raises(ValueError, match="Duplicate step_id"):
            StepStatusMap(
                entries=(
                    StepStatusEntry(step_id=StepId("step_1"), status=StepStatus.PENDING),
                    StepStatusEntry(step_id=StepId("step_1"), status=StepStatus.COMPLETED),
                )
            )

    def test_step_status_map_rejects_invalid_entry_type(self) -> None:
        """Test that invalid entry type is rejected."""
        with pytest.raises(ValueError, match="entries must contain StepStatusEntry"):
            StepStatusMap(entries=(("step-1", "PENDING"),))  # type: ignore[arg-type]

    def test_step_status_map_with_status_updates_existing(self) -> None:
        """Test updating an existing step status."""
        mapping = StepStatusMap(
            entries=(StepStatusEntry(step_id=StepId("step_1"), status=StepStatus.PENDING),)
        )

        updated = mapping.with_status(StepId("step_1"), StepStatus.COMPLETED)

        assert updated.get(StepId("step_1"), StepStatus.PENDING) == StepStatus.COMPLETED
        assert mapping.get(StepId("step_1"), StepStatus.COMPLETED) == StepStatus.PENDING

    def test_step_status_map_with_status_adds_new(self) -> None:
        """Test adding a new step status."""
        mapping = StepStatusMap(entries=())

        updated = mapping.with_status(StepId("step_2"), StepStatus.IN_PROGRESS)

        assert updated.get(StepId("step_2"), StepStatus.PENDING) == StepStatus.IN_PROGRESS

    def test_step_status_map_property_multiple_ids(self) -> None:
        """Property-style test across multiple step IDs."""
        mapping = StepStatusMap(entries=())
        step_ids = ("step_a", "step_b", "step_c", "step_d")

        updated = mapping
        for step_id in step_ids:
            updated = updated.with_status(StepId(step_id), StepStatus.COMPLETED)

        for step_id in step_ids:
            assert updated.get(StepId(step_id), StepStatus.PENDING) == StepStatus.COMPLETED
