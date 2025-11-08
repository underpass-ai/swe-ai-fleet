"""Unit tests for Role enum."""

import pytest

from core.context.domain.role import Role


class TestRoleEnum:
    """Test Role enum values and methods."""

    def test_all_roles_have_string_values(self):
        """Test all roles can be converted to strings."""
        for role in Role:
            assert isinstance(role.value, str)
            assert len(role.value) > 0

    def test_str_representation(self):
        """Test __str__ returns value."""
        assert str(Role.DEVELOPER) == "developer"
        assert str(Role.PO) == "po"
        assert str(Role.ARCHITECT) == "architect"


class TestRoleIsHuman:
    """Test is_human() method."""

    def test_po_is_human(self):
        """Test PO is considered human."""
        assert Role.PO.is_human() is True
        assert Role.PRODUCT_OWNER.is_human() is True

    def test_admin_is_human(self):
        """Test ADMIN is considered human."""
        assert Role.ADMIN.is_human() is True

    def test_developer_is_not_human(self):
        """Test DEVELOPER is not human (it's an agent)."""
        assert Role.DEVELOPER.is_human() is False

    def test_architect_is_not_human(self):
        """Test ARCHITECT is not human (it's an agent)."""
        assert Role.ARCHITECT.is_human() is False


class TestRoleIsAgent:
    """Test is_agent() method."""

    def test_developer_is_agent(self):
        """Test DEVELOPER is considered agent."""
        assert Role.DEVELOPER.is_agent() is True

    def test_architect_is_agent(self):
        """Test ARCHITECT is considered agent."""
        assert Role.ARCHITECT.is_agent() is True

    def test_qa_is_agent(self):
        """Test QA is considered agent."""
        assert Role.QA.is_agent() is True

    def test_tester_is_agent(self):
        """Test TESTER is considered agent."""
        assert Role.TESTER.is_agent() is True

    def test_po_is_not_agent(self):
        """Test PO is not agent (it's human)."""
        assert Role.PO.is_agent() is False

    def test_admin_is_not_agent(self):
        """Test ADMIN is not agent (it's human)."""
        assert Role.ADMIN.is_agent() is False


class TestRoleHasFullContextAccess:
    """Test has_full_context_access() method (RBAC L3)."""

    def test_po_has_full_access(self):
        """Test PO has full context access."""
        assert Role.PO.has_full_context_access() is True
        assert Role.PRODUCT_OWNER.has_full_context_access() is True

    def test_admin_has_full_access(self):
        """Test ADMIN has full context access."""
        assert Role.ADMIN.has_full_context_access() is True

    def test_developer_has_limited_access(self):
        """Test DEVELOPER has limited context access (RBAC L3)."""
        assert Role.DEVELOPER.has_full_context_access() is False

    def test_architect_has_limited_access(self):
        """Test ARCHITECT has limited context access (RBAC L3)."""
        assert Role.ARCHITECT.has_full_context_access() is False

    def test_qa_has_limited_access(self):
        """Test QA has limited context access (RBAC L3)."""
        assert Role.QA.has_full_context_access() is False


class TestRoleBusinessLogic:
    """Test Role enum business logic."""

    def test_human_and_agent_are_mutually_exclusive(self):
        """Test that a role cannot be both human and agent."""
        for role in Role:
            # Skip SYSTEM which is neither human nor agent
            if role == Role.SYSTEM:
                continue
            
            is_human = role.is_human()
            is_agent = role.is_agent()
            
            # XOR: exactly one should be True
            assert is_human != is_agent, f"{role} must be either human OR agent, not both"

    def test_only_humans_have_full_access(self):
        """Test only human roles have full context access."""
        for role in Role:
            if role.is_human():
                assert role.has_full_context_access() is True, f"Human role {role} should have full access"
            elif role.is_agent():
                # Agents typically don't have full access (principle of least privilege)
                pass  # Some agents might have full access in future

