"""Unit tests for idempotent_grpc_handler middleware.

Tests use mocks to avoid hitting real storage or executing real handlers.
Following repository rules: unit tests MUST NOT hit external systems.
"""

from typing import Protocol
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest


class MockRequest:
    """Mock protobuf request message."""

    def __init__(self, request_id: str | None = None) -> None:
        """Initialize mock request."""
        self.request_id = request_id


class MockResponse:
    """Mock protobuf response message."""

    def __init__(self, success: bool = True, message: str = "") -> None:
        """Initialize mock response."""
        self.success = success
        self.message = message

    def SerializeToString(self) -> bytes:
        """Serialize to bytes."""
        return f"response:{self.success}:{self.message}".encode("utf-8")

    def ParseFromString(self, data: bytes) -> None:
        """Parse from bytes."""
        decoded = data.decode("utf-8")
        parts = decoded.split(":")
        if len(parts) >= 3:
            self.success = parts[1] == "True"
            self.message = ":".join(parts[2:])


class CommandLogPortProtocol(Protocol):
    """Protocol for CommandLogPort (to avoid import issues)."""

    async def get_response(self, request_id: str) -> bytes | None:
        """Get cached response."""
        ...

    async def store_response(self, request_id: str, response_bytes: bytes) -> None:
        """Store response."""
        ...


class TestIdempotentGrpcHandler:
    """Test cases for idempotent_grpc_handler middleware."""

    @pytest.fixture
    def mock_command_log(self) -> MagicMock:
        """Create a mock CommandLogPort."""
        command_log = MagicMock(spec=CommandLogPortProtocol)
        command_log.get_response = AsyncMock(return_value=None)
        command_log.store_response = AsyncMock()
        return command_log

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock gRPC context."""
        context = MagicMock()
        context.set_code = MagicMock()
        context.set_details = MagicMock()
        return context

    @pytest.fixture
    def mock_handler(self) -> AsyncMock:
        """Create a mock handler function."""
        handler = AsyncMock(return_value=MockResponse(success=True, message="Success"))
        return handler

    @pytest.fixture
    def decorated_handler(
        self,
        mock_command_log: MagicMock,
        mock_handler: AsyncMock,
    ) -> AsyncMock:
        """Create decorated handler with middleware."""
        # Import here to avoid import errors during test collection
        from planning.infrastructure.grpc.middleware.idempotent_grpc_handler import (
            idempotent_grpc_handler,
        )
        return idempotent_grpc_handler(
            command_log=mock_command_log,
            response_type=MockResponse,
        )(mock_handler)

    @pytest.mark.asyncio
    async def test_handler_executes_when_no_cached_response(
        self,
        decorated_handler: AsyncMock,
        mock_command_log: MagicMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler executes when no cached response found."""
        request = MockRequest(request_id="test-request-id")
        mock_command_log.get_response.return_value = None

        response = await decorated_handler(request, mock_context)

        assert response.success is True
        mock_handler.assert_awaited_once_with(request, mock_context)
        mock_command_log.get_response.assert_awaited_once_with("test-request-id")

    @pytest.mark.asyncio
    async def test_handler_returns_cached_response_when_found(
        self,
        decorated_handler: AsyncMock,
        mock_command_log: MagicMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler returns cached response when found in command log."""
        request = MockRequest(request_id="test-request-id")
        cached_bytes = b"response:True:Cached response"
        mock_command_log.get_response.return_value = cached_bytes

        response = await decorated_handler(request, mock_context)

        assert response.success is True
        assert response.message == "Cached response"
        mock_handler.assert_not_awaited()
        mock_command_log.get_response.assert_awaited_once_with("test-request-id")

    @pytest.mark.asyncio
    async def test_handler_stores_response_after_successful_execution(
        self,
        decorated_handler: AsyncMock,
        mock_command_log: MagicMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler stores response after successful execution."""
        request = MockRequest(request_id="test-request-id")
        mock_command_log.get_response.return_value = None
        mock_handler.return_value = MockResponse(success=True, message="Success")

        await decorated_handler(request, mock_context)

        mock_command_log.store_response.assert_awaited_once()
        call_args = mock_command_log.store_response.call_args
        assert call_args[0][0] == "test-request-id"
        assert isinstance(call_args[0][1], bytes)

    @pytest.mark.asyncio
    async def test_handler_does_not_store_failed_response(
        self,
        decorated_handler: AsyncMock,
        mock_command_log: MagicMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler does not store failed responses."""
        request = MockRequest(request_id="test-request-id")
        mock_command_log.get_response.return_value = None
        mock_handler.return_value = MockResponse(success=False, message="Error")

        await decorated_handler(request, mock_context)

        mock_command_log.store_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handler_stores_response_without_success_field(
        self,
        mock_command_log: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test handler stores response when response has no success field."""
        # Import here to avoid import errors
        from planning.infrastructure.grpc.middleware.idempotent_grpc_handler import (
            idempotent_grpc_handler,
        )

        class ResponseWithoutSuccess:
            def SerializeToString(self) -> bytes:
                return b"response_bytes"

        mock_handler = AsyncMock(return_value=ResponseWithoutSuccess())
        decorated_handler = idempotent_grpc_handler(
            command_log=mock_command_log,
            response_type=ResponseWithoutSuccess,
        )(mock_handler)

        request = MockRequest(request_id="test-request-id")
        mock_command_log.get_response.return_value = None

        await decorated_handler(request, mock_context)

        mock_command_log.store_response.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handler_fails_fast_when_request_id_missing(
        self,
        decorated_handler: AsyncMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler fails fast when request_id field is missing."""
        request = MagicMock()
        delattr(request, "request_id")  # Remove request_id attribute

        response = await decorated_handler(request, mock_context)

        assert response.success is False
        assert "request_id field is required" in response.message
        mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
        mock_handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handler_fails_fast_when_request_id_empty(
        self,
        decorated_handler: AsyncMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler fails fast when request_id is empty."""
        request = MockRequest(request_id="")

        response = await decorated_handler(request, mock_context)

        assert response.success is False
        assert "request_id cannot be empty" in response.message
        mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
        mock_handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handler_strips_whitespace_from_request_id(
        self,
        decorated_handler: AsyncMock,
        mock_command_log: MagicMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler strips whitespace from request_id."""
        request = MockRequest(request_id="  test-request-id  ")
        mock_command_log.get_response.return_value = None

        await decorated_handler(request, mock_context)

        mock_command_log.get_response.assert_awaited_once_with("test-request-id")

    @pytest.mark.asyncio
    async def test_handler_fail_open_on_command_log_error(
        self,
        decorated_handler: AsyncMock,
        mock_command_log: MagicMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler executes anyway if command log check fails (fail-open)."""
        request = MockRequest(request_id="test-request-id")
        mock_command_log.get_response.side_effect = Exception("Storage error")

        response = await decorated_handler(request, mock_context)

        assert response.success is True
        mock_handler.assert_awaited_once_with(request, mock_context)

    @pytest.mark.asyncio
    async def test_handler_fail_open_on_store_error(
        self,
        decorated_handler: AsyncMock,
        mock_command_log: MagicMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler continues if storing response fails (best effort)."""
        request = MockRequest(request_id="test-request-id")
        mock_command_log.get_response.return_value = None
        mock_command_log.store_response.side_effect = Exception("Storage error")

        response = await decorated_handler(request, mock_context)

        assert response.success is True
        mock_handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handler_passes_additional_args(
        self,
        decorated_handler: AsyncMock,
        mock_command_log: MagicMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler passes additional args and kwargs to original handler."""
        request = MockRequest(request_id="test-request-id")
        mock_command_log.get_response.return_value = None

        await decorated_handler(request, mock_context, "arg1", "arg2", kwarg1="value1")

        mock_handler.assert_awaited_once_with(request, mock_context, "arg1", "arg2", kwarg1="value1")

    @pytest.mark.asyncio
    async def test_handler_handles_non_string_request_id(
        self,
        decorated_handler: AsyncMock,
        mock_command_log: MagicMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler converts non-string request_id to string."""
        request = MagicMock()
        request.request_id = 12345  # type: ignore[assignment]
        mock_command_log.get_response.return_value = None

        await decorated_handler(request, mock_context)

        mock_command_log.get_response.assert_awaited_once_with("12345")

    # ========== B0.5: Restart & Redelivery Tests ==========

    @pytest.mark.asyncio
    async def test_handler_returns_cached_response_after_restart(
        self,
        decorated_handler: AsyncMock,
        mock_command_log: MagicMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler returns cached response after service restart (idempotency persists)."""
        request = MockRequest(request_id="test-request-id")
        # Simulate cached response from previous execution (before restart)
        cached_bytes = b"response:True:Previous execution result"
        mock_command_log.get_response.return_value = cached_bytes

        response = await decorated_handler(request, mock_context)

        # Should return cached response without executing handler
        assert response.success is True
        assert response.message == "Previous execution result"
        mock_handler.assert_not_awaited()
        mock_command_log.get_response.assert_awaited_once_with("test-request-id")

    @pytest.mark.asyncio
    async def test_handler_stores_response_for_future_restarts(
        self,
        decorated_handler: AsyncMock,
        mock_command_log: MagicMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler stores response so future restarts can use cached response."""
        request = MockRequest(request_id="test-request-id")
        mock_command_log.get_response.return_value = None
        mock_handler.return_value = MockResponse(success=True, message="New execution")

        response = await decorated_handler(request, mock_context)

        # Handler executed
        assert response.success is True
        assert response.message == "New execution"
        mock_handler.assert_awaited_once()

        # Response should be stored for future restarts
        mock_command_log.store_response.assert_awaited_once()
        call_args = mock_command_log.store_response.call_args
        assert call_args[0][0] == "test-request-id"
        assert isinstance(call_args[0][1], bytes)

    @pytest.mark.asyncio
    async def test_handler_idempotent_after_multiple_restarts(
        self,
        decorated_handler: AsyncMock,
        mock_command_log: MagicMock,
        mock_context: MagicMock,
        mock_handler: AsyncMock,
    ) -> None:
        """Test handler is idempotent after multiple restarts and redeliveries."""
        request = MockRequest(request_id="test-request-id")
        cached_bytes = b"response:True:Original execution"

        # Simulate multiple restarts - each time returns cached response
        for attempt in range(1, 4):
            mock_command_log.get_response.return_value = cached_bytes
            response = await decorated_handler(request, mock_context)

            assert response.success is True
            assert response.message == "Original execution"
            # Handler should never be called (cached response used)
            assert mock_handler.await_count == 0

        # Verify get_response was called multiple times (once per restart)
        assert mock_command_log.get_response.await_count == 3
        # Verify handler was never called
        mock_handler.assert_not_awaited()
