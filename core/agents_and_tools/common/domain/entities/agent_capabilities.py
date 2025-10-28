"""Domain entity for agent capabilities."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentCapabilities:
    """
    Represents the tools and capabilities available to an agent.

    This entity encapsulates what operations an agent can perform
    with its available tools in the current execution mode.

    Attributes:
        tools: Dictionary mapping tool names to their operations and descriptions
        mode: Execution mode ("full" or "read_only")
        capabilities: List of capability strings (e.g., "files.read_file")
        summary: Human-readable summary of capabilities
    """

    tools: dict[str, Any]
    mode: str
    capabilities: list[str]
    summary: str

    def __post_init__(self) -> None:
        """Validate capabilities invariants."""
        if self.mode not in ("full", "read_only"):
            raise ValueError(f"Invalid mode: {self.mode}. Must be 'full' or 'read_only'")
        if not self.capabilities:
            raise ValueError("capabilities cannot be empty")
        if not self.summary:
            raise ValueError("summary cannot be empty")

