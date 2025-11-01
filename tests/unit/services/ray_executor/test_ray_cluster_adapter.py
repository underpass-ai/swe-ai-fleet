"""Unit tests for RayClusterAdapter."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from services.ray_executor.infrastructure.adapters.ray_cluster_adapter import RayClusterAdapter
from services.ray_executor.domain.entities import DeliberationResult


# =============================================================================
# Constructor Tests
# =============================================================================

class TestRayClusterAdapterConstructor:
    """Test adapter constructor."""

    def test_creates_with_registry(self):
        """Should create adapter with deliberations registry."""
        deliberations_registry = {}

        adapter = RayClusterAdapter(deliberations_registry=deliberations_registry)

        assert adapter._deliberations == deliberations_registry


# =============================================================================
# Submit Deliberation Tests
# =============================================================================

class TestRayClusterAdapterSubmit:
    """Test submit_deliberation method."""

    @pytest.mark.asyncio
    @patch('services.ray_executor.infrastructure.adapters.ray_cluster_adapter.RayAgentFactory')
    @patch('services.ray_executor.infrastructure.adapters.ray_cluster_adapter.RayAgentJob')
    async def test_submits_deliberation_to_ray(self, mock_ray_job, mock_factory):
        """Should submit deliberation to Ray cluster."""
        # Setup mocks
        mock_executor = Mock()
        mock_factory.create.return_value = mock_executor
        
        mock_remote_actor = Mock()
        mock_future = Mock()
        mock_remote_actor.run.remote.return_value = mock_future
        mock_ray_job.remote.return_value = mock_remote_actor

        deliberations_registry = {}
        adapter = RayClusterAdapter(deliberations_registry=deliberations_registry)

        # Execute
        result = await adapter.submit_deliberation(
            deliberation_id="delib-123",
            task_id="task-456",
            task_description="Implement feature X",
            role="ARCHITECT",
            agents=[{"agent_id": "agent-1", "role": "ARCHITECT"}],
            constraints={"max_operations": 10},
            vllm_url="http://vllm:8000",
            vllm_model="qwen",
        )

        # Verify result
        assert result == "delib-123"

        # Verify deliberation was registered
        assert "delib-123" in deliberations_registry
        delib = deliberations_registry["delib-123"]
        assert delib["task_id"] == "task-456"
        assert delib["role"] == "ARCHITECT"
        assert delib["status"] == "running"
        assert "start_time" in delib
        assert delib["agents"] == ["agent-1"]

    @pytest.mark.asyncio
    async def test_rejects_empty_agents_list(self):
        """Should reject when no agents provided."""
        deliberations_registry = {}
        adapter = RayClusterAdapter(deliberations_registry=deliberations_registry)

        with pytest.raises(ValueError, match="At least one agent required"):
            await adapter.submit_deliberation(
                deliberation_id="delib-123",
                task_id="task-456",
                task_description="Test",
                role="DEV",
                agents=[],  # Empty!
                constraints={},
                vllm_url="http://vllm:8000",
                vllm_model="qwen",
            )


# =============================================================================
# Check Status - Not Found Tests
# =============================================================================

class TestRayClusterAdapterCheckStatusNotFound:
    """Test check_deliberation_status when not found."""

    @pytest.mark.asyncio
    async def test_returns_not_found_when_not_in_registry(self):
        """Should return not_found status."""
        deliberations_registry = {}
        adapter = RayClusterAdapter(deliberations_registry=deliberations_registry)

        status, result, error = await adapter.check_deliberation_status("nonexistent")

        assert status == "not_found"
        assert result is None
        assert "not found" in error


# =============================================================================
# Check Status - Running Tests
# =============================================================================

class TestRayClusterAdapterCheckStatusRunning:
    """Test check_deliberation_status for running jobs."""

    @pytest.mark.asyncio
    @patch('services.ray_executor.infrastructure.adapters.ray_cluster_adapter.ray')
    async def test_returns_running_when_job_not_ready(self, mock_ray):
        """Should return running status when Ray job not ready."""
        mock_future = Mock()
        mock_ray.wait.return_value = ([], [mock_future])  # Not ready

        deliberations_registry = {
            "delib-123": {
                "future": mock_future,
                "status": "running",
            }
        }

        adapter = RayClusterAdapter(deliberations_registry=deliberations_registry)

        status, result, error = await adapter.check_deliberation_status("delib-123")

        assert status == "running"
        assert result is None
        assert error is None


# =============================================================================
# Check Status - Completed Tests
# =============================================================================

class TestRayClusterAdapterCheckStatusCompleted:
    """Test check_deliberation_status for completed jobs."""

    @pytest.mark.asyncio
    @patch('services.ray_executor.infrastructure.adapters.ray_cluster_adapter.ray')
    async def test_returns_completed_with_result(self, mock_ray):
        """Should return completed status with DeliberationResult entity."""
        mock_future = Mock()
        mock_ray.wait.return_value = ([mock_future], [])  # Ready
        mock_ray.get.return_value = {
            "agent_id": "agent-1",
            "proposal": "Implement using microservices",
            "reasoning": "Better scalability",
            "score": 0.95,  # Must be 0.0-1.0
            "metadata": {"confidence": "high"},
        }

        deliberations_registry = {
            "delib-123": {
                "future": mock_future,
                "status": "running",
            }
        }

        adapter = RayClusterAdapter(deliberations_registry=deliberations_registry)

        status, result, error = await adapter.check_deliberation_status("delib-123")

        # Verify status
        assert status == "completed"
        assert error is None

        # Verify result entity
        assert isinstance(result, DeliberationResult)
        assert result.agent_id == "agent-1"
        assert result.proposal == "Implement using microservices"
        assert result.reasoning == "Better scalability"
        assert result.score == 0.95
        assert result.metadata == {"confidence": "high"}

    @pytest.mark.asyncio
    @patch('services.ray_executor.infrastructure.adapters.ray_cluster_adapter.ray')
    async def test_handles_missing_optional_fields_in_result(self, mock_ray):
        """Should use defaults for missing fields in Ray result."""
        mock_future = Mock()
        mock_ray.wait.return_value = ([mock_future], [])
        mock_ray.get.return_value = {
            "agent_id": "agent-1",
            "proposal": "Valid proposal",  # Required
            "reasoning": "Valid reasoning",  # Default if missing
            "score": 0.75,  # Default if missing
            # metadata missing - will use default
        }

        deliberations_registry = {
            "delib-123": {
                "future": mock_future,
                "status": "running",
            }
        }

        adapter = RayClusterAdapter(deliberations_registry=deliberations_registry)

        status, result, error = await adapter.check_deliberation_status("delib-123")

        assert status == "completed"
        assert isinstance(result, DeliberationResult)
        assert result.agent_id == "agent-1"
        assert result.proposal == "Valid proposal"
        assert result.metadata == {}  # Default empty dict


# =============================================================================
# Check Status - Error Handling Tests
# =============================================================================

class TestRayClusterAdapterCheckStatusErrors:
    """Test error handling in status check."""

    @pytest.mark.asyncio
    @patch('services.ray_executor.infrastructure.adapters.ray_cluster_adapter.ray')
    async def test_returns_failed_on_exception(self, mock_ray):
        """Should return failed status on Ray exception."""
        mock_future = Mock()
        mock_ray.wait.side_effect = Exception("Ray cluster connection lost")

        deliberations_registry = {
            "delib-123": {
                "future": mock_future,
                "status": "running",
            }
        }

        adapter = RayClusterAdapter(deliberations_registry=deliberations_registry)

        status, result, error = await adapter.check_deliberation_status("delib-123")

        assert status == "failed"
        assert result is None
        assert "Ray cluster connection lost" in error


# =============================================================================
# Get Active Jobs Tests
# =============================================================================

class TestRayClusterAdapterGetActiveJobs:
    """Test get_active_jobs method."""

    @pytest.mark.asyncio
    async def test_returns_all_deliberations_from_registry(self):
        """Should return all deliberations as list of items."""
        deliberations_registry = {
            "delib-1": {"status": "running"},
            "delib-2": {"status": "completed"},
            "delib-3": {"status": "running"},
        }

        adapter = RayClusterAdapter(deliberations_registry=deliberations_registry)

        jobs = await adapter.get_active_jobs()

        # Should return all items (use case filters)
        assert len(jobs) == 3

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_deliberations(self):
        """Should return empty list when no deliberations."""
        deliberations_registry = {}

        adapter = RayClusterAdapter(deliberations_registry=deliberations_registry)

        jobs = await adapter.get_active_jobs()

        assert jobs == []

