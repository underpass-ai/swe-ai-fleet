"""Unit tests for Brief value object."""

import pytest
from planning.domain.value_objects import Brief


def test_brief_creation_success():
    """Test successful Brief creation."""
    brief = Brief("User should be able to login with email and password")
    assert "email and password" in brief.value


def test_brief_is_frozen():
    """Test that Brief is immutable."""
    brief = Brief("Test brief")

    with pytest.raises(Exception):  # FrozenInstanceError
        brief.value = "New brief"  # type: ignore


def test_brief_rejects_empty_string():
    """Test that Brief rejects empty string."""
    with pytest.raises(ValueError, match="Brief cannot be empty"):
        Brief("")


def test_brief_rejects_whitespace():
    """Test that Brief rejects whitespace-only string."""
    with pytest.raises(ValueError, match="Brief cannot be empty"):
        Brief("   ")


def test_brief_max_length():
    """Test that Brief enforces max length (2000 chars)."""
    valid_brief = "A" * 2000
    brief = Brief(valid_brief)
    assert len(brief.value) == 2000


def test_brief_rejects_too_long():
    """Test that Brief rejects strings > 2000 chars."""
    too_long = "A" * 2001

    with pytest.raises(ValueError, match="Brief too long"):
        Brief(too_long)


def test_brief_str_representation_short():
    """Test string representation for short brief."""
    brief = Brief("Short brief")
    assert str(brief) == "Short brief"


def test_brief_str_representation_long():
    """Test string representation for long brief (truncated)."""
    long_text = "A" * 150
    brief = Brief(long_text)
    result = str(brief)

    assert result.endswith("...")
    assert len(result) == 103  # 100 chars + "..."


def test_brief_equality():
    """Test that Briefs with same value are equal."""
    brief1 = Brief("Same content")
    brief2 = Brief("Same content")
    brief3 = Brief("Different content")

    assert brief1 == brief2
    assert brief1 != brief3

