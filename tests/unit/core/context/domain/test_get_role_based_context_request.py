"""Unit tests for GetRoleBasedContextRequest DTO."""

import pytest

from core.context.domain.role import Role
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.get_role_based_context_request import GetRoleBasedContextRequest


class TestGetRoleBasedContextRequestCreation:
    """Test GetRoleBasedContextRequest creation."""

    def test_create_minimal_request(self):
        """Test creating request with required fields only."""
        req = GetRoleBasedContextRequest(
            story_id=StoryId(value="story-123"),
            requesting_role=Role.DEVELOPER,
            user_id="user-456",
        )

        assert req.story_id.to_string() == "story-123"
        assert req.requesting_role == Role.DEVELOPER
        assert req.user_id == "user-456"
        assert req.include_timeline is True  # Default
        assert req.include_summaries is True  # Default
        assert req.timeline_events == 50  # Default

    def test_create_with_all_fields(self):
        """Test creating request with all optional fields."""
        req = GetRoleBasedContextRequest(
            story_id=StoryId(value="story-789"),
            requesting_role=Role.ARCHITECT,
            user_id="user-999",
            include_timeline=False,
            include_summaries=False,
            timeline_events=100,
        )

        assert req.include_timeline is False
        assert req.include_summaries is False
        assert req.timeline_events == 100


class TestGetRoleBasedContextRequestValidation:
    """Test GetRoleBasedContextRequest validation (fail-fast)."""

    def test_empty_user_id_raises_error(self):
        """Test empty user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id is required"):
            GetRoleBasedContextRequest(
                story_id=StoryId(value="story-123"),
                requesting_role=Role.DEVELOPER,
                user_id="",
            )

    def test_negative_timeline_events_raises_error(self):
        """Test negative timeline_events raises ValueError."""
        with pytest.raises(ValueError, match="timeline_events must be >= 0"):
            GetRoleBasedContextRequest(
                story_id=StoryId(value="story-123"),
                requesting_role=Role.DEVELOPER,
                user_id="user-123",
                timeline_events=-10,
            )

    def test_zero_timeline_events_is_allowed(self):
        """Test zero timeline_events is allowed (means no timeline)."""
        req = GetRoleBasedContextRequest(
            story_id=StoryId(value="story-123"),
            requesting_role=Role.DEVELOPER,
            user_id="user-123",
            timeline_events=0,
        )

        assert req.timeline_events == 0


class TestGetRoleBasedContextRequestImmutability:
    """Test GetRoleBasedContextRequest is immutable."""

    def test_cannot_modify_story_id(self):
        """Test story_id cannot be modified."""
        req = GetRoleBasedContextRequest(
            story_id=StoryId(value="story-123"),
            requesting_role=Role.DEVELOPER,
            user_id="user-456",
        )

        with pytest.raises(AttributeError):
            req.story_id = StoryId(value="hacked-story")  # type: ignore

    def test_cannot_modify_role(self):
        """Test requesting_role cannot be modified."""
        req = GetRoleBasedContextRequest(
            story_id=StoryId(value="story-123"),
            requesting_role=Role.DEVELOPER,
            user_id="user-456",
        )

        with pytest.raises(AttributeError):
            req.requesting_role = Role.ADMIN  # type: ignore


class TestGetRoleBasedContextRequestEdgeCases:
    """Test edge cases for GetRoleBasedContextRequest."""

    def test_whitespace_user_id_allowed(self):
        """Test user_id with whitespace is allowed (validation is minimal)."""
        # Note: Real validation would trim, but this DTO accepts as-is
        req = GetRoleBasedContextRequest(
            story_id=StoryId(value="story-123"),
            requesting_role=Role.DEVELOPER,
            user_id="   ",  # Only whitespace - allowed
        )

        assert req.user_id == "   "

    def test_very_large_timeline_events_allowed(self):
        """Test very large timeline_events value is allowed."""
        req = GetRoleBasedContextRequest(
            story_id=StoryId(value="story-123"),
            requesting_role=Role.DEVELOPER,
            user_id="user-456",
            timeline_events=10000,
        )

        assert req.timeline_events == 10000

    def test_different_roles_allowed(self):
        """Test all roles can be used in request."""
        story_id = StoryId(value="story-123")
        user_id = "user-456"

        for role in Role:
            req = GetRoleBasedContextRequest(
                story_id=story_id,
                requesting_role=role,
                user_id=user_id,
            )
            assert req.requesting_role == role

