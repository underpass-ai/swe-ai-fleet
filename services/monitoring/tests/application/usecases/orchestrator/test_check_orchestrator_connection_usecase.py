"""Tests for CheckOrchestratorConnectionUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from services.monitoring.application.usecases.orchestrator.check_orchestrator_connection_usecase import (
    CheckOrchestratorConnectionUseCase,
)


class TestCheckOrchestratorConnectionUseCase:
    """Test cases for CheckOrchestratorConnectionUseCase."""
    
    def test_initialization(self):
        """Test use case initialization with dependencies."""
        mock_query_port = MagicMock()
        use_case = CheckOrchestratorConnectionUseCase(mock_query_port)
        
        assert use_case._orchestrator_query is mock_query_port
    
    @pytest.mark.asyncio
    async def test_execute_connection_available(self):
        """Test successful connection check when orchestrator is available."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_query_port.is_orchestrator_available.return_value = True
        
        # Execute use case
        use_case = CheckOrchestratorConnectionUseCase(mock_query_port)
        result = await use_case.execute()
        
        # Verify
        assert result is True
        mock_query_port.is_orchestrator_available.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_connection_unavailable(self):
        """Test connection check when orchestrator is unavailable."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_query_port.is_orchestrator_available.return_value = False
        
        # Execute use case
        use_case = CheckOrchestratorConnectionUseCase(mock_query_port)
        result = await use_case.execute()
        
        # Verify
        assert result is False
        mock_query_port.is_orchestrator_available.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_with_connection_error(self):
        """Test connection check with connection error."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_query_port.is_orchestrator_available.side_effect = ConnectionError("Connection failed")
        
        # Execute use case
        use_case = CheckOrchestratorConnectionUseCase(mock_query_port)
        
        # Verify exception is propagated
        with pytest.raises(ConnectionError, match="Connection failed"):
            await use_case.execute()
    
    @pytest.mark.asyncio
    async def test_execute_with_runtime_error(self):
        """Test connection check with runtime error."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_query_port.is_orchestrator_available.side_effect = RuntimeError("Service unavailable")
        
        # Execute use case
        use_case = CheckOrchestratorConnectionUseCase(mock_query_port)
        
        # Verify exception is propagated
        with pytest.raises(RuntimeError, match="Service unavailable"):
            await use_case.execute()
    
    @pytest.mark.asyncio
    async def test_execute_delegates_to_port(self):
        """Test that execute method properly delegates to port."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_query_port.is_orchestrator_available.return_value = True
        
        # Execute use case
        use_case = CheckOrchestratorConnectionUseCase(mock_query_port)
        await use_case.execute()
        
        # Verify delegation
        mock_query_port.is_orchestrator_available.assert_called_once_with()
    
    def test_use_case_follows_hexagonal_architecture(self):
        """Test that use case follows hexagonal architecture principles."""
        # Use case should only depend on ports, not infrastructure
        mock_query_port = MagicMock()
        use_case = CheckOrchestratorConnectionUseCase(mock_query_port)
        
        # Should not have direct infrastructure dependencies
        assert hasattr(use_case, '_orchestrator_query')
        assert not hasattr(use_case, '_grpc_adapter')
        assert not hasattr(use_case, '_http_client')
        assert not hasattr(use_case, '_database')
    
    def test_use_case_has_single_responsibility(self):
        """Test that use case has single responsibility."""
        mock_query_port = MagicMock()
        use_case = CheckOrchestratorConnectionUseCase(mock_query_port)
        
        # Should only have execute method for connection checking
        public_methods = [method for method in dir(use_case) if not method.startswith('_')]
        assert 'execute' in public_methods
        assert len(public_methods) == 1  # Only execute method
    
    @pytest.mark.asyncio
    async def test_execute_returns_boolean(self):
        """Test that execute method returns boolean value."""
        # Setup mocks
        mock_query_port = AsyncMock()
        mock_query_port.is_orchestrator_available.return_value = True
        
        # Execute use case
        use_case = CheckOrchestratorConnectionUseCase(mock_query_port)
        result = await use_case.execute()
        
        # Verify return type
        assert isinstance(result, bool)
