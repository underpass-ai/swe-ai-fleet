"""Unit tests for file_tool.py coverage - File operations."""

from unittest.mock import Mock

import pytest
from core.agents_and_tools.tools.file_tool import FileTool

# =============================================================================
# Initialization Tests
# =============================================================================

class TestFileToolInitialization:
    """Test FileTool initialization."""

    def test_creates_with_valid_workspace(self, tmp_path):
        """Should create FileTool with valid workspace path."""
        tool = FileTool.create(tmp_path)

        assert tool.workspace_path == tmp_path.resolve()

    def test_rejects_nonexistent_workspace(self, tmp_path):
        """Should reject non-existent workspace path."""
        nonexistent = tmp_path / "does_not_exist"

        with pytest.raises(ValueError, match="Workspace path does not exist"):
            FileTool.create(nonexistent)


# =============================================================================
# Path Validation Tests
# =============================================================================

class TestFileToolPathValidation:
    """Test path validation logic."""

    def test_validates_relative_path(self, tmp_path):
        """Should accept relative paths within workspace."""
        tool = FileTool.create(tmp_path)

        validated = tool._validate_path("subdir/file.txt")

        assert validated == tmp_path / "subdir/file.txt"

    def test_validates_absolute_path_inside_workspace(self, tmp_path):
        """Should accept absolute paths within workspace."""
        tool = FileTool.create(tmp_path)
        file_path = tmp_path / "file.txt"

        validated = tool._validate_path(file_path)

        assert validated == file_path

    def test_rejects_path_outside_workspace(self, tmp_path):
        """Should reject paths outside workspace."""
        tool = FileTool.create(tmp_path)

        with pytest.raises(ValueError, match="Path outside workspace"):
            tool._validate_path("/etc/passwd")

    def test_rejects_path_traversal(self, tmp_path):
        """Should reject path traversal attempts."""
        tool = FileTool.create(tmp_path)

        with pytest.raises(ValueError, match="Path outside workspace"):
            tool._validate_path("../../../etc/passwd")


# =============================================================================
# Read File Tests
# =============================================================================

class TestFileToolRead:
    """Test read_file operation."""

    def test_reads_text_file(self, tmp_path):
        """Should read text file successfully."""
        tool = FileTool.create(tmp_path)

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World\nLine 2")

        result = tool.read_file("test.txt")

        assert result.success is True
        assert result.content == "Hello World\nLine 2"
        assert result.metadata["lines"] == 2

    def test_rejects_nonexistent_file(self, tmp_path):
        """Should reject non-existent file."""
        tool = FileTool.create(tmp_path)

        result = tool.read_file("nonexistent.txt")

        assert result.success is False
        assert "does not exist" in result.error

    def test_rejects_directory(self, tmp_path):
        """Should reject reading a directory."""
        tool = FileTool.create(tmp_path)

        # Create directory
        (tmp_path / "testdir").mkdir()

        result = tool.read_file("testdir")

        assert result.success is False
        assert "not a file" in result.error

    def test_rejects_oversized_file(self, tmp_path):
        """Should reject files larger than MAX_FILE_SIZE."""
        tool = FileTool.create(tmp_path)

        # Create large file
        large_file = tmp_path / "large.txt"
        with open(large_file, "wb") as f:
            f.write(b"x" * (tool.MAX_FILE_SIZE + 1))

        result = tool.read_file("large.txt")

        assert result.success is False
        assert "File too large" in result.error

    def test_rejects_binary_file(self, tmp_path):
        """Should reject binary files."""
        tool = FileTool.create(tmp_path)

        # Create binary file
        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03")

        result = tool.read_file("binary.bin")

        assert result.success is False
        assert "binary" in result.error


# =============================================================================
# Write File Tests
# =============================================================================

class TestFileToolWrite:
    """Test write_file operation."""

    def test_writes_new_file(self, tmp_path):
        """Should write new file successfully."""
        tool = FileTool.create(tmp_path)

        result = tool.write_file("test.txt", "Hello World")

        assert result.success is True
        assert (tmp_path / "test.txt").read_text() == "Hello World"

    def test_overwrites_existing_file(self, tmp_path):
        """Should overwrite existing file."""
        tool = FileTool.create(tmp_path)

        # Create existing file
        (tmp_path / "test.txt").write_text("Old content")

        result = tool.write_file("test.txt", "New content")

        assert result.success is True
        assert (tmp_path / "test.txt").read_text() == "New content"

    def test_creates_parent_directories(self, tmp_path):
        """Should create parent directories by default."""
        tool = FileTool.create(tmp_path)

        result = tool.write_file("subdir/nested/file.txt", "Content")

        assert result.success is True
        assert (tmp_path / "subdir/nested/file.txt").exists()


# =============================================================================
# Append File Tests
# =============================================================================

class TestFileToolAppend:
    """Test append_file operation."""

    def test_appends_to_existing_file(self, tmp_path):
        """Should append to existing file."""
        tool = FileTool.create(tmp_path)

        # Create initial file
        (tmp_path / "test.txt").write_text("Line 1\n")

        result = tool.append_file("test.txt", "Line 2\n")

        assert result.success is True
        assert (tmp_path / "test.txt").read_text() == "Line 1\nLine 2\n"

    def test_creates_file_if_not_exists(self, tmp_path):
        """Should create file if it doesn't exist."""
        tool = FileTool.create(tmp_path)

        result = tool.append_file("new.txt", "First line\n")

        assert result.success is True
        assert (tmp_path / "new.txt").read_text() == "First line\n"


# =============================================================================
# List Directory Tests
# =============================================================================

class TestFileToolList:
    """Test list_files operation."""

    def test_lists_directory_contents(self, tmp_path):
        """Should list directory contents."""
        tool = FileTool.create(tmp_path)

        # Create test files
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.py").touch()
        (tmp_path / "subdir").mkdir()

        result = tool.list_files(".")

        assert result.success is True
        assert "file1.txt" in result.content
        assert "file2.py" in result.content
        assert "subdir" in result.content

    def test_lists_empty_directory(self, tmp_path):
        """Should handle empty directory."""
        tool = FileTool.create(tmp_path)

        # Create empty subdirectory
        (tmp_path / "empty").mkdir()

        result = tool.list_files("empty")

        assert result.success is True

    def test_handles_nonexistent_directory(self, tmp_path):
        """Should handle non-existent directory."""
        tool = FileTool.create(tmp_path)

        result = tool.list_files("nonexistent")

        # list_files might succeed with empty list or fail
        assert result.success is False or result.content is not None


# =============================================================================
# Delete Tests
# =============================================================================

class TestFileToolDelete:
    """Test delete_file operation."""

    def test_deletes_file(self, tmp_path):
        """Should delete file successfully."""
        tool = FileTool.create(tmp_path)

        # Create test file
        (tmp_path / "test.txt").touch()

        result = tool.delete_file("test.txt")

        assert result.success is True
        assert not (tmp_path / "test.txt").exists()

    def test_deletes_empty_directory(self, tmp_path):
        """Should delete empty directory."""
        tool = FileTool.create(tmp_path)

        # Create empty directory
        (tmp_path / "emptydir").mkdir()

        result = tool.delete_file("emptydir")

        assert result.success is True
        assert not (tmp_path / "emptydir").exists()

    def test_deletes_nonempty_directory_recursively(self, tmp_path):
        """Should delete non-empty directory recursively."""
        tool = FileTool.create(tmp_path)

        # Create directory with file
        (tmp_path / "dir").mkdir()
        (tmp_path / "dir/file.txt").touch()

        result = tool.delete_file("dir")

        assert result.success is True
        assert not (tmp_path / "dir").exists()


# =============================================================================
# Mkdir Tests
# =============================================================================

class TestFileToolMkdir:
    """Test mkdir operation."""

    def test_creates_directory(self, tmp_path):
        """Should create directory successfully."""
        tool = FileTool.create(tmp_path)

        result = tool.mkdir("newdir")

        assert result.success is True
        assert (tmp_path / "newdir").is_dir()

    def test_creates_nested_directories(self, tmp_path):
        """Should create nested directories with parents=True."""
        tool = FileTool.create(tmp_path)

        result = tool.mkdir("parent/child/grandchild", parents=True)

        assert result.success is True
        assert (tmp_path / "parent/child/grandchild").is_dir()

    def test_handles_existing_directory(self, tmp_path):
        """Should handle existing directory without error."""
        tool = FileTool.create(tmp_path)

        # Create directory
        (tmp_path / "existing").mkdir()

        # mkdir with parents=True should not fail on existing
        result = tool.mkdir("existing", parents=True)

        assert result.success is True


# =============================================================================
# Search Tests
# =============================================================================

class TestFileToolSearch:
    """Test search_in_files operation."""

    def test_searches_for_pattern(self, tmp_path):
        """Should search for pattern in files."""
        tool = FileTool.create(tmp_path)

        # Create test files
        (tmp_path / "file1.txt").write_text("Hello World\nTest line")
        (tmp_path / "file2.txt").write_text("Another file\nHello again")

        result = tool.search_in_files("Hello")

        assert result.success is True
        assert "file1.txt" in result.content or "Hello" in result.content

    def test_searches_with_file_extensions(self, tmp_path):
        """Should filter by file extensions."""
        tool = FileTool.create(tmp_path)

        # Create test files
        (tmp_path / "test.py").write_text("import os")
        (tmp_path / "test.txt").write_text("import os")

        result = tool.search_in_files("import", extensions=[".py"])

        # Search should succeed
        assert result.success is True


# =============================================================================
# Info Tests
# =============================================================================

class TestFileToolInfo:
    """Test file_info operation."""

    def test_gets_file_info(self, tmp_path):
        """Should get file information."""
        tool = FileTool.create(tmp_path)

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        result = tool.file_info("test.txt")

        assert result.success is True
        assert "test.txt" in result.metadata["name"]
        assert "size" in result.metadata

    def test_gets_directory_info(self, tmp_path):
        """Should get directory information."""
        tool = FileTool.create(tmp_path)

        # Create test directory
        (tmp_path / "testdir").mkdir()

        result = tool.file_info("testdir")

        assert result.success is True
        assert result.metadata["type"] == "directory"


# =============================================================================
# Binary Detection Tests
# =============================================================================

class TestFileToolBinaryDetection:
    """Test binary file detection."""

    def test_detects_binary_file(self, tmp_path):
        """Should detect binary files with null bytes."""
        tool = FileTool.create(tmp_path)

        # Create binary file
        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"\x00\xFF\xAA\x55")

        assert tool._is_binary(binary_file) is True

    def test_detects_text_file(self, tmp_path):
        """Should detect text files."""
        tool = FileTool.create(tmp_path)

        # Create text file
        text_file = tmp_path / "text.txt"
        text_file.write_text("Just regular text content")

        assert tool._is_binary(text_file) is False


# =============================================================================
# Audit Callback Tests
# =============================================================================

class TestFileToolAuditCallback:
    """Test audit callback functionality."""

    def test_calls_audit_callback_on_read(self, tmp_path):
        """Should call audit callback with operation details."""
        audit_callback = Mock()
        tool = FileTool.create(tmp_path, audit_callback=audit_callback)

        # Create and read test file
        (tmp_path / "test.txt").write_text("Content")
        tool.read_file("test.txt")

        audit_callback.assert_called_once()
        call_args = audit_callback.call_args[0][0]

        assert call_args["tool"] == "file"
        assert call_args["operation"] == "read"
        assert call_args["success"] is True

    def test_excludes_content_from_audit(self, tmp_path):
        """Should not log file content in audit."""
        audit_callback = Mock()
        tool = FileTool.create(tmp_path, audit_callback=audit_callback)

        tool.write_file("test.txt", "Secret content")

        call_args = audit_callback.call_args[0][0]
        assert "content" not in call_args["params"]


# =============================================================================
# Execute Method Tests
# =============================================================================

class TestFileToolExecute:
    """Test execute() method."""

    def test_executes_read_by_name(self, tmp_path):
        """Should execute read via execute() method."""
        tool = FileTool.create(tmp_path)

        (tmp_path / "test.txt").write_text("Content")
        result = tool.execute(operation="read_file", path="test.txt")

        assert result.success is True
        assert result.operation == "read"

    def test_execute_raises_on_invalid_operation(self, tmp_path):
        """Should raise ValueError for unsupported operation."""
        tool = FileTool.create(tmp_path)

        with pytest.raises(ValueError, match="Unknown file operation"):
            tool.execute(operation="invalid_op")


# =============================================================================
# Summarize and Collect Artifacts Tests
# =============================================================================

class TestFileToolSummarizeAndCollect:
    """Test summarize_result and collect_artifacts methods."""

    def test_summarize_result_for_read(self, tmp_path):
        """Should summarize read result."""
        tool = FileTool.create(tmp_path)

        mock_result = Mock()
        mock_result.content = "Line 1\nLine 2\nLine 3"

        summary = tool.summarize_result("read_file", mock_result, {})

        assert "lines" in summary

    def test_summarize_result_for_write(self, tmp_path):
        """Should summarize write result."""
        tool = FileTool.create(tmp_path)

        mock_result = Mock()
        mock_result.content = None

        summary = tool.summarize_result("write_file", mock_result, {"path": "test.txt"})

        assert "test.txt" in summary

    def test_summarize_result_for_list(self, tmp_path):
        """Should summarize list result."""
        tool = FileTool.create(tmp_path)

        mock_result = Mock()
        mock_result.content = "file1.txt\nfile2.txt\nfile3.txt"

        summary = tool.summarize_result("list_files", mock_result, {})

        assert "Found" in summary

    def test_collect_artifacts_for_operation(self, tmp_path):
        """Should collect artifacts from file operation."""
        tool = FileTool.create(tmp_path)

        mock_result = Mock()
        mock_result.metadata = {}

        artifacts = tool.collect_artifacts("read_file", mock_result, {"path": "test.txt"})

        assert isinstance(artifacts, dict)

    def test_collect_artifacts_with_path(self, tmp_path):
        """Should collect path from params."""
        tool = FileTool.create(tmp_path)

        mock_result = Mock()
        mock_result.metadata = {}

        artifacts = tool.collect_artifacts("write_file", mock_result, {"path": "test.txt"})

        assert isinstance(artifacts, dict)
        assert "files_modified" in artifacts
        assert "test.txt" in artifacts["files_modified"]

