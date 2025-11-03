"""Unit tests for VLLMAgent."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from core.agents_and_tools.agents import AgentResult, VLLMAgent
from core.agents_and_tools.agents.domain.entities import ExecutionConstraints
from core.agents_and_tools.agents.domain.entities.rbac import RoleFactory
from core.agents_and_tools.agents.infrastructure.dtos.agent_initialization_config import (
    AgentInitializationConfig,
)
from core.agents_and_tools.agents.infrastructure.factories.vllm_agent_factory import VLLMAgentFactory


def create_test_config(
    workspace_path, agent_id="test-agent-001", role="DEV", vllm_url="http://vllm:8000", **kwargs
):
    """Helper to create AgentInitializationConfig for tests."""
    # Convert string role to Role object using RoleFactory
    role_obj = RoleFactory.create_role_by_name(role.lower())

    return AgentInitializationConfig(
        agent_id=agent_id,
        role=role_obj,  # Now uses Role value object
        workspace_path=workspace_path,
        vllm_url=vllm_url,
        **kwargs
    )


def mock_plan_use_case(agent, steps):
    """Helper to mock the plan use case in an agent."""
    from core.agents_and_tools.agents.application.dtos.plan_dto import PlanDTO

    mock_usecase = AsyncMock()
    mock_usecase.execute.return_value = PlanDTO(
        steps=steps,
        reasoning="Mocked plan for testing"
    )
    # Mock in both places for backward compatibility
    agent.generate_plan_usecase = mock_usecase
    # NEW: Mock in the use case where it's actually called
    agent.execute_task_usecase.generate_plan_usecase = mock_usecase


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

    # Use factory to create agent with all dependencies
    agent = VLLMAgentFactory.create(config)

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
    agent = VLLMAgentFactory.create(config)

    assert agent.agent_id == "test-agent-planning"
    assert agent.role == "DEV"
    assert agent.enable_tools is False
    # Tools are initialized but operations are restricted
    assert len(agent.tools) == 6, "Tools should be initialized"
    assert "files" in agent.tools
    assert "git" in agent.tools

    # Verify mode is read-only
    tools_info = agent.get_available_tools()
    assert tools_info.mode == "read_only"


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
    agent = VLLMAgentFactory.create(config)

    assert agent.role == "DEV"  # Should be uppercase


@pytest.mark.asyncio
async def test_agent_simple_task_list_files(temp_workspace):
    """Test agent can execute simple task."""
    from core.agents_and_tools.agents.domain.entities import ExecutionStep

    config = create_test_config(temp_workspace, agent_id="test-agent-003")
    agent = VLLMAgentFactory.create(config)

    # Mock the plan to list files
    mock_plan_use_case(agent, [
        ExecutionStep(tool="files", operation="list_files", params={"path": ".", "recursive": False}),
    ])

    result = await agent.execute_task(
        task="Show me the files in the workspace",
        constraints=ExecutionConstraints(),
        context="Python project",
    )

    assert isinstance(result, AgentResult)
    assert result.success
    assert result.operations.count() > 0
    assert result.operations.get_all()[0].tool_name == "files"


@pytest.mark.asyncio
async def test_agent_add_function_task(temp_workspace):
    """Test agent can add function to file."""
    from core.agents_and_tools.agents.domain.entities import ExecutionStep

    config = create_test_config(temp_workspace, agent_id="test-agent-004")
    agent = VLLMAgentFactory.create(config)

    # Mock the plan to read, append, and test
    mock_plan_use_case(agent, [
        ExecutionStep(tool="files", operation="read_file", params={"path": "src/utils.py"}),
        ExecutionStep(tool="files", operation="append_file", params={"path": "src/utils.py", "content": "\ndef hello_world():\n    return 'Hello, World!'"}),
        ExecutionStep(tool="tests", operation="pytest", params={"path": "tests"}),
    ])

    result = await agent.execute_task(
        task="Add hello_world() function to src/utils.py",
        constraints=ExecutionConstraints(abort_on_error=False),  # Continue even if pytest fails
        context="Python 3.13 project",
    )

    assert isinstance(result, AgentResult)
    # Overall success depends on all steps, but we care about file modification
    assert result.operations.count() >= 2  # read + append + ...

    # Check that function was added (main goal)
    utils_content = (temp_workspace / "src" / "utils.py").read_text()
    assert "hello_world" in utils_content
    assert "def hello_world()" in utils_content

    # Check artifacts (from git.status or files operations)
    # May be files_modified or files_changed depending on operation
    artifacts_dict = result.artifacts.get_all()
    has_file_artifact = (
        "files_modified" in artifacts_dict or "files_changed" in artifacts_dict
    )
    assert has_file_artifact, f"Missing file artifact. Got: {list(artifacts_dict.keys())}"

    # Verify file operations succeeded
    file_ops = result.operations.get_by_tool("files")
    assert all(op.success for op in file_ops), "File operations should succeed"


@pytest.mark.asyncio
async def test_agent_handles_error_gracefully(temp_workspace):
    """Test agent handles errors without crashing."""
    config = create_test_config(temp_workspace, agent_id="test-agent-005")
    agent = VLLMAgentFactory.create(config)

    # Try to read non-existent file
    result = await agent.execute_task(
        task="Read the contents of nonexistent.txt",
        constraints=ExecutionConstraints(abort_on_error=True),
        context="",
    )

    # Should fail gracefully
    assert isinstance(result, AgentResult)
    # May succeed (lists files) or fail (reads file) depending on plan
    # Either way, should not raise exception


@pytest.mark.asyncio
async def test_agent_respects_max_operations(temp_workspace):
    """Test agent respects max_operations constraint."""
    config = create_test_config(temp_workspace, agent_id="test-agent-006")
    agent = VLLMAgentFactory.create(config)

    result = await agent.execute_task(
        task="Add function to utils.py",
        constraints=ExecutionConstraints(max_operations=2),  # Limit to 2 operations
    )

    assert isinstance(result, AgentResult)
    assert result.operations.count() <= 2


@pytest.mark.asyncio
async def test_agent_with_audit_callback(temp_workspace):
    """Test agent calls audit callback."""
    from core.agents_and_tools.agents.domain.entities import ExecutionStep

    audit_events = []

    def audit_callback(event):
        audit_events.append(event)

    config = create_test_config(temp_workspace, agent_id="test-agent-007", audit_callback=audit_callback)
    agent = VLLMAgentFactory.create(config)

    # Mock the plan to list files
    mock_plan_use_case(agent, [
        ExecutionStep(tool="files", operation="list_files", params={"path": ".", "recursive": False}),
    ])

    result = await agent.execute_task(
        task="List files in workspace",
        constraints=ExecutionConstraints(),
        context="",
    )

    assert result.success
    # Audit events should have been recorded by tools
    # (Tools call audit_callback internally)
    assert len(audit_events) > 0


@pytest.mark.asyncio
async def test_agent_plan_generation():
    """Test plan generation for different task types."""
    from unittest.mock import AsyncMock

    from core.agents_and_tools.agents.application.dtos.plan_dto import PlanDTO
    from core.agents_and_tools.agents.domain.entities import ExecutionStep

    # This tests the _generate_plan method indirectly
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        workspace.mkdir(exist_ok=True)

        config = create_test_config(workspace, agent_id="test-agent-008")
        agent = VLLMAgentFactory.create(config)

        # Mock the generate_plan_usecase
        mock_usecase = AsyncMock()
        agent.generate_plan_usecase = mock_usecase

        # Test "add function" plan
        mock_usecase.execute.return_value = PlanDTO(
            steps=[
                ExecutionStep(tool="files", operation="read_file", params={"path": "main.py"}),
                ExecutionStep(tool="files", operation="append_file", params={"path": "main.py", "content": "\ndef hello(): pass\n"}),
            ],
            reasoning="Add hello function"
        )

        plan = await agent._generate_plan(
            task="Add hello() to main.py",
            context="",
            constraints={},
        )
        assert len(plan.steps) > 0
        assert any(step.tool == "files" for step in plan.steps)

        # Test "fix bug" plan
        mock_usecase.execute.return_value = PlanDTO(
            steps=[
                ExecutionStep(tool="files", operation="search_in_files", params={"pattern": "BUG", "path": "src/"}),
                ExecutionStep(tool="tests", operation="pytest", params={"path": "tests"}),
            ],
            reasoning="Find and test bugs"
        )

        plan = await agent._generate_plan(
            task="Fix bug in module.py",
            context="",
            constraints={},
        )
        assert len(plan.steps) > 0

        # Test "run tests" plan
        mock_usecase.execute.return_value = PlanDTO(
            steps=[
                ExecutionStep(tool="tests", operation="pytest", params={"path": "tests", "verbose": True}),
            ],
            reasoning="Run tests"
        )

        plan = await agent._generate_plan(
            task="Run all tests",
            context="",
            constraints={},
        )
        assert len(plan.steps) > 0
        assert any(step.tool == "tests" for step in plan.steps)

