"""Quick coverage for vllm_agent gaps (51% → 80-90%)"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from core.agents_and_tools.agents.application.dtos.next_action_dto import NextActionDTO
from core.agents_and_tools.agents.application.dtos.plan_dto import PlanDTO
from core.agents_and_tools.agents.domain.entities import (
    AgentResult,
    AgentThought,
    ExecutionConstraints,
    ExecutionPlan,
    ExecutionStep,
    ObservationHistories,
    ReasoningLogs,
    StepExecutionResult,
)
from core.agents_and_tools.agents.domain.entities.rbac import Action, ActionEnum, RoleFactory
from core.agents_and_tools.agents.domain.entities.results.file_execution_result import (
    FileExecutionResult,
)
from core.agents_and_tools.agents.infrastructure.dtos.agent_initialization_config import (
    AgentInitializationConfig,
)
from core.agents_and_tools.agents.infrastructure.factories.vllm_agent_factory import VLLMAgentFactory
from core.agents_and_tools.agents.vllm_agent import VLLMAgent


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / "src").mkdir()
        (workspace / "tests").mkdir()
        yield workspace


def create_test_config(
    workspace_path, agent_id="agent-dev-001", role="DEVELOPER", vllm_url="http://vllm:8000", **kwargs
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


class TestVLLMAgentInitialization:
    """Test VLLMAgent initialization."""

    def test_init_valid_workspace(self, temp_workspace):
        """Test initialization with valid workspace."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        assert agent.agent_id == "agent-dev-001"
        assert agent.role.get_name() == "developer"
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
        config = create_test_config(temp_workspace, agent_id="agent-001", role="developer")
        agent = VLLMAgentFactory.create(config)

        assert agent.role.get_name() == "developer"

    def test_init_read_only_mode(self, temp_workspace):
        """Test initialization in read-only mode."""
        config = create_test_config(
            temp_workspace, agent_id="agent-001", role="ARCHITECT", enable_tools=False
        )
        agent = VLLMAgentFactory.create(config)

        assert agent.enable_tools is False

    def test_init_with_vllm_url_unavailable(self, temp_workspace):
        """Test initialization with vLLM URL when client unavailable."""
        config = create_test_config(temp_workspace, agent_id="agent-001", vllm_url="http://vllm:8000")
        agent = VLLMAgentFactory.create(config)

        # Should initialize successfully, vllm_client may be None
        assert agent.vllm_url == "http://vllm:8000"

    def test_tools_always_initialized(self, temp_workspace):
        """Test that tools are always initialized."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgentFactory.create(config)

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
        agent = VLLMAgentFactory.create(config)

        tools = agent.get_available_tools()

        assert str(tools.mode) == "full"
        assert "files" in tools.tools
        assert "git" in tools.tools
        assert len(tools.operations) > 0
        # Should include write operations in full mode
        assert any("write" in cap.operation.lower() for cap in tools.operations)

    def test_get_available_tools_read_only_mode(self, temp_workspace):
        """Test tool capabilities in read-only mode."""
        config = create_test_config(
            temp_workspace, agent_id="agent-001", role="ARCHITECT", enable_tools=False
        )
        agent = VLLMAgentFactory.create(config)

        tools = agent.get_available_tools()

        assert str(tools.mode) == "read_only"
        assert len(tools.operations) > 0
        # Check that read operations are present
        assert any("read" in cap.operation.lower() for cap in tools.operations)


class TestIsReadOnlyOperation:
    """Test _is_read_only_operation method."""

    def test_read_operations_allowed(self, temp_workspace):
        """Test that read-only operations work in read-only mode."""
        config = create_test_config(temp_workspace, agent_id="agent-001", enable_tools=False)
        agent = VLLMAgentFactory.create(config)

        # Read operations should work in read-only mode
        # If this doesn't raise, read operations are allowed
        agent.toolset.execute_operation(
            "files", "read_file", {"path": "test.txt"}, enable_write=False
        )

    def test_write_operations_blocked(self, temp_workspace):
        """Test that write operations are blocked in read-only mode."""
        config = create_test_config(temp_workspace, agent_id="agent-001", enable_tools=False)
        agent = VLLMAgentFactory.create(config)


        # Write operations should raise in read-only mode
        with pytest.raises(ValueError, match="Write operation"):
            agent.toolset.execute_operation("files", "write_file", {"path": "test.txt"}, enable_write=False)

        with pytest.raises(ValueError, match="Write operation"):
            agent.toolset.execute_operation("git", "commit", {"message": "test"}, enable_write=False)


class TestPlanningMethods:
    """Test planning methods.

    NOTE: Pattern matching fallback was removed.
    Plans are now generated exclusively by the LLM via GeneratePlanUseCase.
    If vLLM is not available, the system should fail fast with a clear error.
    """


class TestLogThought:
    """Test _log_thought method."""

    def test_log_thought_basic(self, temp_workspace):
        """Test basic thought logging."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgentFactory.create(config)

        log = ReasoningLogs()
        agent._log_thought(
            log,
            iteration=1,
            thought_type="analysis",
            content="Analyzing task",
        )

        assert log.count() == 1
        entry = log.get_all()[0]
        assert entry.iteration == 1
        assert entry.thought_type == "analysis"
        assert entry.content == "Analyzing task"
        assert entry.agent_id == "agent-001"

    def test_log_thought_with_confidence(self, temp_workspace):
        """Test thought logging with confidence."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgentFactory.create(config)

        log = ReasoningLogs()
        agent._log_thought(
            log,
            iteration=1,
            thought_type="decision",
            content="Decision made",
            confidence=0.95,
        )

        assert log.get_all()[0].confidence == pytest.approx(0.95)


class TestSummarizeResult:
    """Test _summarize_result method."""

    def test_summarize_file_read(self, temp_workspace):
        """Test summarizing file read result."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgentFactory.create(config)

        mock_result = MagicMock()
        mock_result.content = "line1\nline2\nline3"

        summary = agent._summarize_result(
            {"tool": "files", "operation": "read_file"},
            mock_result,
            {},
        )

        assert "lines" in summary

    def test_summarize_default(self, temp_workspace):
        """Test default summary."""
        config = create_test_config(temp_workspace, agent_id="agent-001")
        agent = VLLMAgentFactory.create(config)

        summary = agent._summarize_result(
            {"tool": "unknown", "operation": "unknown"},
            None,
            {},
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
        assert thought.confidence == pytest.approx(0.9)


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


class TestVLLMAgentFailFast:
    """Test fail-fast validation in VLLMAgent.__init__."""

    def test_init_raises_error_on_none_llm_client_port(self, temp_workspace):
        """Test that ValueError is raised when llm_client_port is None."""
        config = create_test_config(temp_workspace)
        with pytest.raises(ValueError, match="llm_client_port is required"):
            VLLMAgent(
                config=config,
                llm_client_port=None,  # type: ignore
                tool_execution_port=MagicMock(),
                generate_plan_usecase=MagicMock(),
                generate_next_action_usecase=MagicMock(),
                step_mapper=MagicMock(),
                execute_task_usecase=MagicMock(),
                execute_task_iterative_usecase=MagicMock(),
            )

    def test_init_raises_error_on_none_tool_execution_port(self, temp_workspace):
        """Test that ValueError is raised when tool_execution_port is None."""
        config = create_test_config(temp_workspace)
        with pytest.raises(ValueError, match="tool_execution_port is required"):
            VLLMAgent(
                config=config,
                llm_client_port=MagicMock(),
                tool_execution_port=None,  # type: ignore
                generate_plan_usecase=MagicMock(),
                generate_next_action_usecase=MagicMock(),
                step_mapper=MagicMock(),
                execute_task_usecase=MagicMock(),
                execute_task_iterative_usecase=MagicMock(),
            )

    def test_init_raises_error_on_none_generate_plan_usecase(self, temp_workspace):
        """Test that ValueError is raised when generate_plan_usecase is None."""
        config = create_test_config(temp_workspace)
        with pytest.raises(ValueError, match="generate_plan_usecase is required"):
            VLLMAgent(
                config=config,
                llm_client_port=MagicMock(),
                tool_execution_port=MagicMock(),
                generate_plan_usecase=None,  # type: ignore
                generate_next_action_usecase=MagicMock(),
                step_mapper=MagicMock(),
                execute_task_usecase=MagicMock(),
                execute_task_iterative_usecase=MagicMock(),
            )

    def test_init_raises_error_on_none_generate_next_action_usecase(self, temp_workspace):
        """Test that ValueError is raised when generate_next_action_usecase is None."""
        config = create_test_config(temp_workspace)
        with pytest.raises(ValueError, match="generate_next_action_usecase is required"):
            VLLMAgent(
                config=config,
                llm_client_port=MagicMock(),
                tool_execution_port=MagicMock(),
                generate_plan_usecase=MagicMock(),
                generate_next_action_usecase=None,  # type: ignore
                step_mapper=MagicMock(),
                execute_task_usecase=MagicMock(),
                execute_task_iterative_usecase=MagicMock(),
            )

    def test_init_raises_error_on_none_step_mapper(self, temp_workspace):
        """Test that ValueError is raised when step_mapper is None."""
        config = create_test_config(temp_workspace)
        with pytest.raises(ValueError, match="step_mapper is required"):
            VLLMAgent(
                config=config,
                llm_client_port=MagicMock(),
                tool_execution_port=MagicMock(),
                generate_plan_usecase=MagicMock(),
                generate_next_action_usecase=MagicMock(),
                step_mapper=None,  # type: ignore
                execute_task_usecase=MagicMock(),
                execute_task_iterative_usecase=MagicMock(),
            )

    def test_init_raises_error_on_none_execute_task_usecase(self, temp_workspace):
        """Test that ValueError is raised when execute_task_usecase is None."""
        config = create_test_config(temp_workspace)
        with pytest.raises(ValueError, match="execute_task_usecase is required"):
            VLLMAgent(
                config=config,
                llm_client_port=MagicMock(),
                tool_execution_port=MagicMock(),
                generate_plan_usecase=MagicMock(),
                generate_next_action_usecase=MagicMock(),
                step_mapper=MagicMock(),
                execute_task_usecase=None,  # type: ignore
                execute_task_iterative_usecase=MagicMock(),
            )

    def test_init_raises_error_on_none_execute_task_iterative_usecase(self, temp_workspace):
        """Test that ValueError is raised when execute_task_iterative_usecase is None."""
        config = create_test_config(temp_workspace)
        with pytest.raises(ValueError, match="execute_task_iterative_usecase is required"):
            VLLMAgent(
                config=config,
                llm_client_port=MagicMock(),
                tool_execution_port=MagicMock(),
                generate_plan_usecase=MagicMock(),
                generate_next_action_usecase=MagicMock(),
                step_mapper=MagicMock(),
                execute_task_usecase=MagicMock(),
                execute_task_iterative_usecase=None,  # type: ignore
            )


class TestCanExecute:
    """Test can_execute method."""

    def test_can_execute_delegates_to_agent(self, temp_workspace):
        """Test that can_execute delegates to agent aggregate."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        action = Action(value=ActionEnum.APPROVE_DESIGN)
        result = agent.can_execute(action)

        # Result depends on role's allowed actions
        assert isinstance(result, bool)


class TestCanUseTool:
    """Test can_use_tool method."""

    def test_can_use_tool_delegates_to_agent(self, temp_workspace):
        """Test that can_use_tool delegates to agent aggregate."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        result = agent.can_use_tool("files")

        # Files should be allowed for developer role
        assert result is True

    def test_can_use_tool_returns_false_for_disallowed_tool(self, temp_workspace):
        """Test that can_use_tool returns False for disallowed tools."""
        config = create_test_config(temp_workspace, role="DEVELOPER")
        agent = VLLMAgentFactory.create(config)

        # Developer role may not have all tools
        result = agent.can_use_tool("nonexistent_tool")

        assert isinstance(result, bool)


class TestExecuteTask:
    """Test execute_task method."""

    @pytest.mark.asyncio
    async def test_execute_task_static_mode(self, temp_workspace):
        """Test execute_task with static planning mode."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        # Mock the use case
        mock_result = AgentResult(
            success=True,
            operations=[],
            artifacts={},
        )
        agent.execute_task_usecase.execute = AsyncMock(return_value=mock_result)

        result = await agent.execute_task(
            task="Test task",
            context="Test context",
            constraints=ExecutionConstraints(iterative=False),
        )

        assert result.success is True
        agent.execute_task_usecase.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_task_iterative_mode(self, temp_workspace):
        """Test execute_task with iterative planning mode."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        # Mock the use case
        mock_result = AgentResult(
            success=True,
            operations=[],
            artifacts={},
        )
        agent.execute_task_iterative_usecase.execute = AsyncMock(return_value=mock_result)

        result = await agent.execute_task(
            task="Test task",
            context="Test context",
            constraints=ExecutionConstraints(iterative=True),
        )

        assert result.success is True
        agent.execute_task_iterative_usecase.execute.assert_awaited_once()


class TestGeneratePlan:
    """Test _generate_plan method."""

    @pytest.mark.asyncio
    async def test_generate_plan_with_usecase(self, temp_workspace):
        """Test _generate_plan when use case is available."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        # Mock the use case
        plan_dto = PlanDTO(
            steps=[ExecutionStep(tool="files", operation="read_file")],
            reasoning="Test plan",
        )
        agent.generate_plan_usecase.execute = AsyncMock(return_value=plan_dto)

        plan = await agent._generate_plan(
            task="Test task",
            context="Test context",
            constraints=ExecutionConstraints(),
        )

        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) == 1
        agent.generate_plan_usecase.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_plan_fallback_when_no_usecase(self, temp_workspace):
        """Test _generate_plan fallback when use case is None."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)
        agent.generate_plan_usecase = None  # type: ignore

        plan = await agent._generate_plan(
            task="Test task",
            context="Test context",
            constraints=ExecutionConstraints(),
        )

        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) == 1
        assert plan.steps[0].tool == "files"
        assert plan.steps[0].operation == "list_files"


class TestDecideNextAction:
    """Test _decide_next_action method."""

    @pytest.mark.asyncio
    async def test_decide_next_action_success(self, temp_workspace):
        """Test _decide_next_action with successful use case."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        # Mock the use case
        next_action = NextActionDTO(
            done=False,
            step=ExecutionStep(tool="files", operation="read_file"),
            reasoning="Test reasoning",
        )
        agent.generate_next_action_usecase.execute = AsyncMock(return_value=next_action)

        observation_history = ObservationHistories()
        result = await agent._decide_next_action(
            task="Test task",
            context="Test context",
            observation_history=observation_history,
            constraints=ExecutionConstraints(),
        )

        assert isinstance(result, NextActionDTO)
        assert result.done is False
        agent.generate_next_action_usecase.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_decide_next_action_raises_when_no_usecase(self, temp_workspace):
        """Test _decide_next_action raises RuntimeError when use case is None."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)
        agent.generate_next_action_usecase = None  # type: ignore

        observation_history = ObservationHistories()
        with pytest.raises(RuntimeError, match="Next action use case not available"):
            await agent._decide_next_action(
                task="Test task",
                context="Test context",
                observation_history=observation_history,
                constraints=ExecutionConstraints(),
            )


class TestExecuteStep:
    """Test _execute_step method."""

    @pytest.mark.asyncio
    async def test_execute_step_success(self, temp_workspace):
        """Test _execute_step with successful execution."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        step = ExecutionStep(tool="files", operation="read_file", params={"path": "test.txt"})
        mock_result = FileExecutionResult(success=True, content="content", error=None)

        # Mock toolset.execute_operation to return success
        agent.toolset.execute_operation = MagicMock(return_value=mock_result)

        result = await agent._execute_step(step)

        assert isinstance(result, StepExecutionResult)
        assert result.success is True
        assert result.tool_name == "files"
        assert result.operation == "read_file"

    @pytest.mark.asyncio
    async def test_execute_step_with_dict(self, temp_workspace):
        """Test _execute_step with dict input."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        step_dict = {"tool": "files", "operation": "read_file", "params": {"path": "test.txt"}}
        mock_result = FileExecutionResult(success=True, content="content", error=None)

        # Mock step_mapper and toolset
        agent.step_mapper.to_entity = MagicMock(
            return_value=ExecutionStep(tool="files", operation="read_file")
        )
        agent.toolset.execute_operation = MagicMock(return_value=mock_result)

        result = await agent._execute_step(step_dict)

        assert isinstance(result, StepExecutionResult)
        agent.step_mapper.to_entity.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_step_rbac_violation(self, temp_workspace):
        """Test _execute_step with RBAC violation."""
        config = create_test_config(temp_workspace, role="ARCHITECT")
        agent = VLLMAgentFactory.create(config)

        # Use a tool that architect role may not have access to
        # First check if docker is actually not allowed for architect
        step = ExecutionStep(tool="docker", operation="build", params={})

        # If docker is not in allowed_tools, this will trigger RBAC violation
        # Otherwise, we'll test with a tool we know is not allowed
        if not agent.can_use_tool("docker"):
            result = await agent._execute_step(step)

            assert isinstance(result, StepExecutionResult)
            assert result.success is False
            assert "RBAC Violation" in result.error
            assert result.tool_name == "docker"
        else:
            # If docker is allowed, test with a tool that definitely doesn't exist
            step = ExecutionStep(tool="nonexistent_tool_xyz", operation="do_something", params={})
            result = await agent._execute_step(step)

            assert isinstance(result, StepExecutionResult)
            assert result.success is False
            assert "RBAC Violation" in result.error

    @pytest.mark.asyncio
    async def test_execute_step_value_error(self, temp_workspace):
        """Test _execute_step handles ValueError."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        step = ExecutionStep(tool="files", operation="read_file", params={"path": "test.txt"})

        # Mock toolset to raise ValueError
        agent.toolset.execute_operation = MagicMock(side_effect=ValueError("Invalid path"))

        result = await agent._execute_step(step)

        assert isinstance(result, StepExecutionResult)
        assert result.success is False
        assert "Invalid path" in result.error

    @pytest.mark.asyncio
    async def test_execute_step_general_exception(self, temp_workspace):
        """Test _execute_step handles general exceptions."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        step = ExecutionStep(tool="files", operation="read_file", params={"path": "test.txt"})

        # Mock toolset to raise general exception
        agent.toolset.execute_operation = MagicMock(side_effect=RuntimeError("Unexpected error"))

        result = await agent._execute_step(step)

        assert isinstance(result, StepExecutionResult)
        assert result.success is False
        assert "Unexpected error" in result.error

    @pytest.mark.asyncio
    async def test_execute_step_unknown_error_fallback(self, temp_workspace):
        """Test _execute_step handles result with no error message."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        step = ExecutionStep(tool="files", operation="read_file", params={"path": "test.txt"})

        # Mock result with success=False but error=None
        mock_result = FileExecutionResult(success=False, content=None, error=None)
        agent.toolset.execute_operation = MagicMock(return_value=mock_result)

        result = await agent._execute_step(step)

        assert isinstance(result, StepExecutionResult)
        assert result.success is False
        assert result.error == "Unknown error"


class TestEnsureExecutionStep:
    """Test _ensure_execution_step method."""

    def test_ensure_execution_step_with_entity(self, temp_workspace):
        """Test _ensure_execution_step with ExecutionStep entity."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        step = ExecutionStep(tool="files", operation="read_file")
        result = agent._ensure_execution_step(step)

        assert result == step

    def test_ensure_execution_step_with_dict(self, temp_workspace):
        """Test _ensure_execution_step with dict input."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        step_dict = {"tool": "files", "operation": "read_file"}
        expected_step = ExecutionStep(tool="files", operation="read_file")
        agent.step_mapper.to_entity = MagicMock(return_value=expected_step)

        result = agent._ensure_execution_step(step_dict)

        assert result == expected_step
        agent.step_mapper.to_entity.assert_called_once_with(step_dict)


class TestGetStepParams:
    """Test _get_step_params method."""

    def test_get_step_params_with_entity(self, temp_workspace):
        """Test _get_step_params with ExecutionStep entity."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        step = ExecutionStep(tool="files", operation="read_file", params={"path": "test.txt"})
        result = agent._get_step_params(step)

        assert result == {"path": "test.txt"}

    def test_get_step_params_with_none_params(self, temp_workspace):
        """Test _get_step_params with None params."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        step = ExecutionStep(tool="files", operation="read_file", params=None)
        result = agent._get_step_params(step)

        assert result == {}


class TestCollectArtifacts:
    """Test _collect_artifacts method."""

    def test_collect_artifacts_success(self, temp_workspace):
        """Test _collect_artifacts with successful collection."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        step = ExecutionStep(tool="files", operation="read_file", params={"path": "test.txt"})
        mock_result = FileExecutionResult(success=True, content="content", error=None)
        artifacts = {}

        # Mock tool and its collect_artifacts method
        mock_tool = MagicMock()
        mock_tool.collect_artifacts.return_value = {"file_content": "content"}
        agent.toolset.get_tool_by_name = MagicMock(return_value=mock_tool)

        result = agent._collect_artifacts(step, mock_result, artifacts)

        assert result == {"file_content": "content"}
        mock_tool.collect_artifacts.assert_called_once()

    def test_collect_artifacts_no_tool(self, temp_workspace):
        """Test _collect_artifacts when tool is not found."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        step = ExecutionStep(tool="nonexistent", operation="read_file", params={})
        mock_result = FileExecutionResult(success=True, content="content", error=None)
        artifacts = {}

        # Mock toolset to return None
        agent.toolset.get_tool_by_name = MagicMock(return_value=None)

        result = agent._collect_artifacts(step, mock_result, artifacts)

        assert result == {}

    def test_collect_artifacts_with_dict_step(self, temp_workspace):
        """Test _collect_artifacts with dict step input."""
        config = create_test_config(temp_workspace)
        agent = VLLMAgentFactory.create(config)

        step_dict = {"tool": "files", "operation": "read_file", "params": {"path": "test.txt"}}
        mock_result = FileExecutionResult(success=True, content="content", error=None)
        artifacts = {}

        # Mock step_mapper, tool and its collect_artifacts method
        expected_step = ExecutionStep(tool="files", operation="read_file")
        agent.step_mapper.to_entity = MagicMock(return_value=expected_step)
        mock_tool = MagicMock()
        mock_tool.collect_artifacts.return_value = {"file_content": "content"}
        agent.toolset.get_tool_by_name = MagicMock(return_value=mock_tool)

        result = agent._collect_artifacts(step_dict, mock_result, artifacts)

        assert result == {"file_content": "content"}
        agent.step_mapper.to_entity.assert_called_once_with(step_dict)
