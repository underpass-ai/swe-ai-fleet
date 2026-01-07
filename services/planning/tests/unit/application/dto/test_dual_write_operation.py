"""Unit tests for DualWriteOperation DTO.

Following repository rules:
- Test DTO validation logic
- Test edge cases and invalid inputs
- No external dependencies
"""

from datetime import UTC, datetime

import pytest

from planning.application.dto.dual_write_operation import (
    DualWriteOperation,
    DualWriteStatus,
)


class TestDualWriteOperation:
    """Test cases for DualWriteOperation DTO."""

    def test_create_operation_happy_path(self) -> None:
        """Test creating a valid DualWriteOperation."""
        timestamp = datetime.now(UTC).isoformat()

        operation = DualWriteOperation(
            operation_id="test-op-123",
            status=DualWriteStatus.PENDING,
            attempts=0,
            last_error=None,
            created_at=timestamp,
            updated_at=timestamp,
        )

        assert operation.operation_id == "test-op-123"
        assert operation.status == DualWriteStatus.PENDING
        assert operation.attempts == 0
        assert operation.last_error is None
        assert operation.created_at == timestamp
        assert operation.updated_at == timestamp

    def test_create_operation_completed(self) -> None:
        """Test creating a COMPLETED operation."""
        timestamp = datetime.now(UTC).isoformat()

        operation = DualWriteOperation(
            operation_id="test-op-456",
            status=DualWriteStatus.COMPLETED,
            attempts=1,
            last_error=None,
            created_at=timestamp,
            updated_at=timestamp,
        )

        assert operation.status == DualWriteStatus.COMPLETED

    def test_create_operation_with_error(self) -> None:
        """Test creating an operation with error message."""
        timestamp = datetime.now(UTC).isoformat()

        operation = DualWriteOperation(
            operation_id="test-op-789",
            status=DualWriteStatus.PENDING,
            attempts=2,
            last_error="Connection timeout",
            created_at=timestamp,
            updated_at=timestamp,
        )

        assert operation.last_error == "Connection timeout"
        assert operation.attempts == 2

    def test_operation_id_cannot_be_empty(self) -> None:
        """Test that operation_id cannot be empty."""
        timestamp = datetime.now(UTC).isoformat()

        with pytest.raises(ValueError, match="operation_id cannot be empty"):
            DualWriteOperation(
                operation_id="",
                status=DualWriteStatus.PENDING,
                attempts=0,
                last_error=None,
                created_at=timestamp,
                updated_at=timestamp,
            )

    def test_invalid_status_raises_error(self) -> None:
        """Test that invalid status raises ValueError."""
        timestamp = datetime.now(UTC).isoformat()

        with pytest.raises(ValueError, match="Invalid status"):
            # Use type: ignore to bypass type checking for this test
            DualWriteOperation(
                operation_id="test-op",
                status="INVALID",  # type: ignore[arg-type]
                attempts=0,
                last_error=None,
                created_at=timestamp,
                updated_at=timestamp,
            )

    def test_negative_attempts_raises_error(self) -> None:
        """Test that negative attempts raises ValueError."""
        timestamp = datetime.now(UTC).isoformat()

        with pytest.raises(ValueError, match="attempts cannot be negative"):
            DualWriteOperation(
                operation_id="test-op",
                status=DualWriteStatus.PENDING,
                attempts=-1,
                last_error=None,
                created_at=timestamp,
                updated_at=timestamp,
            )

    def test_empty_created_at_raises_error(self) -> None:
        """Test that empty created_at raises ValueError."""
        with pytest.raises(ValueError, match="created_at cannot be empty"):
            DualWriteOperation(
                operation_id="test-op",
                status=DualWriteStatus.PENDING,
                attempts=0,
                last_error=None,
                created_at="",
                updated_at=datetime.now(UTC).isoformat(),
            )

    def test_empty_updated_at_raises_error(self) -> None:
        """Test that empty updated_at raises ValueError."""
        with pytest.raises(ValueError, match="updated_at cannot be empty"):
            DualWriteOperation(
                operation_id="test-op",
                status=DualWriteStatus.PENDING,
                attempts=0,
                last_error=None,
                created_at=datetime.now(UTC).isoformat(),
                updated_at="",
            )

    def test_invalid_timestamp_format_raises_error(self) -> None:
        """Test that invalid timestamp format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid timestamp format"):
            DualWriteOperation(
                operation_id="test-op",
                status=DualWriteStatus.PENDING,
                attempts=0,
                last_error=None,
                created_at="invalid-timestamp",
                updated_at="invalid-timestamp",
            )

    def test_timestamp_with_z_format_accepted(self) -> None:
        """Test that timestamps with Z suffix are accepted."""
        # Create timestamp without offset, then add Z
        timestamp_base = datetime.now(UTC).replace(tzinfo=None).isoformat()
        timestamp_z = timestamp_base + "Z"

        operation = DualWriteOperation(
            operation_id="test-op",
            status=DualWriteStatus.PENDING,
            attempts=0,
            last_error=None,
            created_at=timestamp_z,
            updated_at=timestamp_z,
        )

        assert operation.operation_id == "test-op"


class TestDualWriteStatus:
    """Test cases for DualWriteStatus enum."""

    def test_status_values(self) -> None:
        """Test that status enum has expected values."""
        assert DualWriteStatus.PENDING == "PENDING"
        assert DualWriteStatus.COMPLETED == "COMPLETED"

    def test_status_is_string_enum(self) -> None:
        """Test that DualWriteStatus is a string enum."""
        assert isinstance(DualWriteStatus.PENDING, str)
        assert isinstance(DualWriteStatus.COMPLETED, str)
