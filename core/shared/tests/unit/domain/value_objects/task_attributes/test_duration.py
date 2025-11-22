"""Unit tests for Duration value object."""

from __future__ import annotations

import pytest

from core.shared.domain.value_objects.task_attributes.duration import Duration


class TestDuration:
    """Tests for Duration value object."""

    def test_negative_duration_fails(self) -> None:
        """Test that negative duration is rejected."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Duration(-1)

    def test_duration_rejects_unrealistic_value(self) -> None:
        """Test that duration > 1000 hours is rejected."""
        with pytest.raises(ValueError, match="too large"):
            Duration(1001)

    def test_valid_duration_creates_instance(self) -> None:
        """Test that valid duration creates instance."""
        duration = Duration(5)
        assert duration.hours == 5
        assert duration.to_hours() == 5

    def test_from_optional_defaults_to_zero(self) -> None:
        """Test that from_optional(None) defaults to zero."""
        duration = Duration.from_optional(None)
        assert duration.to_hours() == 0

    def test_from_optional_with_zero_or_negative_defaults_to_zero(self) -> None:
        """Test that from_optional(0) or negative defaults to zero."""
        duration_zero = Duration.from_optional(0)
        assert duration_zero.to_hours() == 0

        duration_negative = Duration.from_optional(-5)
        assert duration_negative.to_hours() == 0

    def test_from_optional_returns_value(self) -> None:
        """Test that from_optional returns the provided value."""
        duration = Duration.from_optional(5)
        assert duration.to_hours() == 5

    def test_zero_factory_creates_zero_duration(self) -> None:
        """Test that zero() factory creates zero duration."""
        duration = Duration.zero()
        assert duration.hours == 0
        assert duration.to_hours() == 0

    def test_str_representation(self) -> None:
        """Test string representation."""
        duration = Duration(5)
        assert str(duration) == "5h"

