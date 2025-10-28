"""
Adapter for Tool Execution Port.

This adapter implements ToolExecutionPort by delegating to ToolFactory.
Following Hexagonal Architecture:
- ToolExecutionPort is the domain abstraction
- ToolExecutionAdapter implements it (infrastructure)
- ToolFactory handles tool creation and execution (infrastructure detail)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.agents_and_tools.agents.domain.entities.db_execution_result import DbExecutionResult
from core.agents_and_tools.agents.domain.entities.docker_execution_result import (
    DockerExecutionResult,
)
from core.agents_and_tools.agents.domain.entities.file_execution_result import FileExecutionResult
from core.agents_and_tools.agents.domain.entities.git_execution_result import GitExecutionResult
from core.agents_and_tools.agents.domain.entities.http_execution_result import HttpExecutionResult
from core.agents_and_tools.agents.domain.entities.test_execution_result import (
    TestExecutionResult,
)
from core.agents_and_tools.agents.infrastructure.adapters.tool_factory import ToolFactory
from core.agents_and_tools.common.domain.entities import AgentCapabilities
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort


class ToolExecutionAdapter(ToolExecutionPort):
    """
    Adapter for tool execution that implements ToolExecutionPort.

    This adapter wraps ToolFactory to provide tool execution as a port.
    It follows Hexagonal Architecture by:
    - Implementing ToolExecutionPort (domain contract)
    - Delegating to ToolFactory (infrastructure detail)
    - Returning domain entities

    Benefits:
    - Decouples domain from ToolFactory
    - Enables dependency injection and testing
    - Maintains hexagonal boundaries
    """

    def __init__(
        self,
        workspace_path: str,
        audit_callback: Callable[[str, str, dict[str, Any] | None], None] | None = None,
    ) -> None:
        """
        Initialize the adapter.

        Args:
            workspace_path: Path to the workspace directory where tools operate
            audit_callback: Optional callback for audit logging of tool operations
        """
        # Create ToolFactory instance (infrastructure detail)
        self._tool_factory = ToolFactory(
            workspace_path=workspace_path,
            audit_callback=audit_callback,
        )

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
        return self._tool_factory.execute_operation(tool_name, operation, params, enable_write)

    def get_tool_by_name(self, tool_name: str) -> Any | None:
        """
        Get tool instance by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool instance or None if not found
        """
        return self._tool_factory.get_tool_by_name(tool_name)

    def is_available(self, tool_name: str) -> bool:
        """
        Check if a tool is available.

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool is available, False otherwise
        """
        return self._tool_factory.is_available(tool_name)

    def get_available_tools(self) -> list[str]:
        """
        Get list of all available tool names.

        Returns:
            List of available tool names (as strings)
        """
        return self._tool_factory.get_available_tools()

    def get_all_tools(self) -> dict[str, Any]:
        """
        Get all available tools as a dictionary.

        Returns:
            Dictionary mapping tool names to tool instances
        """
        return self._tool_factory.get_all_tools()

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
        return self._tool_factory.get_available_tools_description(enable_write_operations)

