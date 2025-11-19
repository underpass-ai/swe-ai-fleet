"""Collection of operations."""

from dataclasses import dataclass, field
from typing import Any

from core.agents_and_tools.agents.domain.entities.core.operation import Operation


@dataclass
class Operations:
    """Collection of tool operations with utility methods."""

    items: list[Operation] = field(default_factory=list)  # List of Operation entities

    def add(
        self,
        tool_name: str,
        operation: str,
        success: bool,
        params: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Add an operation to the collection."""
        from datetime import datetime

        operation_entity = Operation(
            tool_name=tool_name,
            operation_name=operation,
            params=params or {},
            result=result or {},
            timestamp=datetime.now(),
            success=success,
            error=error,
            duration_ms=duration_ms,
        )
        self.items.append(operation_entity)

    def get_all(self) -> list[Operation]:
        """Get all operations."""
        return self.items

    def get_by_tool(self, tool_name: str) -> list[Operation]:
        """Get all operations for a specific tool."""
        return [op for op in self.items if op.tool_name == tool_name]

    def get_by_operation(self, operation_name: str) -> list[Operation]:
        """Get all operations with a specific operation name."""
        return [op for op in self.items if op.operation_name == operation_name]

    def get_successful(self) -> list[Operation]:
        """Get all successful operations."""
        return [op for op in self.items if op.success]

    def get_failed(self) -> list[Operation]:
        """Get all failed operations."""
        return [op for op in self.items if not op.success]

    def count(self) -> int:
        """Get the number of operations."""
        return len(self.items)

