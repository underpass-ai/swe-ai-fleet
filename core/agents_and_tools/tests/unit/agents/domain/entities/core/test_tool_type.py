"""Unit tests for ToolType enumeration."""

import pytest
from core.agents_and_tools.agents.domain.entities.core.tool_type import ToolType


class TestToolTypeEnum:
    """Test ToolType enum values."""

    def test_all_tool_types_exist(self):
        """Test all expected tool types exist."""
        assert ToolType.FILES == ToolType("files")
        assert ToolType.GIT == ToolType("git")
        assert ToolType.TESTS == ToolType("tests")
        assert ToolType.HTTP == ToolType("http")
        assert ToolType.DB == ToolType("db")
        assert ToolType.DOCKER == ToolType("docker")

    def test_tool_type_values(self):
        """Test tool type string values."""
        assert ToolType.FILES.value == "files"
        assert ToolType.GIT.value == "git"
        assert ToolType.TESTS.value == "tests"
        assert ToolType.HTTP.value == "http"
        assert ToolType.DB.value == "db"
        assert ToolType.DOCKER.value == "docker"


class TestToolTypeFromString:
    """Test ToolType.from_string() method."""

    def test_from_string_with_valid_tool_names(self):
        """Test from_string with valid tool names."""
        assert ToolType.from_string("files") == ToolType.FILES
        assert ToolType.from_string("git") == ToolType.GIT
        assert ToolType.from_string("tests") == ToolType.TESTS
        assert ToolType.from_string("http") == ToolType.HTTP
        assert ToolType.from_string("db") == ToolType.DB
        assert ToolType.from_string("docker") == ToolType.DOCKER

    def test_from_string_raises_error_on_invalid_tool_name(self):
        """Test from_string raises error on invalid tool name."""
        with pytest.raises(ValueError, match="Unknown tool type"):
            ToolType.from_string("invalid_tool")

    def test_from_string_raises_error_on_empty_string(self):
        """Test from_string raises error on empty string."""
        with pytest.raises(ValueError, match="Unknown tool type"):
            ToolType.from_string("")

    def test_from_string_is_case_sensitive(self):
        """Test from_string is case sensitive."""
        with pytest.raises(ValueError, match="Unknown tool type"):
            ToolType.from_string("FILES")


class TestToolTypeStringRepresentation:
    """Test ToolType string representation."""

    def test_str_returns_tool_name(self):
        """Test __str__ returns the tool name."""
        assert str(ToolType.FILES) == "files"
        assert str(ToolType.GIT) == "git"
        assert str(ToolType.TESTS) == "tests"
        assert str(ToolType.HTTP) == "http"
        assert str(ToolType.DB) == "db"
        assert str(ToolType.DOCKER) == "docker"

