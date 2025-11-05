"""Unit tests for ExecuteTaskUseCase."""

from unittest.mock import AsyncMock, Mock

import pytest
from core.agents_and_tools.agents.application.dtos.plan_dto import PlanDTO
from core.agents_and_tools.agents.application.dtos.step_execution_dto import StepExecutionDTO
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
from core.agents_and_tools.agents.application.usecases.execute_task_usecase import ExecuteTaskUseCase
from core.agents_and_tools.agents.application.usecases.generate_plan_usecase import GeneratePlanUseCase
from core.agents_and_tools.agents.domain.entities import (
    AgentResult,
    Artifact,
    ExecutionConstraints,
    ExecutionStep,
    ReasoningLogs,
)
from core.agents_and_tools.agents.domain.entities.rbac import RoleFactory
from core.agents_and_tools.agents.infrastructure.mappers.artifact_mapper import ArtifactMapper
from core.agents_and_tools.agents.infrastructure.mappers.execution_step_mapper import ExecutionStepMapper
from core.agents_and_tools.common.domain.entities import (
    AgentCapabilities,
    Capability,
    CapabilityCollection,
    ExecutionMode,
    ExecutionModeEnum,
    ToolDefinition,
    ToolRegistry,
)
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort

# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_tool_execution_port():
    """Create mock ToolExecutionPort."""
    port = Mock(spec=ToolExecutionPort)
    # Create mock AgentCapabilities with proper domain entities
    tool_def = ToolDefinition(
        name="files",
        operations={"list_files": {}, "read_file": {}}
    )
    capabilities = [
        Capability(tool="files", operation="list_files"),
        Capability(tool="files", operation="read_file"),
    ]
    port.get_available_tools_description.return_value = AgentCapabilities(
        tools=ToolRegistry.from_definitions([tool_def]),
        mode=ExecutionMode(value=ExecutionModeEnum.FULL),
        operations=CapabilityCollection.from_list(capabilities),
        summary="Mock agent with files tool"
    )
    return port


@pytest.fixture
def mock_step_mapper():
    """Create mock ExecutionStepMapper."""
    return Mock(spec=ExecutionStepMapper)


@pytest.fixture
def mock_artifact_mapper():
    """Create mock ArtifactMapper."""
    mapper = Mock(spec=ArtifactMapper)
    mapper.to_entity_dict.return_value = {}
    return mapper


@pytest.fixture
def mock_generate_plan_usecase():
    """Create mock GeneratePlanUseCase."""
    return AsyncMock(spec=GeneratePlanUseCase)


@pytest.fixture
def create_usecase(
    mock_tool_execution_port,
    mock_step_mapper,
    mock_artifact_mapper,
    mock_generate_plan_usecase,
):
    """Factory to create ExecuteTaskUseCase with mocked dependencies."""
    def _create(agent_id="test-agent", role="developer"):
        # Create Role object from string
        role_obj = RoleFactory.create_role_by_name(role)
        log_reasoning_service = LogReasoningApplicationService(agent_id=agent_id, role=role_obj)
        result_summarization_service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port,
        )
        artifact_collection_service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )
        step_execution_service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=role_obj.allowed_tools,  # RBAC: Use role's allowed tools
        )
        return ExecuteTaskUseCase(
            tool_execution_port=mock_tool_execution_port,
            step_mapper=mock_step_mapper,
            artifact_mapper=mock_artifact_mapper,
            generate_plan_usecase=mock_generate_plan_usecase,
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

class TestExecuteTaskUseCaseConstructor:
    """Test constructor fail-fast validation."""

    def test_rejects_missing_tool_execution_port(
        self, mock_tool_execution_port, mock_step_mapper, mock_artifact_mapper, mock_generate_plan_usecase
    ):
        """Should raise ValueError if tool_execution_port is None."""
        log_service = LogReasoningApplicationService(agent_id="test", role=RoleFactory.create_developer())
        result_summ_service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        artifact_coll_service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )
        step_exec_service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests"}),  # Default for tests
        )
        with pytest.raises(ValueError, match="tool_execution_port is required"):
            ExecuteTaskUseCase(
                tool_execution_port=None,
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_plan_usecase=mock_generate_plan_usecase,
                log_reasoning_service=log_service,
                result_summarization_service=result_summ_service,
                artifact_collection_service=artifact_coll_service,
                step_execution_service=step_exec_service,
                agent_id="test",
            )

    def test_rejects_missing_step_mapper(
        self, mock_tool_execution_port, mock_artifact_mapper, mock_generate_plan_usecase
    ):
        """Should raise ValueError if step_mapper is None."""
        log_service = LogReasoningApplicationService(agent_id="test", role=RoleFactory.create_developer())
        result_summ_service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        artifact_coll_service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )
        step_exec_service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests"}),  # Default for tests
        )
        with pytest.raises(ValueError, match="step_mapper is required"):
            ExecuteTaskUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=None,
                artifact_mapper=mock_artifact_mapper,
                generate_plan_usecase=mock_generate_plan_usecase,
                log_reasoning_service=log_service,
                result_summarization_service=result_summ_service,
                artifact_collection_service=artifact_coll_service,
                step_execution_service=step_exec_service,
                agent_id="test",
            )

    def test_rejects_missing_artifact_mapper(
        self, mock_tool_execution_port, mock_step_mapper, mock_artifact_mapper, mock_generate_plan_usecase
    ):
        """Should raise ValueError if artifact_mapper is None."""
        log_service = LogReasoningApplicationService(agent_id="test", role=RoleFactory.create_developer())
        result_summ_service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        artifact_coll_service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )
        step_exec_service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests"}),  # Default for tests
        )
        with pytest.raises(ValueError, match="artifact_mapper is required"):
            ExecuteTaskUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=mock_step_mapper,
                artifact_mapper=None,
                generate_plan_usecase=mock_generate_plan_usecase,
                log_reasoning_service=log_service,
                result_summarization_service=result_summ_service,
                artifact_collection_service=artifact_coll_service,
                step_execution_service=step_exec_service,
                agent_id="test",
            )

    def test_rejects_missing_generate_plan_usecase(
        self, mock_tool_execution_port, mock_step_mapper, mock_artifact_mapper
    ):
        """Should raise ValueError if generate_plan_usecase is None."""
        log_service = LogReasoningApplicationService(agent_id="test", role=RoleFactory.create_developer())
        result_summ_service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        artifact_coll_service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )
        step_exec_service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests"}),  # Default for tests
        )
        with pytest.raises(ValueError, match="generate_plan_usecase is required"):
            ExecuteTaskUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_plan_usecase=None,
                log_reasoning_service=log_service,
                result_summarization_service=result_summ_service,
                artifact_collection_service=artifact_coll_service,
                step_execution_service=step_exec_service,
                agent_id="test",
            )

    def test_rejects_missing_log_reasoning_service(
        self, mock_tool_execution_port, mock_step_mapper, mock_artifact_mapper, mock_generate_plan_usecase
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
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests"}),  # Default for tests
        )
        with pytest.raises(ValueError, match="log_reasoning_service is required"):
            ExecuteTaskUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_plan_usecase=mock_generate_plan_usecase,
                log_reasoning_service=None,
                result_summarization_service=result_summ_service,
                artifact_collection_service=artifact_coll_service,
                step_execution_service=step_exec_service,
                agent_id="test",
            )

    def test_rejects_missing_result_summarization_service(
        self, mock_tool_execution_port, mock_step_mapper, mock_artifact_mapper, mock_generate_plan_usecase
    ):
        """Should raise ValueError if result_summarization_service is None."""
        log_service = LogReasoningApplicationService(agent_id="test", role=RoleFactory.create_developer())
        artifact_coll_service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )
        step_exec_service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests"}),  # Default for tests
        )
        with pytest.raises(ValueError, match="result_summarization_service is required"):
            ExecuteTaskUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_plan_usecase=mock_generate_plan_usecase,
                log_reasoning_service=log_service,
                result_summarization_service=None,
                artifact_collection_service=artifact_coll_service,
                step_execution_service=step_exec_service,
                agent_id="test",
            )

    def test_rejects_missing_artifact_collection_service(
        self, mock_tool_execution_port, mock_step_mapper, mock_artifact_mapper, mock_generate_plan_usecase
    ):
        """Should raise ValueError if artifact_collection_service is None."""
        log_service = LogReasoningApplicationService(agent_id="test", role=RoleFactory.create_developer())
        result_summ_service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        step_exec_service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests"}),  # Default for tests
        )
        with pytest.raises(ValueError, match="artifact_collection_service is required"):
            ExecuteTaskUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_plan_usecase=mock_generate_plan_usecase,
                log_reasoning_service=log_service,
                result_summarization_service=result_summ_service,
                artifact_collection_service=None,
                step_execution_service=step_exec_service,
                agent_id="test",
            )

    def test_rejects_missing_step_execution_service(
        self, mock_tool_execution_port, mock_step_mapper, mock_artifact_mapper, mock_generate_plan_usecase
    ):
        """Should raise ValueError if step_execution_service is None."""
        log_service = LogReasoningApplicationService(agent_id="test", role=RoleFactory.create_developer())
        result_summ_service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        artifact_coll_service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )
        with pytest.raises(ValueError, match="step_execution_service is required"):
            ExecuteTaskUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_plan_usecase=mock_generate_plan_usecase,
                log_reasoning_service=log_service,
                result_summarization_service=result_summ_service,
                artifact_collection_service=artifact_coll_service,
                step_execution_service=None,
                agent_id="test",
            )

    def test_rejects_missing_agent_id(
        self, mock_tool_execution_port, mock_step_mapper, mock_artifact_mapper, mock_generate_plan_usecase
    ):
        """Should raise ValueError if agent_id is empty."""
        log_service = LogReasoningApplicationService(agent_id="temp", role=RoleFactory.create_developer())
        result_summ_service = ResultSummarizationApplicationService(
            tool_execution_port=mock_tool_execution_port
        )
        artifact_coll_service = ArtifactCollectionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            artifact_mapper=mock_artifact_mapper,
        )
        step_exec_service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=frozenset({"files", "git", "tests"}),  # Default for tests
        )
        with pytest.raises(ValueError, match="agent_id is required"):
            ExecuteTaskUseCase(
                tool_execution_port=mock_tool_execution_port,
                step_mapper=mock_step_mapper,
                artifact_mapper=mock_artifact_mapper,
                generate_plan_usecase=mock_generate_plan_usecase,
                log_reasoning_service=log_service,
                result_summarization_service=result_summ_service,
                artifact_collection_service=artifact_coll_service,
                step_execution_service=step_exec_service,
                agent_id="",
            )

    def test_accepts_all_required_dependencies(self, create_usecase):
        """Should create instance when all dependencies provided."""
        usecase = create_usecase(agent_id="test-agent-123", role="QA")

        assert usecase.agent_id == "test-agent-123"
        assert usecase.role.get_name() == "qa"  # Role is now a value object (lowercase)
        assert usecase.tool_execution_port is not None
        assert usecase.step_mapper is not None
        assert usecase.artifact_mapper is not None
        assert usecase.generate_plan_usecase is not None


# =============================================================================
# Happy Path Tests
# =============================================================================

class TestExecuteTaskUseCaseHappyPath:
    """Test successful task execution scenarios."""

    @pytest.mark.asyncio
    async def test_execute_task_with_single_step_plan(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port
    ):
        """Should execute single-step plan successfully."""
        # Arrange
        step = ExecutionStep(tool="files", operation="list_files", params={"path": "."})
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=[step],
            reasoning="List files in workspace"
        )

        # Mock successful tool execution
        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        # Mock tool for summarization and artifacts
        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Listed 5 files"
        tool_mock.collect_artifacts.return_value = {"files_found": 5}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="List files in workspace",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        assert isinstance(result, AgentResult)
        assert result.success is True
        assert result.operations.count() == 1
        assert result.error is None
        mock_generate_plan_usecase.execute.assert_called_once()
        mock_tool_execution_port.execute_operation.assert_called_once_with(
            tool_name="files",
            operation="list_files",
            params={"path": "."},
            enable_write=True,
        )

    @pytest.mark.asyncio
    async def test_execute_task_with_multi_step_plan(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port
    ):
        """Should execute multi-step plan in order."""
        # Arrange
        steps = [
            ExecutionStep(tool="files", operation="list_files", params={"path": "."}),
            ExecutionStep(tool="files", operation="read_file", params={"path": "test.py"}),
            ExecutionStep(tool="git", operation="status", params={}),
        ]
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=steps,
            reasoning="List, read, check git status"
        )

        # Mock all executions as successful
        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Success"
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Check project status",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        assert result.success is True
        assert result.operations.count() == 3
        assert mock_tool_execution_port.execute_operation.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_task_with_empty_plan(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port
    ):
        """Should handle empty plan gracefully."""
        # Arrange
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=[],
            reasoning="No steps needed"
        )

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Do nothing",
            context="Empty task",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        assert result.success is True  # All operations succeeded (vacuously true)
        assert result.operations.count() == 0
        mock_tool_execution_port.execute_operation.assert_not_called()


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestExecuteTaskUseCaseErrorHandling:
    """Test error handling and failure scenarios."""

    @pytest.mark.asyncio
    async def test_execute_task_with_failed_step_abort_on_error(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port
    ):
        """Should stop execution when step fails and abort_on_error is True."""
        # Arrange
        steps = [
            ExecutionStep(tool="files", operation="read_file", params={"path": "missing.py"}),
            ExecutionStep(tool="files", operation="list_files", params={"path": "."}),
        ]
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=steps,
            reasoning="Read then list"
        )

        # First step fails
        failed_result = Mock(success=False, error="File not found")
        mock_tool_execution_port.execute_operation.return_value = failed_result
        mock_tool_execution_port.get_tool_by_name.return_value = Mock()

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Read missing file",
            context="Python project",
            constraints=ExecutionConstraints(abort_on_error=True),
            enable_write=True,
        )

        # Assert
        assert result.success is False
        assert result.operations.count() == 1  # Only first step executed
        assert "File not found" in result.error
        # Second step should NOT have been called
        assert mock_tool_execution_port.execute_operation.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_task_with_failed_step_continue_on_error(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port
    ):
        """Should continue execution when step fails and abort_on_error is False."""
        # Arrange
        steps = [
            ExecutionStep(tool="files", operation="read_file", params={"path": "missing.py"}),
            ExecutionStep(tool="files", operation="list_files", params={"path": "."}),
        ]
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=steps,
            reasoning="Read then list"
        )

        # First step fails, second succeeds
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
            task="Try to read",
            context="Python project",
            constraints=ExecutionConstraints(abort_on_error=False),
            enable_write=True,
        )

        # Assert
        assert result.success is False  # Overall failed (not all succeeded)
        assert result.operations.count() == 2  # Both steps executed
        assert mock_tool_execution_port.execute_operation.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_task_with_plan_generation_failure(
        self, create_usecase, mock_generate_plan_usecase
    ):
        """Should handle plan generation failure gracefully."""
        # Arrange
        mock_generate_plan_usecase.execute.side_effect = RuntimeError("LLM API error")

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Generate plan",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        assert result.success is False
        assert "LLM API error" in result.error
        assert result.operations.count() == 0

    @pytest.mark.asyncio
    async def test_execute_task_with_tool_execution_exception(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port
    ):
        """Should handle tool execution exceptions gracefully."""
        # Arrange
        step = ExecutionStep(tool="files", operation="list_files", params={"path": "."})
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=[step],
            reasoning="List files"
        )

        # Tool execution raises exception
        mock_tool_execution_port.execute_operation.side_effect = ValueError("Invalid path")
        mock_tool_execution_port.get_tool_by_name.return_value = Mock()

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="List files",
            context="Python project",
            constraints=ExecutionConstraints(abort_on_error=True),
            enable_write=True,
        )

        # Assert
        assert result.success is False
        assert "Invalid path" in result.error

    @pytest.mark.asyncio
    async def test_execute_task_with_fatal_exception(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port
    ):
        """Should handle fatal exceptions and return error result."""
        # Arrange
        step = ExecutionStep(tool="files", operation="list_files", params={"path": "."})
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=[step],
            reasoning="List files"
        )

        # Simulate fatal error during execution
        mock_tool_execution_port.execute_operation.side_effect = Exception("Fatal error")

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="List files",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        assert result.success is False
        assert "Fatal error" in result.error


# =============================================================================
# Constraints Tests
# =============================================================================

class TestExecuteTaskUseCaseConstraints:
    """Test execution constraints enforcement."""

    @pytest.mark.asyncio
    async def test_execute_task_respects_max_operations(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port
    ):
        """Should stop execution when max_operations limit is reached."""
        # Arrange
        steps = [
            ExecutionStep(tool="files", operation="list_files", params={"path": f"dir{i}"})
            for i in range(10)
        ]
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=steps,
            reasoning="List many directories"
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
            task="List directories",
            context="Python project",
            constraints=ExecutionConstraints(max_operations=5),
            enable_write=True,
        )

        # Assert
        assert result.operations.count() == 5  # Stopped at max_operations
        assert mock_tool_execution_port.execute_operation.call_count == 5

    @pytest.mark.asyncio
    async def test_execute_task_respects_abort_on_error_true(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port
    ):
        """Should abort on first error when abort_on_error is True."""
        # Arrange
        steps = [
            ExecutionStep(tool="files", operation="read_file", params={"path": "file1.py"}),
            ExecutionStep(tool="files", operation="read_file", params={"path": "file2.py"}),
        ]
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=steps,
            reasoning="Read files"
        )

        # First fails
        mock_tool_execution_port.execute_operation.side_effect = [
            Mock(success=False, error="File not found"),
        ]
        mock_tool_execution_port.get_tool_by_name.return_value = Mock()

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="Read files",
            context="Python project",
            constraints=ExecutionConstraints(abort_on_error=True),
            enable_write=True,
        )

        # Assert
        assert result.success is False
        assert result.operations.count() == 1
        assert mock_tool_execution_port.execute_operation.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_task_with_enable_write_false(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port
    ):
        """Should pass enable_write=False to tool execution."""
        # Arrange
        step = ExecutionStep(tool="files", operation="list_files", params={"path": "."})
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=[step],
            reasoning="List files (read-only)"
        )

        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Success"
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase()

        # Act
        await usecase.execute(
            task="List files",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=False,  # Read-only mode
        )

        # Assert
        mock_tool_execution_port.execute_operation.assert_called_once_with(
            tool_name="files",
            operation="list_files",
            params={"path": "."},
            enable_write=False,  # Verify read-only passed through
        )


# =============================================================================
# Orchestration Tests
# =============================================================================

class TestExecuteTaskUseCaseOrchestration:
    """Test orchestration logic and dependencies."""

    @pytest.mark.asyncio
    async def test_execute_task_calls_generate_plan_usecase(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port
    ):
        """Should call generate_plan_usecase with correct parameters."""
        # Arrange
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=[],
            reasoning="Empty plan"
        )

        usecase = create_usecase(agent_id="agent-123", role="QA")

        # Act
        await usecase.execute(
            task="Test task",
            context="Test context",
            constraints=ExecutionConstraints(max_operations=10),
            enable_write=True,
        )

        # Assert
        mock_generate_plan_usecase.execute.assert_called_once()
        call_kwargs = mock_generate_plan_usecase.execute.call_args[1]
        assert call_kwargs["task"] == "Test task"
        assert call_kwargs["context"] == "Test context"
        # role is now a Role object
        assert call_kwargs["role"].get_name() == "qa"
        assert isinstance(call_kwargs["constraints"], ExecutionConstraints)

    @pytest.mark.asyncio
    async def test_execute_task_executes_steps_in_order(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port
    ):
        """Should execute steps in the order they appear in plan."""
        # Arrange
        steps = [
            ExecutionStep(tool="files", operation="read_file", params={"path": "a.py"}),
            ExecutionStep(tool="files", operation="read_file", params={"path": "b.py"}),
            ExecutionStep(tool="files", operation="read_file", params={"path": "c.py"}),
        ]
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=steps,
            reasoning="Read files in order"
        )

        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Success"
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase()

        # Act
        await usecase.execute(
            task="Read files",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        calls = mock_tool_execution_port.execute_operation.call_args_list
        assert len(calls) == 3
        assert calls[0][1]["params"]["path"] == "a.py"
        assert calls[1][1]["params"]["path"] == "b.py"
        assert calls[2][1]["params"]["path"] == "c.py"

    @pytest.mark.asyncio
    async def test_execute_task_collects_artifacts(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port, mock_artifact_mapper
    ):
        """Should collect artifacts from successful steps."""
        # Arrange
        step = ExecutionStep(tool="files", operation="list_files", params={"path": "."})
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=[step],
            reasoning="List files"
        )

        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        # Mock artifact collection
        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Listed 3 files"
        tool_mock.collect_artifacts.return_value = {"files_found": 3}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        mock_artifact_mapper.to_entity_dict.return_value = {
            "files_found": Artifact(name="files_found", value=3, artifact_type="count")
        }

        usecase = create_usecase()

        # Act
        result = await usecase.execute(
            task="List files",
            context="Python project",
            constraints=ExecutionConstraints(),
            enable_write=True,
        )

        # Assert
        tool_mock.collect_artifacts.assert_called_once()
        mock_artifact_mapper.to_entity_dict.assert_called_once_with({"files_found": 3})
        assert result.artifacts.count() == 1

    @pytest.mark.asyncio
    async def test_execute_task_populates_reasoning_log(
        self, create_usecase, mock_generate_plan_usecase, mock_tool_execution_port
    ):
        """Should populate reasoning log with thoughts."""
        # Arrange
        step = ExecutionStep(tool="files", operation="list_files", params={"path": "."})
        mock_generate_plan_usecase.execute.return_value = PlanDTO(
            steps=[step],
            reasoning="List workspace files"
        )

        result_entity = Mock(success=True, error=None)
        mock_tool_execution_port.execute_operation.return_value = result_entity

        tool_mock = Mock()
        tool_mock.summarize_result.return_value = "Listed 5 files"
        tool_mock.collect_artifacts.return_value = {}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        usecase = create_usecase(agent_id="agent-456", role="developer")

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

        # Verify reasoning log contains expected thought types
        all_thoughts = result.reasoning_log.get_all()
        thought_types = {t.thought_type for t in all_thoughts}
        assert "analysis" in thought_types  # Initial thought
        assert "decision" in thought_types  # Plan generation
        assert "action" in thought_types    # Step execution
        assert "observation" in thought_types  # Step result
        assert "conclusion" in thought_types  # Final thought


# =============================================================================
# Helper Method Tests
# =============================================================================

class TestExecuteTaskUseCaseHelperMethods:
    """Test helper methods in isolation."""

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
        tool_mock.summarize_result.assert_called_once_with(
            "list_files",
            tool_result,
            {"path": "."}
        )

    def test_collect_artifacts_delegates_to_tool(
        self, create_usecase, mock_tool_execution_port, mock_artifact_mapper
    ):
        """Should delegate artifact collection to tool."""
        # Arrange
        step = ExecutionStep(tool="files", operation="read_file", params={"path": "test.py"})
        step_result = StepExecutionDTO(success=True, result=Mock(), error=None)

        tool_mock = Mock()
        tool_mock.collect_artifacts.return_value = {"file_content": "print('hello')"}
        mock_tool_execution_port.get_tool_by_name.return_value = tool_mock

        mock_artifact_mapper.to_entity_dict.return_value = {
            "file_content": Artifact(name="file_content", value="print('hello')", artifact_type="text")
        }

        usecase = create_usecase()

        # Act
        artifacts = usecase._collect_artifacts(step, step_result)

        # Assert
        tool_mock.collect_artifacts.assert_called_once()
        mock_artifact_mapper.to_entity_dict.assert_called_once_with({"file_content": "print('hello')"})
        assert "file_content" in artifacts

