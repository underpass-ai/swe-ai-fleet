"""Unit tests for GitTool."""

import subprocess

import pytest

from core.agents_and_tools.tools import GitTool


class TestGitTool:
    """Test Git Tool operations."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create test workspace with git repo."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test Agent"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "agent@test.com"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )

        return workspace

    @pytest.fixture
    def git_tool(self, workspace):
        """Create GitTool instance."""
        return GitTool(workspace)

    def test_git_status(self, git_tool):
        """Test git status command."""
        result = git_tool.status()

        assert result.success
        assert result.operation == "status"
        # Git output can be in different languages
        assert len(result.stdout) > 0 or len(result.stderr) > 0

    def test_git_add_and_commit(self, git_tool, workspace):
        """Test adding and committing files."""
        # Create a file
        test_file = workspace / "test.txt"
        test_file.write_text("test content\n")

        # Add file
        add_result = git_tool.add(["test.txt"])
        assert add_result.success

        # Commit
        commit_result = git_tool.commit("test: add test file")
        assert commit_result.success
        assert commit_result.operation == "commit"

    def test_git_branch_operations(self, git_tool):
        """Test branch operations."""
        # Create branch
        checkout_result = git_tool.checkout("test-branch", create=True)
        assert checkout_result.success
        assert checkout_result.operation == "checkout"

        # List branches - just verify command succeeds
        branch_result = git_tool.branch(list_all=False)
        assert branch_result.success
        assert branch_result.operation == "branch"

    def test_git_log(self, git_tool, workspace):
        """Test git log command."""
        # Create a commit first
        test_file = workspace / "initial.txt"
        test_file.write_text("initial commit\n")
        git_tool.add(["initial.txt"])
        git_tool.commit("Initial commit")

        # Get log
        log_result = git_tool.log(max_count=5, oneline=True)

        assert log_result.success
        assert "Initial commit" in log_result.stdout

    def test_git_diff(self, git_tool, workspace):
        """Test git diff command."""
        # Create and commit file
        test_file = workspace / "test.txt"
        test_file.write_text("original\n")
        git_tool.add(["test.txt"])
        git_tool.commit("Add test file")

        # Modify file
        test_file.write_text("modified\n")

        # Diff
        diff_result = git_tool.diff(cached=False)

        assert diff_result.success
        # Should show the change
        assert "modified" in diff_result.stdout or "-original" in diff_result.stdout

    def test_invalid_git_url(self, git_tool):
        """Test cloning with invalid URL."""
        # file:// protocol should be rejected
        with pytest.raises(ValueError, match="Only https://"):
            git_tool.clone("file:///tmp/repo")

    def test_audit_callback_called(self, workspace):
        """Test audit callback is invoked."""
        audit_log = []

        def audit_callback(entry):
            audit_log.append(entry)

        git = GitTool(workspace, audit_callback=audit_callback)

        # Perform operation
        git.status()

        # Verify audit was called
        assert len(audit_log) == 1
        assert audit_log[0]["tool"] == "git"
        assert audit_log[0]["operation"] == "status"
        assert "success" in audit_log[0]

