"""Unit tests for DeliberateAsync use case."""
from unittest.mock import Mock, patch

import pytest

# Check if Ray is available (skip tests if not)
try:
    import ray
    if not hasattr(ray, 'remote'):
        pytest.skip("Ray not available (namespace package conflict)", allow_module_level=True)
except ImportError:
    pytest.skip("Ray not installed", allow_module_level=True)

from swe_ai_fleet.orchestrator.usecases.deliberate_async_usecase import DeliberateAsync


class TestDeliberateAsync:
    """Unit tests for DeliberateAsync."""
    
    @pytest.fixture
    def deliberate_async(self):
        """Create DeliberateAsync instance for testing."""
        # Mock Ray Executor stub
        mock_stub = Mock()
        return DeliberateAsync(
            ray_executor_stub=mock_stub,
            vllm_url="http://vllm-test:8000",
            model="test-model",
            nats_url="nats://nats-test:4222",
            temperature=0.7,
            max_tokens=1024,
            timeout=30,
        )
    
    def test_initialization(self, deliberate_async):
        """Test DeliberateAsync initialization."""
        assert deliberate_async.vllm_url == "http://vllm-test:8000"
        assert deliberate_async.model == "test-model"
        assert deliberate_async.nats_url == "nats://nats-test:4222"
        assert deliberate_async.temperature == 0.7
        assert deliberate_async.max_tokens == 1024
        assert deliberate_async.timeout == 30
    
    def test_ray_executor_stub_initialization(self, deliberate_async):
        """Test Ray Executor stub is properly initialized."""
        assert deliberate_async.ray_executor is not None
        assert hasattr(deliberate_async.ray_executor, 'ExecuteDeliberation')
    
    def test_connect_ray_with_stub(
        self
    ):
        """Test Ray Executor stub initialization."""
        mock_stub = Mock()
        deliberate = DeliberateAsync(
            ray_executor_stub=mock_stub,
            vllm_url="http://test:8000",
            model="test",
            nats_url="nats://test:4222",
        )
        
        # Verify stub is set correctly
        assert deliberate.ray_executor == mock_stub
    
    @pytest.mark.asyncio
    async def test_execute_basic(self, deliberate_async):
        """Test basic execution of deliberation via gRPC."""
        # Mock gRPC response
        mock_response = Mock()
        mock_response.deliberation_id = "test-job-001"
        mock_response.status = "submitted"
        mock_response.message = "Deliberation submitted successfully"
        
        # Mock the ExecuteDeliberation call as async
        mock_execute = Mock()
        async def async_execute(request):
            return mock_response
        mock_execute.side_effect = async_execute
        
        deliberate_async.ray_executor.ExecuteDeliberation = mock_execute
        
        # Execute deliberation
        result = await deliberate_async.execute(
            task_id="test-task-001",
            task_description="Write factorial function",
            role="DEV",
            num_agents=3,
            constraints={"rubric": "Clean code"},
            rounds=1,
        )
        
        # Verify gRPC call was made
        deliberate_async.ray_executor.ExecuteDeliberation.assert_called_once()
        
        # Verify result structure
        assert result["task_id"] == "test-task-001"
        assert result["num_agents"] == 3
        assert result["role"] == "DEV"
        assert result["status"] == "submitted"
        assert "deliberation_id" in result
        assert result["deliberation_id"] == "test-job-001"
    
    @pytest.mark.asyncio
    async def test_execute_generates_task_id_if_not_provided(self, deliberate_async):
        """Test that task_id is generated if not provided."""
        # Mock gRPC response
        mock_response = Mock()
        mock_response.deliberation_id = "test-job-002"
        mock_response.status = "submitted"
        mock_response.message = "Deliberation submitted successfully"
        
        mock_execute = Mock()
        async def async_execute(request):
            return mock_response
        mock_execute.side_effect = async_execute
        
        deliberate_async.ray_executor.ExecuteDeliberation = mock_execute
        
        result = await deliberate_async.execute(
            task_id=None,  # No task_id provided
            task_description="Test task",
            role="QA",
            num_agents=2,
        )
        
        # Verify task_id was generated
        assert result["task_id"] is not None
        assert result["task_id"].startswith("task-")
        assert len(result["task_id"]) > 5  # UUID format
    
    @pytest.mark.asyncio
    async def test_execute_with_different_roles(self, deliberate_async):
        """Test execution with different roles."""
        roles = ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]
        
        for role in roles:
            # Mock gRPC response for each role
            mock_response = Mock()
            mock_response.deliberation_id = f"test-job-{role.lower()}"
            mock_response.status = "submitted"
            mock_response.message = f"Deliberation submitted for {role}"
            
            async def mock_execute(request):
                return mock_response
            
            deliberate_async.ray_executor.ExecuteDeliberation = mock_execute
            
            result = await deliberate_async.execute(
                task_id=f"test-{role.lower()}",
                task_description="Test task",
                role=role,
                num_agents=2,
            )
            
            assert result["role"] == role
            # Verify deliberation ID matches role
            assert result["deliberation_id"] == f"test-job-{role.lower()}"
    
    @pytest.mark.asyncio
    async def test_execute_handles_none_constraints(self, deliberate_async):
        """Test that None constraints are handled properly."""
        # Mock gRPC response
        mock_response = Mock()
        mock_response.deliberation_id = "test-job-none-constraints"
        mock_response.status = "submitted"
        mock_response.message = "Deliberation submitted successfully"
        
        mock_execute = Mock()
        async def async_execute(request):
            return mock_response
        mock_execute.side_effect = async_execute
        
        deliberate_async.ray_executor.ExecuteDeliberation = mock_execute
        
        result = await deliberate_async.execute(
            task_id="test-task",
            task_description="Test",
            role="DEV",
            num_agents=1,
            constraints=None,  # None constraints
        )
        
        # Should not raise error
        assert result["status"] == "submitted"
        
        # Verify gRPC call was made
        deliberate_async.ray_executor.ExecuteDeliberation.assert_called_once()

