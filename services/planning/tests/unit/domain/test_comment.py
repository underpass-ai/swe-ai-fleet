"""Unit tests for Comment value object."""

import pytest

from planning.domain.value_objects import Comment


def test_comment_creation_success():
    """Test successful Comment creation."""
    comment = Comment("This looks good to me")
    assert comment.value == "This looks good to me"


def test_comment_is_frozen():
    """Test that Comment is immutable."""
    comment = Comment("Test")

    with pytest.raises(Exception):  # FrozenInstanceError
        comment.value = "New"  # type: ignore


def test_comment_allows_empty_string():
    """Test that Comment allows empty string (optional)."""
    comment = Comment("")
    assert comment.value == ""
    assert comment.is_empty()


def test_comment_is_empty_whitespace():
    """Test is_empty for whitespace-only comment."""
    comment = Comment("   ")
    assert comment.is_empty()


def test_comment_is_empty_false_for_content():
    """Test is_empty returns False when comment has content."""
    comment = Comment("Good work")
    assert not comment.is_empty()


def test_comment_max_length():
    """Test that Comment enforces max length (1000 chars)."""
    valid_comment = "A" * 1000
    comment = Comment(valid_comment)
    assert len(comment.value) == 1000


def test_comment_rejects_too_long():
    """Test that Comment rejects strings > 1000 chars."""
    too_long = "A" * 1001

    with pytest.raises(ValueError, match="Comment too long"):
        Comment(too_long)


def test_comment_str_representation():
    """Test string representation."""
    comment = Comment("Nice work!")
    assert str(comment) == "Nice work!"


def test_comment_str_representation_empty():
    """Test string representation for empty comment."""
    comment = Comment("")
    assert str(comment) == "(no comment)"


def test_comment_equality():
    """Test that Comments with same value are equal."""
    comment1 = Comment("Same")
    comment2 = Comment("Same")
    comment3 = Comment("Different")

    assert comment1 == comment2
    assert comment1 != comment3

