"""Unit tests for ValkeyStorageAdapter - interface verification only.

Note: Full functionality testing of Valkey adapter requires integration tests
with real Valkey instance due to async Redis operations and serialization logic.
"""

import pytest
from unittest.mock import patch, AsyncMock

from planning.infrastructure.adapters.valkey_adapter import ValkeyStorageAdapter, ValkeyConfig


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
    with patch('redis.asyncio.from_url') as mock_from_url:
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client

        ValkeyStorageAdapter(config=valkey_config)

        # Verify Redis client was created with correct URL
        mock_from_url.assert_called_once()
        call_args = mock_from_url.call_args[0][0]
        assert call_args.startswith("redis://localhost:6379")


def test_valkey_adapter_has_required_methods(valkey_config):
    """Test ValkeyStorageAdapter has all required methods (interface verification)."""
    with patch('redis.asyncio.from_url'):
        adapter = ValkeyStorageAdapter(config=valkey_config)

        # Verify adapter has all required async methods
        assert hasattr(adapter, 'save_story')
        assert hasattr(adapter, 'get_story')
        assert hasattr(adapter, 'list_stories')
        assert hasattr(adapter, 'update_story')
        assert hasattr(adapter, 'delete_story')
        assert hasattr(adapter, 'close')

        # Verify they are async (except close)
        import inspect
        assert inspect.iscoroutinefunction(adapter.save_story)
        assert inspect.iscoroutinefunction(adapter.get_story)
        assert inspect.iscoroutinefunction(adapter.list_stories)
        assert inspect.iscoroutinefunction(adapter.update_story)
        assert inspect.iscoroutinefunction(adapter.delete_story)


@pytest.mark.asyncio
async def test_valkey_adapter_close(valkey_config):
    """Test close closes Redis connection."""
    with patch('redis.asyncio.from_url') as mock_from_url:
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client

        adapter = ValkeyStorageAdapter(config=valkey_config)
        adapter.close()

        mock_client.close.assert_awaited_once()
