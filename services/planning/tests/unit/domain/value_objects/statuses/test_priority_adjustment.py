"""Unit tests for PriorityAdjustment enum and value object."""

import pytest
from planning.domain.value_objects.statuses.priority_adjustment import (
    PriorityAdjustment,
    PriorityAdjustmentEnum,
)


def test_priority_adjustment_enum_values() -> None:
    """Test that PriorityAdjustmentEnum has correct values."""
    # Assert
    assert PriorityAdjustmentEnum.HIGH.value == "HIGH"
    assert PriorityAdjustmentEnum.MEDIUM.value == "MEDIUM"
    assert PriorityAdjustmentEnum.LOW.value == "LOW"


def test_priority_adjustment_enum_str_representation() -> None:
    """Test string representation of enum."""
    # Act & Assert
    assert str(PriorityAdjustmentEnum.HIGH) == "HIGH"
    assert str(PriorityAdjustmentEnum.MEDIUM) == "MEDIUM"
    assert str(PriorityAdjustmentEnum.LOW) == "LOW"


def test_priority_adjustment_creation_with_enum() -> None:
    """Test creating PriorityAdjustment with enum value."""
    # Arrange & Act
    adjustment = PriorityAdjustment(value=PriorityAdjustmentEnum.HIGH)

    # Assert
    assert adjustment.value == PriorityAdjustmentEnum.HIGH
    assert str(adjustment) == "HIGH"


def test_priority_adjustment_from_string_high() -> None:
    """Test creating PriorityAdjustment from string HIGH."""
    # Act
    adjustment = PriorityAdjustment.from_string("HIGH")

    # Assert
    assert adjustment.value == PriorityAdjustmentEnum.HIGH
    assert str(adjustment) == "HIGH"


def test_priority_adjustment_from_string_medium() -> None:
    """Test creating PriorityAdjustment from string MEDIUM."""
    # Act
    adjustment = PriorityAdjustment.from_string("MEDIUM")

    # Assert
    assert adjustment.value == PriorityAdjustmentEnum.MEDIUM
    assert str(adjustment) == "MEDIUM"


def test_priority_adjustment_from_string_low() -> None:
    """Test creating PriorityAdjustment from string LOW."""
    # Act
    adjustment = PriorityAdjustment.from_string("LOW")

    # Assert
    assert adjustment.value == PriorityAdjustmentEnum.LOW
    assert str(adjustment) == "LOW"


def test_priority_adjustment_from_string_case_insensitive() -> None:
    """Test that from_string is case-insensitive."""
    # Act
    adjustment_high = PriorityAdjustment.from_string("high")
    adjustment_medium = PriorityAdjustment.from_string("medium")
    adjustment_low = PriorityAdjustment.from_string("low")

    # Assert
    assert adjustment_high.value == PriorityAdjustmentEnum.HIGH
    assert adjustment_medium.value == PriorityAdjustmentEnum.MEDIUM
    assert adjustment_low.value == PriorityAdjustmentEnum.LOW


def test_priority_adjustment_from_string_strips_whitespace() -> None:
    """Test that from_string strips whitespace."""
    # Act
    adjustment = PriorityAdjustment.from_string("  HIGH  ")

    # Assert
    assert adjustment.value == PriorityAdjustmentEnum.HIGH


def test_priority_adjustment_from_string_rejects_invalid() -> None:
    """Test that from_string rejects invalid values."""
    # Act & Assert
    with pytest.raises(ValueError, match="Invalid priority adjustment"):
        PriorityAdjustment.from_string("CRITICAL")


def test_priority_adjustment_from_string_rejects_empty() -> None:
    """Test that from_string rejects empty string."""
    # Act & Assert
    with pytest.raises(ValueError, match="Invalid priority adjustment"):
        PriorityAdjustment.from_string("")


def test_priority_adjustment_from_string_rejects_whitespace_only() -> None:
    """Test that from_string rejects whitespace-only string."""
    # Act & Assert
    with pytest.raises(ValueError, match="Invalid priority adjustment"):
        PriorityAdjustment.from_string("   ")


def test_priority_adjustment_is_immutable() -> None:
    """Test that PriorityAdjustment is frozen (immutable)."""
    # Arrange
    adjustment = PriorityAdjustment(value=PriorityAdjustmentEnum.HIGH)

    # Act & Assert
    with pytest.raises(Exception):  # FrozenInstanceError
        adjustment.value = PriorityAdjustmentEnum.LOW  # type: ignore


def test_priority_adjustment_str_representation() -> None:
    """Test string representation."""
    # Arrange
    adjustment = PriorityAdjustment(value=PriorityAdjustmentEnum.MEDIUM)

    # Act & Assert
    assert str(adjustment) == "MEDIUM"


def test_priority_adjustment_repr_representation() -> None:
    """Test repr representation."""
    # Arrange
    adjustment = PriorityAdjustment(value=PriorityAdjustmentEnum.HIGH)

    # Act
    repr_str = repr(adjustment)

    # Assert
    assert "PriorityAdjustment" in repr_str
    assert "HIGH" in repr_str


def test_priority_adjustment_equality() -> None:
    """Test that two PriorityAdjustments with same value are equal."""
    # Arrange
    adjustment1 = PriorityAdjustment(value=PriorityAdjustmentEnum.HIGH)
    adjustment2 = PriorityAdjustment(value=PriorityAdjustmentEnum.HIGH)

    # Act & Assert
    assert adjustment1 == adjustment2


def test_priority_adjustment_inequality() -> None:
    """Test that PriorityAdjustments with different values are not equal."""
    # Arrange
    adjustment1 = PriorityAdjustment(value=PriorityAdjustmentEnum.HIGH)
    adjustment2 = PriorityAdjustment(value=PriorityAdjustmentEnum.LOW)

    # Act & Assert
    assert adjustment1 != adjustment2


def test_priority_adjustment_hash_consistency() -> None:
    """Test that PriorityAdjustment can be hashed (for use in sets/dicts)."""
    # Arrange
    adjustment1 = PriorityAdjustment(value=PriorityAdjustmentEnum.MEDIUM)
    adjustment2 = PriorityAdjustment(value=PriorityAdjustmentEnum.MEDIUM)

    # Act & Assert: Same values = same hash
    assert hash(adjustment1) == hash(adjustment2)

    # Can be used in set
    adjustment_set = {adjustment1, adjustment2}
    assert len(adjustment_set) == 1  # Only one unique adjustment


def test_priority_adjustment_all_valid_values() -> None:
    """Test all valid priority adjustment values."""
    # Test HIGH
    high = PriorityAdjustment.from_string("HIGH")
    assert high.value == PriorityAdjustmentEnum.HIGH

    # Test MEDIUM
    medium = PriorityAdjustment.from_string("MEDIUM")
    assert medium.value == PriorityAdjustmentEnum.MEDIUM

    # Test LOW
    low = PriorityAdjustment.from_string("LOW")
    assert low.value == PriorityAdjustmentEnum.LOW


def test_priority_adjustment_mixed_case() -> None:
    """Test that from_string handles mixed case."""
    # Act
    adjustment = PriorityAdjustment.from_string("HiGh")

    # Assert
    assert adjustment.value == PriorityAdjustmentEnum.HIGH

