"""Tests for GrpcOrchestratorQueryAdapter."""

from unittest.mock import MagicMock, patch

import pytest
from services.monitoring.domain.entities.orchestrator.orchestrator_info import OrchestratorInfo
from services.monitoring.infrastructure.orchestrator_connectors.grpc.adapters.grpc_orchestrator_query_adapter import (
    GrpcOrchestratorQueryAdapter,
)


class TestGrpcOrchestratorQueryAdapter:
    """Test cases for GrpcOrchestratorQueryAdapter."""
    
    def test_adapter_initialization(self):
        """Test adapter initialization with default address."""
        adapter = GrpcOrchestratorQueryAdapter()
        
        assert adapter.orchestrator_address == "orchestrator.swe-ai-fleet.svc.cluster.local:50055"
        assert adapter.channel is None
        assert adapter._connected is False
    
    def test_adapter_initialization_with_custom_address(self):
        """Test adapter initialization with custom address."""
        custom_address = "localhost:50055"
        adapter = GrpcOrchestratorQueryAdapter(custom_address)
        
        assert adapter.orchestrator_address == custom_address
        assert adapter.channel is None
        assert adapter._connected is False
    
    @patch('grpc.aio.insecure_channel')
    def test_ensure_connection_success(self, mock_channel):
        """Test successful connection establishment."""
        mock_channel.return_value = MagicMock()
        adapter = GrpcOrchestratorQueryAdapter()
        
        adapter._ensure_connection()
        
        assert adapter._connected is True
        assert adapter.channel is not None
        mock_channel.assert_called_once_with(adapter.orchestrator_address)
    
    @patch('grpc.aio.insecure_channel')
    def test_ensure_connection_failure(self, mock_channel):
        """Test connection establishment failure."""
        mock_channel.side_effect = Exception("Connection failed")
        adapter = GrpcOrchestratorQueryAdapter()
        
        with pytest.raises(ConnectionError, match="Failed to connect to orchestrator"):
            adapter._ensure_connection()
        
        assert adapter._connected is False
        assert adapter.channel is None
    
    def test_close_connection(self):
        """Test connection closure."""
        adapter = GrpcOrchestratorQueryAdapter()
        mock_channel = MagicMock()
        adapter.channel = mock_channel
        adapter._connected = True
        
        adapter._close_connection()
        
        assert adapter._connected is False
        assert adapter.channel is None
        mock_channel.close.assert_called_once()
    
    def test_close_connection_no_channel(self):
        """Test connection closure when no channel exists."""
        adapter = GrpcOrchestratorQueryAdapter()
        
        # Should not raise an error
        adapter._close_connection()
        
        assert adapter._connected is False
        assert adapter.channel is None
    
    @pytest.mark.asyncio
    @patch('grpc.aio.insecure_channel')
    async def test_get_orchestrator_info_connection_error(self, mock_channel):
        """Test orchestrator info retrieval with connection error."""
        # Setup mocks
        mock_channel.side_effect = Exception("Connection failed")
        
        adapter = GrpcOrchestratorQueryAdapter()
        
        result = await adapter.get_orchestrator_info()
        
        assert isinstance(result, OrchestratorInfo)
        assert result.is_connected() is False
        assert result.is_healthy() is False
        assert "Unexpected error" in result.connection_status.error
    
    @pytest.mark.asyncio
    @patch('grpc.aio.insecure_channel')
    async def test_is_orchestrator_available_failure(self, mock_channel):
        """Test orchestrator availability check failure."""
        # Setup mocks
        mock_channel.side_effect = Exception("Connection failed")
        
        adapter = GrpcOrchestratorQueryAdapter()
        
        result = await adapter.is_orchestrator_available()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_connection_status(self):
        """Test connection status retrieval."""
        adapter = GrpcOrchestratorQueryAdapter()
        
        # Initially not connected
        assert await adapter.get_connection_status() is False
        
        # Simulate connection
        adapter._connected = True
        adapter.channel = MagicMock()
        
        assert await adapter.get_connection_status() is True
    
    
    @pytest.mark.asyncio
    @patch('grpc.aio.insecure_channel')
    async def test_context_manager(self, mock_channel):
        """Test adapter as async context manager."""
        mock_channel.return_value = MagicMock()
        adapter = GrpcOrchestratorQueryAdapter()
        
        async with adapter as ctx_adapter:
            assert ctx_adapter is adapter
            assert adapter._connected is True
            assert adapter.channel is not None
        
        # After context exit, connection should be closed
        assert adapter._connected is False
        assert adapter.channel is None