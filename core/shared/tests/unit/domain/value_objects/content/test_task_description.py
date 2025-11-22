"""Unit tests for TaskDescription value object."""

from __future__ import annotations

import pytest

from core.shared.domain.value_objects.content.task_description import TaskDescription


class TestTaskDescription:
    """Tests for TaskDescription value object."""

    def test_task_description_rejects_empty(self) -> None:
        """Test that empty description is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            TaskDescription("")

    def test_task_description_rejects_whitespace_only(self) -> None:
        """Test that whitespace-only description is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            TaskDescription("   ")

    def test_task_description_rejects_long_value(self) -> None:
        """Test that description > 2000 chars is rejected."""
        long_description = "x" * 2001
        with pytest.raises(ValueError, match="too long"):
            TaskDescription(long_description)

    def test_valid_task_description_creates_instance(self) -> None:
        """Test that valid description creates instance."""
        description = TaskDescription("Implement user authentication")
        assert description.value == "Implement user authentication"

    def test_str_representation_truncates_long_text(self) -> None:
        """Test that string representation truncates long text."""
        long_text = "x" * 150
        description = TaskDescription(long_text)
        str_repr = str(description)
        assert len(str_repr) == 103  # 100 chars + "..."
        assert str_repr.endswith("...")

    def test_str_representation_keeps_short_text(self) -> None:
        """Test that string representation keeps short text."""
        short_text = "Short description"
        description = TaskDescription(short_text)
        assert str(description) == short_text

