"""Collection of operations."""

from dataclasses import dataclass, field

from core.agents_and_tools.agents.domain.entities.operation import Operation


@dataclass
class Operations:
    """Collection of tool operations with utility methods."""

    operations: list[Operation] = field(default_factory=list)  # List of Operation entities

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
            operation=operation,
            params=params or {},
            result=result or {},
            timestamp=datetime.now(),
            success=success,
            error=error,
            duration_ms=duration_ms,
        )
        self.operations.append(operation_entity)

    def get_all(self) -> list[Operation]:
        """Get all operations."""
        return self.operations

    def get_by_tool(self, tool_name: str) -> list[Operation]:
        """Get all operations for a specific tool."""
        return [op for op in self.operations if op.tool_name == tool_name]

    def get_by_operation(self, operation_name: str) -> list[Operation]:
        """Get all operations with a specific operation name."""
        return [op for op in self.operations if op.operation == operation_name]

    def get_successful(self) -> list[Operation]:
        """Get all successful operations."""
        return [op for op in self.operations if op.success]

    def get_failed(self) -> list[Operation]:
        """Get all failed operations."""
        return [op for op in self.operations if not op.success]

    def count(self) -> int:
        """Get the number of operations."""
        return len(self.operations)

    def to_dict(self) -> list[dict]:
        """Convert to list of dicts for serialization."""
        return [
            {
                "tool": op.tool_name,
                "operation": op.operation,
                "success": op.success,
                "error": op.error,
                "timestamp": op.timestamp.isoformat() if op.timestamp else None,
            }
            for op in self.operations
        ]

