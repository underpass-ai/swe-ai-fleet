"""Tests for GetCouncilsInfoUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from services.monitoring.application.usecases.orchestrator.get_councils_info_usecase import (
    GetCouncilsInfoUseCase,
)
from services.monitoring.domain.entities.orchestrator.council_info import CouncilInfo
from services.monitoring.domain.entities.orchestrator.orchestrator_info import OrchestratorInfo


class TestGetCouncilsInfoUseCase:
    """Test cases for GetCouncilsInfoUseCase."""
    
    def test_initialization(self):
        """Test use case initialization with dependencies."""
        mock_info_port = MagicMock()
        use_case = GetCouncilsInfoUseCase(mock_info_port)
        
        assert use_case._orchestrator_info is mock_info_port
    
    @pytest.mark.asyncio
    async def test_execute_success_with_agents(self):
        """Test successful councils info retrieval with agents."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_council1 = MagicMock(spec=CouncilInfo)
        mock_council2 = MagicMock(spec=CouncilInfo)
        mock_orchestrator_info = MagicMock(spec=OrchestratorInfo)
        mock_orchestrator_info.councils = [mock_council1, mock_council2]
        mock_query_port.get_orchestrator_info.return_value = mock_orchestrator_info
        
        # Execute use case
        use_case = GetCouncilsInfoUseCase(mock_query_port)
        result = await use_case.execute()
        
        # Verify
        assert result == [mock_council1, mock_council2]
        assert len(result) == 2
        mock_query_port.get_orchestrator_info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_success_without_agents(self):
        """Test successful councils info retrieval without agents."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_council = MagicMock(spec=CouncilInfo)
        mock_orchestrator_info = MagicMock(spec=OrchestratorInfo)
        mock_orchestrator_info.councils = [mock_council]
        mock_query_port.get_orchestrator_info.return_value = mock_orchestrator_info
        
        # Execute use case
        use_case = GetCouncilsInfoUseCase(mock_query_port)
        result = await use_case.execute()
        
        # Verify
        assert result == [mock_council]
        assert len(result) == 1
        mock_query_port.get_orchestrator_info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_empty_councils(self):
        """Test councils info retrieval when no councils exist."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_orchestrator_info = MagicMock(spec=OrchestratorInfo)
        mock_orchestrator_info.councils = []
        mock_query_port.get_orchestrator_info.return_value = mock_orchestrator_info
        
        # Execute use case
        use_case = GetCouncilsInfoUseCase(mock_query_port)
        result = await use_case.execute()
        
        # Verify
        assert result == []
        assert len(result) == 0
        mock_query_port.get_orchestrator_info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_with_connection_error(self):
        """Test councils info retrieval with connection error."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_query_port.get_orchestrator_info.side_effect = ConnectionError("Orchestrator not available")
        
        # Execute use case
        use_case = GetCouncilsInfoUseCase(mock_query_port)
        
        # Verify exception is propagated
        with pytest.raises(ConnectionError, match="Orchestrator not available"):
            await use_case.execute()
    
    @pytest.mark.asyncio
    async def test_execute_with_runtime_error(self):
        """Test councils info retrieval with runtime error."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_query_port.get_orchestrator_info.side_effect = RuntimeError("Query failed")
        
        # Execute use case
        use_case = GetCouncilsInfoUseCase(mock_query_port)
        
        # Verify exception is propagated
        with pytest.raises(RuntimeError, match="Query failed"):
            await use_case.execute()
    
    @pytest.mark.asyncio
    async def test_execute_delegates_to_port(self):
        """Test that execute method properly delegates to port."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_orchestrator_info = MagicMock(spec=OrchestratorInfo)
        mock_orchestrator_info.councils = []
        mock_query_port.get_orchestrator_info.return_value = mock_orchestrator_info
        
        # Execute use case
        use_case = GetCouncilsInfoUseCase(mock_query_port)
        await use_case.execute()
        
        # Verify delegation
        mock_query_port.get_orchestrator_info.assert_called_once_with()
    
    def test_use_case_follows_hexagonal_architecture(self):
        """Test that use case follows hexagonal architecture principles."""
        # Use case should only depend on ports, not infrastructure
        mock_info_port = MagicMock()
        use_case = GetCouncilsInfoUseCase(mock_info_port)
        
        # Should not have direct infrastructure dependencies
        assert hasattr(use_case, '_orchestrator_info')
        assert not hasattr(use_case, '_grpc_adapter')
        assert not hasattr(use_case, '_http_client')
        assert not hasattr(use_case, '_database')
    
    def test_use_case_has_single_responsibility(self):
        """Test that use case has single responsibility."""
        mock_query_port = MagicMock()
        use_case = GetCouncilsInfoUseCase(mock_query_port)
        
        # Should only have execute method for councils info retrieval
        public_methods = [method for method in dir(use_case) if not method.startswith('_')]
        assert 'execute' in public_methods
        assert len(public_methods) == 1  # Only execute method
    
    @pytest.mark.asyncio
    async def test_execute_returns_council_info_list(self):
        """Test that execute method returns list of CouncilInfo objects."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_council = MagicMock(spec=CouncilInfo)
        mock_orchestrator_info = MagicMock(spec=OrchestratorInfo)
        mock_orchestrator_info.councils = [mock_council]
        mock_query_port.get_orchestrator_info.return_value = mock_orchestrator_info
        
        # Execute use case
        use_case = GetCouncilsInfoUseCase(mock_query_port)
        result = await use_case.execute()
        
        # Verify return type
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], CouncilInfo)
