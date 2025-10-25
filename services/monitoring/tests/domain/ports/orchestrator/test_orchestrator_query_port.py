"""Tests for OrchestratorQueryPort."""


import pytest
from services.monitoring.domain.entities.orchestrator.agent_info import AgentInfo
from services.monitoring.domain.entities.orchestrator.council_info import CouncilInfo
from services.monitoring.domain.entities.orchestrator.orchestrator_connection_status import (
    OrchestratorConnectionStatus,
)
from services.monitoring.domain.entities.orchestrator.orchestrator_info import OrchestratorInfo
from services.monitoring.domain.ports.orchestrator.orchestrator_query_port import (
    OrchestratorQueryPort,
)


class MockOrchestratorQueryAdapter(OrchestratorQueryPort):
    """Mock implementation of OrchestratorQueryPort for testing."""
    
    def __init__(self):
        self.orchestrator_info = None
        self.is_available = True
        self.connection_status = True
    
    async def get_orchestrator_info(self) -> OrchestratorInfo:
        """Mock implementation."""
        if self.orchestrator_info is None:
            # Create default mock orchestrator info
            councils = [
                CouncilInfo(
                    council_id="council-dev-001",
                    role="DEV",
                    emoji="🧑‍💻",
                    status="active",
                    model="llama-3.1-8b",
                    total_agents=2,
                    agents=[
                        AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
                        AgentInfo(agent_id="agent-dev-002", role="DEV", status="busy")
                    ]
                )
            ]
            
            connection_status = OrchestratorConnectionStatus.create_connected_status(
                total_councils=1,
                total_agents=2
            )
            
            self.orchestrator_info = OrchestratorInfo(
                connection_status=connection_status,
                councils=councils
            )
        
        return self.orchestrator_info
    
    async def is_orchestrator_available(self) -> bool:
        """Mock implementation."""
        return self.is_available
    
    async def get_connection_status(self) -> bool:
        """Mock implementation."""
        return self.connection_status


class TestOrchestratorQueryPort:
    """Test cases for OrchestratorQueryPort interface."""
    
    def test_port_is_abstract(self):
        """Test that OrchestratorQueryPort is abstract."""
        with pytest.raises(TypeError):
            OrchestratorQueryPort()
    
    def test_mock_adapter_implements_port(self):
        """Test that mock adapter implements the port interface."""
        adapter = MockOrchestratorQueryAdapter()
        assert isinstance(adapter, OrchestratorQueryPort)
    
    @pytest.mark.asyncio
    async def test_get_orchestrator_info_returns_orchestrator_info(self):
        """Test that get_orchestrator_info returns OrchestratorInfo."""
        adapter = MockOrchestratorQueryAdapter()
        
        result = await adapter.get_orchestrator_info()
        
        assert isinstance(result, OrchestratorInfo)
        assert result.is_connected() is True
        assert result.is_healthy() is True
        assert result.total_councils == 1
        assert result.total_agents == 2
    
    @pytest.mark.asyncio
    async def test_is_orchestrator_available_returns_bool(self):
        """Test that is_orchestrator_available returns boolean."""
        adapter = MockOrchestratorQueryAdapter()
        
        result = await adapter.is_orchestrator_available()
        
        assert isinstance(result, bool)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_connection_status_returns_bool(self):
        """Test that get_connection_status returns boolean."""
        adapter = MockOrchestratorQueryAdapter()
        
        result = await adapter.get_connection_status()
        
        assert isinstance(result, bool)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_adapter_can_be_configured(self):
        """Test that adapter can be configured for different scenarios."""
        adapter = MockOrchestratorQueryAdapter()
        
        # Configure for unavailable orchestrator
        adapter.is_available = False
        adapter.connection_status = False
        
        # Create disconnected orchestrator info
        adapter.orchestrator_info = OrchestratorInfo.create_disconnected_orchestrator(
            error="Service unavailable"
        )
        
        assert await adapter.is_orchestrator_available() is False
        assert await adapter.get_connection_status() is False
        
        orchestrator_info = await adapter.get_orchestrator_info()
        assert orchestrator_info.is_connected() is False
        assert orchestrator_info.is_healthy() is False
