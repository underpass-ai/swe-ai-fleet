"""Domain entity for agent capabilities."""

from dataclasses import dataclass

from .capability_collection import CapabilityCollection
from .execution_mode import ExecutionMode
from .tool_registry import ToolRegistry


@dataclass(frozen=True)
class AgentCapabilities:
    """
    Represents the tools and capabilities available to an agent.

    This entity encapsulates what operations an agent can perform
    with its available tools in the current execution mode.

    Attributes:
        tools: Registry of available tools (domain collection)
        mode: Execution mode value object (full or read_only)
        operations: Collection of operations this agent can perform (domain model)
        summary: Human-readable summary of capabilities

    All attributes are domain entities (ZERO primitives).
    """

    tools: ToolRegistry
    mode: ExecutionMode
    operations: CapabilityCollection
    summary: str

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Type checking is handled by type hints.
        This validates business rules only.

        Raises:
            ValueError: If summary is empty
        """
        if not self.summary:
            raise ValueError("summary cannot be empty")

    def filter_by_allowed_tools(self, allowed_tools: frozenset[str]) -> "AgentCapabilities":
        """Filter capabilities by allowed tools for a role.

        Tell, Don't Ask: AgentCapabilities filters itself by role permissions.

        Args:
            allowed_tools: Set of tool names allowed for the role

        Returns:
            New AgentCapabilities with only allowed tools

        Examples:
            >>> from .execution_mode import ExecutionMode, ExecutionModeEnum
            >>> from .capability import Capability
            >>> from .capability_collection import CapabilityCollection
            >>> from .tool_definition import ToolDefinition
            >>> from .tool_registry import ToolRegistry
            >>> all_caps = AgentCapabilities(
            ...     tools=ToolRegistry.from_definitions([
            ...         ToolDefinition("files", {...}),
            ...         ToolDefinition("git", {...}),
            ...         ToolDefinition("db", {...})
            ...     ]),
            ...     mode=ExecutionMode(value=ExecutionModeEnum.FULL),
            ...     operations=CapabilityCollection.from_list([
            ...         Capability("files", "read"),
            ...         Capability("git", "commit"),
            ...         Capability("db", "query")
            ...     ]),
            ...     summary="All tools"
            ... )
            >>> allowed = frozenset(["files", "git"])
            >>> filtered = all_caps.filter_by_allowed_tools(allowed)
            >>> "db" not in filtered.tools
            True
        """
        # Filter tools registry (only allowed tool names)
        filtered_tools = self.tools.filter_by_names(allowed_tools)

        # Filter operations collection (only operations for allowed tools)
        filtered_ops = self.operations.filter_by_tools(allowed_tools)

        # Build summary
        tool_names = filtered_tools.get_tool_names()
        summary = f"Available tools for role: {', '.join(tool_names)} ({self.mode})"

        return AgentCapabilities(
            tools=filtered_tools,
            mode=self.mode,
            operations=filtered_ops,
            summary=summary,
        )

