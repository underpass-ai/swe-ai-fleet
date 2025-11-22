"""Tests for InternalServicerContext."""

import grpc
import pytest
from services.context.infrastructure.adapters.internal_servicer_context import (
    InternalServicerContext,
)
from services.context.infrastructure.adapters.servicer_error import ServicerError


class TestInternalServicerContextInit:
    """Test InternalServicerContext initialization."""

    def test_init_sets_no_error_state(self) -> None:
        """Test that __init__ sets no error state."""
        context = InternalServicerContext()

        assert context._has_error is False
        assert context._error_code == grpc.StatusCode.OK
        assert context._error_details == ""

    def test_has_error_returns_false_initially(self) -> None:
        """Test that has_error returns False initially."""
        context = InternalServicerContext()

        assert context.has_error() is False


class TestInternalServicerContextSetCode:
    """Test set_code method."""

    def test_set_code_sets_error_state(self) -> None:
        """Test that set_code sets error state."""
        context = InternalServicerContext()

        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)

        assert context._has_error is True
        assert context._error_code == grpc.StatusCode.INVALID_ARGUMENT
        assert context.has_error() is True

    def test_set_code_overwrites_previous_code(self) -> None:
        """Test that set_code overwrites previous code."""
        context = InternalServicerContext()

        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_code(grpc.StatusCode.NOT_FOUND)

        assert context._error_code == grpc.StatusCode.NOT_FOUND


class TestInternalServicerContextSetDetails:
    """Test set_details method."""

    def test_set_details_stores_details(self) -> None:
        """Test that set_details stores details."""
        context = InternalServicerContext()

        context.set_details("Error details")

        assert context._error_details == "Error details"

    def test_set_details_overwrites_previous_details(self) -> None:
        """Test that set_details overwrites previous details."""
        context = InternalServicerContext()

        context.set_details("First details")
        context.set_details("Second details")

        assert context._error_details == "Second details"


class TestInternalServicerContextGetError:
    """Test get_error method."""

    def test_get_error_raises_when_no_error(self) -> None:
        """Test that get_error raises when no error is set."""
        context = InternalServicerContext()

        with pytest.raises(RuntimeError, match="No error set on context"):
            context.get_error()

    def test_get_error_returns_servicer_error_when_error_set(self) -> None:
        """Test that get_error returns ServicerError when error is set."""
        context = InternalServicerContext()

        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details("Invalid argument provided")

        error = context.get_error()

        assert isinstance(error, ServicerError)
        assert error.code == grpc.StatusCode.INVALID_ARGUMENT
        assert error.details == "Invalid argument provided"

    def test_get_error_uses_latest_code_and_details(self) -> None:
        """Test that get_error uses latest code and details."""
        context = InternalServicerContext()

        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details("First details")
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("Second details")

        error = context.get_error()

        assert error.code == grpc.StatusCode.NOT_FOUND
        assert error.details == "Second details"


class TestInternalServicerContextIntegration:
    """Test InternalServicerContext integration scenarios."""

    def test_full_error_flow(self) -> None:
        """Test complete error setting and retrieval flow."""
        context = InternalServicerContext()

        # Initially no error
        assert context.has_error() is False

        # Set error
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details("Invalid argument")

        # Check error exists
        assert context.has_error() is True

        # Get error
        error = context.get_error()
        assert error.code == grpc.StatusCode.INVALID_ARGUMENT
        assert error.details == "Invalid argument"

