"""Domain entity for tool execution results."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolExecutionResult:
    """
    Domain entity representing the result of a tool operation.

    This entity is independent of infrastructure Result types (FileResult, GitResult, etc.).
    It provides a unified interface for all tool execution results in the domain layer.

    Attributes:
        success: Whether the operation succeeded
        tool_name: Name of the tool that was executed
        operation: Name of the operation that was executed
        content: Result content (stdout, content, etc.)
        error: Error message if operation failed
        metadata: Additional metadata about the operation
    """

    success: bool
    tool_name: str
    operation: str
    content: str | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Validate result data (fail fast)."""
        if not self.tool_name:
            raise ValueError("Tool name cannot be empty")
        if not self.operation:
            raise ValueError("Operation cannot be empty")
        # Note: error is optional even for failures (some tools don't return error messages)

