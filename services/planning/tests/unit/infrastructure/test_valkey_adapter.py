"""Unit tests for ValkeyStorageAdapter - interface verification only.

Note: Full functionality testing of Valkey adapter requires integration tests
with real Valkey instance due to async Redis operations and serialization logic.
"""

from unittest.mock import AsyncMock, patch

import pytest
from planning.infrastructure.adapters.valkey_adapter import ValkeyStorageAdapter
from planning.infrastructure.adapters.valkey_config import ValkeyConfig


@pytest.fixture
def valkey_config():
    """Create Valkey configuration."""
    return ValkeyConfig(
        host="localhost",
        port=6379,
        db=0,
    )


@pytest.mark.asyncio
async def test_valkey_adapter_init(valkey_config):
    """Test ValkeyStorageAdapter initialization."""
    with patch('redis.Redis') as mock_redis_class:
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client

        ValkeyStorageAdapter(config=valkey_config)

        # Verify Redis client was created with correct parameters
        mock_redis_class.assert_called_once_with(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True,
        )
        mock_client.ping.assert_called_once()


def test_valkey_adapter_has_required_methods(valkey_config):
    """Test ValkeyStorageAdapter has all required methods (interface verification)."""
    with patch('redis.Redis') as mock_redis_class:
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)

        # Verify adapter has all required async methods (stories)
        assert hasattr(adapter, 'save_story')
        assert hasattr(adapter, 'get_story')
        assert hasattr(adapter, 'list_stories')
        assert hasattr(adapter, 'update_story')
        assert hasattr(adapter, 'delete_story')
        # Verify adapter has all required async methods (projects)
        assert hasattr(adapter, 'save_project')
        assert hasattr(adapter, 'get_project')
        assert hasattr(adapter, 'list_projects')
        assert hasattr(adapter, 'close')

        # Verify they are async (except close)
        import inspect
        assert inspect.iscoroutinefunction(adapter.save_story)
        assert inspect.iscoroutinefunction(adapter.get_story)
        assert inspect.iscoroutinefunction(adapter.list_stories)
        assert inspect.iscoroutinefunction(adapter.update_story)
        assert inspect.iscoroutinefunction(adapter.delete_story)
        assert inspect.iscoroutinefunction(adapter.save_project)
        assert inspect.iscoroutinefunction(adapter.get_project)
        assert inspect.iscoroutinefunction(adapter.list_projects)


@pytest.mark.asyncio
async def test_valkey_adapter_close(valkey_config):
    """Test close closes Redis connection."""
    with patch('redis.Redis') as mock_redis_class:
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)
        adapter.close()

        mock_client.close.assert_called_once()
