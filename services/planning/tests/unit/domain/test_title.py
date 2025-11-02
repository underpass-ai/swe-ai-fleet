"""Unit tests for Title value object."""

import pytest

from planning.domain.value_objects import Title


def test_title_creation_success():
    """Test successful Title creation."""
    title = Title("As a user I want to login")
    assert title.value == "As a user I want to login"


def test_title_is_frozen():
    """Test that Title is immutable."""
    title = Title("Test")

    with pytest.raises(Exception):  # FrozenInstanceError
        title.value = "New title"  # type: ignore


def test_title_rejects_empty_string():
    """Test that Title rejects empty string."""
    with pytest.raises(ValueError, match="Title cannot be empty"):
        Title("")


def test_title_rejects_whitespace():
    """Test that Title rejects whitespace-only string."""
    with pytest.raises(ValueError, match="Title cannot be empty"):
        Title("   ")


def test_title_max_length():
    """Test that Title enforces max length (200 chars)."""
    valid_title = "A" * 200
    title = Title(valid_title)
    assert len(title.value) == 200


def test_title_rejects_too_long():
    """Test that Title rejects strings > 200 chars."""
    too_long = "A" * 201

    with pytest.raises(ValueError, match="Title too long"):
        Title(too_long)


def test_title_str_representation():
    """Test string representation."""
    title = Title("User login feature")
    assert str(title) == "User login feature"


def test_title_equality():
    """Test that Titles with same value are equal."""
    title1 = Title("Login")
    title2 = Title("Login")
    title3 = Title("Logout")

    assert title1 == title2
    assert title1 != title3


def test_title_with_special_characters():
    """Test Title with special characters."""
    special_titles = [
        "As a user, I want to login - Part 1",
        "Feature: User authentication (OAuth2)",
        "Bug fix: Login fails with @ in email",
    ]

    for title_str in special_titles:
        title = Title(title_str)
        assert title.value == title_str

