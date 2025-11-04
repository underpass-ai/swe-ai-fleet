"""Capability value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    """Value Object: Single tool capability (tool.operation).

    Represents a specific operation that an agent can perform.

    Domain Invariants:
    - Tool name cannot be empty
    - Operation name cannot be empty
    - Capability is immutable

    Examples:
        >>> cap = Capability(tool="files", operation="read_file")
        >>> cap.to_string()
        'files.read_file'
        >>> cap.is_write_operation()
        False
    """

    tool: str
    operation: str

    def __post_init__(self) -> None:
        """Validate capability (fail-fast).

        Raises:
            ValueError: If tool or operation is empty
        """
        if not self.tool:
            raise ValueError("Tool name cannot be empty")
        if not self.operation:
            raise ValueError("Operation name cannot be empty")

    def to_string(self) -> str:
        """Convert to string representation.

        Returns:
            String in format "tool.operation" (e.g., "files.read_file")
        """
        return f"{self.tool}.{self.operation}"

    def is_write_operation(self) -> bool:
        """Check if this is a write operation.

        Write operations modify state (write, edit, commit, push, etc.)

        Returns:
            True if write operation, False if read-only
        """
        write_ops = {
            "write_file", "edit_file", "append_file", "delete_file",
            "commit", "push", "add",
            "build", "run", "stop",
            "post", "put", "patch", "delete",
            "execute_migration", "insert", "update",
        }
        return self.operation in write_ops

    def __str__(self) -> str:
        """String representation."""
        return self.to_string()

