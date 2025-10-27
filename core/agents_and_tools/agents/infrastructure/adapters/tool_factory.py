"""
Tool Factory for Agent Infrastructure.

This Factory follows the Factory Pattern and Hexagonal Architecture:
- Creates and provides access to agent tools
- Handles initialization of required and optional tools
- Manages tool lifecycle and availability
- Converts tool results to domain entities via mappers

Factory Pattern Benefits:
- Single responsibility: Creation and provisioning of tools
- Encapsulates complex tool initialization logic
- Simplifies tool access for consumers
- Supports dependency injection for testing

Usage:
    factory = ToolFactory(
        workspace_path="/workspace/project",
        audit_callback=my_audit_callback
    )

    # Create/get tools
    git_tool = factory.create_tool("git")
    file_tool = factory.create_tool("files")

    # Check availability
    if factory.is_available("docker"):
        docker_tool = factory.create_tool("docker")
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from core.agents_and_tools.agents.domain.entities.db_execution_result import DbExecutionResult
from core.agents_and_tools.agents.domain.entities.docker_execution_result import (
    DockerExecutionResult,
)
from core.agents_and_tools.agents.domain.entities.file_execution_result import FileExecutionResult
from core.agents_and_tools.agents.domain.entities.git_execution_result import GitExecutionResult
from core.agents_and_tools.agents.domain.entities.http_execution_result import HttpExecutionResult
from core.agents_and_tools.agents.domain.entities.test_execution_result import TestExecutionResult
from core.agents_and_tools.agents.domain.entities.tool_type import ToolType
from core.agents_and_tools.agents.infrastructure.mappers.db_result_mapper import DbResultMapper
from core.agents_and_tools.agents.infrastructure.mappers.docker_result_mapper import (
    DockerResultMapper,
)
from core.agents_and_tools.agents.infrastructure.mappers.file_result_mapper import FileResultMapper
from core.agents_and_tools.agents.infrastructure.mappers.git_result_mapper import GitResultMapper
from core.agents_and_tools.agents.infrastructure.mappers.http_result_mapper import HttpResultMapper
from core.agents_and_tools.agents.infrastructure.mappers.test_result_mapper import TestResultMapper
from core.agents_and_tools.tools import (
    DatabaseTool,
    DockerTool,
    FileTool,
    GitTool,
    HttpTool,
    TestTool,
)

logger = logging.getLogger(__name__)


class ToolFactory:
    """
    Factory for creating and managing agent tools.

    This Factory follows the Factory Pattern and Hexagonal Architecture:
    - Creates tools based on ToolType enum
    - Manages tool lifecycle and availability
    - Provides tool instances to consumers
    - Handles optional tools with graceful degradation

    Responsibilities:
    - Tool instantiation based on type
    - Tool availability management
    - Result mapping to domain entities
    """

    def __init__(
        self,
        workspace_path: str,
        audit_callback: Callable[[str, str, dict[str, Any] | None], None] | None = None,
    ):
        """
        Initialize the tool factory.

        Args:
            workspace_path: Path to the workspace directory where tools operate
            audit_callback: Optional callback for audit logging of tool operations

        Example:
            factory = ToolFactory(
                workspace_path="/workspace/myproject",
                audit_callback=lambda op, tool, args: log(op, tool, args)
            )
        """
        self.workspace_path = workspace_path
        self.audit_callback = audit_callback

        # Initialize specific mappers for each tool type
        self.mappers = {
            ToolType.FILES: FileResultMapper(),
            ToolType.GIT: GitResultMapper(),
            ToolType.TESTS: TestResultMapper(),
            ToolType.HTTP: HttpResultMapper(),
            ToolType.DB: DbResultMapper(),
            ToolType.DOCKER: DockerResultMapper(),
        }

        # Initialize required tools
        self._tools = {
            ToolType.GIT: GitTool(workspace_path, audit_callback),
            ToolType.FILES: FileTool(workspace_path, audit_callback),
            ToolType.TESTS: TestTool(workspace_path, audit_callback),
            ToolType.HTTP: HttpTool(audit_callback=audit_callback),
            ToolType.DB: DatabaseTool(audit_callback=audit_callback),
        }

        # Initialize optional Docker tool
        try:
            self._tools[ToolType.DOCKER] = DockerTool(workspace_path, audit_callback=audit_callback)
            logger.info("Docker tool initialized successfully")
        except RuntimeError as e:
            logger.warning(f"Docker tool not available: {e}")
            # Docker tool will not be in self._tools dict

        # Log available tools
        available_tools = [str(tool.value) for tool in self._tools.keys()]
        logger.info(
            f"ToolFactory initialized with {len(available_tools)} tools: {', '.join(available_tools)}"
        )

    def create_tool(self, tool_name: str | ToolType) -> Any | None:
        """
        Create and return a tool instance.

        Args:
            tool_name: Name of the tool (string or ToolType enum)

        Returns:
            Tool instance or None if not found

        Example:
            git_tool = factory.create_tool("git")
            if git_tool:
                git_tool.status()
        """
        try:
            tool_type = ToolType.from_string(tool_name) if isinstance(tool_name, str) else tool_name
            return self._tools.get(tool_type)
        except ValueError:
            return None

    def get_all_tools(self) -> dict[str, Any]:
        """
        Get all available tools as a dictionary (converted to strings for compatibility).

        Returns:
            Dictionary mapping tool names (strings) to tool instances

        Example:
            tools = toolset.get_all_tools()
            for name, tool in tools.items():
                print(f"{name}: {tool}")
        """
        return {str(key.value): value for key, value in self._tools.items()}

    def is_available(self, tool_name: str | ToolType) -> bool:
        """
        Check if a tool is available.

        Args:
            tool_name: Name of the tool (string or ToolType enum)

        Returns:
            True if tool is available, False otherwise

        Example:
            if factory.is_available("docker"):
                # Use Docker-specific features
                pass
        """
        try:
            tool_type = ToolType.from_string(tool_name) if isinstance(tool_name, str) else tool_name
            return tool_type in self._tools
        except ValueError:
            return False

    def get_available_tools(self) -> list[str]:
        """
        Get list of all available tool names.

        Returns:
            List of available tool names (as strings)

        Example:
            tools = toolset.get_available_tools()
            print(f"Available tools: {', '.join(tools)}")
        """
        return [str(tool.value) for tool in self._tools.keys()]

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
            try:
                tool_type = ToolType.from_string(tool_name)
                if tool_type in self._tools:
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
            except ValueError:
                # Skip unknown tools
                pass

        return {
            "tools": tool_descriptions,
            "mode": mode,
            "capabilities": capabilities,
            "summary": f"ToolFactory has {len(self._tools)} tools available in {mode} mode"
        }

    def execute_operation(
        self, tool_name: str | ToolType, operation: str, params: dict[str, Any]
    ) -> FileExecutionResult | GitExecutionResult | TestExecutionResult | HttpExecutionResult | DbExecutionResult | DockerExecutionResult:
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
        # Convert string to ToolType if needed
        tool_type = ToolType.from_string(tool_name) if isinstance(tool_name, str) else tool_name

        # Get tool from factory
        tool = self.create_tool(tool_type)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Get explicit method mapping
        tool_method_map = self._get_tool_method_map(tool)
        method = tool_method_map.get(operation)

        if not method:
            raise ValueError(f"Unknown operation: {tool_name}.{operation}")

        # Execute method explicitly
        infrastructure_result = method(**params)

        # Get specific mapper for this tool type
        mapper = self.mappers.get(tool_type)
        if not mapper:
            raise ValueError(f"No mapper found for tool: {tool_name}")

        # Convert to domain entity using specific mapper
        return mapper.to_entity(infrastructure_result)

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

