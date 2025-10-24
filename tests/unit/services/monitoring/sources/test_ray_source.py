"""
Tests for Ray Source monitoring module.

Tests with proper mocking to avoid external dependencies and ensure fast execution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from services.monitoring.sources.ray_source import RaySource


class TestRaySource:
    """Test Ray monitoring source with mocks."""

    def test_initialization(self):
        """Test Ray source initialization."""
        source = RaySource()
        
        assert source.ray_executor_host == "ray-executor.swe-ai-fleet.svc.cluster.local"
        assert source.ray_executor_port == 50056
        assert source.channel is None
        assert source.stub is None

    def test_initialization_with_custom_config(self):
        """Test Ray source initialization with custom configuration."""
        custom_host = "custom-ray:50057"
        custom_port = 50057
        source = RaySource(ray_executor_host=custom_host, ray_executor_port=custom_port)
        
        assert source.ray_executor_host == custom_host
        assert source.ray_executor_port == custom_port

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to Ray Executor."""
        source = RaySource()
        
        mock_channel = AsyncMock()
        mock_stub = MagicMock()
        
        with patch('grpc.aio.insecure_channel', return_value=mock_channel) as mock_channel_func:
            with patch('gen.ray_executor_pb2_grpc.RayExecutorServiceStub', return_value=mock_stub) as mock_stub_func:
                await source.connect()
                
                assert source.channel == mock_channel
                assert source.stub == mock_stub
                mock_channel_func.assert_called_once_with(f"{source.ray_executor_host}:{source.ray_executor_port}")
                mock_stub_func.assert_called_once_with(mock_channel)

    @pytest.mark.asyncio
    async def test_connect_import_error(self):
        """Test connection when gRPC stubs are not available."""
        source = RaySource()
        
        with patch('gen.ray_executor_pb2_grpc', side_effect=ImportError("No module named 'gen'")):
            await source.connect()
            
            assert source.channel is None
            assert source.stub is None

    @pytest.mark.asyncio
    async def test_connect_exception(self):
        """Test connection failure due to exception."""
        source = RaySource()
        
        with patch('grpc.aio.insecure_channel', side_effect=Exception("Connection failed")):
            await source.connect()
            
            assert source.channel is None
            assert source.stub is None

    @pytest.mark.asyncio
    async def test_close_with_channel(self):
        """Test close when channel exists."""
        source = RaySource()
        mock_channel = AsyncMock()
        source.channel = mock_channel
        
        await source.close()
        
        mock_channel.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_channel(self):
        """Test close when channel is None."""
        source = RaySource()
        source.channel = None
        
        # Should not raise exception
        await source.close()

    @pytest.mark.asyncio
    async def test_get_executor_stats_no_stub(self):
        """Test get_executor_stats when stub is not initialized."""
        source = RaySource()
        source.stub = None
        
        result = await source.get_executor_stats()
        
        assert result["connected"] is False
        assert "error" in result
        assert result["error"] == "Ray Executor not connected"

    @pytest.mark.asyncio
    async def test_get_executor_stats_success(self):
        """Test successful get_executor_stats."""
        source = RaySource()
        
        mock_stub = AsyncMock()
        mock_response = MagicMock()
        mock_response.active_jobs = 3
        mock_response.completed_jobs = 15
        mock_response.failed_jobs = 2
        mock_response.total_executions = 20
        mock_response.avg_execution_time_ms = 1500.5
        mock_response.last_execution_time_ms = 1200
        
        mock_stub.GetExecutorStats.return_value = mock_response
        source.stub = mock_stub
        
        result = await source.get_executor_stats()
        
        assert result["connected"] is True
        assert result["active_jobs"] == 3
        assert result["completed_jobs"] == 15
        assert result["failed_jobs"] == 2
        assert result["total_executions"] == 20
        assert result["avg_execution_time_ms"] == 1500.5
        assert result["last_execution_time_ms"] == 1200

    @pytest.mark.asyncio
    async def test_get_executor_stats_exception(self):
        """Test get_executor_stats when exception occurs."""
        source = RaySource()
        
        mock_stub = AsyncMock()
        mock_stub.GetExecutorStats.side_effect = Exception("gRPC call failed")
        source.stub = mock_stub
        
        result = await source.get_executor_stats()
        
        assert result["connected"] is False
        assert "error" in result
        assert result["error"] == "gRPC call failed"

    @pytest.mark.asyncio
    async def test_get_cluster_stats_no_stub(self):
        """Test get_cluster_stats when stub is not initialized."""
        source = RaySource()
        source.stub = None
        
        result = await source.get_cluster_stats()
        
        assert result["connected"] is False
        assert "error" in result
        assert result["error"] == "Ray Executor not connected"

    @pytest.mark.asyncio
    async def test_get_cluster_stats_success(self):
        """Test successful get_cluster_stats."""
        source = RaySource()
        
        mock_stub = AsyncMock()
        mock_response = MagicMock()
        mock_response.num_nodes = 4
        mock_response.total_cpus = 16
        mock_response.total_memory_gb = 64.0
        mock_response.gpu_count = 2
        mock_response.cluster_utilization = 0.75
        
        mock_stub.GetClusterStats.return_value = mock_response
        source.stub = mock_stub
        
        result = await source.get_cluster_stats()
        
        assert result["connected"] is True
        assert result["num_nodes"] == 4
        assert result["total_cpus"] == 16
        assert result["total_memory_gb"] == 64.0
        assert result["gpu_count"] == 2
        assert result["cluster_utilization"] == 0.75

    @pytest.mark.asyncio
    async def test_get_cluster_stats_exception(self):
        """Test get_cluster_stats when exception occurs."""
        source = RaySource()
        
        mock_stub = AsyncMock()
        mock_stub.GetClusterStats.side_effect = Exception("gRPC call failed")
        source.stub = mock_stub
        
        result = await source.get_cluster_stats()
        
        assert result["connected"] is False
        assert "error" in result
        assert result["error"] == "gRPC call failed"

    def test_has_required_methods(self):
        """Test that RaySource has all required methods."""
        source = RaySource()
        
        required_methods = ['connect', 'close', 'get_executor_stats', 'get_cluster_stats']
        for method in required_methods:
            assert hasattr(source, method), f"Missing method: {method}"
            assert callable(getattr(source, method)), f"Method {method} is not callable"