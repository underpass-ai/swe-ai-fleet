"""Tests for GetOrchestratorInfoUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from services.monitoring.application.usecases.orchestrator.get_orchestrator_info_usecase import (
    GetOrchestratorInfoUseCase,
)
from services.monitoring.domain.entities.orchestrator.orchestrator_info import OrchestratorInfo


class TestGetOrchestratorInfoUseCase:
    """Test cases for GetOrchestratorInfoUseCase."""
    
    def test_initialization(self):
        """Test use case initialization with dependencies."""
        mock_query_port = MagicMock()
        use_case = GetOrchestratorInfoUseCase(mock_query_port)
        
        assert use_case._orchestrator_query is mock_query_port
    
    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful orchestrator info retrieval."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_orchestrator_info = MagicMock(spec=OrchestratorInfo)
        mock_query_port.get_orchestrator_info.return_value = mock_orchestrator_info
        
        # Execute use case
        use_case = GetOrchestratorInfoUseCase(mock_query_port)
        result = await use_case.execute()
        
        # Verify
        assert result is mock_orchestrator_info
        mock_query_port.get_orchestrator_info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_with_connection_error(self):
        """Test orchestrator info retrieval with connection error."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_query_port.get_orchestrator_info.side_effect = ConnectionError("Orchestrator not available")
        
        # Execute use case
        use_case = GetOrchestratorInfoUseCase(mock_query_port)
        
        # Verify exception is propagated
        with pytest.raises(ConnectionError, match="Orchestrator not available"):
            await use_case.execute()
    
    @pytest.mark.asyncio
    async def test_execute_with_runtime_error(self):
        """Test orchestrator info retrieval with runtime error."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_query_port.get_orchestrator_info.side_effect = RuntimeError("Query failed")
        
        # Execute use case
        use_case = GetOrchestratorInfoUseCase(mock_query_port)
        
        # Verify exception is propagated
        with pytest.raises(RuntimeError, match="Query failed"):
            await use_case.execute()
    
    @pytest.mark.asyncio
    async def test_execute_delegates_to_port(self):
        """Test that execute method properly delegates to port."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_orchestrator_info = MagicMock(spec=OrchestratorInfo)
        mock_query_port.get_orchestrator_info.return_value = mock_orchestrator_info
        
        # Execute use case
        use_case = GetOrchestratorInfoUseCase(mock_query_port)
        await use_case.execute()
        
        # Verify delegation
        mock_query_port.get_orchestrator_info.assert_called_once_with()
    
    def test_use_case_follows_hexagonal_architecture(self):
        """Test that use case follows hexagonal architecture principles."""
        # Use case should only depend on ports, not infrastructure
        mock_query_port = MagicMock()
        use_case = GetOrchestratorInfoUseCase(mock_query_port)
        
        # Should not have direct infrastructure dependencies
        assert hasattr(use_case, '_orchestrator_query')
        assert not hasattr(use_case, '_grpc_adapter')
        assert not hasattr(use_case, '_http_client')
        assert not hasattr(use_case, '_database')
    
    def test_use_case_has_single_responsibility(self):
        """Test that use case has single responsibility."""
        mock_query_port = MagicMock()
        use_case = GetOrchestratorInfoUseCase(mock_query_port)
        
        # Should only have execute method for orchestrator info retrieval
        public_methods = [method for method in dir(use_case) if not method.startswith('_')]
        assert 'execute' in public_methods
        assert len(public_methods) == 1  # Only execute method
