"""Tool registry collection."""

from dataclasses import dataclass

from .tool_definition import ToolDefinition


@dataclass(frozen=True)
class ToolRegistry:
    """Value Object: Registry of available tools with domain behavior.

    Encapsulates a collection of tools and provides domain logic for
    querying, filtering, and validating them.

    Domain Invariants:
    - Cannot be empty
    - All items must be ToolDefinition instances
    - Tool names must be unique
    - Registry is immutable

    Examples:
        >>> registry = ToolRegistry({
        ...     "files": ToolDefinition("files", {...}),
        ...     "git": ToolDefinition("git", {...})
        ... })
        >>> registry.has_tool("git")
        True
        >>> registry.count()
        2
        >>> registry.get_tool_names()
        ['files', 'git']
    """

    tools: dict[str, ToolDefinition]  # Internal storage

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Type checking is handled by type hints.
        This validates business rules only.

        Raises:
            ValueError: If registry is empty
            ValueError: If tool keys don't match tool names (business rule)
        """
        if not self.tools:
            raise ValueError("ToolRegistry cannot be empty")

        # Business rule: key must match tool name for consistency
        for tool_name, tool_def in self.tools.items():
            if tool_name != tool_def.name:
                raise ValueError(
                    f"Tool key '{tool_name}' must match tool name '{tool_def.name}'"
                )

    @classmethod
    def from_definitions(cls, definitions: list[ToolDefinition]) -> "ToolRegistry":
        """Create registry from list of tool definitions.

        Args:
            definitions: List of ToolDefinition objects

        Returns:
            New ToolRegistry

        Raises:
            ValueError: If definitions list is empty
        """
        if not definitions:
            raise ValueError("Cannot create ToolRegistry from empty list")

        tools_dict = {tool.name: tool for tool in definitions}
        return cls(tools=tools_dict)

    def has_tool(self, tool_name: str) -> bool:
        """Check if registry contains a specific tool.

        Tell, Don't Ask: Registry knows if it contains a tool.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool exists, False otherwise
        """
        return tool_name in self.tools

    def get_tool(self, tool_name: str) -> ToolDefinition:
        """Get tool definition by name.

        Args:
            tool_name: Name of the tool

        Returns:
            ToolDefinition for the requested tool

        Raises:
            KeyError: If tool not found
        """
        if tool_name not in self.tools:
            raise KeyError(f"Tool '{tool_name}' not found in registry")
        return self.tools[tool_name]

    def get_tool_names(self) -> list[str]:
        """Get list of all tool names.

        Returns:
            Sorted list of tool names
        """
        return sorted(self.tools.keys())

    def count(self) -> int:
        """Get number of tools in registry.

        Returns:
            Count of tools
        """
        return len(self.tools)

    def filter_by_names(self, allowed_names: frozenset[str]) -> "ToolRegistry":
        """Create new registry with only allowed tools.

        Business Logic: RBAC filtering.

        Args:
            allowed_names: Set of tool names to keep

        Returns:
            New ToolRegistry with filtered tools

        Raises:
            ValueError: If filtering results in empty registry
        """
        filtered = {
            name: tool for name, tool in self.tools.items() if name in allowed_names
        }
        if not filtered:
            raise ValueError("Filtering resulted in empty registry")
        return ToolRegistry(tools=filtered)

    def to_dict(self) -> dict[str, ToolDefinition]:
        """Convert to dict (for internal use only).

        Note: Prefer using domain methods over dict access.

        Returns:
            Dictionary of tool names to ToolDefinition
        """
        return dict(self.tools)

    def __contains__(self, tool_name: str) -> bool:
        """Support 'in' operator.

        Args:
            tool_name: Tool name to check

        Returns:
            True if tool exists
        """
        return tool_name in self.tools

    def __iter__(self):
        """Allow iteration over tool definitions."""
        return iter(self.tools.values())

    def __len__(self) -> int:
        """Support len() function."""
        return len(self.tools)

