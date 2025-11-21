"""Unit tests for Reason value object."""

import pytest
from planning.domain.value_objects import Reason


def test_reason_creation_success():
    """Test successful Reason creation."""
    reason = Reason("Design is too complex and needs simplification")
    assert "complex" in reason.value


def test_reason_is_frozen():
    """Test that Reason is immutable."""
    reason = Reason("Test reason")

    with pytest.raises(Exception):  # FrozenInstanceError
        reason.value = "New reason"  # type: ignore


def test_reason_rejects_empty_string():
    """Test that Reason rejects empty string."""
    with pytest.raises(ValueError, match="Reason cannot be empty"):
        Reason("")


def test_reason_rejects_whitespace():
    """Test that Reason rejects whitespace-only string."""
    with pytest.raises(ValueError, match="Reason cannot be empty"):
        Reason("   ")


def test_reason_max_length():
    """Test that Reason enforces max length (500 chars)."""
    valid_reason = "A" * 500
    reason = Reason(valid_reason)
    assert len(reason.value) == 500


def test_reason_rejects_too_long():
    """Test that Reason rejects strings > 500 chars."""
    too_long = "A" * 501

    with pytest.raises(ValueError, match="Reason too long"):
        Reason(too_long)


def test_reason_str_representation():
    """Test string representation."""
    reason = Reason("Needs more detail")
    assert str(reason) == "Needs more detail"


def test_reason_equality():
    """Test that Reasons with same value are equal."""
    reason1 = Reason("Too complex")
    reason2 = Reason("Too complex")
    reason3 = Reason("Missing tests")

    assert reason1 == reason2
    assert reason1 != reason3


def test_reason_common_rejection_patterns():
    """Test common rejection reason patterns."""
    common_reasons = [
        "Missing acceptance criteria",
        "DoR score too low (need more detail)",
        "Technical approach is not scalable",
        "Conflicts with architecture principles",
    ]

    for reason_str in common_reasons:
        reason = Reason(reason_str)
        assert reason.value == reason_str

