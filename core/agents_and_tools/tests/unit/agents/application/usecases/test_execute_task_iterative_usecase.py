"""Unit tests for ExecuteTaskIterativeUseCase."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.agents_and_tools.agents.application.dtos.next_action_dto import NextActionDTO
from core.agents_and_tools.agents.application.dtos.step_execution_dto import StepExecutionDTO
from core.agents_and_tools.agents.application.usecases.execute_task_iterative_usecase import (
    ExecuteTaskIterativeUseCase,
)
from core.agents_and_tools.agents.domain.entities import (
    Artifact,
    Artifacts,
    AuditTrails,
    ExecutionConstraints,
    ExecutionStep,
    ObservationHistories,
    Operations,
    ReasoningLogs,
)
from core.agents_and_tools.agents.domain.entities.results.file_execution_result import (
    FileExecutionResult,
)


@pytest.fixture
def mock_tool_execution_port() -> MagicMock:
    """Create mock ToolExecutionPort."""
    mock = MagicMock()
    mock.get_available_tools_description.return_value = MagicMock()
    return mock


@pytest.fixture
def mock_step_mapper() -> MagicMock:
    """Create mock ExecutionStepMapper."""
    return MagicMock()


@pytest.fixture
def mock_artifact_mapper() -> MagicMock:
    """Create mock ArtifactMapper."""
    return MagicMock()


@pytest.fixture
def mock_generate_next_action_usecase() -> AsyncMock:
    """Create mock GenerateNextActionUseCase."""
    return AsyncMock()


@pytest.fixture
def mock_log_reasoning_service() -> MagicMock:
    """Create mock LogReasoningApplicationService."""
    mock = MagicMock()
    mock.role = MagicMock()
    mock.role.get_name.return_value = "DEVELOPER"
    return mock


@pytest.fixture
def mock_result_summarization_service() -> MagicMock:
    """Create mock ResultSummarizationApplicationService."""
    return MagicMock()


@pytest.fixture
def mock_artifact_collection_service() -> MagicMock:
    """Create mock ArtifactCollectionApplicationService."""
    return MagicMock()


@pytest.fixture
def mock_step_execution_service() -> AsyncMock:
    """Create mock StepExecutionApplicationService."""
    return AsyncMock()


@pytest.fixture
def use_case(
    mock_tool_execution_port: MagicMock,
    mock_step_mapper: MagicMock,
    mock_artifact_mapper: MagicMock,
    mock_generate_next_action_usecase: AsyncMock,
    mock_log_reasoning_service: MagicMock,
    mock_result_summarization_service: MagicMock,
    mock_artifact_collection_service: MagicMock,
    mock_step_execution_service: AsyncMock,
) -> ExecuteTaskIterativeUseCase:
    """Create ExecuteTaskIterativeUseCase instance."""
    return ExecuteTaskIterativeUseCase(
        tool_execution_port=mock_tool_execution_port,
        step_mapper=mock_step_mapper,
        artifact_mapper=mock_artifact_mapper,
        generate_next_action_usecase=mock_generate_next_action_usecase,
        log_reasoning_service=mock_log_reasoning_service,
        result_summarization_service=mock_result_summarization_service,
        artifact_collection_service=mock_artifact_collection_service,
        step_execution_service=mock_step_execution_service,
        agent_id="test-agent-001",
    )


@pytest.fixture
def execution_step() -> ExecutionStep:
    """Create valid execution step."""
    return ExecutionStep(
        tool="files",
        operation="read_file",
        params={"path": "test.py"},
    )


@pytest.fixture
def execution_constraints() -> ExecutionConstraints:
    """Create execution constraints."""
    return ExecutionConstraints(
        max_operations=10,
        abort_on_error=True,
        iterative=True,
        max_iterations=5,
    )


class TestExecuteTaskIterativeUseCaseInitialization:
    """Tests for use case initialization."""

    def test_init_with_valid_params(
        self,
        mock_tool_execution_port: MagicMock,
        mock_step_mapper: MagicMock,
        mock_artifact_mapper: MagicMock,
        mock_generate_next_action_usecase: AsyncMock,
        mock_log_reasoning_service: MagicMock,
        mock_result_summarization_service: MagicMock,
        mock_artifact_collection_service: MagicMock,
        mock_step_execution_service: AsyncMock,
    ) -> None:
        """Test initialization with valid parameters."""
        use_case = ExecuteTaskIterativeUseCase(
            tool_execution_port=mock_tool_execution_port,
            step_mapper=mock_step_mapper,
            artifact_mapper=mock_artifact_mapper,
            generate_next_action_usecase=mock_generate_next_action_usecase,
            log_reasoning_service=mock_log_reasoning_service,
            result_summarization_service=mock_result_summarization_service,
            artifact_collection_service=mock_artifact_collection_service,
            step_execution_service=mock_step_execution_service,
            agent_id="test-agent",
        )
        assert use_case.agent_id == "test-agent"
        assert use_case.tool_execution_port == mock_tool_execution_port

    def test_init_with_none_tool_execution_port_raises_error(
        self,
        mock_step_mapper: MagicMock,
        mock_artifact_mapper: MagicMock,
        mock_generate_next_action_usecase: AsyncMock,
        mock_log_reasoning_service: MagicMock,
        mock_result_summarization_service: MagicMock,
        mock_artifact_collection_service: MagicMock,
        mock_step_execution_service: AsyncMock,
    ) -> None:
        """Test that None tool_execution_port raises ValueError."""
        with pytest.raises(ValueError, match="tool_execution_port is required"):
            ExecuteTaskIterativeUseCase(
                tool_execution_port=None,  # type: ignore[arg-type]
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_next_action_usecase=mock_generate_next_action_usecase,
                log_reasoning_service=mock_log_reasoning_service,
                result_summarization_service=mock_result_summarization_service,
                artifact_collection_service=mock_artifact_collection_service,
                step_execution_service=mock_step_execution_service,
                agent_id="test-agent",
            )

    def test_init_with_empty_agent_id_raises_error(
        self,
        mock_tool_execution_port: MagicMock,
        mock_step_mapper: MagicMock,
        mock_artifact_mapper: MagicMock,
        mock_generate_next_action_usecase: AsyncMock,
        mock_log_reasoning_service: MagicMock,
        mock_result_summarization_service: MagicMock,
        mock_artifact_collection_service: MagicMock,
        mock_step_execution_service: AsyncMock,
    ) -> None:
        """Test that empty agent_id raises ValueError."""
        with pytest.raises(ValueError, match="agent_id is required"):
            ExecuteTaskIterativeUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_next_action_usecase=mock_generate_next_action_usecase,
                log_reasoning_service=mock_log_reasoning_service,
                result_summarization_service=mock_result_summarization_service,
                artifact_collection_service=mock_artifact_collection_service,
                step_execution_service=mock_step_execution_service,
                agent_id="",
            )

    def test_init_with_none_step_mapper_raises_error(
        self,
        mock_tool_execution_port: MagicMock,
        mock_artifact_mapper: MagicMock,
        mock_generate_next_action_usecase: AsyncMock,
        mock_log_reasoning_service: MagicMock,
        mock_result_summarization_service: MagicMock,
        mock_artifact_collection_service: MagicMock,
        mock_step_execution_service: AsyncMock,
    ) -> None:
        """Test that None step_mapper raises ValueError."""
        with pytest.raises(ValueError, match="step_mapper is required"):
            ExecuteTaskIterativeUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=None,  # type: ignore[arg-type]
                artifact_mapper=mock_artifact_mapper,
                generate_next_action_usecase=mock_generate_next_action_usecase,
                log_reasoning_service=mock_log_reasoning_service,
                result_summarization_service=mock_result_summarization_service,
                artifact_collection_service=mock_artifact_collection_service,
                step_execution_service=mock_step_execution_service,
                agent_id="test-agent",
            )

    def test_init_with_none_step_execution_service_raises_error(
        self,
        mock_tool_execution_port: MagicMock,
        mock_step_mapper: MagicMock,
        mock_artifact_mapper: MagicMock,
        mock_generate_next_action_usecase: AsyncMock,
        mock_log_reasoning_service: MagicMock,
        mock_result_summarization_service: MagicMock,
        mock_artifact_collection_service: MagicMock,
    ) -> None:
        """Test that None step_execution_service raises ValueError."""
        with pytest.raises(ValueError, match="step_execution_service is required"):
            ExecuteTaskIterativeUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_next_action_usecase=mock_generate_next_action_usecase,
                log_reasoning_service=mock_log_reasoning_service,
                result_summarization_service=mock_result_summarization_service,
                artifact_collection_service=mock_artifact_collection_service,
                step_execution_service=None,  # type: ignore[arg-type]
                agent_id="test-agent",
            )


class TestExecuteStep:
    """Tests for _execute_step method."""

    @pytest.mark.asyncio
    async def test_execute_step_delegates_to_service(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        execution_step: ExecutionStep,
        mock_step_execution_service: AsyncMock,
    ) -> None:
        """Test that _execute_step delegates to step_execution_service."""
        # Given: step execution service returns success
        expected_result = StepExecutionDTO(
            success=True,
            result=FileExecutionResult(success=True, content="content", error=None),
            error=None,
        )
        mock_step_execution_service.execute.return_value = expected_result

        # When: execute step
        result = await use_case._execute_step(execution_step, enable_write=True)

        # Then: service called with correct parameters
        mock_step_execution_service.execute.assert_awaited_once_with(
            execution_step, True
        )
        assert result == expected_result


class TestDecideNextAction:
    """Tests for _decide_next_action method."""

    @pytest.mark.asyncio
    async def test_decide_next_action_delegates_to_usecase(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        mock_generate_next_action_usecase: AsyncMock,
        mock_tool_execution_port: MagicMock,
    ) -> None:
        """Test that _decide_next_action delegates to generate_next_action_usecase."""
        # Given: next action use case returns decision
        expected_action = NextActionDTO(
            done=False,
            step=ExecutionStep(tool="files", operation="read_file", params={}),
            reasoning="Need to read file",
        )
        mock_generate_next_action_usecase.execute.return_value = expected_action

        # When: decide next action
        observation_history = ObservationHistories()
        constraints = ExecutionConstraints()
        result = await use_case._decide_next_action(
            task="test task",
            context="test context",
            observation_history=observation_history,
            constraints=constraints,
        )

        # Then: use case called with correct parameters
        mock_generate_next_action_usecase.execute.assert_awaited_once()
        assert result == expected_action


class TestCheckIterationCompletion:
    """Tests for _check_iteration_completion method."""

    def test_check_completion_with_done_returns_true(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        mock_log_reasoning_service: MagicMock,
    ) -> None:
        """Test that done=True returns should_stop=True."""
        # Given: next action with done=True
        next_action = NextActionDTO(
            done=True,
            step=None,
            reasoning="Task complete",
        )

        # When: check completion
        reasoning_log = ReasoningLogs()
        should_stop, result = use_case._check_iteration_completion(
            next_action, iteration=0, reasoning_log=reasoning_log
        )

        # Then: should stop
        assert should_stop is True
        assert result is None
        mock_log_reasoning_service._log_thought.assert_called_once()

    def test_check_completion_with_no_step_returns_true(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        mock_log_reasoning_service: MagicMock,
    ) -> None:
        """Test that step=None returns should_stop=True."""
        # Given: next action with no step (done=True allows None step)
        next_action = NextActionDTO(
            done=True,
            step=None,
            reasoning="No step needed",
        )

        # When: check completion
        reasoning_log = ReasoningLogs()
        should_stop, result = use_case._check_iteration_completion(
            next_action, iteration=0, reasoning_log=reasoning_log
        )

        # Then: should stop
        assert should_stop is True
        assert result is None

    def test_check_completion_with_step_returns_false(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        execution_step: ExecutionStep,
    ) -> None:
        """Test that step present returns should_stop=False."""
        # Given: next action with step
        next_action = NextActionDTO(
            done=False,
            step=execution_step,
            reasoning="Execute step",
        )

        # When: check completion
        reasoning_log = ReasoningLogs()
        should_stop, result = use_case._check_iteration_completion(
            next_action, iteration=0, reasoning_log=reasoning_log
        )

        # Then: should not stop
        assert should_stop is False
        assert result is None


class TestConvertToExecutionStep:
    """Tests for _convert_to_execution_step method."""

    def test_convert_with_execution_step_returns_as_is(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        execution_step: ExecutionStep,
    ) -> None:
        """Test that ExecutionStep is returned as-is."""
        result = use_case._convert_to_execution_step(execution_step)
        assert result == execution_step

    def test_convert_with_dict_uses_mapper(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        mock_step_mapper: MagicMock,
        execution_step: ExecutionStep,
    ) -> None:
        """Test that dict is converted using mapper."""
        # Given: step as dict
        step_dict = {"tool": "files", "operation": "read_file", "params": {}}
        mock_step_mapper.to_entity.return_value = execution_step

        # When: convert
        result = use_case._convert_to_execution_step(step_dict)

        # Then: mapper called
        mock_step_mapper.to_entity.assert_called_once_with(step_dict)
        assert result == execution_step

    def test_convert_with_none_returns_none(
        self,
        use_case: ExecuteTaskIterativeUseCase,
    ) -> None:
        """Test that None is returned as-is (type ignore expected)."""
        result = use_case._convert_to_execution_step(None)
        assert result is None


class TestProcessIterationResult:
    """Tests for _process_iteration_result method."""

    @pytest.mark.asyncio
    async def test_process_result_success_collects_artifacts(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        execution_step: ExecutionStep,
        mock_artifact_collection_service: MagicMock,
        mock_log_reasoning_service: MagicMock,
    ) -> None:
        """Test that successful result collects artifacts."""
        # Given: successful step execution
        result = StepExecutionDTO(
            success=True,
            result=FileExecutionResult(success=True, content="content", error=None),
            error=None,
        )
        operations = Operations()
        artifacts = Artifacts()
        observation_history = ObservationHistories()
        reasoning_log = ReasoningLogs()
        constraints = ExecutionConstraints(abort_on_error=False)

        # Given: artifact collection returns artifacts
        collected_artifacts = {
            "file_content": Artifact(name="file_content", value="content", artifact_type="text")
        }
        mock_artifact_collection_service.collect.return_value = collected_artifacts

        # When: process result
        abort_result = await use_case._process_iteration_result(
            step=execution_step,
            result=result,
            iteration=0,
            operations=operations,
            artifacts=artifacts,
            observation_history=observation_history,
            reasoning_log=reasoning_log,
            constraints=constraints,
        )

        # Then: no abort
        assert abort_result is None
        # Then: operation added
        assert operations.count() == 1
        # Then: observation added
        assert observation_history.count() == 1
        # Then: artifacts collected
        assert "file_content" in artifacts.items

    @pytest.mark.asyncio
    async def test_process_result_error_with_abort_returns_agent_result(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        execution_step: ExecutionStep,
        mock_log_reasoning_service: MagicMock,
    ) -> None:
        """Test that error with abort_on_error returns AgentResult."""
        # Given: failed step execution
        result = StepExecutionDTO(
            success=False,
            result=None,
            error="File not found",
        )
        operations = Operations()
        artifacts = Artifacts()
        observation_history = ObservationHistories()
        reasoning_log = ReasoningLogs()
        constraints = ExecutionConstraints(abort_on_error=True)

        # When: process result
        abort_result = await use_case._process_iteration_result(
            step=execution_step,
            result=result,
            iteration=0,
            operations=operations,
            artifacts=artifacts,
            observation_history=observation_history,
            reasoning_log=reasoning_log,
            constraints=constraints,
        )

        # Then: abort result returned
        assert abort_result is not None
        assert abort_result.success is False
        assert "Iteration 1 failed" in abort_result.error
        assert abort_result.operations == operations

    @pytest.mark.asyncio
    async def test_process_result_error_without_abort_continues(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        execution_step: ExecutionStep,
        mock_log_reasoning_service: MagicMock,
    ) -> None:
        """Test that error without abort_on_error continues."""
        # Given: failed step execution
        result = StepExecutionDTO(
            success=False,
            result=None,
            error="File not found",
        )
        operations = Operations()
        artifacts = Artifacts()
        observation_history = ObservationHistories()
        reasoning_log = ReasoningLogs()
        constraints = ExecutionConstraints(abort_on_error=False)

        # When: process result
        abort_result = await use_case._process_iteration_result(
            step=execution_step,
            result=result,
            iteration=0,
            operations=operations,
            artifacts=artifacts,
            observation_history=observation_history,
            reasoning_log=reasoning_log,
            constraints=constraints,
        )

        # Then: no abort
        assert abort_result is None
        # Then: operation still added (failed)
        assert operations.count() == 1
        assert not operations.get_all()[0].success


class TestExecuteIterationStep:
    """Tests for _execute_iteration_step method."""

    @pytest.mark.asyncio
    async def test_execute_iteration_step_success(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        execution_step: ExecutionStep,
        mock_step_execution_service: AsyncMock,
        mock_log_reasoning_service: MagicMock,
        mock_artifact_collection_service: MagicMock,
    ) -> None:
        """Test successful iteration step execution."""
        # Given: next action with step
        next_action = NextActionDTO(
            done=False,
            step=execution_step,
            reasoning="Read file",
        )

        # Given: successful step execution
        step_result = StepExecutionDTO(
            success=True,
            result=FileExecutionResult(success=True, content="content", error=None),
            error=None,
        )
        mock_step_execution_service.execute.return_value = step_result

        # Given: artifact collection
        mock_artifact_collection_service.collect.return_value = {}

        operations = Operations()
        artifacts = Artifacts()
        observation_history = ObservationHistories()
        reasoning_log = ReasoningLogs()
        constraints = ExecutionConstraints(abort_on_error=False)

        # When: execute iteration step
        abort_result = await use_case._execute_iteration_step(
            next_action=next_action,
            iteration=0,
            operations=operations,
            artifacts=artifacts,
            observation_history=observation_history,
            reasoning_log=reasoning_log,
            constraints=constraints,
            enable_write=True,
        )

        # Then: no abort
        assert abort_result is None
        # Then: step executed
        mock_step_execution_service.execute.assert_awaited_once_with(
            execution_step, True
        )
        # Then: operation recorded
        assert operations.count() == 1


class TestExecuteReactLoop:
    """Tests for _execute_react_loop method."""

    @pytest.mark.asyncio
    async def test_react_loop_completes_when_done(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        mock_generate_next_action_usecase: AsyncMock,
        mock_log_reasoning_service: MagicMock,
    ) -> None:
        """Test that loop completes when next_action.done=True."""
        # Given: next action returns done=True
        done_action = NextActionDTO(
            done=True,
            step=None,
            reasoning="Task complete",
        )
        mock_generate_next_action_usecase.execute.return_value = done_action

        operations = Operations()
        artifacts = Artifacts()
        observation_history = ObservationHistories()
        reasoning_log = ReasoningLogs()
        constraints = ExecutionConstraints(max_iterations=5)

        # When: execute react loop
        result = await use_case._execute_react_loop(
            task="test task",
            context="test context",
            operations=operations,
            artifacts=artifacts,
            observation_history=observation_history,
            reasoning_log=reasoning_log,
            constraints=constraints,
            enable_write=True,
            max_iterations=5,
        )

        # Then: no early abort
        assert result is None
        # Then: next action called once
        assert mock_generate_next_action_usecase.execute.await_count == 1

    @pytest.mark.asyncio
    async def test_react_loop_stops_at_max_operations(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        execution_step: ExecutionStep,
        mock_generate_next_action_usecase: AsyncMock,
        mock_step_execution_service: AsyncMock,
        mock_artifact_collection_service: MagicMock,
    ) -> None:
        """Test that loop stops when max_operations reached."""
        # Given: next action with step
        next_action = NextActionDTO(
            done=False,
            step=execution_step,
            reasoning="Execute step",
        )
        mock_generate_next_action_usecase.execute.return_value = next_action

        # Given: successful step execution
        step_result = StepExecutionDTO(
            success=True,
            result=FileExecutionResult(success=True, content="content", error=None),
            error=None,
        )
        mock_step_execution_service.execute.return_value = step_result
        mock_artifact_collection_service.collect.return_value = {}

        operations = Operations()
        artifacts = Artifacts()
        observation_history = ObservationHistories()
        reasoning_log = ReasoningLogs()
        constraints = ExecutionConstraints(max_operations=2, max_iterations=10)

        # When: execute react loop
        result = await use_case._execute_react_loop(
            task="test task",
            context="test context",
            operations=operations,
            artifacts=artifacts,
            observation_history=observation_history,
            reasoning_log=reasoning_log,
            constraints=constraints,
            enable_write=True,
            max_iterations=10,
        )

        # Then: no early abort
        assert result is None
        # Then: operations limited to max_operations
        assert operations.count() <= constraints.max_operations

    @pytest.mark.asyncio
    async def test_react_loop_returns_early_abort_on_error(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        execution_step: ExecutionStep,
        mock_generate_next_action_usecase: AsyncMock,
        mock_step_execution_service: AsyncMock,
        mock_log_reasoning_service: MagicMock,
    ) -> None:
        """Test that react loop returns early abort when step fails with abort_on_error."""
        # Given: next action with step
        next_action = NextActionDTO(
            done=False,
            step=execution_step,
            reasoning="Execute step",
        )
        mock_generate_next_action_usecase.execute.return_value = next_action

        # Given: step execution fails
        step_result = StepExecutionDTO(
            success=False,
            result=None,
            error="File not found",
        )
        mock_step_execution_service.execute.return_value = step_result

        operations = Operations()
        artifacts = Artifacts()
        observation_history = ObservationHistories()
        reasoning_log = ReasoningLogs()
        constraints = ExecutionConstraints(abort_on_error=True, max_iterations=5)

        # When: execute react loop
        result = await use_case._execute_react_loop(
            task="test task",
            context="test context",
            operations=operations,
            artifacts=artifacts,
            observation_history=observation_history,
            reasoning_log=reasoning_log,
            constraints=constraints,
            enable_write=True,
            max_iterations=5,
        )

        # Then: early abort result returned
        assert result is not None
        assert result.success is False
        assert "Iteration" in result.error


class TestExecute:
    """Tests for main execute method."""

    @pytest.mark.asyncio
    async def test_execute_successful_completion(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        execution_constraints: ExecutionConstraints,
        mock_generate_next_action_usecase: AsyncMock,
        mock_log_reasoning_service: MagicMock,
    ) -> None:
        """Test successful task execution."""
        # Given: next action returns done=True immediately
        done_action = NextActionDTO(
            done=True,
            step=None,
            reasoning="Task complete",
        )
        mock_generate_next_action_usecase.execute.return_value = done_action

        # When: execute task
        result = await use_case.execute(
            task="test task",
            context="test context",
            constraints=execution_constraints,
            enable_write=True,
        )

        # Then: success result returned
        assert isinstance(result, type(result))  # AgentResult type check
        assert result.success is True
        assert result.operations is not None
        assert result.artifacts is not None
        assert result.reasoning_log is not None

    @pytest.mark.asyncio
    async def test_execute_with_early_abort_returns_abort_result(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        execution_step: ExecutionStep,
        execution_constraints: ExecutionConstraints,
        mock_generate_next_action_usecase: AsyncMock,
        mock_step_execution_service: AsyncMock,
        mock_log_reasoning_service: MagicMock,
    ) -> None:
        """Test that early abort from react loop returns abort result."""
        # Given: next action with step
        next_action = NextActionDTO(
            done=False,
            step=execution_step,
            reasoning="Execute step",
        )
        mock_generate_next_action_usecase.execute.return_value = next_action

        # Given: step execution fails with abort_on_error=True
        step_result = StepExecutionDTO(
            success=False,
            result=None,
            error="File not found",
        )
        mock_step_execution_service.execute.return_value = step_result

        # When: execute task
        result = await use_case.execute(
            task="test task",
            context="test context",
            constraints=execution_constraints,
            enable_write=True,
        )

        # Then: early abort result returned
        assert result.success is False
        assert "Iteration" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_exception_returns_error_result(
        self,
        use_case: ExecuteTaskIterativeUseCase,
        execution_constraints: ExecutionConstraints,
        mock_generate_next_action_usecase: AsyncMock,
        mock_log_reasoning_service: MagicMock,
    ) -> None:
        """Test that exception is caught and returned as error result."""
        # Given: next action use case raises exception
        mock_generate_next_action_usecase.execute.side_effect = RuntimeError("Test error")

        # When: execute task
        result = await use_case.execute(
            task="test task",
            context="test context",
            constraints=execution_constraints,
            enable_write=True,
        )

        # Then: error result returned
        assert result.success is False
        assert result.error == "Test error"
        # Then: error logged
        mock_log_reasoning_service.log_error.assert_called_once()

