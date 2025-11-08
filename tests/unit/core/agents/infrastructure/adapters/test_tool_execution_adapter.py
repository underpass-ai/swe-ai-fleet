"""Unit tests for ToolExecutionAdapter."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from core.agents_and_tools.agents.domain.entities import FileExecutionResult
from core.agents_and_tools.agents.infrastructure.adapters.tool_execution_adapter import (
    ToolExecutionAdapter,
)
from core.agents_and_tools.common.domain.entities.agent_capabilities import AgentCapabilities


class TestToolExecutionAdapter:
    """Test suite for ToolExecutionAdapter."""

    def test_initialization_delegates_to_tool_factory(self, tmp_path):
        """Test that adapter creates and delegates to ToolFactory."""
        # Arrange
        workspace_path = str(tmp_path)
        audit_callback = Mock()

        # Act
        adapter = ToolExecutionAdapter(workspace_path=workspace_path, audit_callback=audit_callback)

        # Assert
        assert adapter is not None
        assert adapter._tool_factory is not None
        assert adapter._tool_factory.workspace_path == workspace_path

    def test_execute_operation_delegates_to_factory(self):
        """Test that execute_operation delegates to ToolFactory."""
        # Arrange
        workspace_path = "/workspace"
        adapter = ToolExecutionAdapter(workspace_path=workspace_path, audit_callback=None)

        # Create a mock result
        expected_result = FileExecutionResult(success=True, content="test", error=None)

        # Mock the factory's execute_operation
        with patch.object(adapter._tool_factory, "execute_operation") as mock_execute:
            mock_execute.return_value = expected_result

            # Act
            result = adapter.execute_operation("files", "read_file", {"path": "test.txt"}, enable_write=True)

            # Assert
            mock_execute.assert_called_once_with("files", "read_file", {"path": "test.txt"}, True)
            assert result == expected_result

    def test_get_tool_by_name_delegates_to_factory(self):
        """Test that get_tool_by_name delegates to ToolFactory."""
        # Arrange
        workspace_path = "/workspace"
        adapter = ToolExecutionAdapter(workspace_path=workspace_path, audit_callback=None)

        # Mock the factory's get_tool_by_name
        mock_tool = Mock()
        with patch.object(adapter._tool_factory, "get_tool_by_name") as mock_get_tool:
            mock_get_tool.return_value = mock_tool

            # Act
            result = adapter.get_tool_by_name("git")

            # Assert
            mock_get_tool.assert_called_once_with("git")
            assert result == mock_tool

    def test_is_available_delegates_to_factory(self):
        """Test that is_available delegates to ToolFactory."""
        # Arrange
        workspace_path = "/workspace"
        adapter = ToolExecutionAdapter(workspace_path=workspace_path, audit_callback=None)

        # Mock the factory's is_available
        with patch.object(adapter._tool_factory, "is_available") as mock_is_available:
            mock_is_available.return_value = True

            # Act
            result = adapter.is_available("git")

            # Assert
            mock_is_available.assert_called_once_with("git")
            assert result is True

    def test_get_available_tools_delegates_to_factory(self):
        """Test that get_available_tools delegates to ToolFactory."""
        # Arrange
        workspace_path = "/workspace"
        adapter = ToolExecutionAdapter(workspace_path=workspace_path, audit_callback=None)

        # Mock the factory's get_available_tools
        expected_tools = ["git", "files", "tests"]
        with patch.object(adapter._tool_factory, "get_available_tools") as mock_get_tools:
            mock_get_tools.return_value = expected_tools

            # Act
            result = adapter.get_available_tools()

            # Assert
            mock_get_tools.assert_called_once()
            assert result == expected_tools

    def test_get_all_tools_delegates_to_factory(self):
        """Test that get_all_tools delegates to ToolFactory."""
        # Arrange
        workspace_path = "/workspace"
        adapter = ToolExecutionAdapter(workspace_path=workspace_path, audit_callback=None)

        # Mock the factory's get_all_tools
        expected_tools = {"git": Mock(), "files": Mock()}
        with patch.object(adapter._tool_factory, "get_all_tools") as mock_get_all:
            mock_get_all.return_value = expected_tools

            # Act
            result = adapter.get_all_tools()

            # Assert
            mock_get_all.assert_called_once()
            assert result == expected_tools

    def test_get_available_tools_description_delegates_to_factory(self):
        """Test that get_available_tools_description delegates to ToolFactory."""
        # Arrange
        workspace_path = "/workspace"
        adapter = ToolExecutionAdapter(workspace_path=workspace_path, audit_callback=None)

        # Mock the factory's get_available_tools_description
        from core.agents_and_tools.common.domain.entities.capability import Capability
        from core.agents_and_tools.common.domain.entities.capability_collection import CapabilityCollection
        from core.agents_and_tools.common.domain.entities.execution_mode import (
            ExecutionMode,
            ExecutionModeEnum,
        )
        from core.agents_and_tools.common.domain.entities.tool_definition import ToolDefinition
        from core.agents_and_tools.common.domain.entities.tool_registry import ToolRegistry

        tool_def = ToolDefinition(
            name="files",
            operations={"read_operations": ["read_file"], "write_operations": ["write_file"]}
        )
        expected_capabilities = AgentCapabilities(
            tools=ToolRegistry.from_definitions([tool_def]),
            mode=ExecutionMode(value=ExecutionModeEnum.FULL),
            operations=CapabilityCollection.from_list([
                Capability(tool="files", operation="read_file"),
                Capability(tool="files", operation="write_file"),
            ]),
            summary="Test capabilities",
        )
        with patch.object(
            adapter._tool_factory, "get_available_tools_description"
        ) as mock_get_desc:
            mock_get_desc.return_value = expected_capabilities

            # Act
            result = adapter.get_available_tools_description(enable_write_operations=True)

            # Assert
            mock_get_desc.assert_called_once_with(True)
            assert result == expected_capabilities

    def test_read_only_mode_blocks_write_operations(self, tmp_path):
        """Test that read-only mode blocks write operations."""
        # Arrange - need valid workspace path
        workspace_path = str(tmp_path)
        adapter = ToolExecutionAdapter(workspace_path=workspace_path, audit_callback=None)

        # Try to execute a write operation in read-only mode
        with pytest.raises(ValueError, match="Write operation.*not allowed"):
            adapter.execute_operation("files", "write_file", {"path": "test.txt"}, enable_write=False)

    def test_production_usage_with_real_workspace(self, tmp_path):
        """Test adapter works with real workspace directory."""
        # Arrange
        workspace_path = str(tmp_path)
        audit_callback = Mock()

        # Act - create adapter with real workspace
        adapter = ToolExecutionAdapter(workspace_path=workspace_path, audit_callback=audit_callback)

        # Assert - basic tools should be available
        assert adapter.is_available("git")
        assert adapter.is_available("files")
        assert adapter.is_available("tests")

        # Should have at least 5 tools
        available_tools = adapter.get_available_tools()
        assert len(available_tools) >= 5

        # All tools dict should match
        all_tools = adapter.get_all_tools()
        assert isinstance(all_tools, dict)
        assert len(all_tools) >= 5

