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

        # Lazy initialization - tools created on demand
        self._tools: dict[ToolType, Any] = {}

        logger.info("ToolFactory initialized (tools will be created on demand)")

    def create_tool(self, tool_name: str | ToolType) -> Any | None:
        """
        Create and return a tool instance (lazy initialization).

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

            # Check if already created
            if tool_type in self._tools:
                return self._tools[tool_type]

            # Create tool on demand using its factory method
            tool = self._create_tool_instance(tool_type)
            if tool is not None:
                self._tools[tool_type] = tool
                logger.debug(f"Created tool: {tool_type.value}")
            return tool
        except ValueError:
            return None

    def get_tool_by_name(self, tool_name: str | ToolType) -> Any | None:
        """
        Get tool instance by name (from cache).

        Args:
            tool_name: Name of the tool (string or ToolType enum)

        Returns:
            Tool instance or None if not found
        """
        try:
            tool_type = ToolType.from_string(tool_name) if isinstance(tool_name, str) else tool_name
            return self._tools.get(tool_type)
        except ValueError:
            return None

    def _create_tool_instance(self, tool_type: ToolType) -> Any | None:
        """Create a tool instance based on type."""
        try:
            if tool_type == ToolType.GIT:
                return GitTool.create(self.workspace_path, self.audit_callback)
            elif tool_type == ToolType.FILES:
                return FileTool.create(self.workspace_path, self.audit_callback)
            elif tool_type == ToolType.TESTS:
                return TestTool.create(self.workspace_path, self.audit_callback)
            elif tool_type == ToolType.HTTP:
                return HttpTool.create(audit_callback=self.audit_callback)
            elif tool_type == ToolType.DB:
                return DatabaseTool.create(audit_callback=self.audit_callback)
            elif tool_type == ToolType.DOCKER:
                try:
                    tool = DockerTool.create(self.workspace_path, audit_callback=self.audit_callback)
                    logger.info("Docker tool initialized successfully")
                    return tool
                except RuntimeError as e:
                    logger.warning(f"Docker tool not available: {e}")
                    return None
            return None
        except Exception as e:
            logger.error(f"Error creating tool {tool_type.value}: {e}")
            return None

    def get_all_tools(self) -> dict[str, Any]:
        """
        Get all available tools as a dictionary (converted to strings for compatibility).

        Creates all tools on first call (lazy initialization).

        Returns:
            Dictionary mapping tool names (strings) to tool instances

        Example:
            tools = toolset.get_all_tools()
            for name, tool in tools.items():
                print(f"{name}: {tool}")
        """
        # Create all tools on first call
        for tool_type in ToolType:
            if tool_type not in self._tools:
                tool = self._create_tool_instance(tool_type)
                if tool is not None:
                    self._tools[tool_type] = tool

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

            # Check if already created
            if tool_type in self._tools:
                return True

            # Try to create it to check if it exists
            tool = self._create_tool_instance(tool_type)
            if tool is not None:
                self._tools[tool_type] = tool
                return True
            return False
        except ValueError:
            return False

    def get_available_tools(self) -> list[str]:
        """
        Get list of all available tool names.

        Creates all tools on first call to list them.

        Returns:
            List of available tool names (as strings)

        Example:
            tools = toolset.get_available_tools()
            print(f"Available tools: {', '.join(tools)}")
        """
        # Create all tools first
        self.get_all_tools()
        return [str(tool.value) for tool in self._tools.keys()]

    def get_tool_count(self) -> int:
        """
        Get the total number of available tools.

        Creates all tools on first call to count them.

        Returns:
            Number of available tools
        """
        # Create all tools first to count them
        self.get_all_tools()
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
            # Only include tools that are actually available in this factory
            try:
                tool_type = ToolType.from_string(tool_name)
                # Check availability (creates tool if needed)
                if self.is_available(tool_type):
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

        # Eagerly create all tools for description (so we know what's available)
        for tool_type in ToolType:
            self.is_available(tool_type)  # This will create and cache tools

        return {
            "tools": tool_descriptions,
            "mode": mode,
            "capabilities": capabilities,
            "summary": f"ToolFactory has {len(self._tools)} tools available in {mode} mode"
        }

    def execute_operation(
        self, tool_name: str | ToolType, operation: str, params: dict[str, Any], enable_write: bool = True
    ) -> FileExecutionResult | GitExecutionResult | TestExecutionResult | HttpExecutionResult | DbExecutionResult | DockerExecutionResult:
        """
        Execute a tool operation and return domain entity.

        Args:
            tool_name: Name of the tool
            operation: Operation to execute
            params: Operation parameters
            enable_write: If False, only allow read-only operations

        Returns:
            ToolExecutionResult domain entity

        Raises:
            ValueError: If operation is not allowed or unknown
        """
        # Convert string to ToolType if needed
        tool_type = ToolType.from_string(tool_name) if isinstance(tool_name, str) else tool_name

        # Get tool from factory
        tool = self.create_tool(tool_type)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Check if write operation is allowed
        if not enable_write:
            if not self._is_read_only_operation(tool_type, operation):
                raise ValueError(f"Write operation '{operation}' not allowed in read-only mode")

        # Execute operation using tool's execute method
        try:
            infrastructure_result = tool.execute(operation, **params)
        except ValueError as e:
            raise ValueError(f"Unknown operation: {tool_name}.{operation}: {e}")

        # Get mapper from tool itself
        mapper = tool.get_mapper()

        # Convert to domain entity using tool's mapper
        return mapper.to_entity(infrastructure_result)

    def _is_read_only_operation(self, tool_type: ToolType, operation: str) -> bool:
        """
        Check if an operation is read-only.

        Read-only operations are those that don't modify state.
        """
        read_only_ops = {
            ToolType.FILES: {"read_file", "search_in_files", "list_files", "file_info", "diff_files"},
            ToolType.GIT: {"status", "log", "diff", "branch"},
            ToolType.TESTS: {"pytest", "go_test", "npm_test", "cargo_test", "make_test"},
            ToolType.DB: {"postgresql_query", "redis_command", "neo4j_query"},
            ToolType.HTTP: {"get", "head"},
            ToolType.DOCKER: {"ps", "logs"},
        }

        allowed_ops = read_only_ops.get(tool_type, set())
        return operation in allowed_ops

