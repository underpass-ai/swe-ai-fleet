"""Unit tests for Role value object."""

import pytest

from core.ceremony_engine.domain.value_objects.role import Role


def test_role_happy_path() -> None:
    """Test creating a valid role."""
    role = Role(id="PO", description="Product Owner", allowed_actions=())

    assert role.id == "PO"
    assert role.description == "Product Owner"
    assert role.allowed_actions == ()


def test_role_with_allowed_actions() -> None:
    """Test creating a role with allowed actions."""
    role = Role(
        id="SYSTEM",
        description="System/automated",
        allowed_actions=("process_data", "publish_event"),
    )

    assert role.id == "SYSTEM"
    assert len(role.allowed_actions) == 2
    assert "process_data" in role.allowed_actions
    assert "publish_event" in role.allowed_actions


def test_role_rejects_empty_id() -> None:
    """Test that empty id raises ValueError."""
    with pytest.raises(ValueError, match="Role id cannot be empty"):
        Role(id="", description="Description", allowed_actions=())


def test_role_rejects_whitespace_id() -> None:
    """Test that whitespace-only id raises ValueError."""
    with pytest.raises(ValueError, match="Role id cannot be empty"):
        Role(id="   ", description="Description", allowed_actions=())


def test_role_rejects_lowercase_id() -> None:
    """Test that lowercase id raises ValueError."""
    with pytest.raises(ValueError, match="Role id must be UPPERCASE"):
        Role(id="po", description="Description", allowed_actions=())


def test_role_rejects_mixed_case_id() -> None:
    """Test that mixed case id raises ValueError."""
    with pytest.raises(ValueError, match="Role id must be UPPERCASE"):
        Role(id="Po", description="Description", allowed_actions=())


def test_role_rejects_empty_description() -> None:
    """Test that empty description raises ValueError."""
    with pytest.raises(ValueError, match="Role description cannot be empty"):
        Role(id="PO", description="", allowed_actions=())


def test_role_rejects_whitespace_description() -> None:
    """Test that whitespace-only description raises ValueError."""
    with pytest.raises(ValueError, match="Role description cannot be empty"):
        Role(id="PO", description="   ", allowed_actions=())


def test_role_str_representation() -> None:
    """Test string representation of role."""
    role = Role(id="PO", description="Product Owner", allowed_actions=())
    assert str(role) == "PO"


def test_role_is_immutable() -> None:
    """Test that role is immutable (frozen dataclass)."""
    role = Role(id="PO", description="Description", allowed_actions=())

    with pytest.raises(Exception):  # frozen dataclass raises exception on mutation
        role.id = "CHANGED"  # type: ignore[misc]


def test_role_allowed_actions_is_tuple() -> None:
    """Test that allowed_actions is stored as tuple (immutable)."""
    actions = ["action1", "action2"]
    role = Role(id="PO", description="Description", allowed_actions=tuple(actions))

    assert isinstance(role.allowed_actions, tuple)
    # Tuple is immutable, so this should not affect the role
    actions.append("action3")
    assert len(role.allowed_actions) == 2
