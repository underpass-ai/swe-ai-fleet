"""Tests for ContextServiceAdapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest
from grpc import aio

from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.infrastructure.adapters.context_service_adapter import (
    ContextServiceAdapter,
    ContextServiceError,
)


@pytest.fixture
def mock_context_pb2_grpc():
    """Mock context_pb2_grpc module."""
    mock_module = MagicMock()
    mock_stub = MagicMock()
    mock_module.ContextServiceStub = MagicMock(return_value=mock_stub)
    return mock_module, mock_stub


@pytest.fixture
def context_adapter(mock_context_pb2_grpc):
    """Create ContextServiceAdapter instance with mocked gRPC."""
    mock_module, mock_stub = mock_context_pb2_grpc
    mock_channel = MagicMock()
    # Make channel.close() awaitable
    mock_channel.close = AsyncMock()

    with patch("grpc.aio.insecure_channel", return_value=mock_channel):
        with patch(
            "planning.infrastructure.adapters.context_service_adapter.context_pb2_grpc",
            mock_module,
        ):
            adapter = ContextServiceAdapter(grpc_address="localhost:50054", timeout_seconds=5.0)
            # Set the mock stub for testing
            adapter._stub = mock_stub
            yield adapter


@pytest.mark.asyncio
async def test_get_context_success(context_adapter):
    """Test successful context retrieval."""
    # Mock response
    mock_response = MagicMock()
    mock_response.context = "Formatted context blocks"
    mock_response.token_count = 150

    context_adapter._stub.GetContext = AsyncMock(return_value=mock_response)

    story_id = StoryId("story-001")
    result = await context_adapter.get_context(
        story_id=story_id,
        role="developer",
        phase="plan",
    )

    assert result == "Formatted context blocks"
    context_adapter._stub.GetContext.assert_awaited_once()

    await context_adapter.close()


@pytest.mark.asyncio
async def test_get_context_reuses_initialized_channel(context_adapter, mock_context_pb2_grpc):
    """Test that channel and stub are reused (initialized in __init__)."""
    mock_module, mock_stub = mock_context_pb2_grpc

    mock_response = MagicMock()
    mock_response.context = "Context"
    mock_response.token_count = 100
    mock_stub.GetContext = AsyncMock(return_value=mock_response)

    story_id = StoryId("story-001")

    # First call uses already-initialized channel
    await context_adapter.get_context(
        story_id=story_id,
        role="developer",
        phase="plan",
    )

    # Second call reuses the same channel
    await context_adapter.get_context(
        story_id=story_id,
        role="developer",
        phase="plan",
    )

    # Verify stub was called twice (channel reused)
    assert mock_stub.GetContext.await_count == 2

    await context_adapter.close()


@pytest.mark.asyncio
async def test_get_context_grpc_error(context_adapter):
    """Test handling of gRPC errors."""
    # Mock gRPC error
    grpc_error = grpc.RpcError()
    grpc_error.code = MagicMock(return_value=grpc.StatusCode.NOT_FOUND)
    grpc_error.details = MagicMock(return_value="Story not found")

    context_adapter._stub.GetContext = AsyncMock(side_effect=grpc_error)

    story_id = StoryId("story-001")

    with pytest.raises(ContextServiceError) as exc_info:
        await context_adapter.get_context(
            story_id=story_id,
            role="developer",
            phase="plan",
        )

    assert "gRPC error calling Context Service" in str(exc_info.value)
    assert "NOT_FOUND" in str(exc_info.value) or "Story not found" in str(
        exc_info.value
    )

    await context_adapter.close()


@pytest.mark.asyncio
async def test_get_context_unexpected_error(context_adapter):
    """Test handling of unexpected errors."""
    # Mock unexpected error
    context_adapter._stub.GetContext = AsyncMock(side_effect=ValueError("Unexpected error"))

    story_id = StoryId("story-001")

    with pytest.raises(ContextServiceError) as exc_info:
        await context_adapter.get_context(
            story_id=story_id,
            role="developer",
            phase="plan",
        )

    assert "Unexpected error calling Context Service" in str(exc_info.value)

    await context_adapter.close()




def test_context_adapter_init_rejects_empty_address():
    """Test that adapter rejects empty grpc_address."""
    with pytest.raises(ValueError, match="grpc_address cannot be empty"):
        ContextServiceAdapter(grpc_address="")

    with pytest.raises(ValueError, match="grpc_address cannot be empty"):
        ContextServiceAdapter(grpc_address="   ")


def test_context_adapter_init_accepts_valid_address(mock_context_pb2_grpc):
    """Test that adapter accepts valid grpc_address."""
    mock_module, mock_stub = mock_context_pb2_grpc
    mock_channel = MagicMock()

    with patch("grpc.aio.insecure_channel", return_value=mock_channel):
        with patch(
            "planning.infrastructure.adapters.context_service_adapter.context_pb2_grpc",
            mock_module,
        ):
            adapter = ContextServiceAdapter(grpc_address="context-service:50054")
            assert adapter._address == "context-service:50054"
            assert adapter._timeout == 5.0
            assert adapter._channel is not None
            assert adapter._stub is not None


def test_context_adapter_init_custom_timeout(mock_context_pb2_grpc):
    """Test that adapter accepts custom timeout."""
    mock_module, mock_stub = mock_context_pb2_grpc
    mock_channel = MagicMock()

    with patch("grpc.aio.insecure_channel", return_value=mock_channel):
        with patch(
            "planning.infrastructure.adapters.context_service_adapter.context_pb2_grpc",
            mock_module,
        ):
            adapter = ContextServiceAdapter(
                grpc_address="context-service:50054", timeout_seconds=10.0
            )
            assert adapter._timeout == 10.0


@pytest.mark.asyncio
async def test_context_adapter_close(context_adapter):
    """Test that close() closes the channel."""
    # Get the mock channel from the fixture (it's already set up)
    mock_channel = context_adapter._channel
    # Make sure close is awaitable
    mock_channel.close = AsyncMock()
    context_adapter._stub = MagicMock()

    await context_adapter.close()

    mock_channel.close.assert_awaited_once()
    # After close(), channel and stub should be None
    assert context_adapter._channel is None
    assert context_adapter._stub is None


@pytest.mark.asyncio
async def test_context_adapter_close_no_channel(context_adapter):
    """Test that close() handles case when channel is None."""
    context_adapter._channel = None
    context_adapter._stub = None

    # Should not raise
    await context_adapter.close()

    assert context_adapter._channel is None
    assert context_adapter._stub is None

