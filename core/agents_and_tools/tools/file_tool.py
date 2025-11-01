"""
File and code operations tool for agent workspace execution.

Provides safe file manipulation within workspace boundaries.
"""

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

FileOperation = Literal[
    "read",
    "write",
    "append",
    "search",
    "list",
    "edit",
    "delete",
    "mkdir",
    "info",
    "diff",
]


@dataclass
class FileResult:
    """Result of a file operation."""

    success: bool
    operation: FileOperation
    content: str | None
    metadata: dict[str, Any]
    error: str | None = None


class FileTool:
    """
    File operations tool for workspace execution.

    Security:
    - All operations restricted to workspace directory
    - Path traversal prevention
    - Binary file detection
    - Size limits for safety
    - Audit trail of all operations
    """

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit

    @staticmethod
    def create(workspace_path: str | Path, audit_callback: Callable | None = None) -> "FileTool":
        """Factory method to create FileTool instance."""
        # Inject mapper dependency
        from core.agents_and_tools.common.infrastructure.mappers import FileResultMapper
        mapper = FileResultMapper()
        return FileTool(workspace_path, audit_callback, mapper)

    def __init__(
        self, workspace_path: str | Path, audit_callback: Callable | None = None, mapper: Any = None
    ):
        """
        Initialize File tool.

        Args:
            workspace_path: Root workspace directory
            audit_callback: Optional callback for audit logging
            mapper: FileResultMapper instance (injected dependency)
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.audit_callback = audit_callback

        # Inject mapper dependency
        if mapper is None:
            from core.agents_and_tools.common.infrastructure.mappers import FileResultMapper
            self.mapper = FileResultMapper()
        else:
            self.mapper = mapper

        # Validate workspace exists
        if not self.workspace_path.exists():
            raise ValueError(f"Workspace path does not exist: {self.workspace_path}")

    def _audit(self, operation: str, params: dict[str, Any], result: FileResult) -> None:
        """Log operation to audit trail."""
        if self.audit_callback:
            self.audit_callback(
                {
                    "tool": "file",
                    "operation": operation,
                    "params": {
                        k: v
                        for k, v in params.items()
                        if k not in ["content"]  # Don't log full content
                    },
                    "success": result.success,
                    "workspace": str(self.workspace_path),
                }
            )

    def _validate_path(self, path: str | Path) -> Path:
        """
        Validate path is within workspace and resolve it.

        Args:
            path: Path to validate

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path is outside workspace
        """
        # Convert to Path and resolve
        if isinstance(path, str):
            path = Path(path)

        # If relative, make it relative to workspace
        if not path.is_absolute():
            path = self.workspace_path / path

        # Resolve to absolute path
        resolved = path.resolve()

        # Check if within workspace
        try:
            resolved.relative_to(self.workspace_path)
        except ValueError:
            raise ValueError(f"Path outside workspace: {path}") from None

        return resolved

    def _is_binary(self, file_path: Path) -> bool:
        """
        Check if file is binary.

        Args:
            file_path: Path to check

        Returns:
            True if binary, False if text
        """
        try:
            # Read first 8KB to detect binary
            with open(file_path, "rb") as f:
                chunk = f.read(8192)
                # Check for null bytes (common in binary files)
                if b"\x00" in chunk:
                    return True
            return False
        except Exception:
            return True  # Assume binary if can't read

    def read_file(self, path: str | Path, encoding: str = "utf-8") -> FileResult:
        """
        Read file contents.

        Args:
            path: File path (relative to workspace or absolute)
            encoding: Text encoding (default: utf-8)

        Returns:
            FileResult with file content
        """
        try:
            file_path = self._validate_path(path)

            if not file_path.exists():
                return FileResult(
                    success=False,
                    operation="read",
                    content=None,
                    metadata={"path": str(file_path)},
                    error="File does not exist",
                )

            if not file_path.is_file():
                return FileResult(
                    success=False,
                    operation="read",
                    content=None,
                    metadata={"path": str(file_path)},
                    error="Path is not a file",
                )

            # Check file size
            size = file_path.stat().st_size
            if size > self.MAX_FILE_SIZE:
                return FileResult(
                    success=False,
                    operation="read",
                    content=None,
                    metadata={"path": str(file_path), "size": size},
                    error=f"File too large: {size} bytes (max: {self.MAX_FILE_SIZE})",
                )

            # Check if binary
            if self._is_binary(file_path):
                return FileResult(
                    success=False,
                    operation="read",
                    content=None,
                    metadata={"path": str(file_path), "type": "binary"},
                    error="Cannot read binary file",
                )

            # Read content
            with open(file_path, encoding=encoding) as f:
                content = f.read()

            result = FileResult(
                success=True,
                operation="read",
                content=content,
                metadata={
                    "path": str(file_path),
                    "size": size,
                    "lines": len(content.splitlines()),
                },
            )

            self._audit("read", {"path": str(path)}, result)
            return result

        except Exception as e:
            return FileResult(
                success=False,
                operation="read",
                content=None,
                metadata={"path": str(path)},
                error=f"Error reading file: {e}",
            )

    def write_file(
        self, path: str | Path, content: str, encoding: str = "utf-8", create_dirs: bool = True
    ) -> FileResult:
        """
        Write content to file (overwrites if exists).

        Args:
            path: File path (relative to workspace or absolute)
            content: Content to write
            encoding: Text encoding (default: utf-8)
            create_dirs: Create parent directories if they don't exist

        Returns:
            FileResult with operation status
        """
        try:
            file_path = self._validate_path(path)

            # Create parent directories if requested
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            with open(file_path, "w", encoding=encoding) as f:
                f.write(content)

            size = file_path.stat().st_size

            result = FileResult(
                success=True,
                operation="write",
                content=None,
                metadata={
                    "path": str(file_path),
                    "size": size,
                    "lines": len(content.splitlines()),
                },
            )

            self._audit("write", {"path": str(path), "size": size}, result)
            return result

        except Exception as e:
            return FileResult(
                success=False,
                operation="write",
                content=None,
                metadata={"path": str(path)},
                error=f"Error writing file: {e}",
            )

    def append_file(self, path: str | Path, content: str, encoding: str = "utf-8") -> FileResult:
        """
        Append content to file.

        Args:
            path: File path (relative to workspace or absolute)
            content: Content to append
            encoding: Text encoding (default: utf-8)

        Returns:
            FileResult with operation status
        """
        try:
            file_path = self._validate_path(path)

            # Append content
            with open(file_path, "a", encoding=encoding) as f:
                f.write(content)

            size = file_path.stat().st_size

            result = FileResult(
                success=True,
                operation="append",
                content=None,
                metadata={"path": str(file_path), "size": size},
            )

            self._audit("append", {"path": str(path)}, result)
            return result

        except Exception as e:
            return FileResult(
                success=False,
                operation="append",
                content=None,
                metadata={"path": str(path)},
                error=f"Error appending to file: {e}",
            )

    def search_in_files(
        self, pattern: str, path: str | Path = ".", extensions: list[str] | None = None
    ) -> FileResult:
        """
        Search for pattern in files using ripgrep.

        Args:
            pattern: Search pattern (regex)
            path: Directory to search in (default: workspace root)
            extensions: File extensions to search (e.g., [".py", ".js"])

        Returns:
            FileResult with search results
        """
        try:
            search_path = self._validate_path(path)

            # Use ripgrep if available, fallback to grep
            cmd = ["rg", "--no-heading", "--line-number", "--color=never"]

            if extensions:
                for ext in extensions:
                    cmd.extend(["--glob", f"*{ext}"])

            cmd.extend([pattern, str(search_path)])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            # ripgrep returns 1 if no matches, 0 if matches, 2+ for errors
            success = result.returncode in [0, 1]

            file_result = FileResult(
                success=success,
                operation="search",
                content=result.stdout if success else None,
                metadata={
                    "pattern": pattern,
                    "path": str(search_path),
                    "matches": len(result.stdout.splitlines()) if success else 0,
                },
                error=result.stderr if not success else None,
            )

            self._audit("search", {"pattern": pattern, "path": str(path)}, file_result)
            return file_result

        except FileNotFoundError:
            # ripgrep not installed, fallback to grep
            try:
                cmd = ["grep", "-rn", "--color=never", pattern, str(search_path)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                success = result.returncode in [0, 1]

                return FileResult(
                    success=success,
                    operation="search",
                    content=result.stdout if success else None,
                    metadata={"pattern": pattern, "path": str(search_path)},
                    error=result.stderr if not success else None,
                )
            except Exception as e:
                return FileResult(
                    success=False,
                    operation="search",
                    content=None,
                    metadata={"pattern": pattern},
                    error=f"Search failed: {e}",
                )

        except Exception as e:
            return FileResult(
                success=False,
                operation="search",
                content=None,
                metadata={"pattern": pattern},
                error=f"Search error: {e}",
            )

    def list_files(
        self,
        path: str | Path = ".",
        recursive: bool = False,
        pattern: str | None = None,
    ) -> FileResult:
        """
        List files in directory.

        Args:
            path: Directory path (relative to workspace or absolute)
            recursive: List recursively
            pattern: Glob pattern to filter files

        Returns:
            FileResult with file listing
        """
        try:
            dir_path = self._validate_path(path)

            if not dir_path.is_dir():
                return FileResult(
                    success=False,
                    operation="list",
                    content=None,
                    metadata={"path": str(dir_path)},
                    error="Path is not a directory",
                )

            # List files
            if recursive:
                if pattern:
                    files = list(dir_path.rglob(pattern))
                else:
                    files = list(dir_path.rglob("*"))
            else:
                if pattern:
                    files = list(dir_path.glob(pattern))
                else:
                    files = list(dir_path.glob("*"))

            # Format output
            file_list = []
            for f in sorted(files):
                rel_path = f.relative_to(self.workspace_path)
                file_type = "dir" if f.is_dir() else "file"
                size = f.stat().st_size if f.is_file() else 0
                file_list.append(f"{file_type:4s} {size:>10d}  {rel_path}")

            content = "\n".join(file_list)

            result = FileResult(
                success=True,
                operation="list",
                content=content,
                metadata={
                    "path": str(dir_path),
                    "count": len(files),
                    "recursive": recursive,
                },
            )

            self._audit("list", {"path": str(path), "recursive": recursive}, result)
            return result

        except Exception as e:
            return FileResult(
                success=False,
                operation="list",
                content=None,
                metadata={"path": str(path)},
                error=f"Error listing files: {e}",
            )

    def edit_file(
        self, path: str | Path, search: str, replace: str, encoding: str = "utf-8"
    ) -> FileResult:
        """
        Edit file by searching and replacing text.

        Args:
            path: File path (relative to workspace or absolute)
            search: Text to search for
            replace: Text to replace with
            encoding: Text encoding (default: utf-8)

        Returns:
            FileResult with operation status
        """
        try:
            # Read current content
            read_result = self.read_file(path, encoding)
            if not read_result.success:
                return read_result

            content = read_result.content
            if content is None:
                return FileResult(
                    success=False,
                    operation="edit",
                    content=None,
                    metadata={"path": str(path)},
                    error="No content to edit",
                )

            # Perform replacement
            new_content = content.replace(search, replace)

            # Count replacements
            replacements = content.count(search)

            if replacements == 0:
                return FileResult(
                    success=False,
                    operation="edit",
                    content=None,
                    metadata={"path": str(path), "replacements": 0},
                    error="Search text not found",
                )

            # Write new content
            write_result = self.write_file(path, new_content, encoding, create_dirs=False)

            if not write_result.success:
                return write_result

            result = FileResult(
                success=True,
                operation="edit",
                content=None,
                metadata={
                    "path": str(path),
                    "replacements": replacements,
                    "size": write_result.metadata["size"],
                },
            )

            self._audit("edit", {"path": str(path), "replacements": replacements}, result)
            return result

        except Exception as e:
            return FileResult(
                success=False,
                operation="edit",
                content=None,
                metadata={"path": str(path)},
                error=f"Error editing file: {e}",
            )

    def delete_file(self, path: str | Path) -> FileResult:
        """
        Delete file or directory.

        Args:
            path: Path to delete (relative to workspace or absolute)

        Returns:
            FileResult with operation status
        """
        try:
            file_path = self._validate_path(path)

            if not file_path.exists():
                return FileResult(
                    success=False,
                    operation="delete",
                    content=None,
                    metadata={"path": str(file_path)},
                    error="Path does not exist",
                )

            # Delete
            if file_path.is_dir():
                import shutil

                shutil.rmtree(file_path)
            else:
                file_path.unlink()

            result = FileResult(
                success=True,
                operation="delete",
                content=None,
                metadata={"path": str(file_path)},
            )

            self._audit("delete", {"path": str(path)}, result)
            return result

        except Exception as e:
            return FileResult(
                success=False,
                operation="delete",
                content=None,
                metadata={"path": str(path)},
                error=f"Error deleting: {e}",
            )

    def mkdir(self, path: str | Path, parents: bool = True) -> FileResult:
        """
        Create directory.

        Args:
            path: Directory path (relative to workspace or absolute)
            parents: Create parent directories if needed

        Returns:
            FileResult with operation status
        """
        try:
            dir_path = self._validate_path(path)

            # Create directory
            dir_path.mkdir(parents=parents, exist_ok=True)

            result = FileResult(
                success=True,
                operation="mkdir",
                content=None,
                metadata={"path": str(dir_path)},
            )

            self._audit("mkdir", {"path": str(path)}, result)
            return result

        except Exception as e:
            return FileResult(
                success=False,
                operation="mkdir",
                content=None,
                metadata={"path": str(path)},
                error=f"Error creating directory: {e}",
            )

    def file_info(self, path: str | Path) -> FileResult:
        """
        Get file information.

        Args:
            path: File path (relative to workspace or absolute)

        Returns:
            FileResult with file metadata
        """
        try:
            file_path = self._validate_path(path)

            if not file_path.exists():
                return FileResult(
                    success=False,
                    operation="info",
                    content=None,
                    metadata={"path": str(file_path)},
                    error="Path does not exist",
                )

            stat = file_path.stat()

            info = {
                "path": str(file_path),
                "name": file_path.name,
                "type": "directory" if file_path.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "permissions": oct(stat.st_mode)[-3:],
            }

            if file_path.is_file():
                info["extension"] = file_path.suffix
                info["is_binary"] = self._is_binary(file_path)

            result = FileResult(
                success=True,
                operation="info",
                content=None,
                metadata=info,
            )

            self._audit("info", {"path": str(path)}, result)
            return result

        except Exception as e:
            return FileResult(
                success=False,
                operation="info",
                content=None,
                metadata={"path": str(path)},
                error=f"Error getting file info: {e}",
            )

    def diff_files(
        self,
        file1: str | Path,
        file2: str | Path | None = None,
        context_lines: int = 3,
        unified: bool = True,
    ) -> FileResult:
        """
        Show differences between files or between file and its content.

        Args:
            file1: First file path (or file to compare with file2)
            file2: Second file path (None to show diff of modified file vs original)
            context_lines: Number of context lines to show (default: 3)
            unified: Use unified diff format (default: True)

        Returns:
            FileResult with diff output

        Examples:
            # Compare two files
            diff_files("src/main.py", "src/main_backup.py")

            # Show changes in file (requires git)
            diff_files("src/main.py")  # Shows git diff if in git repo
        """
        try:
            file1_path = self._validate_path(file1)

            if not file1_path.exists():
                return FileResult(
                    success=False,
                    operation="diff",
                    content=None,
                    metadata={"file1": str(file1_path)},
                    error="First file does not exist",
                )

            if file2 is None:
                # Try to get diff from git if in a git repo
                cmd = ["git", "diff", str(file1_path)]
                result = subprocess.run(
                    cmd,
                    cwd=self.workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    if result.stdout:
                        diff_result = FileResult(
                            success=True,
                            operation="diff",
                            content=result.stdout,
                            metadata={
                                "file1": str(file1_path),
                                "type": "git_diff",
                            },
                        )
                    else:
                        diff_result = FileResult(
                            success=True,
                            operation="diff",
                            content="No changes detected",
                            metadata={
                                "file1": str(file1_path),
                                "type": "git_diff",
                                "changes": False,
                            },
                        )
                else:
                    diff_result = FileResult(
                        success=False,
                        operation="diff",
                        content=None,
                        metadata={"file1": str(file1_path)},
                        error="Not in a git repository or file not tracked",
                    )

                self._audit("diff", {"file1": str(file1)}, diff_result)
                return diff_result

            # Compare two files
            file2_path = self._validate_path(file2)

            if not file2_path.exists():
                return FileResult(
                    success=False,
                    operation="diff",
                    content=None,
                    metadata={"file1": str(file1_path), "file2": str(file2_path)},
                    error="Second file does not exist",
                )

            # Check if files are binary
            if self._is_binary(file1_path) or self._is_binary(file2_path):
                return FileResult(
                    success=False,
                    operation="diff",
                    content=None,
                    metadata={"file1": str(file1_path), "file2": str(file2_path)},
                    error="Cannot diff binary files",
                )

            # Use diff command
            args = ["diff"]
            if unified:
                args.append(f"-u{context_lines}")
            else:
                args.append(f"-c{context_lines}")

            args.extend([str(file1_path), str(file2_path)])

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # diff returns 0 if files are same, 1 if different, 2+ for errors
            success = result.returncode in [0, 1]

            if result.returncode == 0:
                content = "Files are identical"
            elif result.returncode == 1:
                content = result.stdout
            else:
                content = None

            diff_result = FileResult(
                success=success,
                operation="diff",
                content=content,
                metadata={
                    "file1": str(file1_path),
                    "file2": str(file2_path),
                    "identical": result.returncode == 0,
                    "context_lines": context_lines,
                },
                error=result.stderr if not success else None,
            )

            self._audit(
                "diff", {"file1": str(file1), "file2": str(file2)}, diff_result
            )
            return diff_result

        except Exception as e:
            return FileResult(
                success=False,
                operation="diff",
                content=None,
                metadata={"file1": str(file1), "file2": str(file2) if file2 else None},
                error=f"Error computing diff: {e}",
            )

    def get_operations(self) -> dict[str, Any]:
        """Return dictionary mapping operation names to method callables."""
        return {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "append_file": self.append_file,
            "search_in_files": self.search_in_files,
            "list_files": self.list_files,
            "edit_file": self.edit_file,
            "delete_file": self.delete_file,
            "mkdir": self.mkdir,
            "file_info": self.file_info,
            "diff_files": self.diff_files,
        }

    def execute(self, operation: str, **params: Any) -> FileResult:
        """
        Execute a file operation by name.

        Args:
            operation: Name of the operation
            **params: Operation parameters

        Returns:
            FileResult

        Raises:
            ValueError: If operation is not supported
        """
        operations = self.get_operations()
        method = operations.get(operation)
        if not method:
            raise ValueError(f"Unknown file operation: {operation}")
        return method(**params)

    def _get_mapper(self):
        """Return the mapper for FileTool results."""
        # Mapper is now injected via __init__ or factory method
        return self.mapper

    def get_mapper(self):
        """Return the tool's mapper instance."""
        return self.mapper

    def summarize_result(self, operation: str, tool_result: Any, params: dict[str, Any]) -> str:
        """
        Summarize tool operation result for logging.

        Args:
            operation: The operation that was executed
            tool_result: The result from the tool
            params: The operation parameters

        Returns:
            Human-readable summary
        """
        if operation == "read_file":
            if tool_result.content:
                lines = len(tool_result.content.split("\n"))
                return f"Read file ({lines} lines)"
        elif operation == "list_files":
            if tool_result.content:
                files = tool_result.content.split("\n")
                return f"Found {len(files)} files"
        elif operation == "search_in_files":
            if tool_result.content:
                matches = len([line for line in tool_result.content.split("\n") if line.strip()])
                return f"Found {matches} matches"
        elif operation in ["write_file", "append_file", "edit_file"]:
            return f"Modified {params.get('path', 'file')}"

        return "File operation completed"

    def collect_artifacts(self, operation: str, _tool_result: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Collect artifacts from file operation.

        Args:
            operation: The operation that was executed
            tool_result: The result from the tool
            params: The operation parameters

        Returns:
            Dictionary of artifacts
        """
        artifacts = {}

        if operation in ["write_file", "append_file", "edit_file"]:
            file_path = params.get("file_path") or params.get("path")
            if file_path:
                artifacts["files_modified"] = [file_path]

        return artifacts


# Convenience function for use in agent tasks
def execute_file_operation(
    operation: FileOperation,
    workspace_path: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Execute a file operation from agent workspace.

    Args:
        operation: File operation to perform
        workspace_path: Workspace directory path
        **kwargs: Operation-specific parameters

    Returns:
        Dictionary with operation result

    Example:
        result = execute_file_operation(
            "read",
            "/workspace",
            path="src/main.py"
        )
    """
    tool = FileTool(workspace_path)

    # Map operation to method
    operation_map = {
        "read": "read_file",
        "write": "write_file",
        "append": "append_file",
        "search": "search_in_files",
        "list": "list_files",
        "edit": "edit_file",
        "delete": "delete_file",
        "mkdir": "mkdir",
        "info": "file_info",
        "diff": "diff_files",
    }

    method_name = operation_map.get(operation, operation)
    method = getattr(tool, method_name)
    result = method(**kwargs)

    return {
        "success": result.success,
        "operation": result.operation,
        "content": result.content,
        "metadata": result.metadata,
        "error": result.error,
    }

