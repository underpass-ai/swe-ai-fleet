"""Unit tests for DataAccessLogEntry Value Object."""

from datetime import datetime, timedelta

import pytest
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.role import Role
from core.context.domain.value_objects.data_access_log_entry import DataAccessLogEntry


class TestDataAccessLogEntryCreation:
    """Test DataAccessLogEntry creation and validation."""

    def test_create_granted_entry_success(self):
        """Test creating granted access log entry."""
        log_entry = DataAccessLogEntry(
            user_id="user-123",
            role=Role.DEVELOPER,
            story_id=StoryId(value="story-456"),
            accessed_at=datetime.now(),
            accessed_entities={"task": 5, "decision": 3},
            access_granted=True,
        )

        assert log_entry.user_id == "user-123"
        assert log_entry.role == Role.DEVELOPER
        assert log_entry.story_id.to_string() == "story-456"
        assert log_entry.access_granted is True
        assert log_entry.denial_reason is None

    def test_create_denied_entry_with_reason(self):
        """Test creating denied access log entry with reason."""
        log_entry = DataAccessLogEntry(
            user_id="user-999",
            role=Role.QA,
            story_id=StoryId(value="story-secret"),
            accessed_at=datetime.now(),
            accessed_entities={},
            access_granted=False,
            denial_reason="Story not assigned to user",
        )

        assert log_entry.access_granted is False
        assert log_entry.denial_reason == "Story not assigned to user"

    def test_create_with_optional_fields(self):
        """Test creating log entry with optional fields."""
        log_entry = DataAccessLogEntry(
            user_id="user-123",
            role=Role.ARCHITECT,
            story_id=StoryId(value="story-789"),
            accessed_at=datetime.now(),
            accessed_entities={"epic": 1},
            access_granted=True,
            source_ip="192.168.1.100",
            request_id="req-abc-123",
        )

        assert log_entry.source_ip == "192.168.1.100"
        assert log_entry.request_id == "req-abc-123"


class TestDataAccessLogEntryValidation:
    """Test DataAccessLogEntry validation (fail-fast)."""

    def test_empty_user_id_raises_error(self):
        """Test empty user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id is required"):
            DataAccessLogEntry(
                user_id="",
                role=Role.DEVELOPER,
                story_id=StoryId(value="story-123"),
                accessed_at=datetime.now(),
                accessed_entities={},
                access_granted=True,
            )

    def test_future_timestamp_raises_error(self):
        """Test future accessed_at raises ValueError."""
        future = datetime.now() + timedelta(hours=1)

        with pytest.raises(ValueError, match="cannot be in the future"):
            DataAccessLogEntry(
                user_id="user-123",
                role=Role.DEVELOPER,
                story_id=StoryId(value="story-123"),
                accessed_at=future,
                accessed_entities={},
                access_granted=True,
            )

    def test_denied_without_reason_raises_error(self):
        """Test denied access without reason raises ValueError."""
        with pytest.raises(ValueError, match="denial_reason is required"):
            DataAccessLogEntry(
                user_id="user-123",
                role=Role.DEVELOPER,
                story_id=StoryId(value="story-123"),
                accessed_at=datetime.now(),
                accessed_entities={},
                access_granted=False,
                denial_reason=None,  # Missing reason!
            )


class TestDataAccessLogEntryQueryMethods:
    """Test DataAccessLogEntry query methods (Tell, Don't Ask)."""

    def test_was_granted_returns_true_for_granted(self):
        """Test was_granted() returns True for granted access."""
        log_entry = DataAccessLogEntry(
            user_id="user-123",
            role=Role.DEVELOPER,
            story_id=StoryId(value="story-123"),
            accessed_at=datetime.now(),
            accessed_entities={},
            access_granted=True,
        )

        assert log_entry.was_granted() is True
        assert log_entry.was_denied() is False

    def test_was_denied_returns_true_for_denied(self):
        """Test was_denied() returns True for denied access."""
        log_entry = DataAccessLogEntry(
            user_id="user-123",
            role=Role.DEVELOPER,
            story_id=StoryId(value="story-123"),
            accessed_at=datetime.now(),
            accessed_entities={},
            access_granted=False,
            denial_reason="Not authorized",
        )

        assert log_entry.was_denied() is True
        assert log_entry.was_granted() is False

    def test_get_total_entities_accessed(self):
        """Test get_total_entities_accessed() calculates correctly."""
        log_entry = DataAccessLogEntry(
            user_id="user-123",
            role=Role.DEVELOPER,
            story_id=StoryId(value="story-123"),
            accessed_at=datetime.now(),
            accessed_entities={"task": 5, "decision": 3, "epic": 1},
            access_granted=True,
        )

        assert log_entry.get_total_entities_accessed() == 9  # 5 + 3 + 1


class TestDataAccessLogEntryImmutability:
    """Test DataAccessLogEntry is immutable (frozen=True)."""

    def test_cannot_modify_user_id(self):
        """Test user_id cannot be modified."""
        log_entry = DataAccessLogEntry(
            user_id="user-123",
            role=Role.DEVELOPER,
            story_id=StoryId(value="story-123"),
            accessed_at=datetime.now(),
            accessed_entities={},
            access_granted=True,
        )

        with pytest.raises(AttributeError):
            log_entry.user_id = "hacker-999"  # type: ignore

    def test_cannot_modify_access_granted(self):
        """Test access_granted cannot be modified."""
        log_entry = DataAccessLogEntry(
            user_id="user-123",
            role=Role.DEVELOPER,
            story_id=StoryId(value="story-123"),
            accessed_at=datetime.now(),
            accessed_entities={},
            access_granted=True,
        )

        with pytest.raises(AttributeError):
            log_entry.access_granted = False  # type: ignore

