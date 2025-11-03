"""Unit tests for ValkeyStorageAdapter - Configuration and key generation."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from planning.domain import StoryId, StoryState, StoryStateEnum
from planning.infrastructure.adapters.valkey_adapter import ValkeyConfig, ValkeyStorageAdapter
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

        result = adapter._list_stories_sync(state_filter=None, limit=100, offset=0)

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
        adapter._list_stories_sync(state_filter=None, limit=3, offset=2)

        # Should have called smembers once
        mock_redis_instance.smembers.assert_called_once_with("planning:stories:all")

        # Should have attempted to retrieve 3 stories (offset 2, limit 3)
        # Actual retrieval depends on mocked hgetall returning empty
        assert mock_redis_instance.hgetall.call_count == 3

