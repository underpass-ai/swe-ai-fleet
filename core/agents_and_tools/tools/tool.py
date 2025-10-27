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

