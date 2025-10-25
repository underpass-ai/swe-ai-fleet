"""Tests for NATSConnectionAdapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.monitoring.infrastructure.stream_connectors.nats.adapters.nats_connection_adapter import (
    NATSConnectionAdapter,
)


class TestNATSConnectionAdapter:
    """Test suite for NATSConnectionAdapter."""
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection."""
        with patch("services.monitoring.infrastructure.stream_connectors.nats.adapters.nats_connection_adapter.nats.connect") as mock_nats:
            mock_nc = AsyncMock()
            mock_js = MagicMock()
            mock_nc.jetstream.return_value = mock_js
            mock_nats.return_value = mock_nc
            
            adapter = NATSConnectionAdapter("nats://localhost:4222")
            await adapter.connect()
            
            assert adapter.nc is not None
            assert adapter.js is not None
            mock_nats.assert_called_once_with("nats://localhost:4222")
    
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure."""
        with patch("services.monitoring.infrastructure.stream_connectors.nats.adapters.nats_connection_adapter.nats.connect") as mock_nats:
            mock_nats.side_effect = Exception("Connection refused")
            
            adapter = NATSConnectionAdapter("nats://invalid:9999")
            
            with pytest.raises(ConnectionError):
                await adapter.connect()
    
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnection."""
        with patch("services.monitoring.infrastructure.stream_connectors.nats.adapters.nats_connection_adapter.nats.connect") as mock_nats:
            mock_nc = AsyncMock()
            mock_js = MagicMock()
            mock_nc.jetstream.return_value = mock_js
            mock_nats.return_value = mock_nc
            
            adapter = NATSConnectionAdapter("nats://localhost:4222")
            await adapter.connect()
            await adapter.disconnect()
            
            mock_nc.close.assert_called_once()
            assert adapter.nc is None
            assert adapter.js is None
    
    @pytest.mark.asyncio
    async def test_is_connected_true(self):
        """Test is_connected when connected."""
        with patch("services.monitoring.infrastructure.stream_connectors.nats.adapters.nats_connection_adapter.nats.connect") as mock_nats:
            mock_nc = AsyncMock()
            mock_nc.is_connected = True
            mock_js = MagicMock()
            mock_nc.jetstream.return_value = mock_js
            mock_nats.return_value = mock_nc
            
            adapter = NATSConnectionAdapter("nats://localhost:4222")
            await adapter.connect()
            
            assert await adapter.is_connected() is True
    
    @pytest.mark.asyncio
    async def test_is_connected_false(self):
        """Test is_connected when not connected."""
        adapter = NATSConnectionAdapter("nats://localhost:4222")
        
        assert await adapter.is_connected() is False
    
    def test_get_stream_context_success(self):
        """Test getting stream context."""
        adapter = NATSConnectionAdapter("nats://localhost:4222")
        adapter.js = MagicMock()
        
        context = adapter.get_stream_context()
        
        assert context is adapter.js
    
    def test_get_stream_context_not_connected(self):
        """Test getting stream context when not connected."""
        adapter = NATSConnectionAdapter("nats://localhost:4222")
        
        with pytest.raises(RuntimeError, match="Not connected"):
            adapter.get_stream_context()
