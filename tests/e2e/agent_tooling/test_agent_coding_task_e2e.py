"""
E2E test for agent using tools to complete a coding task.

Scenario:
1. Agent receives task: "Add a hello_world() function to utils.py"
2. Agent uses tools to:
   - Read current file
   - Add the function
   - Run tests to verify
   - Commit changes
3. Verify task completion and audit trail

This test runs in a workspace container with all tools available.
"""

import json
import tempfile
from pathlib import Path

import pytest
from core.agents_and_tools.tools import (
    FileTool,
    GitTool,
    TestTool,
    configure_audit_logger,
)


@pytest.mark.e2e
class TestAgentCodingTask:
    """Test agent completing a coding task using tools."""

    @pytest.fixture
    def workspace(self):
        """Create test workspace with a simple Python project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir) / "workspace"
            workspace_path.mkdir()

            # Initialize git repo
            import subprocess

            subprocess.run(
                ["git", "init"],
                cwd=workspace_path,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test Agent"],
                cwd=workspace_path,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "agent@test.com"],
                cwd=workspace_path,
                capture_output=True,
                check=True,
            )

            # Create simple Python project
            (workspace_path / "src").mkdir()

            # Create utils.py with existing functions
            utils_content = '''"""Utility functions."""


def add(a, b):
    """Add two numbers."""
    return a + b


def multiply(a, b):
    """Multiply two numbers."""
    return a * b
'''
            (workspace_path / "src" / "utils.py").write_text(utils_content)

            # Create test file
            test_content = '''"""Tests for utils."""

from src.utils import add, multiply


def test_add():
    """Test add function."""
    assert add(2, 3) == 5


def test_multiply():
    """Test multiply function."""
    assert multiply(2, 3) == 6
'''
            (workspace_path / "test_utils.py").write_text(test_content)

            # Create initial commit
            subprocess.run(
                ["git", "add", "."],
                cwd=workspace_path,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=workspace_path,
                capture_output=True,
                check=True,
            )

            yield workspace_path

    def test_agent_adds_function_to_file(self, workspace):
        """
        Test: Agent receives task to add hello_world() function and completes it.

        Task: "Add a hello_world() function to src/utils.py that returns 'Hello, World!'"

        Expected agent workflow:
        1. Read src/utils.py to understand current code
        2. Add hello_world() function
        3. Read test file to understand testing pattern
        4. Run existing tests to ensure no regressions
        5. Commit the changes
        """
        # Configure audit logging
        audit_log_file = workspace / ".task" / "audit.log"
        audit_log_file.parent.mkdir(exist_ok=True)
        audit_logger = configure_audit_logger(log_file=audit_log_file)

        # Initialize tools (as agent would)
        git = GitTool(workspace, audit_callback=audit_logger.log)
        files = FileTool(workspace, audit_callback=audit_logger.log)
        tests = TestTool(workspace, audit_callback=audit_logger.log)

        # === AGENT WORKFLOW STARTS ===

        # Step 1: Agent reads current file to understand context
        read_result = files.read_file("src/utils.py")
        assert read_result.success
        print(f"✓ Agent read utils.py ({read_result.metadata['lines']} lines)")

        current_code = read_result.content

        # Step 2: Agent adds hello_world() function
        new_function = '''

def hello_world():
    """Return a greeting."""
    return "Hello, World!"
'''

        # Append function to file
        append_result = files.append_file("src/utils.py", new_function)
        assert append_result.success
        print("✓ Agent added hello_world() function")

        # Step 3: Verify function was added
        verify_result = files.read_file("src/utils.py")
        assert verify_result.success
        assert "def hello_world():" in verify_result.content
        assert 'return "Hello, World!"' in verify_result.content
        print("✓ Agent verified function was added")

        # Step 4: Check git status
        status_result = git.status(short=True)
        assert status_result.success
        print(f"✓ Git status: {len(status_result.stdout.splitlines())} changes")

        # Step 5: Run existing tests (ensure no regressions)
        test_result = tests.pytest(path="test_utils.py", verbose=False)
        assert test_result.success
        print("✓ Existing tests still pass (no regressions)")

        # Step 6: Agent commits changes
        git_add_result = git.add(["src/utils.py"])
        assert git_add_result.success

        commit_result = git.commit(
            message="feat: add hello_world() function",
            author="AI Agent <agent@swe-ai-fleet.local>",
        )
        assert commit_result.success
        print("✓ Agent committed changes")

        # Step 7: Verify commit was created
        log_result = git.log(max_count=1, oneline=True)
        assert log_result.success
        assert "hello_world" in log_result.stdout or "feat:" in log_result.stdout
        print("✓ Commit verified in git log")

        # === AGENT WORKFLOW ENDS ===

        # Verify audit trail was created
        assert audit_log_file.exists()
        audit_entries = audit_log_file.read_text().splitlines()

        # Should have audit entries for each operation
        assert len(audit_entries) >= 6  # read, append, read, status, add, commit

        audit_data = [json.loads(line) for line in audit_entries]

        # Verify all operations were audited
        operations = [entry["operation"] for entry in audit_data]
        assert "read" in operations
        assert "append" in operations
        assert "status" in operations
        assert "add" in operations
        assert "commit" in operations

        print(f"✓ Audit trail created: {len(audit_entries)} operations logged")

        # Verify final state
        final_code = (workspace / "src" / "utils.py").read_text()
        assert "def hello_world():" in final_code
        assert "def add(a, b):" in final_code  # Original functions preserved
        assert "def multiply(a, b):" in final_code

        print("\n✅ E2E Test PASSED - Agent successfully completed coding task")

    def test_agent_finds_and_fixes_bug(self, workspace):
        """
        Test: Agent finds bug using search and fixes it.

        Task: "Find and fix the bug in multiply function (should use * not +)"

        Expected workflow:
        1. Search for potential issues
        2. Read file with bug
        3. Fix the bug
        4. Run tests
        5. Commit fix
        """
        # Configure audit
        audit_logger = configure_audit_logger()

        # Initialize tools
        git = GitTool(workspace, audit_callback=audit_logger.log)
        files = FileTool(workspace, audit_callback=audit_logger.log)
        tests = TestTool(workspace, audit_callback=audit_logger.log)

        # Step 1: Introduce a bug in multiply function
        files.edit_file(
            "src/utils.py",
            search="return a * b",
            replace="return a + b  # BUG: should be multiplication",
        )

        # Commit the bug
        git.add(["src/utils.py"])
        git.commit("bug: introduce bug in multiply")

        # === AGENT DEBUGGING WORKFLOW ===

        # Step 2: Run tests to detect failure
        initial_test = tests.pytest(path="test_utils.py")
        assert not initial_test.success  # Test should fail
        print("✓ Agent detected test failure")

        # Step 3: Search for the bug
        search_result = files.search_in_files("BUG", path="src/")
        assert search_result.success
        assert "BUG" in search_result.content  # Found the bug marker
        print("✓ Agent found bug marker")

        # Step 4: Read file to analyze
        code = files.read_file("src/utils.py")
        assert code.success
        print(f"✓ Agent analyzed {code.metadata['lines']} lines")

        # Step 5: Fix the bug
        fix_result = files.edit_file(
            "src/utils.py",
            search="return a + b  # BUG: should be multiplication",
            replace="return a * b",
        )
        assert fix_result.success
        assert fix_result.metadata["replacements"] == 1
        print("✓ Agent fixed bug (1 replacement)")

        # Step 6: Run tests to verify fix
        fixed_test = tests.pytest(path="test_utils.py")
        assert fixed_test.success  # Tests should pass now
        print("✓ Tests pass after fix")

        # Step 7: Commit the fix
        git.add(["src/utils.py"])
        commit_result = git.commit(
            message="fix: correct multiply function to use * instead of +",
            author="AI Agent <agent@swe-ai-fleet.local>",
        )
        assert commit_result.success

        # Step 8: View commit history
        log = git.log(max_count=3)
        assert log.success
        print(f"✓ Commit history: {len(log.stdout.splitlines())} lines")

        print("\n✅ E2E Test PASSED - Agent found and fixed bug using tools")


@pytest.mark.e2e
class TestAgentToolingSecurity:
    """Test security features of agent tools."""

    @pytest.fixture
    def workspace(self):
        """Create test workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir) / "workspace"
            workspace_path.mkdir()
            yield workspace_path

    def test_path_traversal_blocked(self, workspace):
        """Test that path traversal attacks are blocked."""
        files = FileTool(workspace)

        # Try to read outside workspace
        outside_dir = workspace.parent.parent / "secrets"
        outside_dir.mkdir(parents=True, exist_ok=True)
        (outside_dir / "secret.txt").write_text("SECRET DATA")

        # Attempt to read - should fail
        result = files.read_file(outside_dir / "secret.txt")

        assert not result.success
        assert "outside workspace" in result.error.lower()
        print("✓ Path traversal attack blocked")

    def test_command_injection_blocked(self, workspace):
        """Test that command injection is prevented."""
        from core.agents_and_tools.tools.validators import validate_command_args

        # Malicious command args
        with pytest.raises(ValueError, match="Dangerous pattern"):
            validate_command_args(["ls", "; rm -rf /"])

        print("✓ Command injection blocked")

    def test_dangerous_git_url_blocked(self, workspace):
        """Test that dangerous Git URLs are blocked."""
        git = GitTool(workspace)

        # file:// protocol
        with pytest.raises(ValueError, match="Only https://"):
            git.clone("file:///etc/shadow")

        print("✓ Dangerous Git URL blocked")

