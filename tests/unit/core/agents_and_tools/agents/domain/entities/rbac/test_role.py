"""Unit tests for Role value object."""

import pytest

from core.agents_and_tools.agents.domain.entities.rbac.action import (
    Action,
    ActionEnum,
    ScopeEnum,
)
from core.agents_and_tools.agents.domain.entities.rbac.role import Role, RoleEnum


class TestRoleCreation:
    """Test Role value object creation."""

    def test_create_role_with_valid_values(self):
        """Test creating role with valid values."""
        role = Role(
            value=RoleEnum.ARCHITECT,
            allowed_actions=frozenset([ActionEnum.APPROVE_DESIGN]),
            scope=ScopeEnum.TECHNICAL,
        )

        assert role.value == RoleEnum.ARCHITECT
        assert ActionEnum.APPROVE_DESIGN in role.allowed_actions
        assert role.scope == ScopeEnum.TECHNICAL

    def test_create_role_with_invalid_enum_fails(self):
        """Test fail-fast on invalid role enum."""
        with pytest.raises(ValueError, match="Invalid role.*Must be RoleEnum"):
            Role(
                value="invalid_role",  # type: ignore
                allowed_actions=frozenset([ActionEnum.EXECUTE_TASK]),
                scope=ScopeEnum.TECHNICAL,
            )

    def test_create_role_with_empty_actions_fails(self):
        """Test fail-fast on empty allowed_actions."""
        with pytest.raises(ValueError, match="allowed_actions cannot be empty"):
            Role(
                value=RoleEnum.DEVELOPER,
                allowed_actions=frozenset(),  # Empty!
                scope=ScopeEnum.TECHNICAL,
            )

    def test_create_role_with_invalid_scope_fails(self):
        """Test fail-fast on invalid scope."""
        with pytest.raises(ValueError, match="Invalid scope.*Must be ScopeEnum"):
            Role(
                value=RoleEnum.ARCHITECT,
                allowed_actions=frozenset([ActionEnum.APPROVE_DESIGN]),
                scope="invalid_scope",  # type: ignore
            )

    def test_role_is_immutable(self):
        """Test role is frozen (immutable)."""
        role = Role(
            value=RoleEnum.QA,
            allowed_actions=frozenset([ActionEnum.VALIDATE_SPEC]),
            scope=ScopeEnum.QUALITY,
        )

        with pytest.raises(AttributeError):
            role.value = RoleEnum.DEVELOPER  # type: ignore


class TestRoleCanPerform:
    """Test Role.can_perform() method."""

    def test_can_perform_allowed_action_with_matching_scope(self):
        """Test role can perform allowed action with matching scope."""
        role = Role(
            value=RoleEnum.ARCHITECT,
            allowed_actions=frozenset([ActionEnum.APPROVE_DESIGN]),
            scope=ScopeEnum.TECHNICAL,
        )
        action = Action(value=ActionEnum.APPROVE_DESIGN)

        assert role.can_perform(action) is True

    def test_cannot_perform_action_not_in_allowed_actions(self):
        """Test role cannot perform action not in allowed_actions."""
        role = Role(
            value=RoleEnum.ARCHITECT,
            allowed_actions=frozenset([ActionEnum.APPROVE_DESIGN]),
            scope=ScopeEnum.TECHNICAL,
        )
        action = Action(value=ActionEnum.EXECUTE_TASK)  # Not in allowed_actions

        assert role.can_perform(action) is False

    def test_cannot_perform_action_with_wrong_scope(self):
        """Test role cannot perform action with wrong scope.

        Example: QA cannot approve technical design (wrong scope).
        """
        role = Role(
            value=RoleEnum.QA,
            allowed_actions=frozenset([ActionEnum.VALIDATE_SPEC]),
            scope=ScopeEnum.QUALITY,
        )
        action = Action(value=ActionEnum.APPROVE_DESIGN)  # Technical scope

        assert role.can_perform(action) is False

    def test_can_perform_multiple_allowed_actions(self):
        """Test role can perform any of its allowed actions."""
        role = Role(
            value=RoleEnum.DEVELOPER,
            allowed_actions=frozenset([
                ActionEnum.EXECUTE_TASK,
                ActionEnum.RUN_TESTS,
                ActionEnum.COMMIT_CODE,
            ]),
            scope=ScopeEnum.TECHNICAL,
        )

        execute_action = Action(value=ActionEnum.EXECUTE_TASK)
        run_tests_action = Action(value=ActionEnum.RUN_TESTS)
        commit_action = Action(value=ActionEnum.COMMIT_CODE)

        assert role.can_perform(execute_action) is True
        assert role.can_perform(run_tests_action) is True
        assert role.can_perform(commit_action) is True


class TestRoleGetters:
    """Test Role getter methods."""

    def test_get_name_returns_role_name(self):
        """Test get_name returns role name as string."""
        role = Role(
            value=RoleEnum.ARCHITECT,
            allowed_actions=frozenset([ActionEnum.APPROVE_DESIGN]),
            scope=ScopeEnum.TECHNICAL,
        )

        assert role.get_name() == "architect"

    def test_str_returns_role_name(self):
        """Test __str__ returns role name."""
        role = Role(
            value=RoleEnum.QA,
            allowed_actions=frozenset([ActionEnum.VALIDATE_SPEC]),
            scope=ScopeEnum.QUALITY,
        )

        assert str(role) == "qa"


class TestRoleChecks:
    """Test Role type checking methods."""

    def test_is_architect_returns_true_for_architect(self):
        """Test is_architect returns True for architect role."""
        role = Role(
            value=RoleEnum.ARCHITECT,
            allowed_actions=frozenset([ActionEnum.APPROVE_DESIGN]),
            scope=ScopeEnum.TECHNICAL,
        )

        assert role.is_architect() is True
        assert role.is_qa() is False
        assert role.is_developer() is False

    def test_is_qa_returns_true_for_qa(self):
        """Test is_qa returns True for QA role."""
        role = Role(
            value=RoleEnum.QA,
            allowed_actions=frozenset([ActionEnum.VALIDATE_SPEC]),
            scope=ScopeEnum.QUALITY,
        )

        assert role.is_qa() is True
        assert role.is_architect() is False

    def test_is_developer_returns_true_for_developer(self):
        """Test is_developer returns True for developer role."""
        role = Role(
            value=RoleEnum.DEVELOPER,
            allowed_actions=frozenset([ActionEnum.EXECUTE_TASK]),
            scope=ScopeEnum.TECHNICAL,
        )

        assert role.is_developer() is True
        assert role.is_qa() is False

    def test_is_po_returns_true_for_po(self):
        """Test is_po returns True for PO role."""
        role = Role(
            value=RoleEnum.PO,
            allowed_actions=frozenset([ActionEnum.APPROVE_PROPOSAL]),
            scope=ScopeEnum.BUSINESS,
        )

        assert role.is_po() is True
        assert role.is_architect() is False

    def test_is_devops_returns_true_for_devops(self):
        """Test is_devops returns True for devops role."""
        role = Role(
            value=RoleEnum.DEVOPS,
            allowed_actions=frozenset([ActionEnum.DEPLOY_SERVICE]),
            scope=ScopeEnum.OPERATIONS,
        )

        assert role.is_devops() is True
        assert role.is_developer() is False

    def test_is_data_returns_true_for_data(self):
        """Test is_data returns True for data role."""
        role = Role(
            value=RoleEnum.DATA,
            allowed_actions=frozenset([ActionEnum.EXECUTE_MIGRATION]),
            scope=ScopeEnum.DATA,
        )

        assert role.is_data() is True
        assert role.is_architect() is False

