"""Capability collection value object."""

from dataclasses import dataclass

from .capability import Capability


@dataclass(frozen=True)
class CapabilityCollection:
    """Value Object: Collection of capabilities with domain behavior.

    Encapsulates a set of capabilities and provides domain logic for
    querying, filtering, and validating them.

    Domain Invariants:
    - Cannot be empty
    - All items must be Capability instances
    - Collection is immutable

    Examples:
        >>> caps = CapabilityCollection([
        ...     Capability("files", "read_file"),
        ...     Capability("git", "commit"),
        ...     Capability("files", "write_file")
        ... ])
        >>> caps.count()
        3
        >>> caps.has_capability("files", "read_file")
        True
        >>> len(caps.get_by_tool("files"))
        2
    """

    items: tuple[Capability, ...]  # Tuple for immutability

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Type checking is handled by type hints.
        This validates business rules only.

        Raises:
            ValueError: If collection is empty
        """
        if not self.items:
            raise ValueError("CapabilityCollection cannot be empty")

    @classmethod
    def from_list(cls, capabilities: list[Capability]) -> "CapabilityCollection":
        """Create collection from list of capabilities.

        Args:
            capabilities: List of Capability objects

        Returns:
            New CapabilityCollection
        """
        return cls(items=tuple(capabilities))

    def count(self) -> int:
        """Get number of capabilities.

        Returns:
            Count of capabilities
        """
        return len(self.items)

    def has_capability(self, tool: str, operation: str) -> bool:
        """Check if collection contains a specific capability.

        Tell, Don't Ask: Collection knows if it contains a capability.

        Args:
            tool: Tool name
            operation: Operation name

        Returns:
            True if capability exists, False otherwise
        """
        return any(cap.tool == tool and cap.operation == operation for cap in self.items)

    def get_by_tool(self, tool_name: str) -> list[Capability]:
        """Get all capabilities for a specific tool.

        Args:
            tool_name: Name of the tool to filter by

        Returns:
            List of capabilities for the specified tool
        """
        return [cap for cap in self.items if cap.tool == tool_name]

    def get_write_capabilities(self) -> list[Capability]:
        """Get only write capabilities.

        Business Logic: Filter to write operations only.

        Returns:
            List of write capabilities
        """
        return [cap for cap in self.items if cap.is_write_operation()]

    def get_read_capabilities(self) -> list[Capability]:
        """Get only read capabilities.

        Business Logic: Filter to read operations only.

        Returns:
            List of read-only capabilities
        """
        return [cap for cap in self.items if not cap.is_write_operation()]

    def filter_by_tools(self, allowed_tools: frozenset[str]) -> "CapabilityCollection":
        """Create new collection with only allowed tools.

        Business Logic: RBAC filtering.

        Args:
            allowed_tools: Set of tool names to keep

        Returns:
            New CapabilityCollection with filtered capabilities

        Raises:
            ValueError: If filtering results in empty collection
        """
        filtered = [cap for cap in self.items if cap.tool in allowed_tools]
        if not filtered:
            raise ValueError("Filtering resulted in empty collection")
        return CapabilityCollection.from_list(filtered)

    def get_tool_names(self) -> list[str]:
        """Get unique tool names in collection.

        Returns:
            Sorted list of unique tool names
        """
        return sorted({cap.tool for cap in self.items})

    def to_list(self) -> list[Capability]:
        """Convert to list (for compatibility).

        Returns:
            List of Capability objects
        """
        return list(self.items)

    def __iter__(self):
        """Allow iteration over capabilities."""
        return iter(self.items)

    def __len__(self) -> int:
        """Support len() function."""
        return len(self.items)

    def __contains__(self, capability: Capability) -> bool:
        """Support 'in' operator."""
        return capability in self.items

