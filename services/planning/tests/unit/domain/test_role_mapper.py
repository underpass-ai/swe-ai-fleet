"""Unit tests for RoleMapper domain value object."""

import pytest
from planning.domain.value_objects.actors.role import Role
from planning.domain.value_objects.actors.role_mapper import RoleMapper
from planning.domain.value_objects.actors.role_type import RoleType


class TestRoleMapper:
    """Test suite for RoleMapper."""

    def test_from_string_maps_developer_variants(self) -> None:
        """Test that DEVELOPER variants map correctly."""
        assert RoleMapper.from_string("DEVELOPER").value == RoleType.DEVELOPER
        assert RoleMapper.from_string("DEV").value == RoleType.DEVELOPER
        assert RoleMapper.from_string("developer").value == RoleType.DEVELOPER
        assert RoleMapper.from_string("dev").value == RoleType.DEVELOPER

    def test_from_string_maps_qa_variants(self) -> None:
        """Test that QA variants map correctly."""
        assert RoleMapper.from_string("QA").value == RoleType.QA
        assert RoleMapper.from_string("TESTER").value == RoleType.QA
        assert RoleMapper.from_string("qa").value == RoleType.QA
        assert RoleMapper.from_string("tester").value == RoleType.QA

    def test_from_string_maps_architect_variants(self) -> None:
        """Test that ARCHITECT variants map correctly."""
        assert RoleMapper.from_string("ARCHITECT").value == RoleType.ARCHITECT
        assert RoleMapper.from_string("ARCH").value == RoleType.ARCHITECT
        assert RoleMapper.from_string("architect").value == RoleType.ARCHITECT
        assert RoleMapper.from_string("arch").value == RoleType.ARCHITECT

    def test_from_string_maps_product_owner_variants(self) -> None:
        """Test that PRODUCT_OWNER variants map correctly."""
        assert RoleMapper.from_string("PO").value == RoleType.PRODUCT_OWNER
        assert RoleMapper.from_string("PRODUCT_OWNER").value == RoleType.PRODUCT_OWNER
        assert RoleMapper.from_string("po").value == RoleType.PRODUCT_OWNER
        assert RoleMapper.from_string("product_owner").value == RoleType.PRODUCT_OWNER

    def test_from_string_handles_whitespace(self) -> None:
        """Test that whitespace is stripped."""
        assert RoleMapper.from_string("  DEVELOPER  ").value == RoleType.DEVELOPER
        assert RoleMapper.from_string("\tDEV\n").value == RoleType.DEVELOPER

    def test_from_string_defaults_to_developer_for_unknown(self) -> None:
        """Test that unknown roles default to DEVELOPER."""
        assert RoleMapper.from_string("UNKNOWN_ROLE").value == RoleType.DEVELOPER
        assert RoleMapper.from_string("INVALID").value == RoleType.DEVELOPER

    def test_from_string_raises_error_for_empty_string(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            RoleMapper.from_string("")

        with pytest.raises(ValueError, match="cannot be empty"):
            RoleMapper.from_string("   ")

    def test_from_strings_uses_first_role(self) -> None:
        """Test that from_strings uses first role in tuple."""
        roles = ("DEVELOPER", "QA", "ARCHITECT")
        assert RoleMapper.from_strings(roles).value == RoleType.DEVELOPER

    def test_from_strings_raises_error_for_empty_tuple(self) -> None:
        """Test that empty tuple raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            RoleMapper.from_strings(())

    def test_from_strings_returns_role_vo(self) -> None:
        """Test that from_strings returns Role VO."""
        role = RoleMapper.from_strings(("DEVELOPER",))
        assert isinstance(role, Role)
        assert role.value == RoleType.DEVELOPER

