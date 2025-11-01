"""Unit tests for ExecuteTaskIterativeUseCase."""

from unittest.mock import AsyncMock, Mock

import pytest
from core.agents_and_tools.agents.application.dtos.next_action_dto import NextActionDTO
from core.agents_and_tools.agents.application.services.artifact_collection_service import (
    ArtifactCollectionApplicationService,
)
from core.agents_and_tools.agents.application.services.log_reasoning_service import (
    LogReasoningApplicationService,
)
from core.agents_and_tools.agents.application.services.result_summarization_service import (
    ResultSummarizationApplicationService,
)
from core.agents_and_tools.agents.application.services.step_execution_service import (
    StepExecutionApplicationService,
)
from core.agents_and_tools.agents.application.usecases.execute_task_iterative_usecase import (
    ExecuteTaskIterativeUseCase,
)
from core.agents_and_tools.agents.application.usecases.generate_next_action_usecase import (
    GenerateNextActionUseCase,
)
from core.agents_and_tools.agents.domain.entities import (
    Artifact,
    ExecutionConstraints,
    ExecutionStep,
    ObservationHistories,
    ReasoningLogs,
)
from core.agents_and_tools.agents.infrastructure.mappers.artifact_mapper import ArtifactMapper
from core.agents_and_tools.agents.infrastructure.mappers.execution_step_mapper import ExecutionStepMapper
from core.agents_and_tools.common.domain.entities import AgentCapabilities
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort

# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_tool_execution_port():
    """Create mock ToolExecutionPort."""
    port = Mock(spec=ToolExecutionPort)
    port.get_available_tools_description.return_value = AgentCapabilities(
        tools={"files": {"list_files": {}, "read_file": {}}},
        mode="full",
        capabilities=["files.list_files", "files.read_file"],
        summary="Mock agent with files tool"
    )
    return port


@pytest.fixture
def mock_step_mapper():
    """Create mock ExecutionStepMapper."""
    mapper = Mock(spec=ExecutionStepMapper)
    # Default behavior: return the input if it's already an ExecutionStep
    def to_entity(step):
        if isinstance(step, ExecutionStep):
            return step
        # Convert dict to ExecutionStep
        return ExecutionStep(
            tool=step.get("tool", "files"),
            operation=step.get("operation", "list_files"),
            params=step.get("params", {})
        )
    mapper.to_entity.side_effect = to_entity
    return mapper


@pytest.fixture
def mock_artifact_mapper():
    """Create mock ArtifactMapper."""
    mapper = Mock(spec=ArtifactMapper)
    mapper.to_entity_dict.return_value = {}
    return mapper


@pytest.fixture
def mock_generate_next_action_usecase():
    """Create mock GenerateNextActionUseCase."""
    return AsyncMock(spec=GenerateNextActionUseCase)


@pytest.fixture
def create_usecase(
    mock_tool_execution_port,
    mock_step_mapper,
    mock_artifact_mapper,
    mock_generate_next_action_usecase,
):
    """Factory to create ExecuteTaskIterativeUseCase with mocked dependencies."""
    def _create(agent_id="test-agent", role="DEV"):
        log_reasoning_service = LogReasoningApplicationService(agent_id=agent_id, role=role)
        result_summarization_service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port,
        )
        artifact_collection_service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )
        step_execution_service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
        )
        return ExecuteTaskIterativeUseCase(
            tool_execution_port=mock_tool_execution_port,
            step_mapper=mock_step_mapper,
            artifact_mapper=mock_artifact_mapper,
            generate_next_action_usecase=mock_generate_next_action_usecase,
            log_reasoning_service=log_reasoning_service,
            result_summarization_service=result_summarization_service,
            artifact_collection_service=artifact_collection_service,
            step_execution_service=step_execution_service,
            agent_id=agent_id,
        )
    return _create


# =============================================================================
# Constructor Validation Tests
# =============================================================================

class TestExecuteTaskIterativeUseCaseConstructor:
    """Test constructor fail-fast validation."""

    def test_rejects_missing_tool_execution_port(
        self, mock_tool_execution_port, mock_step_mapper, mock_artifact_mapper, mock_generate_next_action_usecase
    ):
        """Should raise ValueError if tool_execution_port is None."""
        log_service = LogReasoningApplicationService(agent_id="test", role="DEV")
        result_summ_service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        artifact_coll_service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )
        step_exec_service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        with pytest.raises(ValueError, match="tool_execution_port is required"):
            ExecuteTaskIterativeUseCase(
                tool_execution_port=None,
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_next_action_usecase=mock_generate_next_action_usecase,
                log_reasoning_service=log_service,
                result_summarization_service=result_summ_service,
                artifact_collection_service=artifact_coll_service,
                step_execution_service=step_exec_service,
                agent_id="test",
            )

    def test_rejects_missing_generate_next_action_usecase(
        self, mock_tool_execution_port, mock_step_mapper, mock_artifact_mapper
    ):
        """Should raise ValueError if generate_next_action_usecase is None."""
        log_service = LogReasoningApplicationService(agent_id="test", role="DEV")
        result_summ_service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        artifact_coll_service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )
        step_exec_service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        with pytest.raises(ValueError, match="generate_next_action_usecase is required"):
            ExecuteTaskIterativeUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_next_action_usecase=None,
                log_reasoning_service=log_service,
                result_summarization_service=result_summ_service,
                artifact_collection_service=artifact_coll_service,
                step_execution_service=step_exec_service,
                agent_id="test",
            )

    def test_rejects_missing_log_reasoning_service(
        self, mock_tool_execution_port, mock_step_mapper, mock_artifact_mapper, mock_generate_next_action_usecase
    ):
        """Should raise ValueError if log_reasoning_service is None."""
        result_summ_service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        artifact_coll_service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )
        step_exec_service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        with pytest.raises(ValueError, match="log_reasoning_service is required"):
            ExecuteTaskIterativeUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_next_action_usecase=mock_generate_next_action_usecase,
                log_reasoning_service=None,
                result_summarization_service=result_summ_service,
                artifact_collection_service=artifact_coll_service,
                step_execution_service=step_exec_service,
                agent_id="test",
            )

    def test_rejects_missing_agent_id(
        self, mock_tool_execution_port, mock_step_mapper, mock_artifact_mapper, mock_generate_next_action_usecase
    ):
        """Should raise ValueError if agent_id is empty."""
        log_service = LogReasoningApplicationService(agent_id="temp", role="DEV")
        result_summ_service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        artifact_coll_service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )
        step_exec_service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        with pytest.raises(ValueError, match="agent_id is required"):
            ExecuteTaskIterativeUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_next_action_usecase=mock_generate_next_action_usecase,
                log_reasoning_service=log_service,
                result_summarization_service=result_summ_service,
                artifact_collection_service=artifact_coll_service,
                step_execution_service=step_exec_service,
                agent_id="",
            )

    def test_accepts_all_required_dependencies(self, create_usecase):
        """Should create instance when all dependencies provided."""
        usecase = create_usecase(agent_id="test-agent-456", role="ARCHITECT")

        assert usecase.agent_id == "test-agent-456"
        assert usecase.role == "ARCHITECT"
        assert usecase.generate_next_action_usecase is not None


# =============================================================================
# Happy Path Tests
# =============================================================================

class TestExecuteTaskIterativeUseCaseHappyPath:
    """Test successful iterative task execution."""

    @pytest.mark.asyncio
    async def test_execute_task_with_single_iteration(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port
    ):
        """Should execute task in single iteration when LLM decides it's done."""
        # Arrange
        step = ExecutionStep(tool="files", operation="list_files", params={"path": "."})

        # First iteration: execute step, second iteration: done
        mock_generate_next_action_usecase.execute.side_effect = [
            NextActionDTO(done=False, step=step, reasoning="List files first"),
            NextActionDTO(done=True, step=None, reasoning="Task complete"),
        ]

        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Listed 5 files"
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="List workspace files",
            context="Python project",
            constraints=ExecutionConstraints(max_iterations=10),
            enable_write=True,
        )

        # Assert
        assert result.success is True
        assert result.operations.count() == 1
        assert mock_generate_next_action_usecase.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_task_with_multiple_iterations(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port
    ):
        """Should execute multiple iterations based on LLM decisions."""
        # Arrange
        steps = [
            ExecutionStep(tool="files", operation="list_files", params={"path": "."}),
            ExecutionStep(tool="files", operation="read_file", params={"path": "test.py"}),
            ExecutionStep(tool="git", operation="status", params={}),
        ]

        # Three iterations with steps, then done
        mock_generate_next_action_usecase.execute.side_effect = [
            NextActionDTO(done=False, step=steps[0], reasoning="List files"),
            NextActionDTO(done=False, step=steps[1], reasoning="Read file"),
            NextActionDTO(done=False, step=steps[2], reasoning="Check git"),
            NextActionDTO(done=True, step=None, reasoning="All done"),
        ]

        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Success"
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Analyze project",
            context="Python project",
            constraints=ExecutionConstraints(max_iterations=10),
            enable_write=True,
        )

        # Assert
        assert result.success is True
        assert result.operations.count() == 3
        assert mock_tool_execution_port.execute_operation.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_task_immediate_done(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port
    ):
        """Should handle LLM deciding task is already complete."""
        # Arrange
        mock_generate_next_action_usecase.execute.return_value = NextActionDTO(
            done=True,
            step=None,
            reasoning="Task already complete"
        )

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Check if done",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        assert result.success is True
        assert result.operations.count() == 0
        mock_tool_execution_port.execute_operation.assert_not_called()


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestExecuteTaskIterativeUseCaseErrorHandling:
    """Test error handling in iterative execution."""

    @pytest.mark.asyncio
    async def test_execute_task_with_failed_step_abort_on_error(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port
    ):
        """Should abort on first error when abort_on_error is True."""
        # Arrange
        step = ExecutionStep(tool="files", operation="read_file", params={"path": "missing.py"})
        mock_generate_next_action_usecase.execute.return_value = NextActionDTO(
            done=False,
            step=step,
            reasoning="Read file"
        )

        failed_result = Mock(success=False, error="File not found")
        mock_tool_execution_port.execute_operation.return_value = failed_result
        mock_tool_execution_port.get_tool_by_name.return_value = Mock()

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Read missing file",
            context="Python project",
            constraints=ExecutionConstraints(abort_on_error=True, max_iterations=10),
            enable_write=True,
        )

        # Assert
        assert result.success is False
        assert "File not found" in result.error
        assert result.operations.count() == 1
        # Should not ask for next action after error
        assert mock_generate_next_action_usecase.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_task_with_failed_step_continue_on_error(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port
    ):
        """Should continue after error when abort_on_error is False."""
        # Arrange
        steps = [
            ExecutionStep(tool="files", operation="read_file", params={"path": "missing.py"}),
            ExecutionStep(tool="files", operation="list_files", params={"path": "."}),
        ]

        mock_generate_next_action_usecase.execute.side_effect = [
            NextActionDTO(done=False, step=steps[0], reasoning="Read file"),
            NextActionDTO(done=False, step=steps[1], reasoning="List files"),
            NextActionDTO(done=True, step=None, reasoning="Done"),
        ]

        # First fails, second succeeds
        mock_tool_execution_port.execute_operation.side_effect = [
            Mock(success=False, error="File not found"),
            Mock(success=True, error=None),
        ]

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Success"
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Try operations",
            context="Python project",
            constraints=ExecutionConstraints(abort_on_error=False, max_iterations=10),
            enable_write=True,
        )

        # Assert
        assert result.success is False  # Not all succeeded
        assert result.operations.count() == 2
        assert mock_tool_execution_port.execute_operation.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_task_with_next_action_exception(
        self, create_usecase, mock_generate_next_action_usecase
    ):
        """Should handle exception from GenerateNextActionUseCase."""
        # Arrange
        mock_generate_next_action_usecase.execute.side_effect = RuntimeError("LLM API error")

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Test task",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        assert result.success is False
        assert "LLM API error" in result.error


# =============================================================================
# Constraints Tests
# =============================================================================

class TestExecuteTaskIterativeUseCaseConstraints:
    """Test execution constraints enforcement."""

    @pytest.mark.asyncio
    async def test_execute_task_respects_max_iterations(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port
    ):
        """Should stop after max_iterations even if not done."""
        # Arrange
        step = ExecutionStep(tool="files", operation="list_files", params={"path": "."})

        # Always return more work to do
        mock_generate_next_action_usecase.execute.return_value = NextActionDTO(
            done=False,
            step=step,
            reasoning="Keep working"
        )

        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Success"
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Long task",
            context="Python project",
            constraints=ExecutionConstraints(max_iterations=3, max_operations=100),
            enable_write=True,
        )

        # Assert
        assert result.operations.count() == 3  # Stopped at max_iterations
        assert mock_generate_next_action_usecase.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_task_respects_max_operations(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port
    ):
        """Should stop after max_operations limit."""
        # Arrange
        step = ExecutionStep(tool="files", operation="list_files", params={"path": "."})

        # Always return more work
        mock_generate_next_action_usecase.execute.return_value = NextActionDTO(
            done=False,
            step=step,
            reasoning="Keep working"
        )

        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Success"
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Many operations",
            context="Python project",
            constraints=ExecutionConstraints(max_iterations=100, max_operations=5),
            enable_write=True,
        )

        # Assert
        assert result.operations.count() == 5  # Stopped at max_operations


# =============================================================================
# Orchestration Tests
# =============================================================================

class TestExecuteTaskIterativeUseCaseOrchestration:
    """Test orchestration and ReAct pattern."""

    @pytest.mark.asyncio
    async def test_execute_task_calls_generate_next_action_usecase(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port
    ):
        """Should call generate_next_action_usecase with correct parameters."""
        # Arrange
        mock_generate_next_action_usecase.execute.return_value = NextActionDTO(
            done=True,
            step=None,
            reasoning="Done"
        )

        usecase = create_usecase(agent_id="agent-789", role="QA")

        # Act
        await usecase.execute(
            task="Test iterative",
            context="Test context",
            constraints=ExecutionConstraints(max_iterations=5),
            enable_write=True,
        )

        # Assert
        mock_generate_next_action_usecase.execute.assert_called_once()
        call_kwargs = mock_generate_next_action_usecase.execute.call_args[1]
        assert call_kwargs["task"] == "Test iterative"
        assert call_kwargs["context"] == "Test context"
        assert isinstance(call_kwargs["observation_history"], ObservationHistories)
        assert isinstance(call_kwargs["available_tools"], AgentCapabilities)

    @pytest.mark.asyncio
    async def test_execute_task_updates_observation_history(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port
    ):
        """Should update observation history after each iteration."""
        # Arrange
        steps = [
            ExecutionStep(tool="files", operation="list_files", params={"path": "."}),
            ExecutionStep(tool="files", operation="read_file", params={"path": "a.py"}),
        ]

        mock_generate_next_action_usecase.execute.side_effect = [
            NextActionDTO(done=False, step=steps[0], reasoning="List first"),
            NextActionDTO(done=False, step=steps[1], reasoning="Read file"),
            NextActionDTO(done=True, step=None, reasoning="Done"),
        ]

        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Success"
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Read files",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        assert result.operations.count() == 2
        # Verify observation history was passed to each next action decision
        for call in mock_generate_next_action_usecase.execute.call_args_list:
            obs_history = call[1]["observation_history"]
            assert isinstance(obs_history, ObservationHistories)

    @pytest.mark.asyncio
    async def test_execute_task_collects_artifacts(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port, mock_artifact_mapper
    ):
        """Should collect artifacts from successful iterations."""
        # Arrange
        step = ExecutionStep(tool="files", operation="read_file", params={"path": "test.py"})

        mock_generate_next_action_usecase.execute.side_effect = [
            NextActionDTO(done=False, step=step, reasoning="Read file"),
            NextActionDTO(done=True, step=None, reasoning="Done"),
        ]

        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Read file"
        tool_mock.collect_artifacts.return_value = {"file_content": "print('hello')"}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        mock_artifact_mapper.to_entity_dict.return_value = {
            "file_content": Artifact(name="file_content", value="print('hello')", artifact_type="text")
        }

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Read file",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        tool_mock.collect_artifacts.assert_called_once()
        assert result.artifacts.count() == 1

    @pytest.mark.asyncio
    async def test_execute_task_populates_reasoning_log(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port
    ):
        """Should populate reasoning log with thoughts from ReAct pattern."""
        # Arrange
        step = ExecutionStep(tool="files", operation="list_files", params={"path": "."})

        mock_generate_next_action_usecase.execute.side_effect = [
            NextActionDTO(done=False, step=step, reasoning="List files"),
            NextActionDTO(done=True, step=None, reasoning="Done"),
        ]

        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Listed files"
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase(agent_id="agent-react", role="DEV")

        # Act
        result = await usecase.execute(
            task="List files",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        assert isinstance(result.reasoning_log, ReasoningLogs)
        assert result.reasoning_log.count() > 0

        # Verify reasoning log contains ReAct pattern thoughts
        all_thoughts = result.reasoning_log.get_all()
        thought_types = {t.thought_type for t in all_thoughts}
        assert "analysis" in thought_types  # Initial analysis
        assert "decision" in thought_types  # LLM decision
        assert "action" in thought_types    # Step execution
        assert "observation" in thought_types  # Result observation
        assert "conclusion" in thought_types  # Final thought


# =============================================================================
# ReAct Pattern Tests
# =============================================================================

class TestExecuteTaskIterativeUseCaseReActPattern:
    """Test ReAct (Reasoning + Acting) pattern implementation."""

    @pytest.mark.asyncio
    async def test_react_pattern_observation_history_grows(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port
    ):
        """Should build observation history as iterations progress."""
        # Arrange
        steps = [
            ExecutionStep(tool="files", operation="list_files", params={"path": "."}),
            ExecutionStep(tool="files", operation="read_file", params={"path": "test.py"}),
        ]

        observation_counts = []

        def capture_observation_count(**kwargs):
            # Capture the COUNT at this moment (not reference to mutable object)
            observation_counts.append(kwargs["observation_history"].count())
            if len(observation_counts) == 1:
                return NextActionDTO(done=False, step=steps[0], reasoning="List")
            elif len(observation_counts) == 2:
                return NextActionDTO(done=False, step=steps[1], reasoning="Read")
            else:
                return NextActionDTO(done=True, step=None, reasoning="Done")

        mock_generate_next_action_usecase.execute.side_effect = capture_observation_count

        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Success"
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase()

        # Act
        await usecase.execute(
            task="Iterative task",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        assert len(observation_counts) == 3
        assert observation_counts[0] == 0  # First iteration, no history
        assert observation_counts[1] == 1  # Second iteration, 1 observation
        assert observation_counts[2] == 2  # Third iteration, 2 observations

    @pytest.mark.asyncio
    async def test_react_pattern_adapts_based_on_observations(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port
    ):
        """Should pass observations to LLM for adaptive decision making."""
        # Arrange
        step1 = ExecutionStep(tool="files", operation="list_files", params={"path": "."})
        step2 = ExecutionStep(tool="files", operation="read_file", params={"path": "found.py"})

        observation_counts = []

        def capture_and_decide(**kwargs):
            # Capture count at decision time
            observation_counts.append(kwargs["observation_history"].count())
            if len(observation_counts) == 1:
                return NextActionDTO(done=False, step=step1, reasoning="Explore workspace")
            elif len(observation_counts) == 2:
                return NextActionDTO(done=False, step=step2, reasoning="Read interesting file")
            else:
                return NextActionDTO(done=True, step=None, reasoning="Analysis complete")

        mock_generate_next_action_usecase.execute.side_effect = capture_and_decide

        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Success"
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Adaptive analysis",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        assert result.success is True
        assert result.operations.count() == 2

        # Verify observation history grew correctly
        assert len(observation_counts) == 3
        assert observation_counts[0] == 0  # First decision: no history yet
        assert observation_counts[1] == 1  # Second decision: 1 observation
        assert observation_counts[2] == 2  # Third decision: 2 observations


# =============================================================================
# Helper Method Tests
# =============================================================================

class TestExecuteTaskIterativeUseCaseHelperMethods:
    """Test helper methods."""

    @pytest.mark.asyncio
    async def test_decide_next_action_delegates_to_usecase(
        self, create_usecase, mock_generate_next_action_usecase, mock_tool_execution_port
    ):
        """Should delegate to GenerateNextActionUseCase."""
        # Arrange
        expected_decision = NextActionDTO(
            done=False,
            step=ExecutionStep(tool="files", operation="list_files", params={}),
            reasoning="LLM decision"
        )
        mock_generate_next_action_usecase.execute.return_value = expected_decision

        usecase = create_usecase()
        obs_history = ObservationHistories()

        # Act
        decision = await usecase._decide_next_action(
            task="Test task",
            context="Test context",
            observation_history=obs_history,
            constraints=ExecutionConstraints(),
        )

        # Assert
        assert decision == expected_decision
        mock_generate_next_action_usecase.execute.assert_called_once()

    def test_summarize_result_delegates_to_tool(self, create_usecase, mock_tool_execution_port):
        """Should delegate result summarization to tool."""
        # Arrange
        step = ExecutionStep(tool="files", operation="list_files", params={"path": "."})
        tool_result = Mock()

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Found 5 files"
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase()

        # Act
        summary = usecase._summarize_result(step, tool_result, {"path": "."})

        # Assert
        assert summary == "Found 5 files"
        tool_mock.summarize_result.assert_called_once()

