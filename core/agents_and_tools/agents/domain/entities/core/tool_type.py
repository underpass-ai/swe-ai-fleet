"""Tool type enumeration for agent tools."""

from enum import Enum


class ToolType(Enum):
    """Enumeration of available tool types."""

    FILES = "files"
    GIT = "git"
    TESTS = "tests"
    HTTP = "http"
    DB = "db"
    DOCKER = "docker"

    @classmethod
    def from_string(cls, tool_name: str) -> "ToolType":
        """Convert string tool name to ToolType enum."""
        for tool_type in cls:
            if tool_type.value == tool_name:
                return tool_type
        raise ValueError(f"Unknown tool type: {tool_name}")

    def __str__(self) -> str:
        """Return the tool name."""
        return self.value

