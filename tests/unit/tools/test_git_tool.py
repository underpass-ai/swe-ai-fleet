"""Unit tests for git_tool.py coverage - Git operations."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import subprocess

from core.agents_and_tools.tools.git_tool import GitTool, GitResult


# =============================================================================
# Initialization Tests
# =============================================================================

class TestGitToolInitialization:
    """Test GitTool initialization."""

    def test_creates_with_valid_workspace(self, tmp_path):
        """Should create GitTool with valid workspace path."""
        tool = GitTool.create(tmp_path)
        
        assert tool.workspace_path == tmp_path.resolve()

    def test_rejects_nonexistent_workspace(self, tmp_path):
        """Should reject non-existent workspace path."""
        nonexistent = tmp_path / "does_not_exist"
        
        with pytest.raises(ValueError, match="Workspace path does not exist"):
            GitTool.create(nonexistent)

    def test_accepts_audit_callback(self, tmp_path):
        """Should accept and store audit callback."""
        callback = Mock()
        tool = GitTool.create(tmp_path, audit_callback=callback)
        
        assert tool.audit_callback == callback


# =============================================================================
# Clone Tests
# =============================================================================

class TestGitToolClone:
    """Test clone operation."""

    @patch('subprocess.run')
    def test_clones_https_repo(self, mock_run, tmp_path):
        """Should clone HTTPS repository."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Cloning into '.'...\n",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        result = tool.clone("https://github.com/user/repo.git")
        
        assert result.success is True
        assert result.operation == "clone"
        
        # Verify git clone command
        call_args = mock_run.call_args[0][0]
        assert call_args[:2] == ["git", "clone"]
        assert "https://github.com/user/repo.git" in call_args

    @patch('subprocess.run')
    def test_clones_with_branch(self, mock_run, tmp_path):
        """Should clone specific branch."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        tool.clone("https://github.com/user/repo.git", branch="develop")
        
        call_args = mock_run.call_args[0][0]
        assert "--branch" in call_args
        assert "develop" in call_args

    @patch('subprocess.run')
    def test_clones_with_depth(self, mock_run, tmp_path):
        """Should clone with depth limit."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        tool.clone("https://github.com/user/repo.git", depth=1)
        
        call_args = mock_run.call_args[0][0]
        assert "--depth" in call_args
        assert "1" in call_args

    def test_rejects_invalid_url_scheme(self, tmp_path):
        """Should reject non-https/git URLs."""
        tool = GitTool.create(tmp_path)
        
        with pytest.raises(ValueError, match="Only https:// and git@ URLs are allowed"):
            tool.clone("ftp://malicious.com/repo.git")


# =============================================================================
# Status Tests
# =============================================================================

class TestGitToolStatus:
    """Test status operation."""

    @patch('subprocess.run')
    def test_gets_status(self, mock_run, tmp_path):
        """Should get git status."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="On branch main\nnothing to commit\n",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        result = tool.status()
        
        assert result.success is True
        assert result.operation == "status"
        assert "nothing to commit" in result.stdout

    @patch('subprocess.run')
    def test_gets_short_status(self, mock_run, tmp_path):
        """Should get short status format."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=" M file.txt\n",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        tool.status(short=True)
        
        call_args = mock_run.call_args[0][0]
        assert "--short" in call_args


# =============================================================================
# Add Tests
# =============================================================================

class TestGitToolAdd:
    """Test add operation."""

    @patch('subprocess.run')
    def test_adds_all_files(self, mock_run, tmp_path):
        """Should add all files."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        result = tool.add("all")
        
        assert result.success is True
        call_args = mock_run.call_args[0][0]
        assert "--all" in call_args

    @patch('subprocess.run')
    def test_adds_specific_files(self, mock_run, tmp_path):
        """Should add specific files."""
        # Create test files
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        tool.add(["file1.txt", "file2.txt"])
        
        call_args = mock_run.call_args[0][0]
        assert "file1.txt" in call_args
        assert "file2.txt" in call_args

    def test_rejects_path_outside_workspace(self, tmp_path):
        """Should reject paths outside workspace."""
        tool = GitTool.create(tmp_path)
        
        with pytest.raises(ValueError, match="Path outside workspace"):
            tool.add(["../../../etc/passwd"])


# =============================================================================
# Commit Tests
# =============================================================================

class TestGitToolCommit:
    """Test commit operation."""

    @patch('subprocess.run')
    def test_commits_with_message(self, mock_run, tmp_path):
        """Should commit with message."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="[main abc123] Test commit\n",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        result = tool.commit("Test commit")
        
        assert result.success is True
        call_args = mock_run.call_args[0][0]
        assert "-m" in call_args
        assert "Test commit" in call_args

    @patch('subprocess.run')
    def test_commits_with_author(self, mock_run, tmp_path):
        """Should commit with custom author."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        tool.commit("Test commit", author="Alice <alice@example.com>")
        
        call_args = mock_run.call_args[0][0]
        assert "--author" in call_args
        assert "Alice <alice@example.com>" in call_args

    def test_rejects_empty_message(self, tmp_path):
        """Should reject empty commit message."""
        tool = GitTool.create(tmp_path)
        
        with pytest.raises(ValueError, match="Commit message cannot be empty"):
            tool.commit("")


# =============================================================================
# Push/Pull Tests
# =============================================================================

class TestGitToolPushPull:
    """Test push and pull operations."""

    @patch('subprocess.run')
    def test_pushes_to_origin(self, mock_run, tmp_path):
        """Should push to origin."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        result = tool.push()
        
        assert result.success is True
        call_args = mock_run.call_args[0][0]
        assert "push" in call_args
        assert "origin" in call_args

    @patch('subprocess.run')
    def test_pushes_with_force(self, mock_run, tmp_path):
        """Should force push with lease."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        tool.push(force=True)
        
        call_args = mock_run.call_args[0][0]
        assert "--force-with-lease" in call_args

    @patch('subprocess.run')
    def test_pulls_from_origin(self, mock_run, tmp_path):
        """Should pull from origin."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Already up to date.\n",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        result = tool.pull()
        
        assert result.success is True
        call_args = mock_run.call_args[0][0]
        assert "pull" in call_args
        assert "origin" in call_args


# =============================================================================
# Checkout/Branch Tests
# =============================================================================

class TestGitToolCheckoutBranch:
    """Test checkout and branch operations."""

    @patch('subprocess.run')
    def test_checkouts_existing_branch(self, mock_run, tmp_path):
        """Should checkout existing branch."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Switched to branch 'develop'\n",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        result = tool.checkout("develop")
        
        assert result.success is True
        call_args = mock_run.call_args[0][0]
        assert "checkout" in call_args
        assert "develop" in call_args

    @patch('subprocess.run')
    def test_creates_new_branch(self, mock_run, tmp_path):
        """Should create and checkout new branch."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        tool.checkout("feature", create=True)
        
        call_args = mock_run.call_args[0][0]
        assert "-b" in call_args
        assert "feature" in call_args

    @patch('subprocess.run')
    def test_lists_branches(self, mock_run, tmp_path):
        """Should list branches."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="* main\n  develop\n",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        result = tool.branch()
        
        assert result.success is True

    @patch('subprocess.run')
    def test_lists_all_branches(self, mock_run, tmp_path):
        """Should list all branches including remote."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        tool.branch(list_all=True)
        
        call_args = mock_run.call_args[0][0]
        assert "--all" in call_args

    @patch('subprocess.run')
    def test_deletes_branch(self, mock_run, tmp_path):
        """Should delete branch."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Deleted branch feature\n",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        tool.branch(delete="feature")
        
        call_args = mock_run.call_args[0][0]
        assert "-d" in call_args
        assert "feature" in call_args


# =============================================================================
# Diff/Log Tests
# =============================================================================

class TestGitToolDiffLog:
    """Test diff and log operations."""

    @patch('subprocess.run')
    def test_shows_diff(self, mock_run, tmp_path):
        """Should show diff."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="diff --git a/file.txt b/file.txt\n",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        result = tool.diff()
        
        assert result.success is True
        assert "diff --git" in result.stdout

    @patch('subprocess.run')
    def test_shows_cached_diff(self, mock_run, tmp_path):
        """Should show staged diff."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        tool.diff(cached=True)
        
        call_args = mock_run.call_args[0][0]
        assert "--cached" in call_args

    @patch('subprocess.run')
    def test_shows_diff_for_files(self, mock_run, tmp_path):
        """Should show diff for specific files."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        tool.diff(files=["file1.txt", "file2.txt"])
        
        call_args = mock_run.call_args[0][0]
        assert "--" in call_args
        assert "file1.txt" in call_args

    @patch('subprocess.run')
    def test_shows_log(self, mock_run, tmp_path):
        """Should show commit log."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="commit abc123\nAuthor: Test\n",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        result = tool.log()
        
        assert result.success is True
        call_args = mock_run.call_args[0][0]
        assert "--max-count=10" in call_args

    @patch('subprocess.run')
    def test_shows_oneline_log(self, mock_run, tmp_path):
        """Should show compact log format."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        tool.log(oneline=True)
        
        call_args = mock_run.call_args[0][0]
        assert "--oneline" in call_args


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestGitToolErrorHandling:
    """Test error handling."""

    @patch('subprocess.run')
    def test_handles_git_command_failure(self, mock_run, tmp_path):
        """Should handle git command failures."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="fatal: not a git repository\n"
        )
        
        tool = GitTool.create(tmp_path)
        result = tool.status()
        
        assert result.success is False
        assert result.exit_code == 1
        assert "not a git repository" in result.stderr

    @patch('subprocess.run')
    def test_handles_timeout(self, mock_run, tmp_path):
        """Should handle command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 300)
        
        tool = GitTool.create(tmp_path)
        result = tool.status()
        
        assert result.success is False
        assert "timed out after 300 seconds" in result.stderr

    @patch('subprocess.run')
    def test_handles_general_exception(self, mock_run, tmp_path):
        """Should handle general exceptions."""
        mock_run.side_effect = Exception("Unexpected error")
        
        tool = GitTool.create(tmp_path)
        result = tool.status()
        
        assert result.success is False
        assert "Error executing git command" in result.stderr

    def test_rejects_cwd_outside_workspace(self, tmp_path):
        """Should reject working directory outside workspace."""
        tool = GitTool.create(tmp_path)
        
        with pytest.raises(ValueError, match="Working directory outside workspace"):
            tool._run_git_command(["status"], "status", cwd="/tmp")


# =============================================================================
# Audit Callback Tests
# =============================================================================

class TestGitToolAuditCallback:
    """Test audit callback functionality."""

    @patch('subprocess.run')
    def test_calls_audit_callback(self, mock_run, tmp_path):
        """Should call audit callback with operation details."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        audit_callback = Mock()
        tool = GitTool.create(tmp_path, audit_callback=audit_callback)
        
        tool.status()
        
        audit_callback.assert_called_once()
        call_args = audit_callback.call_args[0][0]
        
        assert call_args["tool"] == "git"
        assert call_args["operation"] == "status"
        assert call_args["success"] is True


# =============================================================================
# Execute Method Tests
# =============================================================================

class TestGitToolExecute:
    """Test execute() method."""

    @patch('subprocess.run')
    def test_executes_status_by_name(self, mock_run, tmp_path):
        """Should execute status via execute() method."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        tool = GitTool.create(tmp_path)
        result = tool.execute(operation="status")
        
        assert result.success is True
        assert result.operation == "status"

    def test_execute_raises_on_invalid_operation(self, tmp_path):
        """Should raise ValueError for unsupported operation."""
        tool = GitTool.create(tmp_path)
        
        with pytest.raises(ValueError, match="Unknown git operation"):
            tool.execute(operation="invalid_op")


# =============================================================================
# Summarize and Collect Artifacts Tests
# =============================================================================

class TestGitToolSummarizeAndCollect:
    """Test summarize_result and collect_artifacts methods."""

    def test_summarize_result_for_status(self, tmp_path):
        """Should summarize status result."""
        tool = GitTool.create(tmp_path)
        
        mock_result = Mock()
        mock_result.content = " M file1.txt\n M file2.txt\n"
        
        summary = tool.summarize_result("status", mock_result, {})
        
        assert "files changed" in summary

    def test_summarize_result_for_commit(self, tmp_path):
        """Should summarize commit result."""
        tool = GitTool.create(tmp_path)
        
        mock_result = Mock()
        mock_result.content = "[main abc123] Test commit\n"
        
        summary = tool.summarize_result("commit", mock_result, {})
        
        assert "Created commit" in summary

    def test_summarize_result_for_log(self, tmp_path):
        """Should summarize log result."""
        tool = GitTool.create(tmp_path)
        
        mock_result = Mock()
        mock_result.content = "commit abc123\ncommit def456\n"
        
        summary = tool.summarize_result("log", mock_result, {})
        
        assert "commits in history" in summary

    def test_collect_artifacts_for_commit(self, tmp_path):
        """Should collect commit SHA."""
        tool = GitTool.create(tmp_path)
        
        mock_result = Mock()
        mock_result.content = "commit abc1234567890"
        
        artifacts = tool.collect_artifacts("commit", mock_result, {})
        
        assert isinstance(artifacts, dict)
        assert "commit_sha" in artifacts

    def test_collect_artifacts_for_status(self, tmp_path):
        """Should collect changed files."""
        tool = GitTool.create(tmp_path)
        
        mock_result = Mock()
        mock_result.content = " M file1.txt\n A file2.py\n"
        
        artifacts = tool.collect_artifacts("status", mock_result, {})
        
        assert isinstance(artifacts, dict)
        assert "files_changed" in artifacts

    def test_collect_artifacts_without_content(self, tmp_path):
        """Should handle result without content."""
        tool = GitTool.create(tmp_path)
        
        mock_result = Mock()
        mock_result.content = None
        
        artifacts = tool.collect_artifacts("status", mock_result, {})
        
        assert isinstance(artifacts, dict)
        assert artifacts == {}

