"""
Tests for Orchestrator Source monitoring module.

Tests with proper mocking to avoid external dependencies and ensure fast execution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from services.monitoring.sources.orchestrator_source import OrchestratorSource


class TestOrchestratorSource:
    """Test Orchestrator monitoring source with mocks."""

    def test_initialization(self):
        """Test Orchestrator source initialization."""
        source = OrchestratorSource()
        
        assert source.channel is None
        assert source.stub is None
        assert "orchestrator.swe-ai-fleet.svc.cluster.local:50055" in source.address

    def test_initialization_with_env_var(self):
        """Test Orchestrator source initialization with environment variable."""
        with patch.dict('os.environ', {'ORCHESTRATOR_ADDRESS': 'custom:50056'}):
            source = OrchestratorSource()
            
            assert source.address == "custom:50056"

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to Orchestrator."""
        source = OrchestratorSource()
        
        mock_channel = AsyncMock()
        
        with patch('grpc.aio.insecure_channel', return_value=mock_channel) as mock_channel_func:
            await source.connect()
            
            assert source.channel == mock_channel
            mock_channel_func.assert_called_once_with(source.address)

    @pytest.mark.asyncio
    async def test_connect_exception(self):
        """Test connection failure due to exception."""
        source = OrchestratorSource()
        
        with patch('grpc.aio.insecure_channel', side_effect=Exception("Connection failed")):
            await source.connect()
            
            assert source.channel is None

    @pytest.mark.asyncio
    async def test_close_with_channel(self):
        """Test close when channel exists."""
        source = OrchestratorSource()
        mock_channel = AsyncMock()
        source.channel = mock_channel
        
        await source.close()
        
        mock_channel.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_channel(self):
        """Test close when channel is None."""
        source = OrchestratorSource()
        source.channel = None
        
        # Should not raise exception
        await source.close()

    @pytest.mark.asyncio
    async def test_get_deliberation_stats_no_stub(self):
        """Test get_deliberation_stats when stub is not initialized."""
        source = OrchestratorSource()
        source.stub = None
        
        result = await source.get_deliberation_stats()
        
        assert result["total_deliberations"] == 0
        assert result["active_deliberations"] == 0
        assert result["completed_deliberations"] == 0
        assert result["failed_deliberations"] == 0

    @pytest.mark.asyncio
    async def test_get_deliberation_stats_success(self):
        """Test successful get_deliberation_stats."""
        source = OrchestratorSource()
        
        mock_stub = AsyncMock()
        mock_response = MagicMock()
        mock_response.total_deliberations = 10
        mock_response.active_deliberations = 2
        mock_response.completed_deliberations = 7
        mock_response.failed_deliberations = 1
        
        mock_stub.GetDeliberationStats.return_value = mock_response
        source.stub = mock_stub
        
        result = await source.get_deliberation_stats()
        
        assert result["total_deliberations"] == 10
        assert result["active_deliberations"] == 2
        assert result["completed_deliberations"] == 7
        assert result["failed_deliberations"] == 1

    @pytest.mark.asyncio
    async def test_get_deliberation_stats_exception(self):
        """Test get_deliberation_stats when exception occurs."""
        source = OrchestratorSource()
        
        mock_stub = AsyncMock()
        mock_stub.GetDeliberationStats.side_effect = Exception("gRPC call failed")
        source.stub = mock_stub
        
        result = await source.get_deliberation_stats()
        
        assert result["total_deliberations"] == 0
        assert result["active_deliberations"] == 0
        assert result["completed_deliberations"] == 0
        assert result["failed_deliberations"] == 0

    @pytest.mark.asyncio
    async def test_get_council_stats_no_stub(self):
        """Test get_council_stats when stub is not initialized."""
        source = OrchestratorSource()
        source.stub = None
        
        result = await source.get_council_stats()
        
        assert result["total_councils"] == 0
        assert result["active_councils"] == 0
        assert result["avg_council_size"] == 0.0

    @pytest.mark.asyncio
    async def test_get_council_stats_success(self):
        """Test successful get_council_stats."""
        source = OrchestratorSource()
        
        mock_stub = AsyncMock()
        mock_response = MagicMock()
        mock_response.total_councils = 5
        mock_response.active_councils = 2
        mock_response.avg_council_size = 3.5
        
        mock_stub.GetCouncilStats.return_value = mock_response
        source.stub = mock_stub
        
        result = await source.get_council_stats()
        
        assert result["total_councils"] == 5
        assert result["active_councils"] == 2
        assert result["avg_council_size"] == 3.5

    @pytest.mark.asyncio
    async def test_get_agent_stats_no_stub(self):
        """Test get_agent_stats when stub is not initialized."""
        source = OrchestratorSource()
        source.stub = None
        
        result = await source.get_agent_stats()
        
        assert result["total_agents"] == 0
        assert result["active_agents"] == 0
        assert result["idle_agents"] == 0

    @pytest.mark.asyncio
    async def test_get_agent_stats_success(self):
        """Test successful get_agent_stats."""
        source = OrchestratorSource()
        
        mock_stub = AsyncMock()
        mock_response = MagicMock()
        mock_response.total_agents = 8
        mock_response.active_agents = 3
        mock_response.idle_agents = 5
        
        mock_stub.GetAgentStats.return_value = mock_response
        source.stub = mock_stub
        
        result = await source.get_agent_stats()
        
        assert result["total_agents"] == 8
        assert result["active_agents"] == 3
        assert result["idle_agents"] == 5

    @pytest.mark.asyncio
    async def test_get_task_stats_no_stub(self):
        """Test get_task_stats when stub is not initialized."""
        source = OrchestratorSource()
        source.stub = None
        
        result = await source.get_task_stats()
        
        assert result["total_tasks"] == 0
        assert result["pending_tasks"] == 0
        assert result["running_tasks"] == 0
        assert result["completed_tasks"] == 0

    @pytest.mark.asyncio
    async def test_get_task_stats_success(self):
        """Test successful get_task_stats."""
        source = OrchestratorSource()
        
        mock_stub = AsyncMock()
        mock_response = MagicMock()
        mock_response.total_tasks = 20
        mock_response.pending_tasks = 5
        mock_response.running_tasks = 3
        mock_response.completed_tasks = 12
        
        mock_stub.GetTaskStats.return_value = mock_response
        source.stub = mock_stub
        
        result = await source.get_task_stats()
        
        assert result["total_tasks"] == 20
        assert result["pending_tasks"] == 5
        assert result["running_tasks"] == 3
        assert result["completed_tasks"] == 12

    def test_has_required_methods(self):
        """Test that OrchestratorSource has all required methods."""
        source = OrchestratorSource()
        
        required_methods = ['connect', 'close', 'get_deliberation_stats', 'get_council_stats', 'get_agent_stats', 'get_task_stats']
        for method in required_methods:
            assert hasattr(source, method), f"Missing method: {method}"
            assert callable(getattr(source, method)), f"Method {method} is not callable"