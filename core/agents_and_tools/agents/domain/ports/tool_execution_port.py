"""Port for tool execution in the domain layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.agents_and_tools.agents.domain.entities.db_execution_result import DbExecutionResult
from core.agents_and_tools.agents.domain.entities.docker_execution_result import DockerExecutionResult
from core.agents_and_tools.agents.domain.entities.file_execution_result import FileExecutionResult
from core.agents_and_tools.agents.domain.entities.git_execution_result import GitExecutionResult
from core.agents_and_tools.agents.domain.entities.http_execution_result import HttpExecutionResult
from core.agents_and_tools.agents.domain.entities.test_execution_result import TestExecutionResult
from core.agents_and_tools.common.domain.entities import AgentCapabilities


class ToolExecutionPort(ABC):
    """
    Port for executing tool operations.

    This is the domain abstraction for tool execution.
    Implementation should be in infrastructure layer.

    Responsibilities:
    - Execute tool operations
    - Provide access to tool instances
    - Check tool availability
    - Enforce read-only constraints
    """

    @abstractmethod
    def execute_operation(
        self,
        tool_name: str,
        operation: str,
        params: dict[str, Any],
        enable_write: bool = True,
    ) -> (
        FileExecutionResult
        | GitExecutionResult
        | TestExecutionResult
        | HttpExecutionResult
        | DbExecutionResult
        | DockerExecutionResult
    ):
        """
        Execute a tool operation and return domain entity.

        Args:
            tool_name: Name of the tool (e.g., "files", "git")
            operation: Operation to execute (e.g., "read_file", "commit")
            params: Operation parameters as key-value pairs
            enable_write: If False, only allow read-only operations

        Returns:
            ToolExecutionResult domain entity (specific type based on tool)

        Raises:
            ValueError: If operation is not allowed or unknown
        """
        pass

    @abstractmethod
    def get_tool_by_name(self, tool_name: str) -> Any | None:
        """
        Get tool instance by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool instance or None if not found
        """
        pass

    @abstractmethod
    def is_available(self, tool_name: str) -> bool:
        """
        Check if a tool is available.

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool is available, False otherwise
        """
        pass

    @abstractmethod
    def get_available_tools(self) -> list[str]:
        """
        Get list of all available tool names.

        Returns:
            List of available tool names (as strings)
        """
        pass

    @abstractmethod
    def get_available_tools_description(self, enable_write_operations: bool = True) -> AgentCapabilities:
        """
        Get description of available tools and their operations.

        Args:
            enable_write_operations: If True, include write operations; if False, only read

        Returns:
            AgentCapabilities entity with:
            - tools: dict of tool_name -> {operations, description}
            - mode: "full" or "read_only"
            - capabilities: list of what tools can do
            - summary: summary of available tools
        """
        pass

