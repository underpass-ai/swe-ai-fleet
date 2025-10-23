"""Unit tests for FileTool."""

import pytest

from core.tools import FileTool


class TestFileTool:
    """Test File Tool operations."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create test workspace."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        return workspace

    @pytest.fixture
    def file_tool(self, workspace):
        """Create FileTool instance."""
        return FileTool(workspace)

    def test_write_and_read_file(self, file_tool, workspace):
        """Test writing and reading a file."""
        # Write file
        content = "def main():\n    pass\n"
        write_result = file_tool.write_file("main.py", content)

        assert write_result.success
        assert write_result.operation == "write"
        assert (workspace / "main.py").exists()

        # Read file
        read_result = file_tool.read_file("main.py")

        assert read_result.success
        assert read_result.content == content
        assert read_result.metadata["lines"] == 2

    def test_append_file(self, file_tool, workspace):
        """Test appending to a file."""
        # Create file
        file_tool.write_file("log.txt", "Line 1\n")

        # Append
        append_result = file_tool.append_file("log.txt", "Line 2\n")

        assert append_result.success

        # Verify
        read_result = file_tool.read_file("log.txt")
        assert "Line 1\nLine 2\n" == read_result.content

    def test_search_in_files(self, file_tool, workspace):
        """Test searching for patterns in files."""
        # Create test files
        file_tool.write_file("file1.py", "def hello():\n    print('hello')\n")
        file_tool.write_file("file2.py", "def world():\n    print('world')\n")

        # Search for pattern
        result = file_tool.search_in_files("def ", extensions=[".py"])

        assert result.success
        # Should find both files
        assert "file1.py" in result.content or "def hello" in result.content

    def test_list_files(self, file_tool, workspace):
        """Test listing files in directory."""
        # Create structure
        (workspace / "src").mkdir()
        file_tool.write_file("src/main.py", "")
        file_tool.write_file("src/utils.py", "")
        file_tool.write_file("README.md", "")

        # List all files
        result = file_tool.list_files(".", recursive=True)

        assert result.success
        assert "src/main.py" in result.content
        assert "README.md" in result.content
        assert result.metadata["count"] >= 3

    def test_edit_file(self, file_tool, workspace):
        """Test editing file with search/replace."""
        # Create file
        original = "old_name = 'value'\n"
        file_tool.write_file("config.py", original)

        # Edit
        edit_result = file_tool.edit_file("config.py", "old_name", "new_name")

        assert edit_result.success
        assert edit_result.metadata["replacements"] == 1

        # Verify change
        read_result = file_tool.read_file("config.py")
        assert "new_name" in read_result.content
        assert "old_name" not in read_result.content

    def test_mkdir(self, file_tool, workspace):
        """Test creating directories."""
        # Create nested directory
        result = file_tool.mkdir("src/utils/helpers", parents=True)

        assert result.success
        assert (workspace / "src" / "utils" / "helpers").exists()

    def test_delete_file(self, file_tool, workspace):
        """Test deleting files."""
        # Create file
        file_tool.write_file("temp.txt", "temp")

        # Delete
        result = file_tool.delete_file("temp.txt")

        assert result.success
        assert not (workspace / "temp.txt").exists()

    def test_file_info(self, file_tool, workspace):
        """Test getting file information."""
        # Create file
        content = "test content\n"
        file_tool.write_file("test.py", content)

        # Get info
        result = file_tool.file_info("test.py")

        assert result.success
        assert result.metadata["type"] == "file"
        assert result.metadata["size"] > 0
        assert result.metadata["extension"] == ".py"
        assert result.metadata["is_binary"] is False

    def test_diff_identical_files(self, file_tool, workspace):
        """Test diff of identical files."""
        content = "same content\n"
        file_tool.write_file("file1.txt", content)
        file_tool.write_file("file2.txt", content)

        # Diff
        result = file_tool.diff_files("file1.txt", "file2.txt")

        assert result.success
        assert result.metadata["identical"] is True

    def test_diff_different_files(self, file_tool, workspace):
        """Test diff of different files."""
        file_tool.write_file("file1.txt", "line 1\nline 2\n")
        file_tool.write_file("file2.txt", "line 1\nmodified line 2\n")

        # Diff
        result = file_tool.diff_files("file1.txt", "file2.txt")

        assert result.success
        assert result.metadata["identical"] is False
        assert "line 2" in result.content or "modified" in result.content

    def test_path_traversal_protection(self, file_tool, workspace):
        """Test path traversal is prevented."""
        # Create file outside workspace
        outside_dir = workspace.parent.parent / "outside"
        outside_dir.mkdir(parents=True, exist_ok=True)
        outside_file = outside_dir / "secret.txt"
        outside_file.write_text("secret")
        
        # Try to read - should be blocked
        result = file_tool.read_file(outside_file)
        
        # Should fail with error (not raise, returns FileResult)
        assert not result.success
        assert "outside workspace" in result.error.lower()

    def test_binary_file_detection(self, file_tool, workspace):
        """Test binary file is detected and rejected."""
        # Create binary file
        binary_path = workspace / "binary.bin"
        with open(binary_path, "wb") as f:
            f.write(b"\x00\x01\x02\xFF")

        # Try to read
        result = file_tool.read_file("binary.bin")

        assert not result.success
        assert "binary" in result.error.lower()

    def test_large_file_rejected(self, file_tool, workspace):
        """Test very large file is rejected."""
        # Create large file (> 10MB)
        large_path = workspace / "large.txt"
        with open(large_path, "w") as f:
            f.write("A" * (11 * 1024 * 1024))  # 11MB

        # Try to read
        result = file_tool.read_file("large.txt")

        assert not result.success
        assert "too large" in result.error.lower()

