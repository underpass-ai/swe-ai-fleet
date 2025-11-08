"""Unit tests for RoleVisibilityPolicy and related Value Objects."""

import pytest
from core.context.domain.role import Role
from core.context.domain.value_objects.role_visibility_policy import (
    EntityVisibilityRule,
    RoleVisibilityPolicy,
    VisibilityScope,
)


class TestVisibilityScopeEnum:
    """Test VisibilityScope enum."""

    def test_all_scopes_have_string_values(self):
        """Test all scopes have string values."""
        for scope in VisibilityScope:
            assert isinstance(scope.value, str)
            assert len(scope.value) > 0

    def test_scope_values_are_lowercase(self):
        """Test scope values follow lowercase convention."""
        for scope in VisibilityScope:
            assert scope.value == scope.value.lower()


class TestEntityVisibilityRuleCreation:
    """Test EntityVisibilityRule Value Object creation."""

    def test_create_all_access_rule(self):
        """Test creating rule with ALL scope."""
        rule = EntityVisibilityRule(
            scope=VisibilityScope.ALL,
            filter_by="",  # Not used for ALL
            additional_filters={},
        )

        assert rule.scope == VisibilityScope.ALL
        assert rule.allows_all_access() is True
        assert rule.denies_all_access() is False

    def test_create_none_access_rule(self):
        """Test creating rule with NONE scope."""
        rule = EntityVisibilityRule(
            scope=VisibilityScope.NONE,
            filter_by="",  # Not used for NONE
            additional_filters={},
        )

        assert rule.scope == VisibilityScope.NONE
        assert rule.denies_all_access() is True
        assert rule.allows_all_access() is False

    def test_create_assigned_rule(self):
        """Test creating rule with ASSIGNED scope."""
        rule = EntityVisibilityRule(
            scope=VisibilityScope.ASSIGNED,
            filter_by="assigned_to",
            additional_filters={"status": ["active", "in_progress"]},
        )

        assert rule.scope == VisibilityScope.ASSIGNED
        assert rule.filter_by == "assigned_to"
        assert isinstance(rule.additional_filters, dict)
        assert rule.allows_all_access() is False
        assert rule.denies_all_access() is False


class TestEntityVisibilityRuleValidation:
    """Test EntityVisibilityRule validation."""

    def test_assigned_scope_without_filter_by_raises_error(self):
        """Test ASSIGNED scope without filter_by raises ValueError."""
        with pytest.raises(ValueError, match="filter_by is required"):
            EntityVisibilityRule(
                scope=VisibilityScope.ASSIGNED,
                filter_by="",  # Empty!
                additional_filters={},
            )


class TestRoleVisibilityPolicyCreation:
    """Test RoleVisibilityPolicy Value Object creation."""

    def test_create_developer_policy(self):
        """Test creating policy for developer role."""
        policy = RoleVisibilityPolicy(
            role=Role.DEVELOPER,
            epic_rule=EntityVisibilityRule(
                scope=VisibilityScope.NONE,
                filter_by="",
                additional_filters={},
            ),
            story_rule=EntityVisibilityRule(
                scope=VisibilityScope.ASSIGNED,
                filter_by="assigned_to",
                additional_filters={},
            ),
            task_rule=EntityVisibilityRule(
                scope=VisibilityScope.ASSIGNED,
                filter_by="assigned_to",
                additional_filters={},
            ),
            decision_rule=EntityVisibilityRule(
                scope=VisibilityScope.ALL,
                filter_by="",
                additional_filters={},
            ),
            plan_rule=EntityVisibilityRule(
                scope=VisibilityScope.ALL,
                filter_by="",
                additional_filters={},
            ),
            milestone_rule=EntityVisibilityRule(
                scope=VisibilityScope.ALL,
                filter_by="",
                additional_filters={},
            ),
            summary_rule=EntityVisibilityRule(
                scope=VisibilityScope.ALL,
                filter_by="",
                additional_filters={},
            ),
        )

        assert policy.role == Role.DEVELOPER
        assert policy.story_rule.scope == VisibilityScope.ASSIGNED
        assert policy.epic_rule.scope == VisibilityScope.NONE
        assert policy.task_rule.scope == VisibilityScope.ASSIGNED

    def test_create_po_policy_full_access(self):
        """Test creating policy for PO (full access)."""
        policy = RoleVisibilityPolicy(
            role=Role.PO,
            story_rule=EntityVisibilityRule(
    scope=VisibilityScope.ALL,
                filter_by="",
                additional_filters={},
            ),
            epic_rule=EntityVisibilityRule(
                scope=VisibilityScope.ALL,
                filter_by="",
                additional_filters={},
            ),
            task_rule=EntityVisibilityRule(
                scope=VisibilityScope.ALL,
                filter_by="",
                additional_filters={},
            ),
            decision_rule=EntityVisibilityRule(
                scope=VisibilityScope.ALL,
                filter_by="",
                additional_filters={},
            ),
            plan_rule=EntityVisibilityRule(
                scope=VisibilityScope.ALL,
                filter_by="",
                additional_filters={},
            ),
            milestone_rule=EntityVisibilityRule(
                scope=VisibilityScope.ALL,
                filter_by="",
                additional_filters={},
            ),
            summary_rule=EntityVisibilityRule(
                scope=VisibilityScope.ALL,
                filter_by="",
                additional_filters={},
            ),
        )

        assert policy.can_access_stories() is True
        assert policy.can_access_epics() is True
        assert policy.can_access_tasks() is True
        assert policy.has_full_access() is True  # All rules are ALL scope


class TestRoleVisibilityPolicyQueryMethods:
    """Test RoleVisibilityPolicy query methods (Tell, Don't Ask)."""

    def _create_full_policy(self, role: Role, story_scope: VisibilityScope) -> RoleVisibilityPolicy:
        """Helper to create full policy with all 7 rules."""
        return RoleVisibilityPolicy(
            role=role,
            epic_rule=EntityVisibilityRule(scope=VisibilityScope.ALL, filter_by="", additional_filters={}),
            story_rule=EntityVisibilityRule(scope=story_scope, filter_by="assigned_to" if story_scope == VisibilityScope.ASSIGNED else "", additional_filters={}),
            task_rule=EntityVisibilityRule(scope=VisibilityScope.ALL, filter_by="", additional_filters={}),
            decision_rule=EntityVisibilityRule(scope=VisibilityScope.ALL, filter_by="", additional_filters={}),
            plan_rule=EntityVisibilityRule(scope=VisibilityScope.ALL, filter_by="", additional_filters={}),
            milestone_rule=EntityVisibilityRule(scope=VisibilityScope.ALL, filter_by="", additional_filters={}),
            summary_rule=EntityVisibilityRule(scope=VisibilityScope.ALL, filter_by="", additional_filters={}),
        )

    def test_can_access_stories_with_all_scope(self):
        """Test can_access_stories() with ALL scope."""
        policy = self._create_full_policy(Role.ARCHITECT, story_scope=VisibilityScope.ALL)

        assert policy.can_access_stories() is True

    def test_can_access_stories_with_none_scope(self):
        """Test can_access_stories() with NONE scope."""
        policy = self._create_full_policy(Role.QA, story_scope=VisibilityScope.NONE)

        assert policy.can_access_stories() is False


class TestRoleVisibilityPolicyImmutability:
    """Test RoleVisibilityPolicy is immutable."""

    def test_cannot_modify_role(self):
        """Test role cannot be modified."""
        policy = RoleVisibilityPolicy(
            role=Role.DEVELOPER,
            epic_rule=EntityVisibilityRule(scope=VisibilityScope.NONE, filter_by="", additional_filters={}),
            story_rule=EntityVisibilityRule(scope=VisibilityScope.ASSIGNED, filter_by="assigned_to", additional_filters={}),
            task_rule=EntityVisibilityRule(scope=VisibilityScope.ALL, filter_by="", additional_filters={}),
            decision_rule=EntityVisibilityRule(scope=VisibilityScope.ALL, filter_by="", additional_filters={}),
            plan_rule=EntityVisibilityRule(scope=VisibilityScope.ALL, filter_by="", additional_filters={}),
            milestone_rule=EntityVisibilityRule(scope=VisibilityScope.ALL, filter_by="", additional_filters={}),
            summary_rule=EntityVisibilityRule(scope=VisibilityScope.ALL, filter_by="", additional_filters={}),
        )

        with pytest.raises(AttributeError):
            policy.role = Role.ADMIN  # type: ignore

