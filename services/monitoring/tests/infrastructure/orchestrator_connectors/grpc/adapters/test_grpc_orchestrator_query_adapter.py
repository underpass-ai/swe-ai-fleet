"""Tests for GrpcOrchestratorQueryAdapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.monitoring.domain.entities.orchestrator.orchestrator_info import OrchestratorInfo
from services.monitoring.infrastructure.orchestrator_connectors.grpc.adapters.grpc_orchestrator_query_adapter import (
    GrpcOrchestratorQueryAdapter,
)


class TestGrpcOrchestratorQueryAdapter:
    """Test cases for GrpcOrchestratorQueryAdapter."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_mapper = MagicMock()
        self.orchestrator_address = "localhost:50055"
    
    @patch('grpc.aio.insecure_channel')
    def test_adapter_initialization(self, mock_channel):
        """Test adapter initialization with injected dependencies."""
        mock_channel.return_value = MagicMock()
        
        adapter = GrpcOrchestratorQueryAdapter(self.orchestrator_address, self.mock_mapper)
        
        assert adapter.orchestrator_address == self.orchestrator_address
        assert adapter.mapper == self.mock_mapper
        assert adapter.channel is not None
        assert adapter._connected is True
        mock_channel.assert_called_once_with(self.orchestrator_address)
    
    @patch('grpc.aio.insecure_channel')
    def test_close_connection(self, mock_channel):
        """Test connection closure."""
        mock_channel.return_value = MagicMock()
        adapter = GrpcOrchestratorQueryAdapter(self.orchestrator_address, self.mock_mapper)
        mock_channel_instance = MagicMock()
        adapter.channel = mock_channel_instance
        adapter._connected = True
        
        adapter._close_connection()
        
        assert adapter._connected is False
        mock_channel_instance.close.assert_called_once()
    
    @patch('grpc.aio.insecure_channel')
    def test_close_connection_no_channel(self, mock_channel):
        """Test connection closure when no channel exists."""
        mock_channel.return_value = MagicMock()
        adapter = GrpcOrchestratorQueryAdapter(self.orchestrator_address, self.mock_mapper)
        adapter.channel = None
        
        # Should not raise an error
        adapter._close_connection()
        
        assert adapter._connected is False
    
    @pytest.mark.asyncio
    @patch('grpc.aio.insecure_channel')
    async def test_get_orchestrator_info_success(self, mock_channel):
        """Test successful orchestrator info retrieval."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.councils = []
        
        # Setup mock mapper
        expected_orchestrator_info = OrchestratorInfo.create_connected_orchestrator([])
        self.mock_mapper.proto_to_domain.return_value = expected_orchestrator_info
        
        mock_channel.return_value = MagicMock()
        adapter = GrpcOrchestratorQueryAdapter(self.orchestrator_address, self.mock_mapper)
        
        # Mock the gRPC call with AsyncMock
        with patch('builtins.__import__') as mock_import:
            mock_gen_module = MagicMock()
            mock_stub = AsyncMock()
            mock_stub.ListCouncils.return_value = mock_response
            mock_gen_module.orchestrator_pb2_grpc.OrchestratorServiceStub.return_value = mock_stub
            mock_import.side_effect = lambda name, *args: mock_gen_module if name == 'gen' else __import__(name, *args)
            
            result = await adapter.get_orchestrator_info()
            
            assert result == expected_orchestrator_info
            self.mock_mapper.proto_to_domain.assert_called_once_with(mock_response)
    
    @pytest.mark.asyncio
    @patch('grpc.aio.insecure_channel')
    async def test_get_orchestrator_info_grpc_error(self, mock_channel):
        """Test orchestrator info retrieval with gRPC error."""
        import grpc
        
        # Setup mock mapper for error case
        error_orchestrator_info = OrchestratorInfo.create_disconnected_orchestrator("gRPC error")
        self.mock_mapper.create_disconnected_orchestrator.return_value = error_orchestrator_info
        
        mock_channel.return_value = MagicMock()
        adapter = GrpcOrchestratorQueryAdapter(self.orchestrator_address, self.mock_mapper)
        
        # Mock gRPC error
        with patch('builtins.__import__') as mock_import:
            mock_gen_module = MagicMock()
            mock_stub = AsyncMock()
            mock_rpc_error = grpc.RpcError("Connection failed")
            mock_rpc_error.details = lambda: "Connection failed"
            mock_stub.ListCouncils.side_effect = mock_rpc_error
            mock_gen_module.orchestrator_pb2_grpc.OrchestratorServiceStub.return_value = mock_stub
            mock_import.side_effect = lambda name, *args: mock_gen_module if name == 'gen' else __import__(name, *args)
            
            result = await adapter.get_orchestrator_info()
            
            assert result == error_orchestrator_info
            self.mock_mapper.create_disconnected_orchestrator.assert_called_once_with(
                error="gRPC error: Connection failed"
            )
    
    @pytest.mark.asyncio
    @patch('grpc.aio.insecure_channel')
    async def test_is_orchestrator_available_success(self, mock_channel):
        """Test successful orchestrator availability check."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.councils = []
        
        # Setup mock mapper
        expected_orchestrator_info = OrchestratorInfo.create_connected_orchestrator([])
        self.mock_mapper.proto_to_domain.return_value = expected_orchestrator_info
        
        mock_channel.return_value = MagicMock()
        adapter = GrpcOrchestratorQueryAdapter(self.orchestrator_address, self.mock_mapper)
        
        # Mock the gRPC call
        with patch('builtins.__import__') as mock_import:
            mock_gen_module = MagicMock()
            mock_stub = AsyncMock()
            mock_stub.ListCouncils.return_value = mock_response
            mock_gen_module.orchestrator_pb2_grpc.OrchestratorServiceStub.return_value = mock_stub
            mock_import.side_effect = lambda name, *args: mock_gen_module if name == 'gen' else __import__(name, *args)
            
            result = await adapter.is_orchestrator_available()
            
            assert result is True
            self.mock_mapper.proto_to_domain.assert_called_once_with(mock_response)
    
    @pytest.mark.asyncio
    @patch('grpc.aio.insecure_channel')
    async def test_is_orchestrator_available_failure(self, mock_channel):
        """Test orchestrator availability check failure."""
        mock_channel.return_value = MagicMock()
        adapter = GrpcOrchestratorQueryAdapter(self.orchestrator_address, self.mock_mapper)
        
        # Mock gRPC error
        with patch('builtins.__import__') as mock_import:
            mock_gen_module = MagicMock()
            mock_stub = AsyncMock()
            mock_stub.ListCouncils.side_effect = Exception("Connection failed")
            mock_gen_module.orchestrator_pb2_grpc.OrchestratorServiceStub.return_value = mock_stub
            mock_import.side_effect = lambda name, *args: mock_gen_module if name == 'gen' else __import__(name, *args)
            
            result = await adapter.is_orchestrator_available()
            
            assert result is False
    
    @pytest.mark.asyncio
    @patch('grpc.aio.insecure_channel')
    async def test_get_connection_status(self, mock_channel):
        """Test connection status retrieval."""
        mock_channel.return_value = MagicMock()
        adapter = GrpcOrchestratorQueryAdapter(self.orchestrator_address, self.mock_mapper)
        
        # Initially connected (due to constructor)
        assert await adapter.get_connection_status() is True
        
        # Simulate disconnection
        adapter._connected = False
        
        assert await adapter.get_connection_status() is False
    
    @pytest.mark.asyncio
    @patch('grpc.aio.insecure_channel')
    async def test_context_manager(self, mock_channel):
        """Test adapter as async context manager."""
        mock_channel.return_value = MagicMock()
        adapter = GrpcOrchestratorQueryAdapter(self.orchestrator_address, self.mock_mapper)
        
        async with adapter as ctx_adapter:
            assert ctx_adapter is adapter
            assert adapter._connected is True
            assert adapter.channel is not None
        
        # After context exit, connection should be closed
        assert adapter._connected is False