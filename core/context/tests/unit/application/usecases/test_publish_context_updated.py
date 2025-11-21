"""Tests for PublishContextUpdatedUseCase."""

from unittest.mock import AsyncMock

import pytest

from core.context.application.usecases.publish_context_updated import (
    PublishContextUpdatedUseCase,
)


class MockMessagingPort:
    """Mock MessagingPort for testing."""

    def __init__(self) -> None:
        """Initialize mock."""
        self.publish_context_updated = AsyncMock()


class TestPublishContextUpdatedUseCaseInit:
    """Test PublishContextUpdatedUseCase initialization."""

    def test_init_stores_messaging_port(self) -> None:
        """Test that __init__ stores messaging port."""
        mock_messaging = MockMessagingPort()
        use_case = PublishContextUpdatedUseCase(messaging_port=mock_messaging)

        assert use_case._messaging is mock_messaging


class TestPublishContextUpdatedUseCaseExecute:
    """Test execute method."""

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Test successful execution."""
        mock_messaging = MockMessagingPort()
        use_case = PublishContextUpdatedUseCase(messaging_port=mock_messaging)

        await use_case.execute(story_id="story-1", version=1)

        mock_messaging.publish_context_updated.assert_awaited_once_with("story-1", 1)

    @pytest.mark.asyncio
    async def test_execute_rejects_empty_story_id(self) -> None:
        """Test execute rejects empty story_id."""
        mock_messaging = MockMessagingPort()
        use_case = PublishContextUpdatedUseCase(messaging_port=mock_messaging)

        with pytest.raises(ValueError, match="story_id cannot be empty"):
            await use_case.execute(story_id="", version=1)

        mock_messaging.publish_context_updated.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_rejects_whitespace_story_id(self) -> None:
        """Test execute rejects whitespace-only story_id."""
        mock_messaging = MockMessagingPort()
        use_case = PublishContextUpdatedUseCase(messaging_port=mock_messaging)

        with pytest.raises(ValueError, match="story_id cannot be empty"):
            await use_case.execute(story_id="   ", version=1)

        mock_messaging.publish_context_updated.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_rejects_negative_version(self) -> None:
        """Test execute rejects negative version."""
        mock_messaging = MockMessagingPort()
        use_case = PublishContextUpdatedUseCase(messaging_port=mock_messaging)

        with pytest.raises(ValueError, match="version must be >= 0"):
            await use_case.execute(story_id="story-1", version=-1)

        mock_messaging.publish_context_updated.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_accepts_zero_version(self) -> None:
        """Test execute accepts zero version."""
        mock_messaging = MockMessagingPort()
        use_case = PublishContextUpdatedUseCase(messaging_port=mock_messaging)

        await use_case.execute(story_id="story-1", version=0)

        mock_messaging.publish_context_updated.assert_awaited_once_with("story-1", 0)

    @pytest.mark.asyncio
    async def test_execute_propagates_messaging_errors(self) -> None:
        """Test execute propagates errors from messaging port."""
        mock_messaging = MockMessagingPort()
        mock_messaging.publish_context_updated.side_effect = RuntimeError("Publish failed")
        use_case = PublishContextUpdatedUseCase(messaging_port=mock_messaging)

        with pytest.raises(RuntimeError, match="Publish failed"):
            await use_case.execute(story_id="story-1", version=1)

        mock_messaging.publish_context_updated.assert_awaited_once()

