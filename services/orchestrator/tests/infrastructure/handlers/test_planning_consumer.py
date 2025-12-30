"""
Tests for OrchestratorPlanningConsumer with auto-dispatch.
"""
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from services.orchestrator.domain.entities import PlanApprovedEvent
from services.orchestrator.infrastructure.handlers.planning_consumer import (
    OrchestratorPlanningConsumer,
)


def _envelope_bytes(event_type: str, payload: dict[str, object]) -> bytes:
    envelope = EventEnvelope(
        event_type=event_type,
        payload=payload,
        idempotency_key=f"idemp-test-{event_type}",
        correlation_id=f"corr-test-{event_type}",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="orchestrator-tests",
    )
    return json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")


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
        mock_msg.data = _envelope_bytes("planning.plan.approved", event.to_dict())

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
        mock_msg.data = _envelope_bytes("planning.plan.approved", event.to_dict())

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
        mock_msg.data = _envelope_bytes("planning.plan.approved", event.to_dict())

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
        mock_msg.data = _envelope_bytes("planning.plan.approved", event.to_dict())

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


class TestOrchestratorPlanningConsumerStoryTransitions:
    """Additional tests for story transition handling."""

    @pytest.mark.asyncio
    async def test_handle_story_transitioned_non_trigger_phase_acks(self, mocker) -> None:
        mock_council_query = Mock()
        mock_messaging = AsyncMock()

        consumer = OrchestratorPlanningConsumer(
            council_query=mock_council_query,
            messaging=mock_messaging,
        )

        event_data = {
            "story_id": "story-001",
            "from_phase": "PLAN",
            "to_phase": "DISCOVER",  # Not in [\"BUILD\", \"TEST\"]
            "timestamp": "2025-10-24T12:00:00Z",
        }

        mock_msg = AsyncMock()
        mock_msg.data = _envelope_bytes("planning.story.transitioned", event_data)

        await consumer._handle_story_transitioned(mock_msg)

        mock_msg.ack.assert_called_once()
        mock_messaging.publish_dict.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_story_transitioned_publish_error_does_not_nak(self, mocker) -> None:
        mock_council_query = Mock()
        mock_messaging = AsyncMock()
        mock_messaging.publish_dict.side_effect = Exception("publish failed")

        consumer = OrchestratorPlanningConsumer(
            council_query=mock_council_query,
            messaging=mock_messaging,
        )

        event_data = {
            "story_id": "story-001",
            "from_phase": "PLAN",
            "to_phase": "BUILD",
            "timestamp": "2025-10-24T12:00:00Z",
        }

        mock_msg = AsyncMock()
        mock_msg.data = _envelope_bytes("planning.story.transitioned", event_data)

        await consumer._handle_story_transitioned(mock_msg)

        mock_msg.ack.assert_called_once()
        mock_msg.nak.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_story_transitioned_invalid_json_naks(self, mocker) -> None:
        mock_council_query = Mock()
        mock_messaging = AsyncMock()

        consumer = OrchestratorPlanningConsumer(
            council_query=mock_council_query,
            messaging=mock_messaging,
        )

        mock_msg = AsyncMock()
        mock_msg.data = b"not-json"

        await consumer._handle_story_transitioned(mock_msg)

        mock_msg.nak.assert_called_once()
        mock_msg.ack.assert_not_called()


class TestOrchestratorPlanningConsumerPlanApprovedBranches:
    """Additional tests for plan approved handling branches."""

    @pytest.mark.asyncio
    async def test_handle_plan_approved_text_message_branch(self, mocker) -> None:
        mock_council_query = Mock()
        mock_messaging = AsyncMock()

        consumer = OrchestratorPlanningConsumer(
            council_query=mock_council_query,
            messaging=mock_messaging,
        )

        mock_msg = AsyncMock()
        mock_msg.ack = AsyncMock()
        mock_msg.nak = AsyncMock()
        # Invalid JSON should be NAKed (no legacy fallback)
        mock_msg.data = b"this-is-not-json"

        await consumer._handle_plan_approved(mock_msg)

        mock_msg.nak.assert_called_once()
        mock_msg.ack.assert_not_called()
        mock_messaging.publish_dict.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_plan_approved_with_empty_roles_skips_auto_dispatch(self, mocker) -> None:
        mock_council_query = Mock()
        mock_messaging = AsyncMock()
        mock_auto_dispatch = AsyncMock()

        consumer = OrchestratorPlanningConsumer(
            council_query=mock_council_query,
            messaging=mock_messaging,
            auto_dispatch_service=mock_auto_dispatch,
        )

        event = create_test_plan_approved_event(roles=[])

        mock_msg = AsyncMock()
        mock_msg.ack = AsyncMock()
        mock_msg.data = _envelope_bytes("planning.plan.approved", event.to_dict())

        await consumer._handle_plan_approved(mock_msg)

        mock_auto_dispatch.dispatch_deliberations_for_plan.assert_not_called()
        mock_msg.ack.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_plan_approved_publish_error_does_not_nak(self, mocker) -> None:
        mock_council_query = Mock()
        mock_messaging = AsyncMock()
        mock_messaging.publish_dict.side_effect = Exception("publish failed")

        consumer = OrchestratorPlanningConsumer(
            council_query=mock_council_query,
            messaging=mock_messaging,
        )

        event = create_test_plan_approved_event(roles=["DEV"])

        mock_msg = AsyncMock()
        mock_msg.ack = AsyncMock()
        mock_msg.data = _envelope_bytes("planning.plan.approved", event.to_dict())

        await consumer._handle_plan_approved(mock_msg)

        mock_msg.ack.assert_called_once()
        mock_msg.nak.assert_not_called()


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

