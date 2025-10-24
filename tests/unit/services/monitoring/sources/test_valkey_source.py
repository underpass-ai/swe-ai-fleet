"""
Tests for ValKey Source monitoring module.

Tests with proper mocking to avoid external dependencies and ensure fast execution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from services.monitoring.sources.valkey_source import ValKeySource


class TestValKeySource:
    """Test ValKey monitoring source with mocks."""

    def test_initialization(self):
        """Test ValKey source initialization."""
        source = ValKeySource()
        
        assert source.client is None
        assert "valkey.swe-ai-fleet.svc.cluster.local:6379" in source.url

    def test_initialization_with_env_var(self):
        """Test ValKey source initialization with environment variable."""
        with patch.dict('os.environ', {'VALKEY_URL': 'redis://custom:6380'}):
            source = ValKeySource()
            
            assert source.url == "redis://custom:6380"

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to ValKey."""
        source = ValKeySource()
        
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        
        with patch('redis.asyncio.from_url', return_value=mock_client) as mock_from_url:
            await source.connect()
            
            assert source.client == mock_client
            mock_from_url.assert_called_once_with(source.url, decode_responses=True)
            mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_import_error(self):
        """Test connection when redis package is not available."""
        source = ValKeySource()
        
        with patch('redis.asyncio', side_effect=ImportError("No module named 'redis'")):
            await source.connect()
            
            assert source.client is None

    @pytest.mark.asyncio
    async def test_connect_exception(self):
        """Test connection failure due to exception."""
        source = ValKeySource()
        
        with patch('redis.asyncio.from_url', side_effect=Exception("Connection failed")):
            await source.connect()
            
            assert source.client is None

    @pytest.mark.asyncio
    async def test_close_with_client(self):
        """Test close when client exists."""
        source = ValKeySource()
        mock_client = AsyncMock()
        source.client = mock_client
        
        await source.close()
        
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_client(self):
        """Test close when client is None."""
        source = ValKeySource()
        source.client = None
        
        # Should not raise exception
        await source.close()

    @pytest.mark.asyncio
    async def test_get_memory_stats_no_client(self):
        """Test get_memory_stats when client is not initialized."""
        source = ValKeySource()
        source.client = None
        
        result = await source.get_memory_stats()
        
        assert result["used_memory"] == 0
        assert result["max_memory"] == 0
        assert result["memory_usage_percent"] == 0.0

    @pytest.mark.asyncio
    async def test_get_memory_stats_success(self):
        """Test successful get_memory_stats."""
        source = ValKeySource()
        
        mock_client = AsyncMock()
        mock_client.info.return_value = {
            "used_memory": 1024000,  # 1MB in bytes
            "maxmemory": 10485760,   # 10MB in bytes
            "used_memory_rss": 2048000
        }
        source.client = mock_client
        
        result = await source.get_memory_stats()
        
        assert result["used_memory"] == 1024000
        assert result["max_memory"] == 10485760
        assert result["memory_usage_percent"] == 9.77  # 1024000 / 10485760 * 100

    @pytest.mark.asyncio
    async def test_get_memory_stats_exception(self):
        """Test get_memory_stats when exception occurs."""
        source = ValKeySource()
        
        mock_client = AsyncMock()
        mock_client.info.side_effect = Exception("Redis error")
        source.client = mock_client
        
        result = await source.get_memory_stats()
        
        assert result["used_memory"] == 0
        assert result["max_memory"] == 0
        assert result["memory_usage_percent"] == 0.0

    @pytest.mark.asyncio
    async def test_get_info_no_client(self):
        """Test get_info when client is not initialized."""
        source = ValKeySource()
        source.client = None
        
        result = await source.get_info()
        
        assert result["redis_version"] == "unknown"
        assert result["connected_clients"] == 0
        assert result["total_commands_processed"] == 0

    @pytest.mark.asyncio
    async def test_get_info_success(self):
        """Test successful get_info."""
        source = ValKeySource()
        
        mock_client = AsyncMock()
        mock_client.info.return_value = {
            "redis_version": "7.0.0",
            "connected_clients": 5,
            "total_commands_processed": 1000,
            "uptime_in_seconds": 3600
        }
        source.client = mock_client
        
        result = await source.get_info()
        
        assert result["redis_version"] == "7.0.0"
        assert result["connected_clients"] == 5
        assert result["total_commands_processed"] == 1000

    @pytest.mark.asyncio
    async def test_get_keyspace_stats_no_client(self):
        """Test get_keyspace_stats when client is not initialized."""
        source = ValKeySource()
        source.client = None
        
        result = await source.get_keyspace_stats()
        
        assert "error" in result
        assert result["error"] == "ValKey client not initialized"

    @pytest.mark.asyncio
    async def test_get_keyspace_stats_success(self):
        """Test successful get_keyspace_stats."""
        source = ValKeySource()
        
        mock_client = AsyncMock()
        mock_client.info.return_value = {
            "db0": {
                "keys": 100,
                "expires": 10,
                "avg_ttl": 3600
            }
        }
        source.client = mock_client
        
        result = await source.get_keyspace_stats()
        
        assert "db0" in result
        assert result["db0"]["keys"] == 100
        assert result["db0"]["expires"] == 10
        assert result["db0"]["avg_ttl"] == 3600

    @pytest.mark.asyncio
    async def test_get_client_stats_no_client(self):
        """Test get_client_stats when client is not initialized."""
        source = ValKeySource()
        source.client = None
        
        result = await source.get_client_stats()
        
        assert result["connected_clients"] == 0
        assert result["blocked_clients"] == 0

    @pytest.mark.asyncio
    async def test_get_client_stats_success(self):
        """Test successful get_client_stats."""
        source = ValKeySource()
        
        mock_client = AsyncMock()
        mock_client.info.return_value = {
            "connected_clients": 3,
            "blocked_clients": 1,
            "client_recent_max_input_buffer": 1024
        }
        source.client = mock_client
        
        result = await source.get_client_stats()
        
        assert result["connected_clients"] == 3
        assert result["blocked_clients"] == 1

    def test_has_required_methods(self):
        """Test that ValKeySource has all required methods."""
        source = ValKeySource()
        
        required_methods = ['connect', 'close', 'get_memory_stats', 'get_info', 'get_keyspace_stats', 'get_client_stats']
        for method in required_methods:
            assert hasattr(source, method), f"Missing method: {method}"
            assert callable(getattr(source, method)), f"Method {method} is not callable"