"""Unit tests for DeriveTasksFromPlanUseCase."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from planning.application.ports.configuration_port import ConfigurationPort
from planning.application.ports.ray_executor_port import RayExecutorPort
from planning.application.usecases.derive_tasks_from_plan_usecase import (
    DeriveTasksFromPlanUseCase,
)
from planning.domain.value_objects.identifiers.deliberation_id import DeliberationId
from planning.domain.value_objects.identifiers.plan_id import PlanId


@pytest.fixture
def mock_ray_executor() -> AsyncMock:
    """Mock Ray Executor port."""
    mock = AsyncMock(spec=RayExecutorPort)
    mock.submit_task_derivation.return_value = DeliberationId("delib-123")
    return mock


@pytest.fixture
def mock_config() -> MagicMock:
    """Mock Configuration port."""
    mock = MagicMock(spec=ConfigurationPort)
    mock.get_task_derivation_config_path.return_value = "config/task_derivation.yaml"
    mock.get_vllm_url.return_value = "http://vllm:8000"
    mock.get_vllm_model.return_value = "Qwen/Qwen2.5-7B-Instruct"
    return mock


@pytest.mark.asyncio
class TestDeriveTasksFromPlanUseCase:
    """Test suite for DeriveTasksFromPlanUseCase."""

    async def test_execute_submits_to_ray_executor(
        self,
        mock_ray_executor: AsyncMock,
        mock_config: MagicMock,
    ) -> None:
        """Test that execute submits job to Ray Executor."""
        # Given: use case with mocked dependencies
        use_case = DeriveTasksFromPlanUseCase(
            ray_executor=mock_ray_executor,
            config=mock_config,
        )

        plan_id = PlanId("plan-001")

        # When: execute use case
        result = await use_case.execute(plan_id)

        # Then: Ray Executor called
        mock_ray_executor.submit_task_derivation.assert_awaited_once()
        assert result == DeliberationId("delib-123")

    async def test_execute_with_invalid_plan_id_raises_error(
        self,
        mock_ray_executor: AsyncMock,
        mock_config: MagicMock,
    ) -> None:
        """Test that invalid plan_id raises ValueError."""
        # Given: use case
        use_case = DeriveTasksFromPlanUseCase(
            ray_executor=mock_ray_executor,
            config=mock_config,
        )

        # When/Then: invalid plan_id
        with pytest.raises(ValueError):
            await use_case.execute(PlanId(""))

