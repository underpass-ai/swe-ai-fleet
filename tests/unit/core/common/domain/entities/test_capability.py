"""Unit tests for Capability value object."""

import pytest
from core.agents_and_tools.common.domain.entities.capability import Capability


class TestCapabilityCreation:
    """Test Capability value object creation."""

    def test_create_capability_with_valid_values(self):
        """Test creating capability with valid tool and operation."""
        cap = Capability(tool="files", operation="read_file")

        assert cap.tool == "files"
        assert cap.operation == "read_file"
        assert cap.to_string() == "files.read_file"

    def test_create_capability_rejects_empty_tool(self):
        """Test fail-fast on empty tool name."""
        with pytest.raises(ValueError, match="Tool name cannot be empty"):
            Capability(tool="", operation="read_file")

    def test_create_capability_rejects_empty_operation(self):
        """Test fail-fast on empty operation name."""
        with pytest.raises(ValueError, match="Operation name cannot be empty"):
            Capability(tool="files", operation="")

    def test_capability_is_immutable(self):
        """Test capability is frozen (immutable)."""
        cap = Capability(tool="files", operation="read_file")

        with pytest.raises(AttributeError):
            cap.tool = "git"  # type: ignore


class TestCapabilityWriteDetection:
    """Test Capability.is_write_operation() method."""

    def test_detects_write_operations(self):
        """Test correctly identifies write operations."""
        write_ops = [
            Capability("files", "write_file"),
            Capability("files", "edit_file"),
            Capability("files", "delete_file"),
            Capability("git", "commit"),
            Capability("git", "push"),
            Capability("db", "insert"),
            Capability("db", "update"),
        ]

        for cap in write_ops:
            assert cap.is_write_operation() is True, f"{cap} should be write operation"

    def test_detects_read_operations(self):
        """Test correctly identifies read operations."""
        read_ops = [
            Capability("files", "read_file"),
            Capability("git", "log"),
            Capability("git", "diff"),
            Capability("db", "query"),
            Capability("http", "get"),
        ]

        for cap in read_ops:
            assert cap.is_write_operation() is False, f"{cap} should be read operation"


class TestCapabilityStringMethods:
    """Test Capability string representation."""

    def test_to_string_formats_correctly(self):
        """Test to_string() formats as tool.operation."""
        cap = Capability("git", "commit")
        assert cap.to_string() == "git.commit"

    def test_str_returns_formatted_string(self):
        """Test __str__ returns formatted string."""
        cap = Capability("files", "read_file")
        assert str(cap) == "files.read_file"

