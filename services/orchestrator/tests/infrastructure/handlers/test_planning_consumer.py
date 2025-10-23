"""
Tests for OrchestratorPlanningConsumer with auto-dispatch.
"""
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from services.orchestrator.domain.entities import PlanApprovedEvent
from services.orchestrator.infrastructure.handlers.planning_consumer import (
    OrchestratorPlanningConsumer,
)


def create_test_plan_approved_event(**kwargs):
    """Helper to create PlanApprovedEvent with defaults for testing."""
    defaults = {
        "story_id": "story-456",
        "plan_id": "plan-123",
        "approved_by": "po@example.com",
        "roles": ["DEV"],
        "timestamp": datetime.now(UTC).isoformat(),
    }
    defaults.update(kwargs)
    return PlanApprovedEvent(**defaults)


class TestOrchestratorPlanningConsumerAutoDispatch:
    """Test auto-dispatch functionality in planning consumer."""

    @pytest.fixture
    def mock_council_query(self):
        """Mock CouncilQueryPort."""
        mock = Mock()
        mock.has_council = Mock(return_value=True)
        return mock

    @pytest.fixture
    def mock_messaging(self):
        """Mock MessagingPort."""
        mock = AsyncMock()
        mock.publish_dict = AsyncMock()
        return mock

    @pytest.fixture
    def mock_auto_dispatch_service(self):
        """Mock AutoDispatchService."""
        mock = AsyncMock()
        mock.dispatch_deliberations_for_plan = AsyncMock(return_value={
            "total_roles": 1,
            "successful": 1,
            "failed": 0,
            "results": [{"role": "DEV", "success": True}]
        })
        return mock

    @pytest.fixture
    def consumer_with_deps(self, mock_council_query, mock_messaging, mock_auto_dispatch_service):
        """Create consumer with all dependencies injected."""
        return OrchestratorPlanningConsumer(
            council_query=mock_council_query,
            messaging=mock_messaging,
            auto_dispatch_service=mock_auto_dispatch_service,
        )

    @pytest.fixture
    def consumer_without_deps(self, mock_council_query, mock_messaging):
        """Create consumer without optional dependencies."""
        return OrchestratorPlanningConsumer(
            council_query=mock_council_query,
            messaging=mock_messaging,
            auto_dispatch_service=None,
        )

    @pytest.mark.asyncio
    async def test_auto_dispatch_executes_deliberation(
        self, consumer_with_deps, mock_auto_dispatch_service
    ):
        """Test that auto-dispatch delegates to AutoDispatchService."""
        # Arrange
        event = create_test_plan_approved_event(roles=["DEV"])

        mock_msg = AsyncMock()
        mock_msg.ack = AsyncMock()
        # Mock msg.data as bytes (as NATS would provide)
        mock_msg.data = json.dumps(event.to_dict()).encode('utf-8')

        # Act
        await consumer_with_deps._handle_plan_approved(mock_msg)

        # Assert
        # Verify AutoDispatchService was called with the event
        mock_auto_dispatch_service.dispatch_deliberations_for_plan.assert_called_once_with(event)

        # Verify message was acknowledged
        mock_msg.ack.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_dispatch_with_multiple_roles(
        self, consumer_with_deps, mock_auto_dispatch_service
    ):
        """Test auto-dispatch delegates to service with multiple roles."""
        # Arrange
        event = create_test_plan_approved_event(roles=["DEV", "QA", "DEVOPS"])
        
        # Mock service response for multiple roles
        mock_auto_dispatch_service.dispatch_deliberations_for_plan.return_value = {
            "total_roles": 3,
            "successful": 3,
            "failed": 0,
            "results": [
                {"role": "DEV", "success": True},
                {"role": "QA", "success": True},
                {"role": "DEVOPS", "success": True}
            ]
        }

        mock_msg = AsyncMock()
        mock_msg.ack = AsyncMock()
        mock_msg.data = json.dumps(event.to_dict()).encode("utf-8")

        # Act
        await consumer_with_deps._handle_plan_approved(mock_msg)

        # Assert
        # Verify AutoDispatchService was called
        mock_auto_dispatch_service.dispatch_deliberations_for_plan.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_auto_dispatch_service_handles_errors(
        self, consumer_with_deps, mock_auto_dispatch_service
    ):
        """Test that consumer handles errors from AutoDispatchService gracefully."""
        # Arrange
        event = create_test_plan_approved_event(roles=["NONEXISTENT"])

        # Mock service raising an error
        mock_auto_dispatch_service.dispatch_deliberations_for_plan.side_effect = ValueError(
            "Council for role 'NONEXISTENT' not found"
        )

        mock_msg = AsyncMock()
        mock_msg.ack = AsyncMock()
        mock_msg.nak = AsyncMock()
        mock_msg.data = json.dumps(event.to_dict()).encode("utf-8")

        # Act
        await consumer_with_deps._handle_plan_approved(mock_msg)

        # Assert
        # Verify message was NAKed due to exception
        mock_msg.nak.assert_called_once()
        mock_msg.ack.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_dispatch_disabled_without_dependencies(
        self, consumer_without_deps
    ):
        """Test that auto-dispatch logs warning when service not injected."""
        # Arrange
        event = create_test_plan_approved_event(roles=["DEV"])

        mock_msg = AsyncMock()
        mock_msg.ack = AsyncMock()
        mock_msg.data = json.dumps(event.to_dict()).encode("utf-8")

        # Act
        with patch(
            "services.orchestrator.infrastructure.handlers.planning_consumer.logger"
        ) as mock_logger:
            await consumer_without_deps._handle_plan_approved(mock_msg)

            # Assert
            # Verify warning was logged about missing service
            warning_calls = [
                call for call in mock_logger.warning.call_args_list 
                if "Auto-dispatch disabled" in str(call)
            ]
            assert len(warning_calls) == 1  # One warning for auto_dispatch_service

            # Verify message was still acknowledged (graceful degradation)
            mock_msg.ack.assert_called_once()


class TestOrchestratorPlanningConsumerInitialization:
    """Test consumer initialization."""

    def test_init_with_all_dependencies(self):
        """Test initialization with all dependencies."""
        mock_council_query = Mock()
        mock_messaging = Mock()
        mock_auto_dispatch_service = Mock()

        consumer = OrchestratorPlanningConsumer(
            council_query=mock_council_query,
            messaging=mock_messaging,
            auto_dispatch_service=mock_auto_dispatch_service,
        )

        assert consumer.council_query == mock_council_query
        assert consumer.messaging == mock_messaging
        assert consumer._auto_dispatch_service == mock_auto_dispatch_service

    def test_init_without_optional_dependencies(self):
        """Test initialization without optional dependencies (backwards compatible)."""
        mock_council_query = Mock()
        mock_messaging = Mock()

        consumer = OrchestratorPlanningConsumer(
            council_query=mock_council_query,
            messaging=mock_messaging,
        )

        assert consumer.council_query == mock_council_query
        assert consumer.messaging == mock_messaging
        assert consumer._auto_dispatch_service is None

