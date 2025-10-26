"""Quick coverage for vllm_agent gaps (58% → 70%+)"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agents.vllm_agent import (
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


class TestVLLMAgentInitialization:
    """Test VLLMAgent initialization."""

    def test_init_valid_workspace(self, temp_workspace):
        """Test initialization with valid workspace."""
        agent = VLLMAgent(
            agent_id="agent-dev-001",
            role="DEV",
            workspace_path=temp_workspace,
        )
        
        assert agent.agent_id == "agent-dev-001"
        assert agent.role == "DEV"
        assert agent.workspace_path == temp_workspace
        assert agent.enable_tools is True

    def test_init_invalid_workspace(self):
        """Test initialization with non-existent workspace."""
        with pytest.raises(ValueError, match="Workspace path does not exist"):
            VLLMAgent(
                agent_id="agent-dev-001",
                role="DEV",
                workspace_path="/nonexistent/path",
            )

    def test_init_role_normalization(self, temp_workspace):
        """Test role normalization to uppercase."""
        agent = VLLMAgent(
            agent_id="agent-001",
            role="dev",
            workspace_path=temp_workspace,
        )
        
        assert agent.role == "DEV"

    def test_init_read_only_mode(self, temp_workspace):
        """Test initialization in read-only mode."""
        agent = VLLMAgent(
            agent_id="agent-001",
            role="ARCHITECT",
            workspace_path=temp_workspace,
            enable_tools=False,
        )
        
        assert agent.enable_tools is False

    def test_init_with_vllm_url_unavailable(self, temp_workspace):
        """Test initialization with vLLM URL when client unavailable."""
        agent = VLLMAgent(
            agent_id="agent-001",
            role="DEV",
            workspace_path=temp_workspace,
            vllm_url="http://vllm:8000",
        )
        
        # Should initialize successfully, vllm_client may be None
        assert agent.vllm_url == "http://vllm:8000"

    def test_tools_always_initialized(self, temp_workspace):
        """Test that tools are always initialized."""
        agent = VLLMAgent(
            agent_id="agent-001",
            role="DEV",
            workspace_path=temp_workspace,
        )
        
        assert "files" in agent.tools
        assert "git" in agent.tools
        assert "tests" in agent.tools
        assert "http" in agent.tools
        assert "db" in agent.tools


class TestGetAvailableTools:
    """Test get_available_tools method."""

    def test_get_available_tools_full_mode(self, temp_workspace):
        """Test tool capabilities in full execution mode."""
        agent = VLLMAgent(
            agent_id="agent-001",
            role="DEV",
            workspace_path=temp_workspace,
            enable_tools=True,
        )
        
        tools = agent.get_available_tools()
        
        assert tools["mode"] == "full"
        assert "files" in tools["tools"]
        assert "git" in tools["tools"]
        assert len(tools["capabilities"]) > 0
        # Should include write operations in full mode
        assert any("write" in op.lower() for op in tools["capabilities"])

    def test_get_available_tools_read_only_mode(self, temp_workspace):
        """Test tool capabilities in read-only mode."""
        agent = VLLMAgent(
            agent_id="agent-001",
            role="ARCHITECT",
            workspace_path=temp_workspace,
            enable_tools=False,
        )
        
        tools = agent.get_available_tools()
        
        assert tools["mode"] == "read_only"
        assert len(tools["capabilities"]) > 0
        # Check that read operations are present
        assert any("read" in cap.lower() for cap in tools["capabilities"])


class TestIsReadOnlyOperation:
    """Test _is_read_only_operation method."""

    def test_read_operations_allowed(self, temp_workspace):
        """Test that read-only operations are identified correctly."""
        agent = VLLMAgent(
            agent_id="agent-001",
            role="DEV",
            workspace_path=temp_workspace,
        )
        
        assert agent._is_read_only_operation("files", "read_file") is True
        assert agent._is_read_only_operation("files", "search_in_files") is True
        assert agent._is_read_only_operation("git", "log") is True
        assert agent._is_read_only_operation("tests", "pytest") is True

    def test_write_operations_blocked(self, temp_workspace):
        """Test that write operations are identified correctly."""
        agent = VLLMAgent(
            agent_id="agent-001",
            role="DEV",
            workspace_path=temp_workspace,
        )
        
        assert agent._is_read_only_operation("files", "write_file") is False
        assert agent._is_read_only_operation("files", "delete_file") is False
        assert agent._is_read_only_operation("git", "commit") is False
        assert agent._is_read_only_operation("git", "push") is False


class TestPlanningMethods:
    """Test planning methods."""

    def test_plan_add_function(self, temp_workspace):
        """Test _plan_add_function."""
        agent = VLLMAgent(
            agent_id="agent-001",
            role="DEV",
            workspace_path=temp_workspace,
        )
        
        plan = agent._plan_add_function("Add hello_world() to utils.py")
        
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) > 0
        assert any(step["tool"] == "files" for step in plan.steps)
        assert any(step["tool"] == "git" for step in plan.steps)

    def test_plan_fix_bug(self, temp_workspace):
        """Test _plan_fix_bug."""
        agent = VLLMAgent(
            agent_id="agent-001",
            role="DEV",
            workspace_path=temp_workspace,
        )
        
        plan = agent._plan_fix_bug()
        
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) > 0
        assert any(step["tool"] == "files" for step in plan.steps)

    def test_plan_run_tests(self, temp_workspace):
        """Test _plan_run_tests."""
        agent = VLLMAgent(
            agent_id="agent-001",
            role="DEV",
            workspace_path=temp_workspace,
        )
        
        plan = agent._plan_run_tests()
        
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) > 0
        assert plan.steps[0]["tool"] == "tests"


class TestLogThought:
    """Test _log_thought method."""

    def test_log_thought_basic(self, temp_workspace):
        """Test basic thought logging."""
        agent = VLLMAgent(
            agent_id="agent-001",
            role="DEV",
            workspace_path=temp_workspace,
        )
        
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
        agent = VLLMAgent(
            agent_id="agent-001",
            role="DEV",
            workspace_path=temp_workspace,
        )
        
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
        agent = VLLMAgent(
            agent_id="agent-001",
            role="DEV",
            workspace_path=temp_workspace,
        )
        
        mock_result = MagicMock()
        mock_result.content = "line1\nline2\nline3"
        
        summary = agent._summarize_result(
            {"tool": "files", "operation": "read_file"},
            {"result": mock_result},
        )
        
        assert "lines" in summary

    def test_summarize_default(self, temp_workspace):
        """Test default summary."""
        agent = VLLMAgent(
            agent_id="agent-001",
            role="DEV",
            workspace_path=temp_workspace,
        )
        
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
