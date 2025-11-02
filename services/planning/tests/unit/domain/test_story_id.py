"""Unit tests for StoryId value object."""

import pytest

from planning.domain.value_objects import StoryId


def test_story_id_creation_success():
    """Test successful StoryId creation."""
    story_id = StoryId("s-12345")
    assert story_id.value == "s-12345"


def test_story_id_is_frozen():
    """Test that StoryId is immutable (frozen dataclass)."""
    story_id = StoryId("s-12345")

    with pytest.raises(Exception):  # FrozenInstanceError
        story_id.value = "s-99999"  # type: ignore


def test_story_id_rejects_empty_string():
    """Test that StoryId rejects empty string."""
    with pytest.raises(ValueError, match="StoryId cannot be empty"):
        StoryId("")


def test_story_id_rejects_whitespace():
    """Test that StoryId rejects whitespace-only string."""
    with pytest.raises(ValueError, match="StoryId cannot be whitespace"):
        StoryId("   ")


def test_story_id_str_representation():
    """Test string representation."""
    story_id = StoryId("s-test-001")
    assert str(story_id) == "s-test-001"


def test_story_id_equality():
    """Test equality of StoryId instances."""
    story_id1 = StoryId("s-12345")
    story_id2 = StoryId("s-12345")
    story_id3 = StoryId("s-99999")

    assert story_id1 == story_id2
    assert story_id1 != story_id3

