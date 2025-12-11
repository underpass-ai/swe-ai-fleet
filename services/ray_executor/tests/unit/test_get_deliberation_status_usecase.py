"""Unit tests for GetDeliberationStatusUseCase."""

from unittest.mock import AsyncMock, Mock

import pytest

from services.ray_executor.application.usecases.get_deliberation_status_usecase import (
    GetDeliberationStatusUseCase,
)
from services.ray_executor.domain.entities import (
    DeliberationResult,
    MultiAgentDeliberationResult,
)

# =============================================================================
# Constructor Tests
# =============================================================================

class TestGetDeliberationStatusUseCaseConstructor:
    """Test use case constructor and dependency injection."""

    def test_creates_with_dependencies(self):
        """Should create use case with injected dependencies."""
        ray_cluster = Mock()
        stats_tracker = {}
        deliberations_registry = {}

        use_case = GetDeliberationStatusUseCase(
            ray_cluster=ray_cluster,
            stats_tracker=stats_tracker,
            deliberations_registry=deliberations_registry,
        )

        assert use_case._ray_cluster == ray_cluster
        assert use_case._stats == stats_tracker
        assert use_case._deliberations == deliberations_registry


# =============================================================================
# Execute - Not Found Tests
# =============================================================================

class TestGetDeliberationStatusNotFound:
    """Test behavior when deliberation not found."""

    @pytest.mark.asyncio
    async def test_returns_not_found_when_id_not_in_registry(self):
        """Should return not_found status when deliberation doesn't exist."""
        ray_cluster = AsyncMock()
        stats_tracker = {}
        deliberations_registry = {}

        use_case = GetDeliberationStatusUseCase(
            ray_cluster=ray_cluster,
            stats_tracker=stats_tracker,
            deliberations_registry=deliberations_registry,
        )

        response = await use_case.execute("nonexistent-id")

        assert response.status == "not_found"
        assert "not found" in response.error_message
        assert response.result is None
        # Should not query Ray cluster
        ray_cluster.check_deliberation_status.assert_not_called()


# =============================================================================
# Execute - Running Status Tests
# =============================================================================

class TestGetDeliberationStatusRunning:
    """Test behavior for running deliberations."""

    @pytest.mark.asyncio
    async def test_returns_running_status(self):
        """Should return running status when deliberation in progress."""
        ray_cluster = AsyncMock()
        ray_cluster.check_deliberation_status.return_value = ("running", None, None)

        stats_tracker = {}
        deliberations_registry = {
            "delib-123": {
                "status": "running",
                "start_time": 1234567890.0,
            }
        }

        use_case = GetDeliberationStatusUseCase(
            ray_cluster=ray_cluster,
            stats_tracker=stats_tracker,
            deliberations_registry=deliberations_registry,
        )

        response = await use_case.execute("delib-123")

        assert response.status == "running"
        assert response.result is None
        assert response.error_message is None


# =============================================================================
# Execute - Completed Status Tests
# =============================================================================

class TestGetDeliberationStatusCompleted:
    """Test behavior for completed deliberations."""

    @pytest.mark.asyncio
    async def test_returns_completed_status_with_result(self):
        """Should return completed status with result."""
        result = DeliberationResult(
            agent_id="agent-1",
            proposal="Implement using microservices architecture",
            reasoning="This provides better scalability and maintainability",
            score=0.95,
            metadata={"confidence": "high"},
        )

        ray_cluster = AsyncMock()
        ray_cluster.check_deliberation_status.return_value = ("completed", result, None)

        stats_tracker = {
            "execution_times": [],
            "active_deliberations": 1,
            "completed_deliberations": 0,
            "failed_deliberations": 0,
        }

        deliberations_registry = {
            "delib-123": {
                "status": "running",
                "start_time": 1234567890.0,
            }
        }

        use_case = GetDeliberationStatusUseCase(
            ray_cluster=ray_cluster,
            stats_tracker=stats_tracker,
            deliberations_registry=deliberations_registry,
        )

        response = await use_case.execute("delib-123")

        # Verify response
        assert response.status == "completed"
        assert response.result == result
        assert response.error_message is None

        # Verify registry updated
        assert deliberations_registry["delib-123"]["status"] == "completed"
        assert deliberations_registry["delib-123"]["result"] == result
        assert "end_time" in deliberations_registry["delib-123"]

        # Verify stats updated
        assert stats_tracker["active_deliberations"] == 0
        assert stats_tracker["completed_deliberations"] == 1
        assert len(stats_tracker["execution_times"]) == 1

    @pytest.mark.asyncio
    async def test_calculates_execution_time_on_completion(self):
        """Should calculate and track execution time."""
        result = DeliberationResult(
            agent_id="agent-1",
            proposal="Task completed successfully",
            reasoning="All requirements met",
            score=0.90,
            metadata={},
        )

        ray_cluster = AsyncMock()
        ray_cluster.check_deliberation_status.return_value = ("completed", result, None)

        start_time = 1234567890.0
        stats_tracker = {
            "execution_times": [],
            "active_deliberations": 1,
            "completed_deliberations": 0,
            "failed_deliberations": 0,
        }

        deliberations_registry = {
            "delib-123": {
                "status": "running",
                "start_time": start_time,
            }
        }

        use_case = GetDeliberationStatusUseCase(
            ray_cluster=ray_cluster,
            stats_tracker=stats_tracker,
            deliberations_registry=deliberations_registry,
        )

        await use_case.execute("delib-123")

        # Verify execution time was tracked
        assert len(stats_tracker["execution_times"]) == 1
        execution_time = stats_tracker["execution_times"][0]
        assert execution_time > 0


# =============================================================================
# Execute - Failed Status Tests
# =============================================================================

class TestGetDeliberationStatusFailed:
    """Test behavior for failed deliberations."""

    @pytest.mark.asyncio
    async def test_returns_failed_status_with_error(self):
        """Should return failed status with error message."""
        ray_cluster = AsyncMock()
        ray_cluster.check_deliberation_status.return_value = (
            "failed",
            None,
            "Agent crashed",
        )

        stats_tracker = {
            "active_deliberations": 1,
            "failed_deliberations": 0,
            "completed_deliberations": 0,
        }

        deliberations_registry = {
            "delib-123": {
                "status": "running",
                "start_time": 1234567890.0,
            }
        }

        use_case = GetDeliberationStatusUseCase(
            ray_cluster=ray_cluster,
            stats_tracker=stats_tracker,
            deliberations_registry=deliberations_registry,
        )

        response = await use_case.execute("delib-123")

        # Verify response
        assert response.status == "failed"
        assert response.result is None
        assert response.error_message == "Agent crashed"

        # Verify registry updated
        assert deliberations_registry["delib-123"]["status"] == "failed"
        assert deliberations_registry["delib-123"]["error"] == "Agent crashed"

        # Verify stats updated
        assert stats_tracker["active_deliberations"] == 0
        assert stats_tracker["failed_deliberations"] == 1


# =============================================================================
# Execute - Multi-Agent Completed Status Tests
# =============================================================================

class TestGetDeliberationStatusMultiAgentCompleted:
    """Test behavior for completed multi-agent deliberations."""

    @pytest.mark.asyncio
    async def test_returns_completed_status_with_multi_agent_result(self):
        """Should return completed status with MultiAgentDeliberationResult."""
        result1 = DeliberationResult(
            agent_id="agent-1",
            proposal="Proposal from agent 1",
            reasoning="Reasoning 1",
            score=0.9,
            metadata={},
        )
        result2 = DeliberationResult(
            agent_id="agent-2",
            proposal="Proposal from agent 2",
            reasoning="Reasoning 2",
            score=0.85,
            metadata={},
        )
        result3 = DeliberationResult(
            agent_id="agent-3",
            proposal="Proposal from agent 3",
            reasoning="Reasoning 3",
            score=0.95,
            metadata={},
        )

        multi_result = MultiAgentDeliberationResult(
            agent_results=[result1, result2, result3],
            total_agents=3,
            completed_agents=3,
            failed_agents=0,
        )

        ray_cluster = AsyncMock()
        ray_cluster.check_deliberation_status.return_value = ("completed", multi_result, None)

        stats_tracker = {
            "execution_times": [],
            "active_deliberations": 1,
            "completed_deliberations": 0,
            "failed_deliberations": 0,
        }

        deliberations_registry = {
            "delib-123": {
                "status": "running",
                "start_time": 1234567890.0,
            }
        }

        use_case = GetDeliberationStatusUseCase(
            ray_cluster=ray_cluster,
            stats_tracker=stats_tracker,
            deliberations_registry=deliberations_registry,
        )

        response = await use_case.execute("delib-123")

        # Verify response
        assert response.status == "completed"
        assert isinstance(response.result, MultiAgentDeliberationResult)
        assert response.result.total_agents == 3
        assert response.result.completed_agents == 3
        assert response.result.best_result is not None
        assert response.result.best_result.agent_id == "agent-3"  # Highest score
        assert response.error_message is None

        # Verify registry updated
        assert deliberations_registry["delib-123"]["status"] == "completed"
        assert deliberations_registry["delib-123"]["result"] == multi_result

        # Verify stats updated
        assert stats_tracker["active_deliberations"] == 0
        assert stats_tracker["completed_deliberations"] == 1


# =============================================================================
# Execute - Error Handling Tests
# =============================================================================

class TestGetDeliberationStatusErrorHandling:
    """Test error handling in status check."""

    @pytest.mark.asyncio
    async def test_handles_ray_cluster_exception(self):
        """Should handle exceptions from Ray cluster."""
        ray_cluster = AsyncMock()
        ray_cluster.check_deliberation_status.side_effect = Exception("Ray cluster unavailable")

        stats_tracker = {
            "active_deliberations": 1,
            "failed_deliberations": 0,
            "completed_deliberations": 0,
        }

        deliberations_registry = {
            "delib-123": {
                "status": "running",
                "start_time": 1234567890.0,
            }
        }

        use_case = GetDeliberationStatusUseCase(
            ray_cluster=ray_cluster,
            stats_tracker=stats_tracker,
            deliberations_registry=deliberations_registry,
        )

        response = await use_case.execute("delib-123")

        # Verify failed response
        assert response.status == "failed"
        assert response.result is None
        assert "Ray cluster unavailable" in response.error_message

        # Verify registry marked as failed
        assert deliberations_registry["delib-123"]["status"] == "failed"
        assert deliberations_registry["delib-123"]["error"] == "Ray cluster unavailable"

        # Verify stats updated
        assert stats_tracker["active_deliberations"] == 0
        assert stats_tracker["failed_deliberations"] == 1


# =============================================================================
# Execute - Multi-Agent Completed Status Tests
# =============================================================================

class TestGetDeliberationStatusMultiAgentCompleted:
    """Test behavior for completed multi-agent deliberations."""

    @pytest.mark.asyncio
    async def test_returns_completed_status_with_multi_agent_result(self):
        """Should return completed status with MultiAgentDeliberationResult."""
        result1 = DeliberationResult(
            agent_id="agent-1",
            proposal="Proposal from agent 1",
            reasoning="Reasoning 1",
            score=0.9,
            metadata={},
        )
        result2 = DeliberationResult(
            agent_id="agent-2",
            proposal="Proposal from agent 2",
            reasoning="Reasoning 2",
            score=0.85,
            metadata={},
        )
        result3 = DeliberationResult(
            agent_id="agent-3",
            proposal="Proposal from agent 3",
            reasoning="Reasoning 3",
            score=0.95,
            metadata={},
        )

        multi_result = MultiAgentDeliberationResult(
            agent_results=[result1, result2, result3],
            total_agents=3,
            completed_agents=3,
            failed_agents=0,
        )

        ray_cluster = AsyncMock()
        ray_cluster.check_deliberation_status.return_value = ("completed", multi_result, None)

        stats_tracker = {
            "execution_times": [],
            "active_deliberations": 1,
            "completed_deliberations": 0,
            "failed_deliberations": 0,
        }

        deliberations_registry = {
            "delib-123": {
                "status": "running",
                "start_time": 1234567890.0,
            }
        }

        use_case = GetDeliberationStatusUseCase(
            ray_cluster=ray_cluster,
            stats_tracker=stats_tracker,
            deliberations_registry=deliberations_registry,
        )

        response = await use_case.execute("delib-123")

        # Verify response
        assert response.status == "completed"
        assert isinstance(response.result, MultiAgentDeliberationResult)
        assert response.result.total_agents == 3
        assert response.result.completed_agents == 3
        assert response.result.best_result is not None
        assert response.result.best_result.agent_id == "agent-3"  # Highest score
        assert response.error_message is None

        # Verify registry updated
        assert deliberations_registry["delib-123"]["status"] == "completed"
        assert deliberations_registry["delib-123"]["result"] == multi_result

        # Verify stats updated
        assert stats_tracker["active_deliberations"] == 0
        assert stats_tracker["completed_deliberations"] == 1

