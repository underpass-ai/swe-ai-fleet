"""Tests for ServicerContextErrorHandler."""

import grpc
import pytest

from services.context.infrastructure.adapters.internal_servicer_context import (
    InternalServicerContext,
)
from services.context.infrastructure.adapters.servicer_context_error_handler import (
    ServicerContextErrorHandler,
)


class TestServicerContextErrorHandlerCheckAndRaise:
    """Test check_and_raise method."""

    def test_check_and_raise_does_nothing_when_no_error(self) -> None:
        """Test that check_and_raise does nothing when no error."""
        context = InternalServicerContext()

        # Should not raise
        ServicerContextErrorHandler.check_and_raise(context, "TestOperation")

    def test_check_and_raise_raises_when_error_exists(self) -> None:
        """Test that check_and_raise raises when error exists."""
        context = InternalServicerContext()

        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details("Invalid argument provided")

        with pytest.raises(RuntimeError, match="TestOperation failed: INVALID_ARGUMENT - Invalid argument provided"):
            ServicerContextErrorHandler.check_and_raise(context, "TestOperation")

    def test_check_and_raise_formats_error_message_correctly(self) -> None:
        """Test that check_and_raise formats error message correctly."""
        context = InternalServicerContext()

        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("Resource not found")

        with pytest.raises(RuntimeError) as exc_info:
            ServicerContextErrorHandler.check_and_raise(context, "GetResource")

        assert "GetResource failed" in str(exc_info.value)
        assert "NOT_FOUND" in str(exc_info.value)
        assert "Resource not found" in str(exc_info.value)

    def test_check_and_raise_with_different_status_codes(self) -> None:
        """Test check_and_raise with different gRPC status codes."""
        test_cases = [
            (grpc.StatusCode.INVALID_ARGUMENT, "Invalid argument"),
            (grpc.StatusCode.NOT_FOUND, "Not found"),
            (grpc.StatusCode.INTERNAL, "Internal error"),
            (grpc.StatusCode.UNAVAILABLE, "Service unavailable"),
        ]

        for code, details in test_cases:
            context = InternalServicerContext()
            context.set_code(code)
            context.set_details(details)

            with pytest.raises(RuntimeError) as exc_info:
                ServicerContextErrorHandler.check_and_raise(context, "TestOp")

            assert code.name in str(exc_info.value)
            assert details in str(exc_info.value)

