"""Quick coverage for vllm_agent gaps (58% → 70%+)"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agents_and_tools.agents.vllm_agent import (
    AgentResult,
    AgentThought,
    ExecutionPlan,
    VLLMAgent,
)


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / "src").mkdir()
        (workspace / "tests").mkdir()
        yield workspace


def create_test_config(workspace_path, agent_id="agent-dev-001", role="DEV", vllm_url="http://vllm:8000", **kwargs):
    """Helper to create AgentInitializationConfig for tests."""
    from core.agents_and_tools.agents.infrastructure.dtos.agent_initialization_config import AgentInitializationConfig
    return AgentInitializationConfig(
        agent_id=agent_id,
        role=role.upper(),
        workspace_path=workspace_path,
        vllm_url=vllm_url,
        **kwargs
    )


class TestVLLMAgentInitialization:
    """Test VLLMAgent initialization."""

    def test_init_valid_workspace(self, temp_workspace):
        """Test initialization with valid workspace."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgent(config)

        assert agent.agent_id == "agent-dev-001"
        assert agent.role == "DEV"
        assert agent.workspace_path == temp_workspace
        assert agent.enable_tools is True

    def test_init_invalid_workspace(self):
        """Test initialization with non-existent workspace."""
        with pytest.raises(ValueError, match="Workspace path does not exist"):
            from pathlib import Path
            config = create_test_config(Path("/nonexistent/path"))
            VLLMAgent(config)

    def test_init_role_normalization(self, temp_workspace):
        """Test role normalization to uppercase."""
        config = create_test_config(temp_workspace, agent_id="agent-001", role="dev")
        agent = VLLMAgent(config)

        assert agent.role == "DEV"

    def test_init_read_only_mode(self, temp_workspace):
        """Test initialization in read-only mode."""
        config = create_test_config(temp_workspace, agent_id="agent-001", role="ARCHITECT", enable_tools=False)
        agent = VLLMAgent(config)

        assert agent.enable_tools is False

    def test_init_with_vllm_url_unavailable(self, temp_workspace):
        """Test initialization with vLLM URL when client unavailable."""
        config = create_test_config(temp_workspace, agent_id="agent-001", vllm_url="http://vllm:8000")
        agent = VLLMAgent(config)

        # Should initialize successfully, vllm_client may be None
        assert agent.vllm_url == "http://vllm:8000"

    def test_tools_always_initialized(self, temp_workspace):
        """Test that tools are always initialized."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgent(config)

        assert "files" in agent.tools
        assert "git" in agent.tools
        assert "tests" in agent.tools
        assert "http" in agent.tools
        assert "db" in agent.tools


class TestGetAvailableTools:
    """Test get_available_tools method."""

    def test_get_available_tools_full_mode(self, temp_workspace):
        """Test tool capabilities in full execution mode."""
        config = create_test_config(temp_workspace, agent_id="agent-001", enable_tools=True)
        agent = VLLMAgent(config)

        tools = agent.get_available_tools()

        assert tools["mode"] == "full"
        assert "files" in tools["tools"]
        assert "git" in tools["tools"]
        assert len(tools["capabilities"]) > 0
        # Should include write operations in full mode
        assert any("write" in op.lower() for op in tools["capabilities"])

    def test_get_available_tools_read_only_mode(self, temp_workspace):
        """Test tool capabilities in read-only mode."""
        config = create_test_config(temp_workspace, agent_id="agent-001", role="ARCHITECT", enable_tools=False)
        agent = VLLMAgent(config)

        tools = agent.get_available_tools()

        assert tools["mode"] == "read_only"
        assert len(tools["capabilities"]) > 0
        # Check that read operations are present
        assert any("read" in cap.lower() for cap in tools["capabilities"])


class TestIsReadOnlyOperation:
    """Test _is_read_only_operation method."""

    def test_read_operations_allowed(self, temp_workspace):
        """Test that read-only operations are identified correctly."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgent(config)

        assert agent._is_read_only_operation("files", "read_file") is True
        assert agent._is_read_only_operation("files", "search_in_files") is True
        assert agent._is_read_only_operation("git", "log") is True
        assert agent._is_read_only_operation("tests", "pytest") is True

    def test_write_operations_blocked(self, temp_workspace):
        """Test that write operations are identified correctly."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgent(config)

        assert agent._is_read_only_operation("files", "write_file") is False
        assert agent._is_read_only_operation("files", "delete_file") is False
        assert agent._is_read_only_operation("git", "commit") is False
        assert agent._is_read_only_operation("git", "push") is False


class TestPlanningMethods:
    """Test planning methods."""

    def test_plan_add_function(self, temp_workspace):
        """Test _plan_add_function."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgent(config)

        plan = agent._plan_add_function("Add hello_world() to utils.py")

        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) > 0
        assert any(step["tool"] == "files" for step in plan.steps)
        assert any(step["tool"] == "git" for step in plan.steps)

    def test_plan_fix_bug(self, temp_workspace):
        """Test _plan_fix_bug."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgent(config)

        plan = agent._plan_fix_bug()

        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) > 0
        assert any(step["tool"] == "files" for step in plan.steps)

    def test_plan_run_tests(self, temp_workspace):
        """Test _plan_run_tests."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgent(config)

        plan = agent._plan_run_tests()

        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) > 0
        assert plan.steps[0]["tool"] == "tests"


class TestLogThought:
    """Test _log_thought method."""

    def test_log_thought_basic(self, temp_workspace):
        """Test basic thought logging."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgent(config)

        log = []
        agent._log_thought(
            log,
            iteration=1,
            thought_type="analysis",
            content="Analyzing task",
        )

        assert len(log) == 1
        assert log[0]["iteration"] == 1
        assert log[0]["type"] == "analysis"
        assert log[0]["content"] == "Analyzing task"
        assert log[0]["agent_id"] == "agent-001"

    def test_log_thought_with_confidence(self, temp_workspace):
        """Test thought logging with confidence."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgent(config)

        log = []
        agent._log_thought(
            log,
            iteration=1,
            thought_type="decision",
            content="Decision made",
            confidence=0.95,
        )

        assert log[0]["confidence"] == 0.95


class TestSummarizeResult:
    """Test _summarize_result method."""

    def test_summarize_file_read(self, temp_workspace):
        """Test summarizing file read result."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgent(config)

        mock_result = MagicMock()
        mock_result.content = "line1\nline2\nline3"

        summary = agent._summarize_result(
            {"tool": "files", "operation": "read_file"},
            {"result": mock_result},
        )

        assert "lines" in summary

    def test_summarize_default(self, temp_workspace):
        """Test default summary."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgent(config)

        summary = agent._summarize_result(
            {"tool": "unknown", "operation": "unknown"},
            {"result": None},
        )

        assert summary == "Operation completed"


class TestAgentResult:
    """Test AgentResult dataclass."""

    def test_agent_result_success(self):
        """Test successful agent result."""
        result = AgentResult(
            success=True,
            operations=[{"tool": "git", "operation": "commit"}],
            artifacts={"commit_sha": "abc123"},
        )

        assert result.success is True
        assert len(result.operations) == 1
        assert result.error is None

    def test_agent_result_failure(self):
        """Test failed agent result."""
        result = AgentResult(
            success=False,
            operations=[],
            error="Something went wrong",
        )

        assert result.success is False
        assert result.error == "Something went wrong"


class TestAgentThought:
    """Test AgentThought dataclass."""

    def test_agent_thought_creation(self):
        """Test creating agent thought."""
        thought = AgentThought(
            iteration=1,
            thought_type="analysis",
            content="Analyzing task",
            confidence=0.9,
        )

        assert thought.iteration == 1
        assert thought.thought_type == "analysis"
        assert thought.confidence == 0.9


class TestExecutionPlan:
    """Test ExecutionPlan dataclass."""

    def test_execution_plan_creation(self):
        """Test creating execution plan."""
        plan = ExecutionPlan(
            steps=[
                {"tool": "files", "operation": "read_file"},
            ],
            reasoning="Reading file for analysis",
        )

        assert len(plan.steps) == 1
        assert plan.reasoning == "Reading file for analysis"
