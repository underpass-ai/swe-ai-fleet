"""Tool definition value object."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    """Value Object: Definition of a tool with its operations.

    Represents a tool (e.g., "files", "git") and what operations it supports.

    Domain Invariants:
    - Tool name cannot be empty
    - Must have at least one operation
    - ToolDefinition is immutable

    Examples:
        >>> files_tool = ToolDefinition(
        ...     name="files",
        ...     operations={
        ...         "read_file": {"params": ["path"], "returns": "str"},
        ...         "write_file": {"params": ["path", "content"], "returns": "bool"}
        ...     }
        ... )
        >>> files_tool.has_operation("read_file")
        True
        >>> files_tool.get_operation_names()
        ['read_file', 'write_file']
    """

    name: str
    operations: dict[str, Any]  # operation_name -> operation_metadata

    def __post_init__(self) -> None:
        """Validate tool definition (fail-fast).

        Raises:
            ValueError: If name is empty
            ValueError: If operations is empty
        """
        if not self.name:
            raise ValueError("Tool name cannot be empty")
        if not self.operations:
            raise ValueError(f"Tool '{self.name}' must have at least one operation")

    def has_operation(self, operation_name: str) -> bool:
        """Check if tool supports a specific operation.

        Tell, Don't Ask: Tool knows what operations it supports.

        Args:
            operation_name: Name of the operation to check

        Returns:
            True if operation exists, False otherwise
        """
        return operation_name in self.operations

    def get_operation_names(self) -> list[str]:
        """Get list of available operation names.

        Tell, Don't Ask: Tool provides its operations.

        Returns:
            Sorted list of operation names
        """
        return sorted(self.operations.keys())

    def get_operation_count(self) -> int:
        """Get number of operations available.

        Returns:
            Count of operations
        """
        return len(self.operations)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.name} ({self.get_operation_count()} operations)"

