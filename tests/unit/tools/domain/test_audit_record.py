"""Unit tests for AuditRecord entity."""

import pytest
from core.agents_and_tools.tools.domain.audit_record import AuditRecord

# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestAuditRecordConstructorValidation:
    """Test constructor fail-fast validation."""

    def test_rejects_empty_tool(self):
        """Should raise ValueError if tool is empty."""
        with pytest.raises(ValueError, match="tool is required and cannot be empty"):
            AuditRecord(
                tool="",  # Empty tool
                operation="build",
                params={},
                success=True,
                metadata={},
                workspace="/workspace",
            )

    def test_rejects_whitespace_only_tool(self):
        """Should raise ValueError if tool is whitespace only."""
        with pytest.raises(ValueError, match="tool is required and cannot be empty"):
            AuditRecord(
                tool="   ",  # Whitespace only
                operation="build",
                params={},
                success=True,
                metadata={},
                workspace="/workspace",
            )

    def test_rejects_empty_operation(self):
        """Should raise ValueError if operation is empty."""
        with pytest.raises(ValueError, match="operation is required and cannot be empty"):
            AuditRecord(
                tool="docker",
                operation="",  # Empty operation
                params={},
                success=True,
                metadata={},
                workspace="/workspace",
            )

    def test_rejects_none_params(self):
        """Should raise ValueError if params is None."""
        with pytest.raises(ValueError, match="params is required"):
            AuditRecord(
                tool="docker",
                operation="build",
                params=None,  # None instead of empty dict
                success=True,
                metadata={},
                workspace="/workspace",
            )

    def test_rejects_non_boolean_success(self):
        """Should raise ValueError if success is not a boolean."""
        with pytest.raises(ValueError, match="success must be a boolean"):
            AuditRecord(
                tool="docker",
                operation="run",
                params={},
                success="true",  # String instead of bool
                metadata={},
                workspace="/workspace",
            )

    def test_rejects_none_metadata(self):
        """Should raise ValueError if metadata is None."""
        with pytest.raises(ValueError, match="metadata is required"):
            AuditRecord(
                tool="docker",
                operation="ps",
                params={},
                success=True,
                metadata=None,  # None instead of empty dict
                workspace="/workspace",
            )

    def test_rejects_empty_workspace(self):
        """Should raise ValueError if workspace is empty."""
        with pytest.raises(ValueError, match="workspace is required and cannot be empty"):
            AuditRecord(
                tool="docker",
                operation="logs",
                params={},
                success=True,
                metadata={},
                workspace="",  # Empty workspace
            )

    def test_accepts_valid_entity(self):
        """Should create entity when all fields are valid."""
        record = AuditRecord(
            tool="docker",
            operation="build",
            params={"context": "."},
            success=True,
            metadata={"exit_code": 0, "runtime": "podman"},
            workspace="/home/user/project",
        )

        assert record.tool == "docker"
        assert record.operation == "build"
        assert record.params == {"context": "."}
        assert record.success is True
        assert record.metadata == {"exit_code": 0, "runtime": "podman"}
        assert record.workspace == "/home/user/project"


# =============================================================================
# Immutability Tests
# =============================================================================

class TestAuditRecordImmutability:
    """Test that AuditRecord is immutable (frozen=True)."""

    def test_cannot_modify_tool(self):
        """Should prevent modification of tool field."""
        record = AuditRecord(
            tool="docker",
            operation="run",
            params={},
            success=True,
            metadata={},
            workspace="/workspace",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            record.tool = "git"

    def test_cannot_modify_success(self):
        """Should prevent modification of success field."""
        record = AuditRecord(
            tool="docker",
            operation="build",
            params={},
            success=True,
            metadata={},
            workspace="/workspace",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            record.success = False


# =============================================================================
# Business Logic Tests
# =============================================================================

class TestAuditRecordBusinessLogic:
    """Test domain logic methods."""

    def test_to_dict_returns_complete_dictionary(self):
        """Should convert entity to dictionary with all fields."""
        record = AuditRecord(
            tool="docker",
            operation="build",
            params={"context": ".", "tag": "myapp:latest"},
            success=True,
            metadata={"exit_code": 0, "runtime": "podman"},
            workspace="/home/user/project",
        )

        result_dict = record.to_dict()

        assert result_dict == {
            "tool": "docker",
            "operation": "build",
            "params": {"context": ".", "tag": "myapp:latest"},
            "success": True,
            "metadata": {"exit_code": 0, "runtime": "podman"},
            "workspace": "/home/user/project",
        }

    def test_is_successful_returns_true_when_success(self):
        """Should return True when success is True."""
        record = AuditRecord(
            tool="git",
            operation="commit",
            params={},
            success=True,
            metadata={},
            workspace="/workspace",
        )

        assert record.is_successful() is True

    def test_is_successful_returns_false_when_failed(self):
        """Should return False when success is False."""
        record = AuditRecord(
            tool="docker",
            operation="run",
            params={},
            success=False,
            metadata={"error": "Container failed"},
            workspace="/workspace",
        )

        assert record.is_successful() is False

    def test_get_identifier_returns_tool_operation_combo(self):
        """Should return tool.operation identifier."""
        record = AuditRecord(
            tool="docker",
            operation="build",
            params={},
            success=True,
            metadata={},
            workspace="/workspace",
        )

        assert record.get_identifier() == "docker.build"

    def test_get_identifier_for_different_tools(self):
        """Should create unique identifiers for different tool/operation combos."""
        record1 = AuditRecord(
            tool="docker", operation="build", params={}, success=True, metadata={}, workspace="/"
        )
        record2 = AuditRecord(
            tool="git", operation="commit", params={}, success=True, metadata={}, workspace="/"
        )
        record3 = AuditRecord(
            tool="docker", operation="run", params={}, success=True, metadata={}, workspace="/"
        )

        assert record1.get_identifier() == "docker.build"
        assert record2.get_identifier() == "git.commit"
        assert record3.get_identifier() == "docker.run"
        assert len({record1.get_identifier(), record2.get_identifier(), record3.get_identifier()}) == 3


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestAuditRecordEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_accepts_empty_params_dict(self):
        """Should accept empty dict for params."""
        record = AuditRecord(
            tool="docker",
            operation="ps",
            params={},
            success=True,
            metadata={},
            workspace="/workspace",
        )

        assert record.params == {}

    def test_accepts_empty_metadata_dict(self):
        """Should accept empty dict for metadata."""
        record = AuditRecord(
            tool="docker",
            operation="stop",
            params={},
            success=True,
            metadata={},
            workspace="/workspace",
        )

        assert record.metadata == {}

    def test_accepts_complex_nested_params(self):
        """Should accept complex nested params."""
        complex_params = {
            "context": ".",
            "build_args": {"ENV": "production", "VERSION": "1.0"},
            "tags": ["latest", "v1.0", "stable"],
        }

        record = AuditRecord(
            tool="docker",
            operation="build",
            params=complex_params,
            success=True,
            metadata={},
            workspace="/workspace",
        )

        assert record.params == complex_params
        assert record.params["build_args"]["ENV"] == "production"

    def test_accepts_complex_nested_metadata(self):
        """Should accept complex nested metadata."""
        complex_metadata = {
            "exit_code": 0,
            "runtime": "podman",
            "timing": {"start": "2025-11-01T10:00:00", "end": "2025-11-01T10:05:00"},
            "resources": {"cpu": "2", "memory": "4G"},
        }

        record = AuditRecord(
            tool="docker",
            operation="run",
            params={},
            success=True,
            metadata=complex_metadata,
            workspace="/workspace",
        )

        assert record.metadata == complex_metadata
        assert record.metadata["timing"]["start"] == "2025-11-01T10:00:00"

    def test_to_dict_preserves_nested_structures(self):
        """Should preserve nested dict structures in to_dict()."""
        record = AuditRecord(
            tool="docker",
            operation="exec",
            params={"command": ["sh", "-c", "echo test"]},
            success=True,
            metadata={"container_id": "abc123"},
            workspace="/workspace",
        )

        result_dict = record.to_dict()

        assert result_dict["params"]["command"] == ["sh", "-c", "echo test"]
        assert result_dict["metadata"]["container_id"] == "abc123"

    def test_accepts_absolute_and_relative_workspace_paths(self):
        """Should accept both absolute and relative workspace paths."""
        record1 = AuditRecord(
            tool="docker", operation="build", params={}, success=True, metadata={}, workspace="/abs/path"
        )
        record2 = AuditRecord(
            tool="docker", operation="build", params={}, success=True, metadata={}, workspace="./relative"
        )

        assert record1.workspace == "/abs/path"
        assert record2.workspace == "./relative"

    def test_equality_of_identical_records(self):
        """Should be equal when all fields are the same."""
        record1 = AuditRecord(
            tool="docker",
            operation="build",
            params={"tag": "v1.0"},
            success=True,
            metadata={"exit_code": 0},
            workspace="/workspace",
        )
        record2 = AuditRecord(
            tool="docker",
            operation="build",
            params={"tag": "v1.0"},
            success=True,
            metadata={"exit_code": 0},
            workspace="/workspace",
        )

        assert record1 == record2

    def test_inequality_when_fields_differ(self):
        """Should not be equal when fields differ."""
        record1 = AuditRecord(
            tool="docker", operation="build", params={}, success=True, metadata={}, workspace="/workspace"
        )
        record2 = AuditRecord(
            tool="docker", operation="run", params={}, success=True, metadata={}, workspace="/workspace"
        )

        assert record1 != record2

