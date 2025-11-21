"""Tests for PublishUpdateContextResponseUseCase."""

from unittest.mock import AsyncMock

import pytest
from core.context.application.usecases.publish_update_context_response import (
    PublishUpdateContextResponseUseCase,
)
from core.context.infrastructure.dtos.update_context_response_dto import (
    UpdateContextResponseDTO,
)


class MockMessagingPort:
    """Mock MessagingPort for testing."""

    def __init__(self) -> None:
        """Initialize mock."""
        self.publish_update_context_response = AsyncMock()


class TestPublishUpdateContextResponseUseCaseInit:
    """Test PublishUpdateContextResponseUseCase initialization."""

    def test_init_stores_messaging_port(self) -> None:
        """Test that __init__ stores messaging port."""
        mock_messaging = MockMessagingPort()
        use_case = PublishUpdateContextResponseUseCase(messaging_port=mock_messaging)

        assert use_case._messaging is mock_messaging


class TestPublishUpdateContextResponseUseCaseExecute:
    """Test execute method."""

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Test successful execution."""
        mock_messaging = MockMessagingPort()
        use_case = PublishUpdateContextResponseUseCase(messaging_port=mock_messaging)

        response_dto = UpdateContextResponseDTO(
            story_id="story-1",
            status="success",
            version=1,
            hash="abc123",
            warnings=[],
        )

        await use_case.execute(response_dto)

        mock_messaging.publish_update_context_response.assert_awaited_once_with(response_dto)

    @pytest.mark.asyncio
    async def test_execute_rejects_empty_story_id(self) -> None:
        """Test execute rejects empty story_id in DTO."""
        mock_messaging = MockMessagingPort()
        use_case = PublishUpdateContextResponseUseCase(messaging_port=mock_messaging)

        response_dto = UpdateContextResponseDTO(
            story_id="",
            status="success",
            version=1,
            hash="abc123",
            warnings=[],
        )

        with pytest.raises(ValueError, match="story_id cannot be empty"):
            await use_case.execute(response_dto)

        mock_messaging.publish_update_context_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_rejects_whitespace_story_id(self) -> None:
        """Test execute rejects whitespace-only story_id in DTO."""
        mock_messaging = MockMessagingPort()
        use_case = PublishUpdateContextResponseUseCase(messaging_port=mock_messaging)

        response_dto = UpdateContextResponseDTO(
            story_id="   ",
            status="success",
            version=1,
            hash="abc123",
            warnings=[],
        )

        with pytest.raises(ValueError, match="story_id cannot be empty"):
            await use_case.execute(response_dto)

        mock_messaging.publish_update_context_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_rejects_negative_version(self) -> None:
        """Test execute rejects negative version."""
        mock_messaging = MockMessagingPort()
        use_case = PublishUpdateContextResponseUseCase(messaging_port=mock_messaging)

        response_dto = UpdateContextResponseDTO(
            story_id="story-1",
            status="success",
            version=-1,
            hash="abc123",
            warnings=[],
        )

        with pytest.raises(ValueError, match="version must be >= 0"):
            await use_case.execute(response_dto)

        mock_messaging.publish_update_context_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_accepts_zero_version(self) -> None:
        """Test execute accepts zero version."""
        mock_messaging = MockMessagingPort()
        use_case = PublishUpdateContextResponseUseCase(messaging_port=mock_messaging)

        response_dto = UpdateContextResponseDTO(
            story_id="story-1",
            status="success",
            version=0,
            hash="abc123",
            warnings=[],
        )

        await use_case.execute(response_dto)

        mock_messaging.publish_update_context_response.assert_awaited_once_with(response_dto)

    @pytest.mark.asyncio
    async def test_execute_propagates_messaging_errors(self) -> None:
        """Test execute propagates errors from messaging port."""
        mock_messaging = MockMessagingPort()
        mock_messaging.publish_update_context_response.side_effect = RuntimeError("Publish failed")
        use_case = PublishUpdateContextResponseUseCase(messaging_port=mock_messaging)

        response_dto = UpdateContextResponseDTO(
            story_id="story-1",
            status="success",
            version=1,
            hash="abc123",
            warnings=[],
        )

        with pytest.raises(RuntimeError, match="Failed to publish update context response"):
            await use_case.execute(response_dto)

        mock_messaging.publish_update_context_response.assert_awaited_once()

