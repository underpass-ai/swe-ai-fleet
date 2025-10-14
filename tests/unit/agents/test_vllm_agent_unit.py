"""Unit tests for VLLMAgent."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from swe_ai_fleet.agents import AgentResult, VLLMAgent


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create basic project structure
        (workspace / "src").mkdir()
        (workspace / "tests").mkdir()
        (workspace / "src" / "utils.py").write_text("# Utility functions\n")
        (workspace / "tests" / "test_utils.py").write_text("# Tests\n")

        # Initialize git repo
        import subprocess

        subprocess.run(
            ["git", "init"], cwd=workspace, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test Agent"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@agent.local"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "add", "."], cwd=workspace, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )

        yield workspace


@pytest.mark.asyncio
async def test_agent_initialization(temp_workspace):
    """Test agent initialization with tools enabled."""
    agent = VLLMAgent(
        agent_id="test-agent-001",
        role="DEV",
        workspace_path=temp_workspace,
    )

    assert agent.agent_id == "test-agent-001"
    assert agent.role == "DEV"
    assert agent.workspace_path == temp_workspace
    assert agent.enable_tools is True
    assert "git" in agent.tools
    assert "files" in agent.tools
    assert "tests" in agent.tools


@pytest.mark.asyncio
async def test_agent_initialization_without_tools(temp_workspace):
    """Test agent can be initialized without tools (text-only mode)."""
    agent = VLLMAgent(
        agent_id="test-agent-deliberate",
        role="DEV",
        workspace_path=temp_workspace,
        enable_tools=False,  # Text-only mode
    )

    assert agent.agent_id == "test-agent-deliberate"
    assert agent.role == "DEV"
    assert agent.enable_tools is False
    assert len(agent.tools) == 0


@pytest.mark.asyncio
async def test_agent_initialization_invalid_workspace():
    """Test agent fails with invalid workspace."""
    with pytest.raises(ValueError, match="Workspace path does not exist"):
        VLLMAgent(
            agent_id="test-agent-002",
            role="DEV",
            workspace_path="/nonexistent/path",
        )


@pytest.mark.asyncio
async def test_agent_role_normalization(temp_workspace):
    """Test that agent role is normalized to uppercase."""
    agent = VLLMAgent(
        agent_id="test-agent-norm",
        role="dev",  # lowercase
        workspace_path=temp_workspace,
    )

    assert agent.role == "DEV"  # Should be uppercase


@pytest.mark.asyncio
async def test_agent_simple_task_list_files(temp_workspace):
    """Test agent can execute simple task."""
    agent = VLLMAgent(
        agent_id="test-agent-003",
        role="DEV",
        workspace_path=temp_workspace,
    )

    result = await agent.execute_task(
        task="Show me the files in the workspace",
        context="Python project",
    )

    assert isinstance(result, AgentResult)
    assert result.success
    assert len(result.operations) > 0
    assert result.operations[0]["tool"] == "files"


@pytest.mark.asyncio
async def test_agent_add_function_task(temp_workspace):
    """Test agent can add function to file."""
    agent = VLLMAgent(
        agent_id="test-agent-004",
        role="DEV",
        workspace_path=temp_workspace,
    )

    result = await agent.execute_task(
        task="Add hello_world() function to src/utils.py",
        context="Python 3.13 project",
    )

    assert isinstance(result, AgentResult)
    assert result.success
    assert len(result.operations) >= 2  # read + append + ...

    # Check that function was added
    utils_content = (temp_workspace / "src" / "utils.py").read_text()
    assert "hello_world" in utils_content
    assert "def hello_world()" in utils_content

    # Check artifacts
    assert "files_modified" in result.artifacts
    assert "src/utils.py" in result.artifacts["files_modified"]


@pytest.mark.asyncio
async def test_agent_handles_error_gracefully(temp_workspace):
    """Test agent handles errors without crashing."""
    agent = VLLMAgent(
        agent_id="test-agent-005",
        role="DEV",
        workspace_path=temp_workspace,
    )

    # Try to read non-existent file
    result = await agent.execute_task(
        task="Read the contents of nonexistent.txt",
        context="",
        constraints={"abort_on_error": True},
    )

    # Should fail gracefully
    assert isinstance(result, AgentResult)
    # May succeed (lists files) or fail (reads file) depending on plan
    # Either way, should not raise exception


@pytest.mark.asyncio
async def test_agent_respects_max_operations(temp_workspace):
    """Test agent respects max_operations constraint."""
    agent = VLLMAgent(
        agent_id="test-agent-006",
        role="DEV",
        workspace_path=temp_workspace,
    )

    result = await agent.execute_task(
        task="Add function to utils.py",
        constraints={"max_operations": 2},  # Limit to 2 operations
    )

    assert isinstance(result, AgentResult)
    assert len(result.operations) <= 2


@pytest.mark.asyncio
async def test_agent_with_audit_callback(temp_workspace):
    """Test agent calls audit callback."""
    audit_events = []

    def audit_callback(event):
        audit_events.append(event)

    agent = VLLMAgent(
        agent_id="test-agent-007",
        role="DEV",
        workspace_path=temp_workspace,
        audit_callback=audit_callback,
    )

    result = await agent.execute_task(
        task="List files in workspace",
    )

    assert result.success
    # Audit events should have been recorded by tools
    # (Tools call audit_callback internally)
    assert len(audit_events) > 0


@pytest.mark.asyncio
async def test_agent_plan_generation():
    """Test plan generation for different task types."""
    # This tests the _generate_plan method indirectly
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        workspace.mkdir(exist_ok=True)

        agent = VLLMAgent(
            agent_id="test-agent-008",
            role="DEV",
            workspace_path=workspace,
        )

        # Test "add function" plan
        plan = await agent._generate_plan(
            task="Add hello() to main.py",
            context="",
            constraints={},
        )
        assert len(plan.steps) > 0
        assert any(step["tool"] == "files" for step in plan.steps)

        # Test "fix bug" plan
        plan = await agent._generate_plan(
            task="Fix bug in module.py",
            context="",
            constraints={},
        )
        assert len(plan.steps) > 0

        # Test "run tests" plan
        plan = await agent._generate_plan(
            task="Run all tests",
            context="",
            constraints={},
        )
        assert len(plan.steps) > 0
        assert any(step["tool"] == "tests" for step in plan.steps)

