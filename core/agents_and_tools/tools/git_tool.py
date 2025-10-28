"""
Git operations tool for agent workspace execution.

All operations run within the workspace container with proper validation and audit.
"""

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

GitOperation = Literal[
    "clone",
    "status",
    "add",
    "commit",
    "push",
    "pull",
    "checkout",
    "branch",
    "diff",
    "log",
]


@dataclass
class GitResult:
    """Result of a git operation."""

    success: bool
    operation: GitOperation
    stdout: str
    stderr: str
    exit_code: int
    metadata: dict[str, Any]


class GitTool:
    """
    Git operations tool for workspace execution.

    Security:
    - All operations run in workspace directory only
    - No command injection via shell=False
    - Validation of all inputs
    - Audit trail of all operations
    """

    @staticmethod
    def create(workspace_path: str | Path, audit_callback: Callable | None = None) -> "GitTool":
        """Factory method to create GitTool instance."""
        # Inject mapper dependency
        from core.agents_and_tools.common.infrastructure.mappers import GitResultMapper
        mapper = GitResultMapper()
        return GitTool(workspace_path, audit_callback, mapper)

    def __init__(self, workspace_path: str | Path, audit_callback: Callable | None = None, mapper: Any = None):
        """
        Initialize Git tool.

        Args:
            workspace_path: Root workspace directory
            audit_callback: Optional callback for audit logging
            mapper: GitResultMapper instance (injected dependency)
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.audit_callback = audit_callback

        # Inject mapper dependency
        if mapper is None:
            from core.agents_and_tools.common.infrastructure.mappers import GitResultMapper
            self.mapper = GitResultMapper()
        else:
            self.mapper = mapper

        # Validate workspace exists
        if not self.workspace_path.exists():
            raise ValueError(f"Workspace path does not exist: {self.workspace_path}")

    def _audit(self, operation: str, params: dict[str, Any], result: GitResult) -> None:
        """Log operation to audit trail."""
        if self.audit_callback:
            self.audit_callback(
                {
                    "tool": "git",
                    "operation": operation,
                    "params": params,
                    "success": result.success,
                    "metadata": {"exit_code": result.exit_code},
                    "workspace": str(self.workspace_path),
                }
            )

    def _run_git_command(
        self, args: list[str], operation: GitOperation, cwd: Path | None = None
    ) -> GitResult:
        """
        Run git command safely.

        Args:
            args: Git command arguments (without 'git')
            operation: Operation type for audit
            cwd: Working directory (defaults to workspace_path)

        Returns:
            GitResult with command output and metadata
        """
        if cwd is None:
            cwd = self.workspace_path

        # Ensure cwd is within workspace
        cwd_resolved = Path(cwd).resolve()
        if not str(cwd_resolved).startswith(str(self.workspace_path)):
            raise ValueError(f"Working directory outside workspace: {cwd}")

        cmd = ["git"] + args

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd_resolved,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                check=False,  # Don't raise on non-zero exit
            )

            git_result = GitResult(
                success=result.returncode == 0,
                operation=operation,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                metadata={"cmd": cmd, "cwd": str(cwd_resolved)},
            )

            # Audit the operation
            self._audit(operation, {"args": args}, git_result)

            return git_result

        except subprocess.TimeoutExpired as e:
            return GitResult(
                success=False,
                operation=operation,
                stdout="",
                stderr=f"Command timed out after 300 seconds: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": "timeout"},
            )
        except Exception as e:
            return GitResult(
                success=False,
                operation=operation,
                stdout="",
                stderr=f"Error executing git command: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": str(e)},
            )

    def clone(
        self, repo_url: str, branch: str | None = None, depth: int | None = None
    ) -> GitResult:
        """
        Clone a git repository.

        Args:
            repo_url: Repository URL (https or git protocol)
            branch: Specific branch to clone
            depth: Shallow clone depth (None for full clone)

        Returns:
            GitResult with clone operation status
        """
        # Basic URL validation (prevent command injection)
        if not (repo_url.startswith("https://") or repo_url.startswith("git@")):
            raise ValueError("Only https:// and git@ URLs are allowed")

        args = ["clone"]

        if branch:
            args.extend(["--branch", branch])

        if depth:
            args.extend(["--depth", str(depth)])

        args.append(repo_url)
        args.append(".")  # Clone into current directory

        return self._run_git_command(args, "clone")

    def status(self, short: bool = False) -> GitResult:
        """
        Get git status.

        Args:
            short: Use short format

        Returns:
            GitResult with status output
        """
        args = ["status"]
        if short:
            args.append("--short")

        return self._run_git_command(args, "status")

    def add(self, paths: list[str] | Literal["all"] = "all") -> GitResult:
        """
        Stage files for commit.

        Args:
            paths: List of file paths or "all" for all changes

        Returns:
            GitResult with add operation status
        """
        args = ["add"]

        if paths == "all":
            args.append("--all")
        else:
            # Validate paths are within workspace
            for path in paths:
                full_path = (self.workspace_path / path).resolve()
                if not str(full_path).startswith(str(self.workspace_path)):
                    raise ValueError(f"Path outside workspace: {path}")
            args.extend(paths)

        return self._run_git_command(args, "add")

    def commit(self, message: str, author: str | None = None) -> GitResult:
        """
        Commit staged changes.

        Args:
            message: Commit message
            author: Optional author string (format: "Name <email>")

        Returns:
            GitResult with commit operation status
        """
        if not message:
            raise ValueError("Commit message cannot be empty")

        args = ["commit", "-m", message]

        if author:
            args.extend(["--author", author])

        return self._run_git_command(args, "commit")

    def push(
        self, remote: str = "origin", branch: str | None = None, force: bool = False
    ) -> GitResult:
        """
        Push commits to remote.

        Args:
            remote: Remote name
            branch: Branch name (None for current branch)
            force: Force push (use with caution)

        Returns:
            GitResult with push operation status
        """
        args = ["push"]

        if force:
            args.append("--force-with-lease")  # Safer than --force

        args.append(remote)

        if branch:
            args.append(branch)

        return self._run_git_command(args, "push")

    def pull(self, remote: str = "origin", branch: str | None = None) -> GitResult:
        """
        Pull changes from remote.

        Args:
            remote: Remote name
            branch: Branch name (None for current branch)

        Returns:
            GitResult with pull operation status
        """
        args = ["pull", remote]

        if branch:
            args.append(branch)

        return self._run_git_command(args, "pull")

    def checkout(self, branch: str, create: bool = False) -> GitResult:
        """
        Checkout a branch.

        Args:
            branch: Branch name
            create: Create branch if it doesn't exist

        Returns:
            GitResult with checkout operation status
        """
        args = ["checkout"]

        if create:
            args.append("-b")

        args.append(branch)

        return self._run_git_command(args, "checkout")

    def branch(self, list_all: bool = False, delete: str | None = None) -> GitResult:
        """
        Manage branches.

        Args:
            list_all: List all branches (local and remote)
            delete: Branch name to delete

        Returns:
            GitResult with branch operation status
        """
        args = ["branch"]

        if list_all:
            args.append("--all")

        if delete:
            args.extend(["-d", delete])

        return self._run_git_command(args, "branch")

    def diff(self, cached: bool = False, files: list[str] | None = None) -> GitResult:
        """
        Show changes.

        Args:
            cached: Show staged changes
            files: Specific files to diff

        Returns:
            GitResult with diff output
        """
        args = ["diff"]

        if cached:
            args.append("--cached")

        if files:
            args.append("--")
            args.extend(files)

        return self._run_git_command(args, "diff")

    def log(self, max_count: int = 10, oneline: bool = False) -> GitResult:
        """
        Show commit history.

        Args:
            max_count: Maximum number of commits to show
            oneline: Use compact one-line format

        Returns:
            GitResult with log output
        """
        args = ["log", f"--max-count={max_count}"]

        if oneline:
            args.append("--oneline")

        return self._run_git_command(args, "log")

    def get_operations(self) -> dict[str, Any]:
        """Return dictionary mapping operation names to method callables."""
        return {
            "clone": self.clone,
            "status": self.status,
            "add": self.add,
            "commit": self.commit,
            "push": self.push,
            "pull": self.pull,
            "checkout": self.checkout,
            "branch": self.branch,
            "diff": self.diff,
            "log": self.log,
        }

    def execute(self, operation: str, **params: Any) -> GitResult:
        """
        Execute a git operation by name.

        Args:
            operation: Name of the operation
            **params: Operation parameters

        Returns:
            GitResult

        Raises:
            ValueError: If operation is not supported
        """
        operations = self.get_operations()
        method = operations.get(operation)
        if not method:
            raise ValueError(f"Unknown git operation: {operation}")
        return method(**params)

    def _get_mapper(self):
        """Return the mapper for GitTool results."""
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
        if operation == "status":
            if tool_result.content:
                changes = len([l for l in tool_result.content.split("\n") if l.strip() and not l.startswith("#")])
                return f"{changes} files changed"
        elif operation == "log":
            if tool_result.content:
                commits = len([l for l in tool_result.content.split("\n") if l.strip()])
                return f"{commits} commits in history"
        elif operation == "commit":
            return "Created commit"
        elif operation == "branch":
            return "Listed branches"
        elif operation == "push":
            return "Pushed to remote"
        elif operation == "pull":
            return "Pulled from remote"

        return "Git operation completed"

    def collect_artifacts(self, operation: str, tool_result: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Collect artifacts from git operation.

        Args:
            operation: The operation that was executed
            tool_result: The result from the tool
            params: The operation parameters

        Returns:
            Dictionary of artifacts
        """
        artifacts = {}

        if operation == "commit" and tool_result.content:
            # Extract commit SHA from output
            if "commit" in tool_result.content.lower():
                try:
                    artifacts["commit_sha"] = tool_result.content.split()[1][:7]
                except (IndexError, AttributeError):
                    pass

        if operation == "status" and tool_result.content:
            # Extract changed files
            changed = [
                line.split()[-1]
                for line in tool_result.content.split("\n")
                if line.strip() and not line.startswith("#")
            ]
            if changed:
                artifacts["files_changed"] = changed

        return artifacts


# Convenience function for use in agent tasks
def execute_git_operation(
    operation: GitOperation,
    workspace_path: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Execute a git operation from agent workspace.

    Args:
        operation: Git operation to perform
        workspace_path: Workspace directory path
        **kwargs: Operation-specific parameters

    Returns:
        Dictionary with operation result

    Example:
        result = execute_git_operation(
            "clone",
            "/workspace",
            repo_url="https://github.com/user/repo.git",
            branch="main"
        )
    """
    tool = GitTool(workspace_path)

    # Map operation to method
    method = getattr(tool, operation)
    result = method(**kwargs)

    return {
        "success": result.success,
        "operation": result.operation,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "metadata": result.metadata,
    }

