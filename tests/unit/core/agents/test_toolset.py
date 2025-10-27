"""Unit tests for ToolFactory."""

from __future__ import annotations

from unittest.mock import Mock, patch

from core.agents_and_tools.agents.infrastructure.adapters.tool_factory import ToolFactory


class TestToolFactory:
    """Test suite for ToolFactory."""

    def test_initialization_with_all_tools(self, tmp_path):
        """Test ToolSet initializes all required tools."""
        # Arrange
        workspace_path = str(tmp_path)
        audit_callback = Mock()

        # Act
        toolset = ToolFactory(workspace_path=workspace_path, audit_callback=audit_callback)

        # Assert - All required tools should be present
        assert toolset.is_available("git")
        assert toolset.is_available("files")
        assert toolset.is_available("tests")
        assert toolset.is_available("http")
        assert toolset.is_available("db")

        # Assert - Tool instances are created
        assert toolset.create_tool("git") is not None
        assert toolset.create_tool("files") is not None
        assert toolset.create_tool("tests") is not None
        assert toolset.create_tool("http") is not None
        assert toolset.create_tool("db") is not None

    def test_initialization_without_audit_callback(self, tmp_path):
        """Test ToolSet works without audit callback."""
        # Arrange
        workspace_path = str(tmp_path)

        # Act
        toolset = ToolFactory(workspace_path=workspace_path, audit_callback=None)

        # Assert - Tools still initialized
        assert toolset.get_tool_count() >= 5  # At least required tools
        assert toolset.is_available("git")

    def test_docker_tool_initialization_success(self, tmp_path):
        """Test Docker tool initialization when available."""
        # Arrange
        workspace_path = str(tmp_path)
        audit_callback = Mock()

        # Mock DockerTool to not raise RuntimeError
        with patch("core.agents_and_tools.agents.infrastructure.adapters.toolset.DockerTool"):
            # Act
            toolset = ToolFactory(workspace_path=workspace_path, audit_callback=audit_callback)

            # Assert
            assert toolset.is_available("docker")
            assert toolset.create_tool("docker") is not None

    def test_docker_tool_initialization_failure(self, tmp_path):
        """Test Docker tool gracefully degrades when not available."""
        # Arrange
        workspace_path = str(tmp_path)
        audit_callback = Mock()

        # Mock DockerTool to raise RuntimeError
        with patch(
            "core.agents_and_tools.agents.infrastructure.adapters.tool_factory.DockerTool",
            side_effect=RuntimeError("Docker not available"),
        ):
            # Act
            toolset = ToolFactory(workspace_path=workspace_path, audit_callback=audit_callback)

            # Assert - Docker should not be available, but other tools should
            assert not toolset.is_available("docker")
            assert toolset.create_tool("docker") is None
            assert toolset.is_available("git")  # Other tools still work
            assert toolset.get_tool_count() == 5  # Only required tools

    def test_get_tool_existing(self, tmp_path):
        """Test get_tool returns tool when it exists."""
        # Arrange
        workspace_path = str(tmp_path)
        toolset = ToolFactory(workspace_path=workspace_path)

        # Act
        git_tool = toolset.create_tool("git")

        # Assert
        assert git_tool is not None

    def test_get_tool_nonexistent(self, tmp_path):
        """Test get_tool returns None when tool doesn't exist."""
        # Arrange
        workspace_path = str(tmp_path)
        toolset = ToolFactory(workspace_path=workspace_path)

        # Act
        result = toolset.create_tool("nonexistent")

        # Assert
        assert result is None

    def test_get_all_tools(self, tmp_path):
        """Test get_all_tools returns dictionary of all tools."""
        # Arrange
        workspace_path = str(tmp_path)
        toolset = ToolFactory(workspace_path=workspace_path)

        # Act
        tools = toolset.get_all_tools()

        # Assert
        assert isinstance(tools, dict)
        assert "git" in tools
        assert "files" in tools
        assert "tests" in tools
        assert "http" in tools
        assert "db" in tools
        assert len(tools) >= 5  # At least required tools

    def test_get_all_tools_returns_copy(self, tmp_path):
        """Test get_all_tools returns a copy, not reference."""
        # Arrange
        workspace_path = str(tmp_path)
        toolset = ToolFactory(workspace_path=workspace_path)

        # Act
        tools1 = toolset.get_all_tools()
        tools2 = toolset.get_all_tools()
        tools1["test_key"] = "test_value"

        # Assert - Modifying one shouldn't affect the other
        assert "test_key" not in tools2

    def test_has_tool_existing(self, tmp_path):
        """Test has_tool returns True for existing tools."""
        # Arrange
        workspace_path = str(tmp_path)
        toolset = ToolFactory(workspace_path=workspace_path)

        # Act & Assert
        assert toolset.is_available("git")
        assert toolset.is_available("files")
        assert toolset.is_available("tests")

    def test_has_tool_nonexistent(self, tmp_path):
        """Test has_tool returns False for non-existent tools."""
        # Arrange
        workspace_path = str(tmp_path)
        toolset = ToolFactory(workspace_path=workspace_path)

        # Act & Assert
        assert not toolset.is_available("nonexistent")

    def test_get_available_tools(self, tmp_path):
        """Test get_available_tools returns list of tool names."""
        # Arrange
        workspace_path = str(tmp_path)
        toolset = ToolFactory(workspace_path=workspace_path)

        # Act
        tools = toolset.get_available_tools()

        # Assert
        assert isinstance(tools, list)
        assert "git" in tools
        assert "files" in tools
        assert "tests" in tools
        assert len(tools) >= 5

    def test_get_tool_count(self, tmp_path):
        """Test get_tool_count returns correct number of tools."""
        # Arrange
        workspace_path = str(tmp_path)
        toolset = ToolFactory(workspace_path=workspace_path)

        # Act
        count = toolset.get_tool_count()

        # Assert
        assert count >= 5  # At least required tools
        assert count == len(toolset.get_available_tools())

    def test_tools_passed_to_toolset(self, tmp_path):
        """Test that tools receive correct parameters."""
        # Arrange
        workspace_path = str(tmp_path)
        audit_callback = Mock()

        # Act
        toolset = ToolFactory(workspace_path=workspace_path, audit_callback=audit_callback)

        # Assert - Tools should have been initialized with workspace_path
        git_tool = toolset.create_tool("git")
        assert git_tool is not None

        # The git tool should have workspace_path attribute
        # (We can't easily test private attributes, but we can verify tool works)
        from core.agents_and_tools.tools import GitTool

        # Verify it's the correct type
        assert isinstance(git_tool, GitTool)

    def test_get_available_tools_description_full_mode(self, tmp_path):
        """Test get_available_tools_description returns full mode capabilities."""
        # Arrange
        workspace_path = str(tmp_path)
        toolset = ToolFactory(workspace_path=workspace_path)

        # Act
        description = toolset.get_available_tools_description(enable_write_operations=True)

        # Assert
        assert description["mode"] == "full"
        assert "tools" in description
        assert "capabilities" in description
        assert "summary" in description
        assert len(description["capabilities"]) > 0
        # Should have both read and write operations
        assert any("files.write_file" in cap for cap in description["capabilities"])

    def test_get_available_tools_description_read_only_mode(self, tmp_path):
        """Test get_available_tools_description returns read-only capabilities."""
        # Arrange
        workspace_path = str(tmp_path)
        toolset = ToolFactory(workspace_path=workspace_path)

        # Act
        description = toolset.get_available_tools_description(enable_write_operations=False)

        # Assert
        assert description["mode"] == "read_only"
        assert "tools" in description
        assert "capabilities" in description
        # Should NOT have write operations
        assert not any("files.write_file" in cap for cap in description["capabilities"])
        # But should have read operations
        assert any("files.read_file" in cap for cap in description["capabilities"])

    def test_get_available_tools_description_includes_all_available_tools(self, tmp_path):
        """Test that description only includes tools that are actually available."""
        # Arrange
        workspace_path = str(tmp_path)
        toolset = ToolFactory(workspace_path=workspace_path)

        # Act
        description = toolset.get_available_tools_description()

        # Assert
        assert "tools" in description
        # Should have tools available in this toolset
        assert len(description["capabilities"]) > 0
        # Check that at least one of our initialized tools is mentioned
        available_tools = toolset.get_available_tools()
        for tool_name in available_tools:
            # Verify at least one capability mentions this tool
            tool_mentioned = any(tool_name + "." in cap for cap in description["capabilities"])
            assert tool_mentioned, f"Tool {tool_name} should be mentioned in capabilities"

