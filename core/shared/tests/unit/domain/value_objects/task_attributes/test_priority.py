"""Unit tests for Priority value object."""

from __future__ import annotations

import pytest

from core.shared.domain.value_objects.task_attributes.priority import Priority


class TestPriority:
    """Tests for Priority value object."""

    def test_priority_must_be_positive(self) -> None:
        """Test that priority < 1 is rejected."""
        with pytest.raises(ValueError, match="must be >= 1"):
            Priority(0)

    def test_priority_must_not_exceed_limit(self) -> None:
        """Test that priority > 1000 is rejected."""
        with pytest.raises(ValueError, match="too large"):
            Priority(1001)

    def test_valid_priority_creates_instance(self) -> None:
        """Test that valid priority creates instance."""
        priority = Priority(5)
        assert priority.value == 5
        assert priority.to_int() == 5

    def test_from_optional_defaults_to_highest(self) -> None:
        """Test that from_optional(None) defaults to highest priority (1)."""
        priority = Priority.from_optional(None)
        assert priority.to_int() == 1

    def test_from_optional_with_zero_defaults_to_highest(self) -> None:
        """Test that from_optional(0) defaults to highest priority (1)."""
        priority = Priority.from_optional(0)
        assert priority.to_int() == 1

    def test_from_optional_returns_value(self) -> None:
        """Test that from_optional returns the provided value."""
        priority = Priority.from_optional(5)
        assert priority.to_int() == 5

    def test_is_higher_than_compares_values(self) -> None:
        """Test that is_higher_than correctly compares priorities."""
        assert Priority(1).is_higher_than(Priority(3))
        assert not Priority(3).is_higher_than(Priority(1))
        assert not Priority(2).is_higher_than(Priority(2))

    def test_highest_factory_creates_priority_one(self) -> None:
        """Test that highest() factory creates priority 1."""
        priority = Priority.highest()
        assert priority.value == 1
        assert priority.to_int() == 1

    def test_str_representation(self) -> None:
        """Test string representation."""
        priority = Priority(5)
        assert str(priority) == "5"

