"""Unit tests for ExecuteDeliberationUseCase."""

from unittest.mock import AsyncMock

import pytest
from services.ray_executor.application.usecases import ExecuteDeliberationUseCase
from services.ray_executor.domain.entities import DeliberationRequest
from services.ray_executor.domain.value_objects import AgentConfig, TaskConstraints


class MockRayClusterPort:
    """Mock implementation of RayClusterPort for testing."""

    def __init__(self):
        self.submit_deliberation = AsyncMock(return_value="delib-123")
        self.check_deliberation_status = AsyncMock()
        self.get_active_jobs = AsyncMock()


class MockNATSPublisherPort:
    """Mock implementation of NATSPublisherPort for testing."""

    def __init__(self):
        self.publish_stream_event = AsyncMock()
        self.publish_deliberation_result = AsyncMock()


@pytest.mark.asyncio
async def test_execute_deliberation_happy_path():
    """Test successful deliberation submission."""
    # Arrange
    ray_cluster = MockRayClusterPort()
    nats_publisher = MockNATSPublisherPort()
    stats = {
        'total_deliberations': 0,
        'active_deliberations': 0,
        'completed_deliberations': 0,
        'failed_deliberations': 0,
        'execution_times': []
    }

    use_case = ExecuteDeliberationUseCase(
        ray_cluster=ray_cluster,
        nats_publisher=nats_publisher,
        stats_tracker=stats,
    )

    request = DeliberationRequest(
        task_id="task-123",
        task_description="Implement authentication",
        role="DEV",
        constraints=TaskConstraints(
            story_id="story-1",
            plan_id="plan-1",
            timeout_seconds=300,
            max_retries=3,
        ),
        agents=(
            AgentConfig(
                agent_id="agent-1",
                role="DEV",
                model="Qwen/Qwen2.5-Coder-7B-Instruct",
                prompt_template="You are a developer agent",
            ),
        ),
        vllm_url="http://vllm:8000",
        vllm_model="Qwen/Qwen2.5-Coder-7B-Instruct",
    )

    # Act
    result = await use_case.execute(request)

    # Assert
    assert result.status == "submitted"
    assert "deliberation-task-123-" in result.deliberation_id
    assert result.message == "Deliberation submitted to Ray cluster"

    # Verify Ray cluster was called
    ray_cluster.submit_deliberation.assert_awaited_once()

    # Verify NATS event was published
    nats_publisher.publish_stream_event.assert_awaited_once()

    # Verify stats were updated
    assert stats['total_deliberations'] == 1
    assert stats['active_deliberations'] == 1


@pytest.mark.asyncio
async def test_execute_deliberation_without_nats():
    """Test deliberation submission without NATS publisher."""
    # Arrange
    ray_cluster = MockRayClusterPort()
    stats = {
        'total_deliberations': 0,
        'active_deliberations': 0,
        'completed_deliberations': 0,
        'failed_deliberations': 0,
        'execution_times': []
    }

    use_case = ExecuteDeliberationUseCase(
        ray_cluster=ray_cluster,
        nats_publisher=None,  # No NATS
        stats_tracker=stats,
    )

    request = DeliberationRequest(
        task_id="task-123",
        task_description="Implement authentication",
        role="DEV",
        constraints=TaskConstraints(
            story_id="story-1",
            plan_id="plan-1",
        ),
        agents=(
            AgentConfig(
                agent_id="agent-1",
                role="DEV",
                model="Qwen/Qwen2.5-Coder-7B-Instruct",
            ),
        ),
        vllm_url="http://vllm:8000",
        vllm_model="Qwen/Qwen2.5-Coder-7B-Instruct",
    )

    # Act
    result = await use_case.execute(request)

    # Assert
    assert result.status == "submitted"
    assert stats['total_deliberations'] == 1


@pytest.mark.asyncio
async def test_execute_deliberation_ray_failure():
    """Test deliberation submission when Ray fails."""
    # Arrange
    ray_cluster = MockRayClusterPort()
    ray_cluster.submit_deliberation = AsyncMock(
        side_effect=Exception("Ray cluster unreachable")
    )

    stats = {
        'total_deliberations': 0,
        'active_deliberations': 0,
        'completed_deliberations': 0,
        'failed_deliberations': 0,
        'execution_times': []
    }

    use_case = ExecuteDeliberationUseCase(
        ray_cluster=ray_cluster,
        nats_publisher=None,
        stats_tracker=stats,
    )

    request = DeliberationRequest(
        task_id="task-123",
        task_description="Implement authentication",
        role="DEV",
        constraints=TaskConstraints(
            story_id="story-1",
            plan_id="plan-1",
        ),
        agents=(
            AgentConfig(
                agent_id="agent-1",
                role="DEV",
                model="Qwen/Qwen2.5-Coder-7B-Instruct",
            ),
        ),
        vllm_url="http://vllm:8000",
        vllm_model="Qwen/Qwen2.5-Coder-7B-Instruct",
    )

    # Act
    result = await use_case.execute(request)

    # Assert
    assert result.status == "failed"
    assert "Ray cluster unreachable" in result.message
    assert stats['failed_deliberations'] == 1


@pytest.mark.asyncio
async def test_execute_deliberation_validates_empty_task_id():
    """Test that empty task_id raises validation error."""
    # Act & Assert
    with pytest.raises(ValueError, match="task_id cannot be empty"):
        DeliberationRequest(
            task_id="",  # Empty task ID
            task_description="Implement authentication",
            role="DEV",
            constraints=TaskConstraints(
                story_id="story-1",
                plan_id="plan-1",
            ),
            agents=(
                AgentConfig(
                    agent_id="agent-1",
                    role="DEV",
                    model="Qwen/Qwen2.5-Coder-7B-Instruct",
                ),
            ),
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-Coder-7B-Instruct",
        )


@pytest.mark.asyncio
async def test_execute_deliberation_validates_no_agents():
    """Test that empty agents list raises validation error."""
    # Arrange & Act & Assert
    with pytest.raises(ValueError, match="At least one agent is required"):
        DeliberationRequest(
            task_id="task-123",
            task_description="Implement authentication",
            role="DEV",
            constraints=TaskConstraints(
                story_id="story-1",
                plan_id="plan-1",
            ),
            agents=(),  # No agents
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-Coder-7B-Instruct",
        )

