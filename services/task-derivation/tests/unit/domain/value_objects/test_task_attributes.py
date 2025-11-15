"""Unit tests for task attribute value objects."""

from __future__ import annotations

import pytest

from task_derivation.domain.value_objects.task_attributes.duration import Duration
from task_derivation.domain.value_objects.task_attributes.priority import Priority


class TestDuration:
    def test_negative_duration_fails(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            Duration(-1)

    def test_duration_rejects_unrealistic_value(self) -> None:
        with pytest.raises(ValueError, match="Duration too large"):
            Duration(1001)

    def test_from_optional_defaults_to_zero(self) -> None:
        duration = Duration.from_optional(None)
        assert duration.to_hours() == 0

    def test_from_optional_returns_value(self) -> None:
        duration = Duration.from_optional(5)
        assert duration.to_hours() == 5


class TestPriority:
    def test_priority_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="must be >= 1"):
            Priority(0)

    def test_priority_must_not_exceed_limit(self) -> None:
        with pytest.raises(ValueError, match="too large"):
            Priority(1001)

    def test_from_optional_defaults_to_highest(self) -> None:
        priority = Priority.from_optional(None)
        assert priority.to_int() == 1

    def test_from_optional_returns_value(self) -> None:
        priority = Priority.from_optional(5)
        assert priority.to_int() == 5

    def test_is_higher_than_compares_values(self) -> None:
        assert Priority(1).is_higher_than(Priority(3))

