"""Unit tests for Role value object."""

import pytest

from services.workflow.domain.value_objects.role import Role


def test_role_creation_success():
    """Test Role creation with valid values."""
    developer = Role("developer")
    architect = Role("architect")
    qa = Role("qa")
    po = Role("po")
    system = Role("system")

    assert developer.value == "developer"
    assert architect.value == "architect"
    assert qa.value == "qa"
    assert po.value == "po"
    assert system.value == "system"


def test_role_factories():
    """Test Role factory methods."""
    assert Role.developer().value == "developer"
    assert Role.architect().value == "architect"
    assert Role.qa().value == "qa"
    assert Role.po().value == "po"
    assert Role.system().value == "system"


def test_role_invalid_raises_error():
    """Test Role with invalid value raises ValueError."""
    with pytest.raises(ValueError, match="Invalid role"):
        Role("invalid_role")


def test_role_empty_raises_error():
    """Test Role with empty string raises ValueError."""
    with pytest.raises(ValueError, match="Role cannot be empty"):
        Role("")


def test_role_is_validator():
    """Test is_validator() method."""
    assert Role.architect().is_validator() is True
    assert Role.qa().is_validator() is True
    assert Role.po().is_validator() is True
    assert Role.developer().is_validator() is False
    assert Role.system().is_validator() is False


def test_role_is_implementer():
    """Test is_implementer() method."""
    assert Role.developer().is_implementer() is True
    assert Role.architect().is_implementer() is False
    assert Role.qa().is_implementer() is False


def test_role_is_system():
    """Test is_system() method."""
    assert Role.system().is_system() is True
    assert Role.developer().is_system() is False


def test_role_equality_case_insensitive():
    """Test Role equality is case-insensitive."""
    role1 = Role("developer")
    role2 = Role("DEVELOPER")

    assert role1 == role2


def test_role_string_representation():
    """Test Role string representation (lowercase)."""
    role = Role("DEVELOPER")
    assert str(role) == "developer"


def test_role_immutable():
    """Test Role is immutable (frozen)."""
    role = Role("developer")

    with pytest.raises(AttributeError):
        role.value = "architect"  # type: ignore

