"""
ToolSet for Agent Infrastructure.

This adapter manages the lifecycle and access to agent tools following the
Hexagonal Architecture pattern. It handles:
- Initialization of all tools (Git, File, Test, HTTP, Database)
- Optional tools with graceful degradation (Docker)
- Tool access through a clean interface
- Audit logging delegation

Usage:
    toolset = ToolSet(
        workspace_path="/workspace/project",
        audit_callback=my_audit_callback
    )

    # Access tools
    git_tool = toolset.get_tool("git")
    file_tool = toolset.get_tool("files")

    # Get all tools dict
    all_tools = toolset.get_all_tools()

    # Check if tool is available
    if toolset.has_tool("docker"):
        docker_tool = toolset.get_tool("docker")
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from core.agents_and_tools.agents.domain.entities.tool_execution_result import (
    ToolExecutionResult,
)
from core.agents_and_tools.agents.infrastructure.mappers.tool_execution_result_mapper import (
    ToolExecutionResultMapper,
)
from core.agents_and_tools.tools import (
    DatabaseTool,
    DockerTool,
    FileTool,
    GitTool,
    HttpTool,
    TestTool,
)

logger = logging.getLogger(__name__)


class ToolSet:
    """
    Set of agent tools for lifecycle management and access.

    This adapter follows the Hexagonal Architecture pattern:
    - Domain layer: Agent use cases depend on ToolSet interface
    - Infrastructure layer: This concrete implementation initializes tools
    - Dependency Injection: ToolSet can be injected and mocked for testing

    Features:
    - Initializes all required tools (Git, File, Test, HTTP, Database)
    - Handles optional tools gracefully (Docker)
    - Provides clean access interface
    - Logs tool availability for debugging
    """

    def __init__(
        self,
        workspace_path: str,
        audit_callback: Callable[[str, str, dict[str, Any] | None], None] | None = None,
    ):
        """
        Initialize the tools manager.

        Args:
            workspace_path: Path to the workspace directory where tools operate
            audit_callback: Optional callback for audit logging of tool operations

        Example:
            toolset = ToolSet(
                workspace_path="/workspace/myproject",
                audit_callback=lambda op, tool, args: log(op, tool, args)
            )
        """
        self.workspace_path = workspace_path
        self.audit_callback = audit_callback

        # Initialize mapper for domain entity conversion
        self.mapper = ToolExecutionResultMapper()

        # Initialize required tools
        self._tools = {
            "git": GitTool(workspace_path, audit_callback),
            "files": FileTool(workspace_path, audit_callback),
            "tests": TestTool(workspace_path, audit_callback),
            "http": HttpTool(audit_callback=audit_callback),
            "db": DatabaseTool(audit_callback=audit_callback),
        }

        # Initialize optional Docker tool
        try:
            self._tools["docker"] = DockerTool(workspace_path, audit_callback=audit_callback)
            logger.info("Docker tool initialized successfully")
        except RuntimeError as e:
            logger.warning(f"Docker tool not available: {e}")
            # Docker tool will not be in self._tools dict

        # Log available tools
        available_tools = list(self._tools.keys())
        logger.info(
            f"ToolSet initialized with {len(available_tools)} tools: {', '.join(available_tools)}"
        )

    def get_tool(self, tool_name: str) -> Any | None:
        """
        Get a specific tool by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            Tool instance or None if not found

        Example:
            git_tool = toolset.get_tool("git")
            if git_tool:
                git_tool.status()
        """
        return self._tools.get(tool_name)

    def get_all_tools(self) -> dict[str, Any]:
        """
        Get all available tools as a dictionary.

        Returns:
            Dictionary mapping tool names to tool instances

        Example:
            tools = toolset.get_all_tools()
            for name, tool in tools.items():
                print(f"{name}: {tool}")
        """
        return self._tools.copy()

    def has_tool(self, tool_name: str) -> bool:
        """
        Check if a specific tool is available.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool is available, False otherwise

        Example:
            if toolset.has_tool("docker"):
                # Use Docker-specific features
                pass
        """
        return tool_name in self._tools

    def get_available_tools(self) -> list[str]:
        """
        Get list of all available tool names.

        Returns:
            List of available tool names

        Example:
            tools = toolset.get_available_tools()
            print(f"Available tools: {', '.join(tools)}")
        """
        return list(self._tools.keys())

    def get_tool_count(self) -> int:
        """
        Get the total number of available tools.

        Returns:
            Number of available tools
        """
        return len(self._tools)

    def get_available_tools_description(self, enable_write_operations: bool = True) -> dict[str, Any]:
        """
        Get description of available tools and their operations.

        Returns a structured description of all tools the toolset can provide,
        including which operations are available based on mode.

        Args:
            enable_write_operations: If True, include write operations; if False, only read

        Returns:
            Dictionary with:
            - tools: dict of tool_name -> {operations, description}
            - mode: "full" or "read_only"
            - capabilities: list of what tools can do
            - summary: summary of available tools

        Example:
            toolset = ToolSet("/workspace")
            desc = toolset.get_available_tools_description(enable_write_operations=False)
            # Returns read-only operations only
        """
        # Load tool descriptions from JSON resource
        resources_path = Path(__file__).parent.parent.parent.parent / "resources"
        tools_json_path = resources_path / "tools_description.json"

        try:
            with open(tools_json_path) as f:
                tool_descriptions = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Tool descriptions file not found at {tools_json_path}")
            return {
                "tools": {},
                "mode": "read_only",
                "capabilities": [],
                "summary": "No tool descriptions available",
            }

        # Filter available tools based on mode
        mode = "full" if enable_write_operations else "read_only"
        capabilities = []

        for tool_name, tool_info in tool_descriptions.items():
            # Only include tools that are actually available in this toolset
            if tool_name in self._tools:
                # Always include read operations
                read_ops = tool_info.get("read_operations", [])
                capabilities.extend([
                    f"{tool_name}.{op}"
                    for op in read_ops
                ])

                # Include write operations only if enabled
                if enable_write_operations:
                    write_ops = tool_info.get("write_operations", [])
                    capabilities.extend([
                        f"{tool_name}.{op}"
                        for op in write_ops
                    ])

        return {
            "tools": tool_descriptions,
            "mode": mode,
            "capabilities": capabilities,
            "summary": f"ToolSet has {len(self._tools)} tools available in {mode} mode"
        }

    def execute_operation(self, tool_name: str, operation: str, params: dict[str, Any]) -> ToolExecutionResult:
        """
        Execute a tool operation and return domain entity (NO REFLECTION).

        Uses explicit method mapping instead of getattr/hasattr.
        Converts infrastructure Result to domain entity.

        Args:
            tool_name: Name of the tool
            operation: Operation to execute
            params: Operation parameters

        Returns:
            ToolExecutionResult domain entity
        """
        # Get tool
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Get explicit method mapping
        tool_method_map = self._get_tool_method_map(tool)
        method = tool_method_map.get(operation)

        if not method:
            raise ValueError(f"Unknown operation: {tool_name}.{operation}")

        # Execute method explicitly
        infrastructure_result = method(**params)

        # Convert to domain entity
        return self.mapper.infrastructure_to_entity(infrastructure_result, tool_name, operation)

    def _get_tool_method_map(self, tool: Any) -> dict[str, Any]:
        """
        Get explicit method mapping for a tool (NO REFLECTION).

        Args:
            tool: Tool instance

        Returns:
            Dictionary mapping operation names to method callables
        """
        # Explicit mapping - NO getattr, NO reflection
        from core.agents_and_tools.tools import FileTool, GitTool, TestTool, HttpTool, DatabaseTool, DockerTool

        if isinstance(tool, FileTool):
            return {
                "read_file": tool.read_file,
                "write_file": tool.write_file,
                "append_file": tool.append_file,
                "search_in_files": tool.search_in_files,
                "list_files": tool.list_files,
                "edit_file": tool.edit_file,
                "delete_file": tool.delete_file,
                "mkdir": tool.mkdir,
                "file_info": tool.file_info,
                "diff_files": tool.diff_files,
            }
        elif isinstance(tool, GitTool):
            return {
                "clone": tool.clone,
                "status": tool.status,
                "add": tool.add,
                "commit": tool.commit,
                "push": tool.push,
                "pull": tool.pull,
                "checkout": tool.checkout,
                "branch": tool.branch,
                "diff": tool.diff,
                "log": tool.log,
            }
        elif isinstance(tool, TestTool):
            return {
                "pytest": tool.pytest,
                "go_test": tool.go_test,
                "npm_test": tool.npm_test,
                "cargo_test": tool.cargo_test,
                "make_test": tool.make_test,
            }
        elif isinstance(tool, HttpTool):
            return {
                "get": tool.get,
                "post": tool.post,
                "put": tool.put,
                "patch": tool.patch,
                "delete": tool.delete,
                "head": tool.head,
            }
        elif isinstance(tool, DatabaseTool):
            return {
                "postgresql_query": tool.postgresql_query,
                "redis_command": tool.redis_command,
                "neo4j_query": tool.neo4j_query,
            }
        elif isinstance(tool, DockerTool):
            return {
                "build": tool.build,
                "run": tool.run,
                "exec": tool.exec,
                "ps": tool.ps,
                "logs": tool.logs,
                "stop": tool.stop,
                "rm": tool.rm,
            }
        else:
            return {}

