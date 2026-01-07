"""Mapper for DualWriteOperation DTO ↔ external formats (dict/JSON).

Following Hexagonal Architecture:
- Mappers live in infrastructure layer
- DTOs themselves do NOT have to_dict/from_dict methods
- Mapper handles all serialization/deserialization
"""

from datetime import UTC, datetime
from typing import Any

from planning.application.dto.dual_write_operation import (
    DualWriteOperation,
    DualWriteStatus,
)


class DualWriteOperationMapper:
    """Mapper for DualWriteOperation ↔ dict/JSON.

    Following repository rules:
    - No to_dict/from_dict methods in DTO
    - All serialization logic in infrastructure mapper
    - Explicit field mapping (no reflection)
    """

    @staticmethod
    def to_dict(operation: DualWriteOperation) -> dict[str, Any]:
        """Convert DualWriteOperation to dictionary.

        Args:
            operation: DualWriteOperation DTO

        Returns:
            Dictionary representation
        """
        return {
            "operation_id": operation.operation_id,
            "status": operation.status.value,
            "attempts": operation.attempts,
            "last_error": operation.last_error,
            "created_at": operation.created_at,
            "updated_at": operation.updated_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DualWriteOperation:
        """Convert dictionary to DualWriteOperation.

        Args:
            data: Dictionary with operation data

        Returns:
            DualWriteOperation DTO

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if "operation_id" not in data:
            raise ValueError("Missing required field: operation_id")

        if "status" not in data:
            raise ValueError("Missing required field: status")

        status_str = data["status"]
        try:
            status = DualWriteStatus(status_str)
        except ValueError as e:
            raise ValueError(f"Invalid status value: {status_str}") from e

        return DualWriteOperation(
            operation_id=data["operation_id"],
            status=status,
            attempts=data.get("attempts", 0),
            last_error=data.get("last_error"),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            updated_at=data.get("updated_at", datetime.now(UTC).isoformat()),
        )
