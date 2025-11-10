"""Tests for NATSStreamAdapter."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from services.monitoring.domain.entities import PullSubscribeRequest
from services.monitoring.infrastructure.stream_connectors.nats.adapters.nats_stream_adapter import (
    NATSStreamAdapter,
)


class TestNATSStreamAdapter:
    """Test suite for NATSStreamAdapter."""
    
    def test_creation(self):
        """Test creating adapter."""
        adapter = NATSStreamAdapter()
        
        assert adapter.js is None
    
    def test_creation_with_context(self):
        """Test creating adapter with context."""
        mock_js = MagicMock()
        adapter = NATSStreamAdapter(js_context=mock_js)
        
        assert adapter.js is mock_js
    
    def test_set_context(self):
        """Test setting JetStream context."""
        adapter = NATSStreamAdapter()
        mock_js = MagicMock()
        
        adapter.set_context(mock_js)
        
        assert adapter.js is mock_js
    
    @pytest.mark.asyncio
    async def test_pull_subscribe_success(self):
        """Test pull subscribe."""
        mock_js = AsyncMock()
        mock_consumer = MagicMock()
        mock_js.pull_subscribe.return_value = mock_consumer
        
        adapter = NATSStreamAdapter(js_context=mock_js)
        request = PullSubscribeRequest.create(
            subject="events.>",
            stream="orders",
            durable="durable-1"
        )
        result = await adapter.pull_subscribe(request)
        
        mock_js.pull_subscribe.assert_called_once_with(
            "events.>",
            stream="orders",
            durable="durable-1"
        )
        assert result is mock_consumer
    
    @pytest.mark.asyncio
    async def test_pull_subscribe_not_connected(self):
        """Test pull subscribe when not connected."""
        adapter = NATSStreamAdapter()
        request = PullSubscribeRequest.create(
            subject="events.>",
            stream="orders"
        )
        
        with pytest.raises(RuntimeError, match="not set"):
            await adapter.pull_subscribe(request)
    
    @pytest.mark.asyncio
    async def test_subscribe_basic(self):
        """Test basic subscribe."""
        mock_js = AsyncMock()
        mock_consumer = MagicMock()
        mock_js.subscribe.return_value = mock_consumer
        
        adapter = NATSStreamAdapter(js_context=mock_js)
        result = await adapter.subscribe("events.>")
        
        mock_js.subscribe.assert_called_once_with("events.>")
        assert result is mock_consumer
    
    @pytest.mark.asyncio
    async def test_subscribe_with_stream(self):
        """Test subscribe with stream."""
        mock_js = AsyncMock()
        mock_consumer = MagicMock()
        mock_js.subscribe.return_value = mock_consumer
        
        adapter = NATSStreamAdapter(js_context=mock_js)
        result = await adapter.subscribe("events.>", stream="orders")
        
        mock_js.subscribe.assert_called_once_with("events.>", stream="orders")
        assert result is mock_consumer
    
    @pytest.mark.asyncio
    async def test_subscribe_ordered_consumer(self):
        """Test subscribe with ordered consumer."""
        mock_js = AsyncMock()
        mock_consumer = MagicMock()
        mock_js.subscribe.return_value = mock_consumer
        
        adapter = NATSStreamAdapter(js_context=mock_js)
        await adapter.subscribe(
            "events.>",
            stream="orders",
            ordered_consumer=True
        )
        
        mock_js.subscribe.assert_called_once_with(
            "events.>",
            stream="orders",
            ordered_consumer=True
        )
    
    @pytest.mark.asyncio
    async def test_subscribe_not_connected(self):
        """Test subscribe when not connected."""
        adapter = NATSStreamAdapter()
        
        with pytest.raises(RuntimeError, match="not set"):
            await adapter.subscribe("events.>")
    
    @pytest.mark.asyncio
    async def test_create_durable_consumer_success(self):
        """Test creating durable consumer."""
        mock_js = AsyncMock()
        mock_consumer = MagicMock()
        mock_js.pull_subscribe.return_value = mock_consumer
        
        adapter = NATSStreamAdapter(js_context=mock_js)
        result = await adapter.create_durable_consumer(
            "orders.>",
            "orders",
            "monitoring-consumer"
        )
        
        mock_js.pull_subscribe.assert_called_once_with(
            "orders.>",
            stream="orders",
            durable="monitoring-consumer"
        )
        assert result is mock_consumer
    
    @pytest.mark.asyncio
    async def test_create_durable_consumer_not_connected(self):
        """Test creating durable consumer when not connected."""
        adapter = NATSStreamAdapter()
        
        with pytest.raises(RuntimeError, match="not set"):
            await adapter.create_durable_consumer("orders.>", "orders", "consumer-1")