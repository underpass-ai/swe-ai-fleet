"""
Tool Protocol for agent tools.

This protocol defines the interface that all agent tools must implement.
It ensures consistency across different tool types and enables proper
type checking and dependency injection.
"""

from typing import Any, Protocol


class Tool(Protocol):
    """Protocol for agent tools."""

    def get_operations(self) -> dict[str, Any]:
        """
        Return a dictionary mapping operation names to method callables.

        Returns:
            Dictionary where:
            - Key: operation name (e.g., "read_file", "status", "pytest")
            - Value: method callable that performs the operation

        Example:
            {
                "read_file": self.read_file,
                "write_file": self.write_file,
                ...
            }
        """
        ...

    def execute(self, operation: str, **params: Any) -> Any:
        """
        Execute a tool operation by name.

        Args:
            operation: Name of the operation to execute
            **params: Operation-specific parameters

        Returns:
            Result of the operation (tool-specific Result type)

        Raises:
            ValueError: If operation is not supported
        """
        ...
    
    def summarize_result(self, operation: str, tool_result: Any, params: dict[str, Any]) -> str:
        """
        Summarize tool operation result for logging.

        Args:
            operation: The operation that was executed
            tool_result: The result from the tool
            params: The operation parameters

        Returns:
            Human-readable summary of the operation result
        """
        ...

