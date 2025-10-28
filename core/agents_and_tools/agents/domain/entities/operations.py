"""Collection of operations."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.agents_and_tools.agents.domain.entities.operation import Operation


@dataclass
class Operations:
    """Collection of tool operations with utility methods."""

    operations: list[dict] = field(default_factory=list)  # List of operation dicts

    def add(self, operation: dict) -> None:
        """Add an operation to the collection."""
        self.operations.append(operation)

    def get_all(self) -> list[dict]:
        """Get all operations."""
        return self.operations

    def get_by_tool(self, tool_name: str) -> list[dict]:
        """Get all operations for a specific tool."""
        return [op for op in self.operations if op.get("tool") == tool_name]

    def get_by_operation(self, operation_name: str) -> list[dict]:
        """Get all operations with a specific operation name."""
        return [op for op in self.operations if op.get("operation") == operation_name]

    def get_successful(self) -> list[dict]:
        """Get all successful operations."""
        return [op for op in self.operations if op.get("success", False)]

    def get_failed(self) -> list[dict]:
        """Get all failed operations."""
        return [op for op in self.operations if not op.get("success", True)]

    def count(self) -> int:
        """Get the number of operations."""
        return len(self.operations)

    def to_dict(self) -> list[dict]:
        """Convert to list of dicts for serialization."""
        return self.operations

