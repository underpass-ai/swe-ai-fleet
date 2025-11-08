"""Unit tests for AuthorizationChecker Domain Service."""

import pytest
from unittest.mock import AsyncMock

from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.role import Role
from core.context.domain.services.authorization_checker import AuthorizationChecker
from core.context.domain.value_objects.role_visibility_policy import (
    RoleVisibilityPolicy,
    EntityVisibilityRule,
    VisibilityScope,
)
from core.context.ports.story_authorization_port import StoryAuthorizationPort


class TestAuthorizationChecker:
    """Test suite for AuthorizationChecker domain service."""

    @pytest.fixture
    def mock_story_auth_port(self) -> AsyncMock:
        """Create mock StoryAuthorizationPort."""
        return AsyncMock(spec=StoryAuthorizationPort)

    @pytest.fixture
    def checker(self, mock_story_auth_port: AsyncMock) -> AuthorizationChecker:
        """Create AuthorizationChecker with mock port."""
        return AuthorizationChecker(story_auth_port=mock_story_auth_port)

    @pytest.mark.asyncio
    async def test_check_story_access_allows_all_access_scope(
        self,
        checker: AuthorizationChecker,
        mock_story_auth_port: AsyncMock,
    ) -> None:
        """Test that ALL_STORIES scope grants access immediately."""
        rule = EntityVisibilityRule(
            scope=VisibilityScope.ALL,
            filter_by=None,
            additional_filters={},
        )
        story_id = StoryId(value="story-123")

        result = await checker.check_story_access(story_id, "user-456", rule)

        assert result.was_granted() is True
        # Port should NOT be called (early return)
        mock_story_auth_port.is_story_assigned_to_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_story_access_denies_none_scope(
        self,
        checker: AuthorizationChecker,
    ) -> None:
        """Test that NONE scope denies access immediately."""
        rule = EntityVisibilityRule(
            scope=VisibilityScope.NONE,
            filter_by=None,
            additional_filters={},
        )
        story_id = StoryId(value="story-123")

        result = await checker.check_story_access(story_id, "user-456", rule)

        assert result.was_denied() is True
        assert "no story access" in result.get_denial_reason().lower()

    @pytest.mark.asyncio
    async def test_check_story_access_assigned_scope_grants_when_assigned(
        self,
        checker: AuthorizationChecker,
        mock_story_auth_port: AsyncMock,
    ) -> None:
        """Test ASSIGNED scope grants access when story is assigned to user."""
        rule = EntityVisibilityRule(
            scope=VisibilityScope.ASSIGNED,
            filter_by="user_id",
            additional_filters={},
        )
        story_id = StoryId(value="story-123")
        user_id = "user-456"

        # Mock: Story IS assigned to user
        mock_story_auth_port.is_story_assigned_to_user.return_value = True

        result = await checker.check_story_access(story_id, user_id, rule)

        assert result.was_granted() is True
        mock_story_auth_port.is_story_assigned_to_user.assert_called_once_with(story_id, user_id)

    @pytest.mark.asyncio
    async def test_check_story_access_assigned_scope_denies_when_not_assigned(
        self,
        checker: AuthorizationChecker,
        mock_story_auth_port: AsyncMock,
    ) -> None:
        """Test ASSIGNED scope denies access when story is NOT assigned to user."""
        rule = EntityVisibilityRule(
            scope=VisibilityScope.ASSIGNED,
            filter_by="user_id",
            additional_filters={},
        )
        story_id = StoryId(value="story-123")
        user_id = "user-456"

        # Mock: Story is NOT assigned to user
        mock_story_auth_port.is_story_assigned_to_user.return_value = False

        result = await checker.check_story_access(story_id, user_id, rule)

        assert result.was_denied() is True
        assert "not assigned to user" in result.get_denial_reason().lower()

    @pytest.mark.asyncio
    async def test_check_story_access_epic_children_scope_grants_when_epic_assigned(
        self,
        checker: AuthorizationChecker,
        mock_story_auth_port: AsyncMock,
    ) -> None:
        """Test EPIC_CHILDREN scope grants access when epic is assigned to user."""
        rule = EntityVisibilityRule(
            scope=VisibilityScope.EPIC_CHILDREN,
            filter_by="epic_id",
            additional_filters={},
        )
        story_id = StoryId(value="story-123")
        user_id = "user-456"
        epic_id = EpicId(value="epic-789")

        # Mock: Epic IS assigned to user
        mock_story_auth_port.get_epic_for_story.return_value = epic_id
        mock_story_auth_port.is_epic_assigned_to_user.return_value = True

        result = await checker.check_story_access(story_id, user_id, rule)

        assert result.was_granted() is True
        mock_story_auth_port.get_epic_for_story.assert_called_once_with(story_id)
        mock_story_auth_port.is_epic_assigned_to_user.assert_called_once_with(epic_id, user_id)

    @pytest.mark.asyncio
    async def test_check_story_access_epic_children_scope_denies_when_epic_not_assigned(
        self,
        checker: AuthorizationChecker,
        mock_story_auth_port: AsyncMock,
    ) -> None:
        """Test EPIC_CHILDREN scope denies access when epic is NOT assigned to user."""
        rule = EntityVisibilityRule(
            scope=VisibilityScope.EPIC_CHILDREN,
            filter_by="epic_id",
            additional_filters={},
        )
        story_id = StoryId(value="story-123")
        user_id = "user-456"
        epic_id = EpicId(value="epic-789")

        # Mock: Epic is NOT assigned to user
        mock_story_auth_port.get_epic_for_story.return_value = epic_id
        mock_story_auth_port.is_epic_assigned_to_user.return_value = False

        result = await checker.check_story_access(story_id, user_id, rule)

        assert result.was_denied() is True
        assert "epic" in result.get_denial_reason().lower()
        assert "not assigned" in result.get_denial_reason().lower()

    @pytest.mark.asyncio
    async def test_check_story_access_testing_phase_scope_grants_when_in_testing(
        self,
        checker: AuthorizationChecker,
        mock_story_auth_port: AsyncMock,
    ) -> None:
        """Test TESTING_PHASE scope grants access when story is in testing."""
        rule = EntityVisibilityRule(
            scope=VisibilityScope.TESTING_PHASE,
            filter_by="status",
            additional_filters={},
        )
        story_id = StoryId(value="story-123")

        # Mock: Story IS in testing phase
        mock_story_auth_port.is_story_in_testing_phase.return_value = True

        result = await checker.check_story_access(story_id, "user-456", rule)

        assert result.was_granted() is True
        mock_story_auth_port.is_story_in_testing_phase.assert_called_once_with(story_id)

    @pytest.mark.asyncio
    async def test_check_story_access_testing_phase_scope_denies_when_not_in_testing(
        self,
        checker: AuthorizationChecker,
        mock_story_auth_port: AsyncMock,
    ) -> None:
        """Test TESTING_PHASE scope denies access when story is NOT in testing."""
        rule = EntityVisibilityRule(
            scope=VisibilityScope.TESTING_PHASE,
            filter_by="status",
            additional_filters={},
        )
        story_id = StoryId(value="story-123")

        # Mock: Story is NOT in testing phase
        mock_story_auth_port.is_story_in_testing_phase.return_value = False

        result = await checker.check_story_access(story_id, "user-456", rule)

        assert result.was_denied() is True
        assert "not in testing phase" in result.get_denial_reason().lower()

