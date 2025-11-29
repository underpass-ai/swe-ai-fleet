"""Unit tests for DeriveTasksFromPlanUseCase."""

from unittest.mock import AsyncMock

import pytest
from planning.application.ports.messaging_port import MessagingPort
from planning.application.ports.storage_port import StoragePort
from planning.application.usecases.derive_tasks_from_plan_usecase import (
    DeriveTasksFromPlanUseCase,
)
from planning.domain.value_objects.identifiers.plan_id import PlanId


@pytest.fixture
def mock_storage() -> AsyncMock:
    """Mock Storage port."""
    return AsyncMock(spec=StoragePort)


@pytest.fixture
def mock_messaging() -> AsyncMock:
    """Mock Messaging port."""
    return AsyncMock(spec=MessagingPort)


@pytest.mark.asyncio
class TestDeriveTasksFromPlanUseCase:
    """Test suite for DeriveTasksFromPlanUseCase."""

    async def test_execute_publishes_event_to_nats(
        self,
        mock_storage: AsyncMock,
        mock_messaging: AsyncMock,
    ) -> None:
        """Test that execute publishes task.derivation.requested event to NATS."""
        from planning.domain.entities.plan import Plan
        from planning.domain.value_objects.identifiers.story_id import StoryId

        # Given: use case with mocked dependencies
        mock_plan = AsyncMock(spec=Plan)
        # Mocking list/tuple behavior for story_ids
        mock_plan.story_ids = (StoryId("story-001"), StoryId("story-002"))
        mock_plan.roles = ["developer", "qa"]

        mock_storage.get_plan.return_value = mock_plan

        use_case = DeriveTasksFromPlanUseCase(
            storage=mock_storage,
            messaging=mock_messaging,
        )

        plan_id = PlanId("plan-001")

        # When: execute use case
        deliberation_id = await use_case.execute(plan_id)

        # Then: Event published to NATS with correct subject and payload
        mock_messaging.publish_event.assert_awaited_once()
        call_args = mock_messaging.publish_event.call_args

        # Verify subject
        assert call_args.kwargs["subject"] == "task.derivation.requested"

        # Verify payload structure
        payload = call_args.kwargs["payload"]
        assert payload["event_type"] == "task.derivation.requested"
        assert payload["plan_id"] == "plan-001"
        assert payload["story_id"] == "story-001"  # Primary story
        assert payload["story_ids"] == ["story-001", "story-002"]  # All stories
        assert payload["roles"] == ["developer", "qa"]
        assert "deliberation_id" in payload
        assert "requested_at" in payload
        assert "requested_by" in payload

        # Verify deliberation_id returned
        assert deliberation_id.value.startswith("derive-")

    async def test_execute_validates_plan_exists(
        self,
        mock_storage: AsyncMock,
        mock_messaging: AsyncMock,
    ) -> None:
        """Test that execute raises ValueError if plan not found."""
        # Given: storage returns None for missing plan
        mock_storage.get_plan.return_value = None

        use_case = DeriveTasksFromPlanUseCase(
            storage=mock_storage,
            messaging=mock_messaging,
        )

        # When/Then: missing plan raises error
        with pytest.raises(ValueError, match="Plan not found"):
            await use_case.execute(PlanId("plan-missing"))

        # Verify no event was published
        mock_messaging.publish_event.assert_not_awaited()

    async def test_execute_propagates_messaging_error(
        self,
        mock_storage: AsyncMock,
        mock_messaging: AsyncMock,
    ) -> None:
        """Test that execute propagates messaging failures."""
        from planning.domain.entities.plan import Plan
        from planning.domain.value_objects.identifiers.story_id import StoryId

        # Given: messaging fails
        mock_plan = AsyncMock(spec=Plan)
        mock_plan.story_ids = (StoryId("story-001"),)
        mock_plan.roles = ["developer"]

        mock_storage.get_plan.return_value = mock_plan
        mock_messaging.publish_event.side_effect = Exception("NATS connection failed")

        use_case = DeriveTasksFromPlanUseCase(
            storage=mock_storage,
            messaging=mock_messaging,
        )

        # When/Then: messaging error propagates
        with pytest.raises(Exception, match="NATS connection failed"):
            await use_case.execute(PlanId("plan-001"))
