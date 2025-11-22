"""Tests for PublishRehydrateSessionResponseUseCase."""

from unittest.mock import AsyncMock

import pytest
from core.context.application.usecases.publish_rehydrate_session_response import (
    PublishRehydrateSessionResponseUseCase,
)
from core.context.infrastructure.dtos.rehydrate_session_response_dto import (
    RehydrateSessionResponseDTO,
    RehydrationStatsDTO,
)


class MockMessagingPort:
    """Mock MessagingPort for testing."""

    def __init__(self) -> None:
        """Initialize mock."""
        self.publish_rehydrate_session_response = AsyncMock()


class TestPublishRehydrateSessionResponseUseCaseInit:
    """Test PublishRehydrateSessionResponseUseCase initialization."""

    def test_init_stores_messaging_port(self) -> None:
        """Test that __init__ stores messaging port."""
        mock_messaging = MockMessagingPort()
        use_case = PublishRehydrateSessionResponseUseCase(messaging_port=mock_messaging)

        assert use_case._messaging is mock_messaging


class TestPublishRehydrateSessionResponseUseCaseExecute:
    """Test execute method."""

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Test successful execution."""
        mock_messaging = MockMessagingPort()
        use_case = PublishRehydrateSessionResponseUseCase(messaging_port=mock_messaging)

        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV", "QA"],
        )

        response_dto = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats,
        )

        await use_case.execute(response_dto)

        mock_messaging.publish_rehydrate_session_response.assert_awaited_once_with(response_dto)

    @pytest.mark.asyncio
    async def test_execute_rejects_empty_case_id(self) -> None:
        """Test execute rejects empty case_id in DTO."""
        mock_messaging = MockMessagingPort()
        use_case = PublishRehydrateSessionResponseUseCase(messaging_port=mock_messaging)

        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        response_dto = RehydrateSessionResponseDTO(
            case_id="",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats,
        )

        with pytest.raises(ValueError, match="case_id cannot be empty"):
            await use_case.execute(response_dto)

        mock_messaging.publish_rehydrate_session_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_rejects_whitespace_case_id(self) -> None:
        """Test execute rejects whitespace-only case_id in DTO."""
        mock_messaging = MockMessagingPort()
        use_case = PublishRehydrateSessionResponseUseCase(messaging_port=mock_messaging)

        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        response_dto = RehydrateSessionResponseDTO(
            case_id="   ",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats,
        )

        with pytest.raises(ValueError, match="case_id cannot be empty"):
            await use_case.execute(response_dto)

        mock_messaging.publish_rehydrate_session_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_rejects_negative_generated_at_ms(self) -> None:
        """Test execute rejects negative generated_at_ms."""
        mock_messaging = MockMessagingPort()
        use_case = PublishRehydrateSessionResponseUseCase(messaging_port=mock_messaging)

        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        response_dto = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=-1,
            packs_count=2,
            stats=stats,
        )

        with pytest.raises(ValueError, match="generated_at_ms must be >= 0"):
            await use_case.execute(response_dto)

        mock_messaging.publish_rehydrate_session_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_accepts_zero_generated_at_ms(self) -> None:
        """Test execute accepts zero generated_at_ms."""
        mock_messaging = MockMessagingPort()
        use_case = PublishRehydrateSessionResponseUseCase(messaging_port=mock_messaging)

        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        response_dto = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=0,
            packs_count=2,
            stats=stats,
        )

        await use_case.execute(response_dto)

        mock_messaging.publish_rehydrate_session_response.assert_awaited_once_with(response_dto)

    @pytest.mark.asyncio
    async def test_execute_propagates_messaging_errors(self) -> None:
        """Test execute propagates errors from messaging port."""
        mock_messaging = MockMessagingPort()
        mock_messaging.publish_rehydrate_session_response.side_effect = RuntimeError("Publish failed")
        use_case = PublishRehydrateSessionResponseUseCase(messaging_port=mock_messaging)

        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        response_dto = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats,
        )

        with pytest.raises(RuntimeError, match="Failed to publish rehydrate session response"):
            await use_case.execute(response_dto)

        mock_messaging.publish_rehydrate_session_response.assert_awaited_once()

