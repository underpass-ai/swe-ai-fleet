"""Unit tests for ToolRegistry collection."""

import pytest

from core.agents_and_tools.common.domain.entities.tool_definition import ToolDefinition
from core.agents_and_tools.common.domain.entities.tool_registry import ToolRegistry


class TestToolRegistryCreation:
    """Test ToolRegistry creation."""

    def test_create_registry_from_dict(self):
        """Test creating registry from dict."""
        tool1 = ToolDefinition("files", {"read": {}})
        tool2 = ToolDefinition("git", {"commit": {}})

        registry = ToolRegistry(tools={"files": tool1, "git": tool2})

        assert registry.count() == 2
        assert registry.has_tool("files") is True
        assert registry.has_tool("git") is True

    def test_create_registry_from_definitions(self):
        """Test creating registry from list of definitions."""
        tools = [
            ToolDefinition("files", {"read": {}}),
            ToolDefinition("git", {"commit": {}}),
        ]

        registry = ToolRegistry.from_definitions(tools)

        assert registry.count() == 2
        assert "files" in registry
        assert "git" in registry

    def test_create_registry_rejects_empty_tools(self):
        """Test fail-fast on empty registry."""
        with pytest.raises(ValueError, match="ToolRegistry cannot be empty"):
            ToolRegistry(tools={})

    def test_create_registry_rejects_mismatched_key_name(self):
        """Test fail-fast when key doesn't match tool name."""
        tool = ToolDefinition("files", {"read": {}})

        with pytest.raises(ValueError, match="Tool key.*must match tool name"):
            ToolRegistry(tools={"wrong_key": tool})

    def test_from_definitions_rejects_empty_list(self):
        """Test from_definitions rejects empty list."""
        with pytest.raises(ValueError, match="Cannot create ToolRegistry from empty list"):
            ToolRegistry.from_definitions([])


class TestToolRegistryQueries:
    """Test ToolRegistry query methods."""

    def test_has_tool_returns_true_for_existing(self):
        """Test has_tool returns True for existing tools."""
        registry = ToolRegistry.from_definitions([
            ToolDefinition("files", {"read": {}}),
            ToolDefinition("git", {"commit": {}}),
        ])

        assert registry.has_tool("files") is True
        assert registry.has_tool("git") is True

    def test_has_tool_returns_false_for_missing(self):
        """Test has_tool returns False for missing tools."""
        registry = ToolRegistry.from_definitions([ToolDefinition("files", {"read": {}})])

        assert registry.has_tool("docker") is False

    def test_get_tool_returns_definition(self):
        """Test get_tool returns ToolDefinition."""
        tool = ToolDefinition("files", {"read": {}})
        registry = ToolRegistry.from_definitions([tool])

        retrieved = registry.get_tool("files")
        assert retrieved.name == "files"

    def test_get_tool_raises_on_missing(self):
        """Test get_tool raises KeyError for missing tool."""
        registry = ToolRegistry.from_definitions([ToolDefinition("files", {"read": {}})])

        with pytest.raises(KeyError, match="Tool 'docker' not found"):
            registry.get_tool("docker")

    def test_get_tool_names_returns_sorted_list(self):
        """Test get_tool_names returns sorted tool names."""
        registry = ToolRegistry.from_definitions([
            ToolDefinition("git", {"commit": {}}),
            ToolDefinition("files", {"read": {}}),
            ToolDefinition("docker", {"build": {}}),
        ])

        names = registry.get_tool_names()
        assert names == ["docker", "files", "git"]  # Sorted

    def test_count_returns_number_of_tools(self):
        """Test count returns correct number."""
        registry = ToolRegistry.from_definitions([
            ToolDefinition("files", {"read": {}}),
            ToolDefinition("git", {"commit": {}}),
        ])

        assert registry.count() == 2


class TestToolRegistryFiltering:
    """Test ToolRegistry filtering."""

    def test_filter_by_names_returns_subset(self):
        """Test filter_by_names returns new registry with only allowed tools."""
        registry = ToolRegistry.from_definitions([
            ToolDefinition("files", {"read": {}}),
            ToolDefinition("git", {"commit": {}}),
            ToolDefinition("docker", {"build": {}}),
        ])

        filtered = registry.filter_by_names(frozenset(["files", "git"]))

        assert filtered.count() == 2
        assert filtered.has_tool("files") is True
        assert filtered.has_tool("git") is True
        assert filtered.has_tool("docker") is False

    def test_filter_by_names_rejects_empty_result(self):
        """Test filter_by_names raises if result is empty."""
        registry = ToolRegistry.from_definitions([ToolDefinition("files", {"read": {}})])

        with pytest.raises(ValueError, match="Filtering resulted in empty registry"):
            registry.filter_by_names(frozenset(["nonexistent"]))


class TestToolRegistryProtocols:
    """Test ToolRegistry supports Python protocols."""

    def test_contains_operator(self):
        """Test 'in' operator works."""
        registry = ToolRegistry.from_definitions([ToolDefinition("files", {"read": {}})])

        assert "files" in registry
        assert "docker" not in registry

    def test_len_function(self):
        """Test len() works."""
        registry = ToolRegistry.from_definitions([
            ToolDefinition("files", {"read": {}}),
            ToolDefinition("git", {"commit": {}}),
        ])

        assert len(registry) == 2

    def test_iteration(self):
        """Test iteration over registry yields ToolDefinitions."""
        tool1 = ToolDefinition("files", {"read": {}})
        tool2 = ToolDefinition("git", {"commit": {}})
        registry = ToolRegistry.from_definitions([tool1, tool2])

        tools_list = list(registry)
        assert len(tools_list) == 2
        assert all(isinstance(t, ToolDefinition) for t in tools_list)

