"""Unit tests for ValkeyStorageAdapter - Configuration and key generation."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from planning.domain import StoryId, StoryState, StoryStateEnum
from planning.infrastructure.adapters.valkey_adapter import ValkeyStorageAdapter
from planning.infrastructure.adapters.valkey_config import ValkeyConfig
from planning.infrastructure.adapters.valkey_keys import ValkeyKeys


class TestValkeyConfig:
    """Test Valkey configuration."""

    def test_default_config_from_environment(self):
        """Should create config with default values."""
        config = ValkeyConfig()

        assert config.host == "localhost"
        assert config.port == 6379
        assert config.db == 0
        assert config.decode_responses is True

    def test_custom_config(self):
        """Should accept custom configuration values."""
        config = ValkeyConfig(
            host="valkey.example.com",
            port=7000,
            db=1,
            decode_responses=False,
        )

        assert config.host == "valkey.example.com"
        assert config.port == 7000
        assert config.db == 1
        assert config.decode_responses is False

    def test_config_is_immutable(self):
        """Should be frozen dataclass (immutable)."""
        config = ValkeyConfig()

        with pytest.raises(Exception):  # FrozenInstanceError
            config.host = "modified-host"  # type: ignore


class TestValkeyAdapterKeyGeneration:
    """Test key generation methods (no Redis required)."""

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    def test_story_hash_key(self, mock_redis):
        """Should generate correct hash key for story."""
        mock_redis.return_value = MagicMock()
        mock_redis.return_value.ping.return_value = True

        adapter = ValkeyStorageAdapter(ValkeyConfig())
        story_id = StoryId("story-123")

        key = adapter._story_hash_key(story_id)

        assert key == "planning:story:story-123"
        assert key == ValkeyKeys.story_hash(story_id)

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    def test_story_state_key(self, mock_redis):
        """Should generate correct state key for story."""
        mock_redis.return_value = MagicMock()
        mock_redis.return_value.ping.return_value = True

        adapter = ValkeyStorageAdapter(ValkeyConfig())
        story_id = StoryId("story-456")

        key = adapter._story_state_key(story_id)

        assert key == "planning:story:story-456:state"
        assert key == ValkeyKeys.story_state(story_id)

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    def test_all_stories_set_key(self, mock_redis):
        """Should generate correct key for all stories set."""
        mock_redis.return_value = MagicMock()
        mock_redis.return_value.ping.return_value = True

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        key = adapter._all_stories_set_key()

        assert key == "planning:stories:all"
        assert key == ValkeyKeys.all_stories()

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    def test_stories_by_state_set_key(self, mock_redis):
        """Should generate correct key for state-filtered stories."""
        mock_redis.return_value = MagicMock()
        mock_redis.return_value.ping.return_value = True

        adapter = ValkeyStorageAdapter(ValkeyConfig())
        state = StoryState(StoryStateEnum.IN_PROGRESS)

        key = adapter._stories_by_state_set_key(state)

        assert key == "planning:stories:state:IN_PROGRESS"
        assert key == ValkeyKeys.stories_by_state(state)


class TestValkeyAdapterConnectionHandling:
    """Test connection handling."""

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    def test_initialization_pings_redis(self, mock_redis):
        """Should ping Redis during initialization."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        ValkeyStorageAdapter(ValkeyConfig())

        # Verify Redis client was created with correct params
        mock_redis.assert_called_once_with(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True,
        )

        # Verify ping was called to test connection
        mock_redis_instance.ping.assert_called_once()

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    def test_initialization_fails_on_connection_error(self, mock_redis):
        """Should raise exception if cannot connect to Redis."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.side_effect = ConnectionError("Cannot connect to Redis")

        with pytest.raises(ConnectionError, match="Cannot connect to Redis"):
            ValkeyStorageAdapter(ValkeyConfig())

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    def test_close_closes_connection(self, mock_redis):
        """Should close Redis connection when close() called."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        adapter = ValkeyStorageAdapter(ValkeyConfig())
        adapter.close()

        mock_redis_instance.close.assert_called_once()

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    def test_uses_custom_config(self, mock_redis):
        """Should use custom configuration."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        custom_config = ValkeyConfig(
            host="valkey.prod.example.com",
            port=7000,
            db=2,
            decode_responses=False,
        )

        adapter = ValkeyStorageAdapter(custom_config)

        mock_redis.assert_called_once_with(
            host="valkey.prod.example.com",
            port=7000,
            db=2,
            decode_responses=False,
        )

        assert adapter.config == custom_config


class TestValkeyAdapterGetStorySync:
    """Test synchronous get_story logic (called via asyncio.to_thread)."""

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    def test_get_story_sync_returns_none_when_not_found(self, mock_redis):
        """Should return None when story hash is empty."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.hgetall.return_value = {}  # Empty hash

        adapter = ValkeyStorageAdapter(ValkeyConfig())
        story_id = StoryId("nonexistent-123")

        result = adapter._get_story_sync(story_id)

        assert result is None
        mock_redis_instance.hgetall.assert_called_once_with("planning:story:nonexistent-123")


class TestValkeyAdapterListStoriesSync:
    """Test synchronous list_stories logic."""

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    def test_list_stories_sync_returns_empty_list_when_no_stories(self, mock_redis):
        """Should return empty StoryList when no stories exist."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.smembers.return_value = set()  # Empty set

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        result = adapter._list_stories_sync(state_filter=None, epic_id=None, limit=100, offset=0)

        assert result.count() == 0
        mock_redis_instance.smembers.assert_called_once_with("planning:stories:all")

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    def test_list_stories_sync_applies_pagination(self, mock_redis):
        """Should apply offset and limit correctly."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        # Mock 10 story IDs
        story_ids = {f"story-{i:03d}" for i in range(10)}
        mock_redis_instance.smembers.return_value = story_ids

        # Mock hgetall to return None (we're testing pagination, not retrieval)
        mock_redis_instance.hgetall.return_value = {}

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        # Request 3 stories starting from offset 2
        adapter._list_stories_sync(state_filter=None, epic_id=None, limit=3, offset=2)

        # Should have called smembers once
        mock_redis_instance.smembers.assert_called_once_with("planning:stories:all")

        # Should have attempted to retrieve 3 stories (offset 2, limit 3)
        # Actual retrieval depends on mocked hgetall returning empty
        assert mock_redis_instance.hgetall.call_count == 3


class TestValkeyAdapterSaveStory:
    """Test save_story method."""

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    @patch("planning.infrastructure.adapters.valkey_adapter.StoryValkeyMapper")
    async def test_save_story_persists_all_fields(self, mock_mapper, mock_redis):
        """Should persist story hash, state, and set memberships."""
        from datetime import UTC, datetime

        from planning.domain import DORScore, Story, StoryId, StoryState, StoryStateEnum
        from planning.domain.value_objects.actors.user_name import UserName
        from planning.domain.value_objects.content.brief import Brief
        from planning.domain.value_objects.content.title import Title
        from planning.domain.value_objects.identifiers.epic_id import EpicId

        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        story_data = {
            "story_id": "story-123",
            "epic_id": "epic-001",
            "title": "Test Story",
            "brief": "Test brief",
            "state": "DRAFT",
            "dor_score": "0",
            "created_by": "user-1",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        mock_mapper.to_dict.return_value = story_data

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        now = datetime.now(UTC)
        story = Story(
            epic_id=EpicId("epic-001"),
            story_id=StoryId("story-123"),
            title=Title("Test Story"),
            brief=Brief("Test brief"),
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by=UserName("user-1"),
            created_at=now,
            updated_at=now,
        )

        await adapter.save_story(story)

        # Verify mapper was called
        mock_mapper.to_dict.assert_called_once_with(story)

        # Verify Redis operations
        mock_redis_instance.hset.assert_called_once()
        mock_redis_instance.set.assert_called_once()
        assert mock_redis_instance.sadd.call_count == 3  # All stories + state set + epic set


class TestValkeyAdapterGetStory:
    """Test get_story methods."""

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    @patch("planning.infrastructure.adapters.valkey_adapter.asyncio.to_thread")
    async def test_get_story_calls_sync_method(self, mock_to_thread, mock_redis):
        """Should call sync method via asyncio.to_thread."""
        from planning.domain import StoryId

        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        async def mock_coro(*args, **kwargs):
            await asyncio.sleep(0)  # Use async feature
            return None

        mock_to_thread.side_effect = lambda *args, **kwargs: mock_coro()

        adapter = ValkeyStorageAdapter(ValkeyConfig())
        story_id = StoryId("story-123")

        await adapter.get_story(story_id)

        # Verify asyncio.to_thread was called
        assert mock_to_thread.called

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    @patch("planning.infrastructure.adapters.valkey_adapter.StoryValkeyMapper")
    def test_get_story_sync_returns_story_when_found(self, mock_mapper, mock_redis):
        """Should return Story when data exists."""
        from datetime import UTC, datetime

        from planning.domain import DORScore, Story, StoryId, StoryState, StoryStateEnum
        from planning.domain.value_objects.actors.user_name import UserName
        from planning.domain.value_objects.content.brief import Brief
        from planning.domain.value_objects.content.title import Title
        from planning.domain.value_objects.identifiers.epic_id import EpicId

        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        # Mock Redis hash data (bytes)
        story_data = {
            b"story_id": b"story-123",
            b"epic_id": b"epic-001",
            b"title": b"Test Story",
            b"brief": b"Test brief",
            b"state": b"DRAFT",
            b"dor_score": b"0",
            b"created_by": b"user-1",
            b"created_at": datetime.now(UTC).isoformat().encode("utf-8"),
            b"updated_at": datetime.now(UTC).isoformat().encode("utf-8"),
        }
        mock_redis_instance.hgetall.return_value = story_data

        now = datetime.now(UTC)
        expected_story = Story(
            epic_id=EpicId("epic-001"),
            story_id=StoryId("story-123"),
            title=Title("Test Story"),
            brief=Brief("Test brief"),
            state=StoryState(StoryStateEnum.DRAFT),
            dor_score=DORScore(0),
            created_by=UserName("user-1"),
            created_at=now,
            updated_at=now,
        )
        mock_mapper.from_dict.return_value = expected_story

        adapter = ValkeyStorageAdapter(ValkeyConfig())
        story_id = StoryId("story-123")

        result = adapter._get_story_sync(story_id)

        assert result == expected_story
        mock_mapper.from_dict.assert_called_once_with(story_data)


class TestValkeyAdapterListStories:
    """Test list_stories methods."""

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    @patch("planning.infrastructure.adapters.valkey_adapter.asyncio.to_thread")
    async def test_list_stories_calls_sync_method(self, mock_to_thread, mock_redis):
        """Should call sync method via asyncio.to_thread."""
        from planning.domain import StoryList, StoryState, StoryStateEnum

        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        async def mock_coro(*args, **kwargs):
            await asyncio.sleep(0)  # Use async feature
            return StoryList.from_list([])

        mock_to_thread.side_effect = lambda *args, **kwargs: mock_coro()

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        await adapter.list_stories()

        # Verify asyncio.to_thread was called
        assert mock_to_thread.called

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    @patch.object(ValkeyStorageAdapter, "_get_story_sync")
    def test_list_stories_sync_with_state_filter(self, mock_get_story, mock_redis):
        """Should filter by state when state_filter provided."""
        from planning.domain import Story, StoryId, StoryList, StoryState, StoryStateEnum

        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        # Mock state-filtered story IDs
        story_ids = {"story-1", "story-2"}
        mock_redis_instance.smembers.return_value = story_ids

        # Mock story retrieval
        mock_story = MagicMock(spec=Story)
        mock_get_story.return_value = mock_story

        adapter = ValkeyStorageAdapter(ValkeyConfig())
        state_filter = StoryState(StoryStateEnum.IN_PROGRESS)

        result = adapter._list_stories_sync(state_filter=state_filter, epic_id=None, limit=100, offset=0)

        assert isinstance(result, StoryList)
        # Verify state-filtered key was used
        mock_redis_instance.smembers.assert_called_once_with(
            "planning:stories:state:IN_PROGRESS"
        )

    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    @patch.object(ValkeyStorageAdapter, "_get_story_sync")
    def test_list_stories_sync_includes_existing_stories(
        self, mock_get_story, mock_redis
    ):
        """Should include stories that exist when retrieving."""
        from planning.domain import Story, StoryId, StoryList

        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        story_ids = {"story-1", "story-2"}
        mock_redis_instance.smembers.return_value = story_ids

        # Mock story retrieval - first exists, second doesn't
        mock_story = MagicMock(spec=Story)
        mock_get_story.side_effect = [
            mock_story,  # story-1 exists
            None,  # story-2 doesn't exist
        ]

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        result = adapter._list_stories_sync(state_filter=None, epic_id=None, limit=100, offset=0)

        assert isinstance(result, StoryList)
        assert mock_get_story.call_count == 2


class TestValkeyAdapterUpdateStory:
    """Test update_story method."""

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    @patch("planning.infrastructure.adapters.valkey_adapter.StoryValkeyMapper")
    async def test_update_story_updates_hash_and_state(self, mock_mapper, mock_redis):
        """Should update hash and state when state unchanged."""
        from datetime import UTC, datetime

        from planning.domain import DORScore, Story, StoryId, StoryState, StoryStateEnum
        from planning.domain.value_objects.actors.user_name import UserName
        from planning.domain.value_objects.content.brief import Brief
        from planning.domain.value_objects.content.title import Title
        from planning.domain.value_objects.identifiers.epic_id import EpicId

        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        story_data = {"story_id": "story-123", "state": "DRAFT"}
        mock_mapper.to_dict.return_value = story_data
        # Mock hmget return value: [state, epic_id]
        mock_redis_instance.hmget.return_value = ["DRAFT", "epic-001"]

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        now = datetime.now(UTC)
        story = Story(
            epic_id=EpicId("epic-001"),
            story_id=StoryId("story-123"),
            title=Title("Updated Story"),
            brief=Brief("Updated brief"),
            state=StoryState(StoryStateEnum.DRAFT),  # Same state
            dor_score=DORScore(0),
            created_by=UserName("user-1"),
            created_at=now,
            updated_at=now,
        )

        await adapter.update_story(story)

        # Verify hash was updated
        mock_redis_instance.hset.assert_called_once()
        # Verify state sets were NOT updated (state unchanged)
        mock_redis_instance.srem.assert_not_called()
        mock_redis_instance.sadd.assert_not_called()

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    @patch("planning.infrastructure.adapters.valkey_adapter.StoryValkeyMapper")
    async def test_update_story_updates_state_sets_when_state_changes(
        self, mock_mapper, mock_redis
    ):
        """Should update state sets when state changes."""
        from datetime import UTC, datetime

        from planning.domain import DORScore, Story, StoryId, StoryState, StoryStateEnum
        from planning.domain.value_objects.actors.user_name import UserName
        from planning.domain.value_objects.content.brief import Brief
        from planning.domain.value_objects.content.title import Title
        from planning.domain.value_objects.identifiers.epic_id import EpicId

        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        story_data = {"story_id": "story-123", "state": "IN_PROGRESS"}
        mock_mapper.to_dict.return_value = story_data
        # Mock hmget return value: [state, epic_id]
        mock_redis_instance.hmget.return_value = ["DRAFT", "epic-001"]

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        now = datetime.now(UTC)
        story = Story(
            epic_id=EpicId("epic-001"),
            story_id=StoryId("story-123"),
            title=Title("Updated Story"),
            brief=Brief("Updated brief"),
            state=StoryState(StoryStateEnum.IN_PROGRESS),  # Changed state
            dor_score=DORScore(0),
            created_by=UserName("user-1"),
            created_at=now,
            updated_at=now,
        )

        await adapter.update_story(story)

        # Verify state sets were updated
        mock_redis_instance.srem.assert_called_once()  # Remove from old state
        mock_redis_instance.sadd.assert_called_once()  # Add to new state


class TestValkeyAdapterDeleteStory:
    """Test delete_story method."""

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    async def test_delete_story_removes_all_data(self, mock_redis):
        """Should delete hash, state, and set memberships."""
        from planning.domain import StoryId, StoryState, StoryStateEnum

        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        # Mock hmget return value: [state, epic_id]
        mock_redis_instance.hmget.return_value = ["DRAFT", "epic-001"]

        adapter = ValkeyStorageAdapter(ValkeyConfig())
        story_id = StoryId("story-123")

        await adapter.delete_story(story_id)

        # Verify all deletions
        assert mock_redis_instance.delete.call_count == 2  # Hash + state
        mock_redis_instance.srem.assert_called()  # From all stories + state set

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.redis.Redis")
    async def test_delete_story_handles_missing_state(self, mock_redis):
        """Should handle deletion when state is not found."""
        from planning.domain import StoryId

        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        # Mock hmget return value: [state=None, epic_id=None]
        mock_redis_instance.hmget.return_value = [None, None]

        adapter = ValkeyStorageAdapter(ValkeyConfig())
        story_id = StoryId("story-123")

        await adapter.delete_story(story_id)

        # Should still delete hash and remove from all stories set
        assert mock_redis_instance.delete.call_count == 2
        # Should NOT try to remove from state set (state is None)
        # Only srem for all_stories_set should be called

