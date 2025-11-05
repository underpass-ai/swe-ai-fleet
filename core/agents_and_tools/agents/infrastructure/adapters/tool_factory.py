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

from core.agents_and_tools.agents.domain.entities import (
    DbExecutionResult,
    DockerExecutionResult,
    FileExecutionResult,
    GitExecutionResult,
    HttpExecutionResult,
    TestExecutionResult,
    ToolType,
)
from core.agents_and_tools.common.domain.entities import (
    AgentCapabilities,
    Capability,
    CapabilityCollection,
    ExecutionMode,
    ExecutionModeEnum,
    ToolDefinition,
    ToolRegistry,
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

    def get_available_tools_description(self, enable_write_operations: bool = True) -> AgentCapabilities:
        """
        Get description of available tools and their operations.

        Returns a structured description of all tools the toolset can provide,
        including which operations are available based on mode.

        Args:
            enable_write_operations: If True, include write operations; if False, only read

        Returns:
            AgentCapabilities entity with:
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
        except FileNotFoundError as e:
            # Fail-fast: Tool descriptions are REQUIRED for agent capabilities
            # Domain invariants require at least one tool to be available
            raise FileNotFoundError(
                f"Tool descriptions file not found at {tools_json_path}. "
                "This file is required for agent initialization."
            ) from e

        # Filter available tools based on mode
        mode_enum = ExecutionModeEnum.FULL if enable_write_operations else ExecutionModeEnum.READ_ONLY
        capabilities_list: list[Capability] = []
        tool_definitions: list[ToolDefinition] = []

        # Eagerly create all tools to check availability
        for tool_type in ToolType:
            self.is_available(tool_type)  # This will create and cache tools

        for tool_name, tool_info in tool_descriptions.items():
            # Only include tools that are actually available in this factory
            try:
                tool_type = ToolType.from_string(tool_name)
                # Check availability
                if self.is_available(tool_type):
                    # Create ToolDefinition
                    operations_dict = {
                        "read_operations": tool_info.get("read_operations", []),
                        "write_operations": tool_info.get("write_operations", [])
                    }
                    tool_definitions.append(
                        ToolDefinition(name=tool_name, operations=operations_dict)
                    )

                    # Always include read operations as Capability objects
                    read_ops = tool_info.get("read_operations", [])
                    capabilities_list.extend([
                        Capability(tool=tool_name, operation=op)
                        for op in read_ops
                    ])

                    # Include write operations only if enabled
                    if enable_write_operations:
                        write_ops = tool_info.get("write_operations", [])
                        capabilities_list.extend([
                            Capability(tool=tool_name, operation=op)
                            for op in write_ops
                        ])
            except ValueError:
                # Skip unknown tools
                pass

        # Fail-fast: If no tools available, raise exception
        # Domain invariants: ToolRegistry and CapabilityCollection cannot be empty
        if not tool_definitions or not capabilities_list:
            raise ValueError(
                "No tools available in factory. At least one tool must be available to create AgentCapabilities."
            )

        # Create domain entities (guaranteed non-empty)
        tool_registry = ToolRegistry.from_definitions(tool_definitions)
        execution_mode = ExecutionMode(value=mode_enum)
        capability_collection = CapabilityCollection.from_list(capabilities_list)

        return AgentCapabilities(
            tools=tool_registry,
            mode=execution_mode,
            operations=capability_collection,
            summary=f"ToolFactory has {len(self._tools)} tools available in {execution_mode.value.value} mode"
        )

    def execute_operation(
        self, tool_name: str | ToolType, operation: str, params: dict[str, Any], enable_write: bool = True
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
            raise ValueError(f"Unknown operation: {tool_name}.{operation}: {e}") from e

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

