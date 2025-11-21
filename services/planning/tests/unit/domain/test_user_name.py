"""Unit tests for UserName value object."""

import pytest
from planning.domain.value_objects import UserName


def test_user_name_creation_success():
    """Test successful UserName creation."""
    user = UserName("po-tirso")
    assert user.value == "po-tirso"


def test_user_name_is_frozen():
    """Test that UserName is immutable."""
    user = UserName("po-001")

    with pytest.raises(Exception):  # FrozenInstanceError
        user.value = "new-user"  # type: ignore


def test_user_name_rejects_empty_string():
    """Test that UserName rejects empty string."""
    with pytest.raises(ValueError, match="UserName cannot be empty"):
        UserName("")


def test_user_name_rejects_whitespace():
    """Test that UserName rejects whitespace-only string."""
    with pytest.raises(ValueError, match="UserName cannot be empty"):
        UserName("   ")


def test_user_name_max_length():
    """Test that UserName enforces max length (100 chars)."""
    valid_name = "A" * 100
    user = UserName(valid_name)
    assert len(user.value) == 100


def test_user_name_rejects_too_long():
    """Test that UserName rejects strings > 100 chars."""
    too_long = "A" * 101

    with pytest.raises(ValueError, match="UserName too long"):
        UserName(too_long)


def test_user_name_str_representation():
    """Test string representation."""
    user = UserName("architect-john")
    assert str(user) == "architect-john"


def test_user_name_equality():
    """Test that UserNames with same value are equal."""
    user1 = UserName("po-001")
    user2 = UserName("po-001")
    user3 = UserName("po-002")

    assert user1 == user2
    assert user1 != user3


def test_user_name_common_formats():
    """Test common username formats."""
    common_formats = [
        "po-tirso",
        "architect-john",
        "dev-maria",
        "qa-peter",
        "user@domain.com",
        "user_123",
    ]

    for username_str in common_formats:
        user = UserName(username_str)
        assert user.value == username_str

