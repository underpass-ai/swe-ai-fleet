"""Unit tests for VLLMAgent."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from core.agents_and_tools.agents import AgentResult, VLLMAgent
from core.agents_and_tools.agents.infrastructure.dtos.agent_initialization_config import AgentInitializationConfig


def create_test_config(workspace_path, agent_id="test-agent-001", role="DEV", vllm_url="http://vllm:8000", **kwargs):
    """Helper to create AgentInitializationConfig for tests."""
    return AgentInitializationConfig(
        agent_id=agent_id,
        role=role.upper(),
        workspace_path=workspace_path,
        vllm_url=vllm_url,
        **kwargs
    )


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
    config = create_test_config(temp_workspace, agent_id="test-agent-001")
    agent = VLLMAgent(config)

    assert agent.agent_id == "test-agent-001"
    assert agent.role == "DEV"
    assert agent.workspace_path == temp_workspace
    assert agent.enable_tools is True
    assert "git" in agent.tools
    assert "files" in agent.tools
    assert "tests" in agent.tools


@pytest.mark.asyncio
async def test_agent_initialization_without_tools(temp_workspace):
    """Test agent in read-only mode (enable_tools=False)."""
    config = create_test_config(temp_workspace, agent_id="test-agent-planning", enable_tools=False)
    agent = VLLMAgent(config)

    assert agent.agent_id == "test-agent-planning"
    assert agent.role == "DEV"
    assert agent.enable_tools is False
    # Tools are initialized but operations are restricted
    assert len(agent.tools) == 6, "Tools should be initialized"
    assert "files" in agent.tools
    assert "git" in agent.tools

    # Verify mode is read-only
    tools_info = agent.get_available_tools()
    assert tools_info["mode"] == "read_only"


@pytest.mark.asyncio
async def test_agent_initialization_invalid_workspace():
    """Test agent fails with invalid workspace."""
    with pytest.raises(ValueError, match="Workspace path does not exist"):
        config = create_test_config(Path("/nonexistent/path"))
        VLLMAgent(config)


@pytest.mark.asyncio
async def test_agent_role_normalization(temp_workspace):
    """Test that agent role is normalized to uppercase."""
    config = create_test_config(temp_workspace, agent_id="test-agent-norm", role="dev")
    agent = VLLMAgent(config)

    assert agent.role == "DEV"  # Should be uppercase


@pytest.mark.asyncio
async def test_agent_simple_task_list_files(temp_workspace):
    """Test agent can execute simple task."""
    config = create_test_config(temp_workspace, agent_id="test-agent-003")
    agent = VLLMAgent(config)

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
    config = create_test_config(temp_workspace, agent_id="test-agent-004")
    agent = VLLMAgent(config)

    result = await agent.execute_task(
        task="Add hello_world() function to src/utils.py",
        context="Python 3.13 project",
        constraints={
            "abort_on_error": False,  # Continue even if pytest fails (no real tests)
        },
    )

    assert isinstance(result, AgentResult)
    # Overall success depends on all steps, but we care about file modification
    assert len(result.operations) >= 2  # read + append + ...

    # Check that function was added (main goal)
    utils_content = (temp_workspace / "src" / "utils.py").read_text()
    assert "hello_world" in utils_content
    assert "def hello_world()" in utils_content

    # Check artifacts (from git.status or files operations)
    # May be files_modified or files_changed depending on operation
    has_file_artifact = (
        "files_modified" in result.artifacts or "files_changed" in result.artifacts
    )
    assert has_file_artifact, f"Missing file artifact. Got: {result.artifacts.keys()}"

    # Verify file operations succeeded
    file_ops = [op for op in result.operations if op["tool"] == "files"]
    assert all(op["success"] for op in file_ops), "File operations should succeed"


@pytest.mark.asyncio
async def test_agent_handles_error_gracefully(temp_workspace):
    """Test agent handles errors without crashing."""
    config = create_test_config(temp_workspace, agent_id="test-agent-005")
    agent = VLLMAgent(config)

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
    config = create_test_config(temp_workspace, agent_id="test-agent-006")
    agent = VLLMAgent(config)

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

    config = create_test_config(temp_workspace, agent_id="test-agent-007", audit_callback=audit_callback)
    agent = VLLMAgent(config)

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

        config = create_test_config(workspace, agent_id="test-agent-008")
        agent = VLLMAgent(config)

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

