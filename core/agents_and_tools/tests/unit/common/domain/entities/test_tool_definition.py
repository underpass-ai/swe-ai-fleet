"""Unit tests for ToolDefinition value object."""

import pytest
from core.agents_and_tools.common.domain.entities.tool_definition import ToolDefinition


class TestToolDefinitionCreation:
    """Test ToolDefinition value object creation."""

    def test_create_tool_with_operations(self):
        """Test creating tool definition with operations."""
        tool = ToolDefinition(
            name="files",
            operations={
                "read_file": {"params": ["path"], "returns": "str"},
                "write_file": {"params": ["path", "content"], "returns": "bool"},
            },
        )

        assert tool.name == "files"
        assert tool.has_operation("read_file") is True
        assert tool.has_operation("write_file") is True
        assert tool.get_operation_count() == 2

    def test_create_tool_rejects_empty_name(self):
        """Test fail-fast on empty tool name."""
        with pytest.raises(ValueError, match="Tool name cannot be empty"):
            ToolDefinition(name="", operations={"op": {}})

    def test_create_tool_rejects_empty_operations(self):
        """Test fail-fast on empty operations dict."""
        with pytest.raises(ValueError, match="must have at least one operation"):
            ToolDefinition(name="files", operations={})

    def test_tool_is_immutable(self):
        """Test tool is frozen (immutable)."""
        tool = ToolDefinition(name="files", operations={"read": {}})

        with pytest.raises(AttributeError):
            tool.name = "git"  # type: ignore


class TestToolDefinitionQueries:
    """Test ToolDefinition query methods."""

    def test_has_operation_returns_true_for_existing(self):
        """Test has_operation returns True for existing operation."""
        tool = ToolDefinition(name="git", operations={"commit": {}, "push": {}})

        assert tool.has_operation("commit") is True
        assert tool.has_operation("push") is True

    def test_has_operation_returns_false_for_missing(self):
        """Test has_operation returns False for missing operation."""
        tool = ToolDefinition(name="git", operations={"commit": {}})

        assert tool.has_operation("rebase") is False

    def test_get_operation_names_returns_sorted_list(self):
        """Test get_operation_names returns sorted operation names."""
        tool = ToolDefinition(
            name="files", operations={"write": {}, "read": {}, "delete": {}}
        )

        names = tool.get_operation_names()
        assert names == ["delete", "read", "write"]  # Sorted

    def test_get_operation_count_returns_correct_count(self):
        """Test get_operation_count returns number of operations."""
        tool = ToolDefinition(name="http", operations={"get": {}, "post": {}, "put": {}})

        assert tool.get_operation_count() == 3


class TestToolDefinitionStringRepresentation:
    """Test ToolDefinition string methods."""

    def test_str_includes_name_and_count(self):
        """Test __str__ shows tool name and operation count."""
        tool = ToolDefinition(name="files", operations={"read": {}, "write": {}})

        assert str(tool) == "files (2 operations)"

