"""Tests for ServicerError."""

import grpc
import pytest
from services.context.infrastructure.adapters.servicer_error import ServicerError


class TestServicerError:
    """Test ServicerError value object."""

    def test_create_servicer_error_success(self) -> None:
        """Test creating ServicerError with valid data."""
        error = ServicerError(
            code=grpc.StatusCode.INVALID_ARGUMENT,
            details="Invalid argument provided",
        )

        assert error.code == grpc.StatusCode.INVALID_ARGUMENT
        assert error.details == "Invalid argument provided"

    def test_servicer_error_is_immutable(self) -> None:
        """Test that ServicerError is immutable (frozen dataclass)."""
        error = ServicerError(
            code=grpc.StatusCode.INVALID_ARGUMENT,
            details="Invalid argument",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            error.details = "New details"  # type: ignore

    def test_servicer_error_rejects_empty_details(self) -> None:
        """Test that ServicerError rejects empty details."""
        with pytest.raises(ValueError, match="Error details cannot be empty"):
            ServicerError(
                code=grpc.StatusCode.INVALID_ARGUMENT,
                details="",
            )

    def test_servicer_error_rejects_whitespace_details(self) -> None:
        """Test that ServicerError rejects whitespace-only details."""
        with pytest.raises(ValueError, match="Error details cannot be empty"):
            ServicerError(
                code=grpc.StatusCode.INVALID_ARGUMENT,
                details="   ",
            )

    def test_servicer_error_equality(self) -> None:
        """Test ServicerError equality comparison."""
        error1 = ServicerError(
            code=grpc.StatusCode.INVALID_ARGUMENT,
            details="Invalid argument",
        )

        error2 = ServicerError(
            code=grpc.StatusCode.INVALID_ARGUMENT,
            details="Invalid argument",
        )

        assert error1 == error2

    def test_servicer_error_inequality(self) -> None:
        """Test ServicerError inequality comparison."""
        error1 = ServicerError(
            code=grpc.StatusCode.INVALID_ARGUMENT,
            details="Invalid argument",
        )

        error2 = ServicerError(
            code=grpc.StatusCode.NOT_FOUND,
            details="Not found",
        )

        assert error1 != error2

