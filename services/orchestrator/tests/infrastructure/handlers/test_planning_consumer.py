"""
Tests for OrchestratorPlanningConsumer with auto-dispatch.
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest

from services.orchestrator.infrastructure.handlers.planning_consumer import (
    OrchestratorPlanningConsumer,
)
from services.orchestrator.domain.entities import PlanApprovedEvent


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
    def mock_council_registry(self):
        """Mock CouncilRegistry."""
        mock = Mock()
        mock_council = Mock()
        mock.get_council = Mock(return_value=mock_council)
        return mock

    @pytest.fixture
    def mock_stats(self):
        """Mock OrchestratorStatistics."""
        return Mock()

    @pytest.fixture
    def consumer_with_deps(
        self, mock_council_query, mock_messaging, mock_council_registry, mock_stats
    ):
        """Create consumer with all dependencies injected."""
        return OrchestratorPlanningConsumer(
            council_query=mock_council_query,
            messaging=mock_messaging,
            council_registry=mock_council_registry,
            stats=mock_stats,
        )

    @pytest.fixture
    def consumer_without_deps(self, mock_council_query, mock_messaging):
        """Create consumer without optional dependencies."""
        return OrchestratorPlanningConsumer(
            council_query=mock_council_query,
            messaging=mock_messaging,
            council_registry=None,
            stats=None,
        )

    @pytest.mark.asyncio
    async def test_auto_dispatch_executes_deliberation(
        self, consumer_with_deps, mock_council_registry, mock_council_query
    ):
        """Test that auto-dispatch executes deliberation when dependencies are injected."""
        # Arrange
        event = PlanApprovedEvent(
            plan_id="plan-123",
            story_id="story-456",
            approved_by="po@example.com",
            roles=["DEV"],
        )

        mock_result = Mock()
        mock_result.results = [Mock(), Mock()]
        mock_result.duration_ms = 1500

        # Mock the DeliberateUseCase
        with patch(
            "services.orchestrator.infrastructure.handlers.planning_consumer.DeliberateUseCase"
        ) as MockDeliberateUseCase:
            mock_deliberate_uc = AsyncMock()
            mock_deliberate_uc.execute = AsyncMock(return_value=mock_result)
            MockDeliberateUseCase.return_value = mock_deliberate_uc

            # Mock the message
            mock_msg = AsyncMock()
            mock_msg.ack = AsyncMock()
            mock_msg.data = event.to_dict()

            # Act
            await consumer_with_deps._handle_plan_approved(mock_msg)

            # Assert
            # Verify DeliberateUseCase was created
            MockDeliberateUseCase.assert_called_once()

            # Verify execute was called
            mock_deliberate_uc.execute.assert_called_once()
            call_args = mock_deliberate_uc.execute.call_args[1]
            assert call_args["role"] == "DEV"
            assert call_args["story_id"] == "story-456"
            assert call_args["task_id"] == "plan-123"

            # Verify council was queried
            mock_council_query.has_council.assert_called_with("DEV")
            mock_council_registry.get_council.assert_called_with("DEV")

            # Verify message was acknowledged
            mock_msg.ack.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_dispatch_with_multiple_roles(
        self, consumer_with_deps, mock_council_query
    ):
        """Test auto-dispatch handles multiple roles."""
        # Arrange
        event = PlanApprovedEvent(
            plan_id="plan-123",
            story_id="story-456",
            approved_by="po@example.com",
            roles=["DEV", "QA", "DEVOPS"],
        )

        mock_result = Mock()
        mock_result.results = [Mock()]
        mock_result.duration_ms = 1000

        with patch(
            "services.orchestrator.infrastructure.handlers.planning_consumer.DeliberateUseCase"
        ) as MockDeliberateUseCase:
            mock_deliberate_uc = AsyncMock()
            mock_deliberate_uc.execute = AsyncMock(return_value=mock_result)
            MockDeliberateUseCase.return_value = mock_deliberate_uc

            mock_msg = AsyncMock()
            mock_msg.ack = AsyncMock()
            mock_msg.data = event.to_dict()

            # Act
            await consumer_with_deps._handle_plan_approved(mock_msg)

            # Assert
            # Verify DeliberateUseCase.execute was called 3 times (one per role)
            assert mock_deliberate_uc.execute.call_count == 3

            # Verify all roles were processed
            roles_called = [
                call[1]["role"] for call in mock_deliberate_uc.execute.call_args_list
            ]
            assert set(roles_called) == {"DEV", "QA", "DEVOPS"}

    @pytest.mark.asyncio
    async def test_auto_dispatch_fails_if_council_not_found(
        self, consumer_with_deps, mock_council_query
    ):
        """Test that auto-dispatch raises ValueError if council not found (fail-fast)."""
        # Arrange
        event = PlanApprovedEvent(
            plan_id="plan-123",
            story_id="story-456",
            approved_by="po@example.com",
            roles=["NONEXISTENT"],
        )

        # Mock council not found
        mock_council_query.has_council = Mock(return_value=False)

        mock_msg = AsyncMock()
        mock_msg.ack = AsyncMock()
        mock_msg.nak = AsyncMock()
        mock_msg.data = event.to_dict()

        # Act & Assert
        # The handler should catch the exception and NAK the message
        await consumer_with_deps._handle_plan_approved(mock_msg)

        # Verify message was NAKed (not ACKed)
        mock_msg.nak.assert_called_once()
        mock_msg.ack.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_dispatch_disabled_without_dependencies(
        self, consumer_without_deps
    ):
        """Test that auto-dispatch logs warning when dependencies not injected."""
        # Arrange
        event = PlanApprovedEvent(
            plan_id="plan-123",
            story_id="story-456",
            approved_by="po@example.com",
            roles=["DEV"],
        )

        mock_msg = AsyncMock()
        mock_msg.ack = AsyncMock()
        mock_msg.data = event.to_dict()

        # Act
        with patch(
            "services.orchestrator.infrastructure.handlers.planning_consumer.logger"
        ) as mock_logger:
            await consumer_without_deps._handle_plan_approved(mock_msg)

            # Assert
            # Verify warning was logged about missing dependencies
            warning_calls = [
                call for call in mock_logger.warning.call_args_list if "Auto-dispatch disabled" in str(call)
            ]
            assert len(warning_calls) == 2  # One for council_registry, one for stats

            # Verify message was still acknowledged (graceful degradation)
            mock_msg.ack.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_dispatch_continues_on_error(
        self, consumer_with_deps, mock_council_query
    ):
        """Test that auto-dispatch continues with other roles if one fails."""
        # Arrange
        event = PlanApprovedEvent(
            plan_id="plan-123",
            story_id="story-456",
            approved_by="po@example.com",
            roles=["DEV", "QA", "DEVOPS"],
        )

        mock_result = Mock()
        mock_result.results = [Mock()]
        mock_result.duration_ms = 1000

        with patch(
            "services.orchestrator.infrastructure.handlers.planning_consumer.DeliberateUseCase"
        ) as MockDeliberateUseCase:
            mock_deliberate_uc = AsyncMock()
            
            # Make second call fail
            async def execute_side_effect(*args, **kwargs):
                if kwargs["role"] == "QA":
                    raise RuntimeError("QA deliberation failed")
                return mock_result
            
            mock_deliberate_uc.execute = AsyncMock(side_effect=execute_side_effect)
            MockDeliberateUseCase.return_value = mock_deliberate_uc

            mock_msg = AsyncMock()
            mock_msg.ack = AsyncMock()
            mock_msg.data = event.to_dict()

            # Act
            await consumer_with_deps._handle_plan_approved(mock_msg)

            # Assert
            # Verify execute was called 3 times despite one failure
            assert mock_deliberate_uc.execute.call_count == 3

            # Verify message was still acknowledged (partial success)
            mock_msg.ack.assert_called_once()


class TestOrchestratorPlanningConsumerInitialization:
    """Test consumer initialization."""

    def test_init_with_all_dependencies(self):
        """Test initialization with all dependencies."""
        mock_council_query = Mock()
        mock_messaging = Mock()
        mock_council_registry = Mock()
        mock_stats = Mock()

        consumer = OrchestratorPlanningConsumer(
            council_query=mock_council_query,
            messaging=mock_messaging,
            council_registry=mock_council_registry,
            stats=mock_stats,
        )

        assert consumer.council_query == mock_council_query
        assert consumer.messaging == mock_messaging
        assert consumer.council_registry == mock_council_registry
        assert consumer.stats == mock_stats

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
        assert consumer.council_registry is None
        assert consumer.stats is None

