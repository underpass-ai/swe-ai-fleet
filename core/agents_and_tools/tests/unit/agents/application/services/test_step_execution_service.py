"""Unit tests for StepExecutionApplicationService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.agents_and_tools.agents.application.dtos.step_execution_dto import StepExecutionDTO
from core.agents_and_tools.agents.application.services.step_execution_service import (
    StepExecutionApplicationService,
)
from core.agents_and_tools.agents.domain.entities.core.execution_step import ExecutionStep
from core.agents_and_tools.agents.domain.entities.results.file_execution_result import (
    FileExecutionResult,
)
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort


@pytest.fixture
def mock_tool_execution_port() -> MagicMock:
    """Create mock ToolExecutionPort."""
    return MagicMock(spec=ToolExecutionPort)


@pytest.fixture
def allowed_tools() -> frozenset[str]:
    """Create allowed tools set."""
    return frozenset(["files", "git", "tests"])


@pytest.fixture
def step_execution_service(
    mock_tool_execution_port: MagicMock, allowed_tools: frozenset[str]
) -> StepExecutionApplicationService:
    """Create StepExecutionApplicationService instance."""
    return StepExecutionApplicationService(
        tool_execution_port=mock_tool_execution_port,
        allowed_tools=allowed_tools,
    )


@pytest.fixture
def execution_step() -> ExecutionStep:
    """Create valid execution step."""
    return ExecutionStep(
        tool="files",
        operation="read_file",
        params={"path": "test.py"},
    )


class TestStepExecutionServiceInitialization:
    """Tests for service initialization."""

    def test_init_with_valid_params(
        self, mock_tool_execution_port: MagicMock, allowed_tools: frozenset[str]
    ) -> None:
        """Test initialization with valid parameters."""
        service = StepExecutionApplicationService(
            tool_execution_port=mock_tool_execution_port,
            allowed_tools=allowed_tools,
        )
        assert service.tool_execution_port == mock_tool_execution_port
        assert service.allowed_tools == allowed_tools

    def test_init_with_none_tool_execution_port_raises_error(
        self, allowed_tools: frozenset[str]
    ) -> None:
        """Test that None tool_execution_port raises ValueError."""
        with pytest.raises(ValueError, match="tool_execution_port is required"):
            StepExecutionApplicationService(
                tool_execution_port=None,  # type: ignore[arg-type]
                allowed_tools=allowed_tools,
            )

    def test_init_with_empty_allowed_tools_raises_error(
        self, mock_tool_execution_port: MagicMock
    ) -> None:
        """Test that empty allowed_tools raises ValueError."""
        with pytest.raises(ValueError, match="allowed_tools is required"):
            StepExecutionApplicationService(
                tool_execution_port=mock_tool_execution_port,
                allowed_tools=frozenset(),
            )


class TestStepExecutionServiceRBAC:
    """Tests for RBAC enforcement."""

    @pytest.mark.asyncio
    async def test_execute_with_disallowed_tool_returns_error(
        self,
        step_execution_service: StepExecutionApplicationService,
        execution_step: ExecutionStep,
    ) -> None:
        """Test that disallowed tool returns RBAC violation error."""
        # Given: step with disallowed tool
        step = ExecutionStep(
            tool="docker",  # Not in allowed_tools
            operation="build",
            params={},
        )

        # When: execute step
        result = await step_execution_service.execute(step)

        # Then: RBAC violation error returned
        assert result.success is False
        assert result.result is None
        assert result.error is not None
        assert "RBAC Violation" in result.error
        assert "docker" in result.error
        assert "files" in result.error or "git" in result.error  # Allowed tools listed

        # Then: tool execution port not called
        step_execution_service.tool_execution_port.execute_operation.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_with_allowed_tool_proceeds(
        self,
        step_execution_service: StepExecutionApplicationService,
        execution_step: ExecutionStep,
        mock_tool_execution_port: MagicMock,
    ) -> None:
        """Test that allowed tool proceeds to execution."""
        # Given: successful tool execution
        mock_result = FileExecutionResult(
            success=True,
            content="file content",
            error=None,
        )
        mock_tool_execution_port.execute_operation.return_value = mock_result

        # When: execute step with allowed tool
        result = await step_execution_service.execute(execution_step)

        # Then: tool execution port called
        mock_tool_execution_port.execute_operation.assert_called_once_with(
            tool_name="files",
            operation="read_file",
            params={"path": "test.py"},
            enable_write=True,
        )

        # Then: success result returned
        assert result.success is True
        assert result.result == mock_result
        assert result.error is None


class TestStepExecutionServiceSuccess:
    """Tests for successful execution."""

    @pytest.mark.asyncio
    async def test_execute_success_returns_success_dto(
        self,
        step_execution_service: StepExecutionApplicationService,
        execution_step: ExecutionStep,
        mock_tool_execution_port: MagicMock,
    ) -> None:
        """Test successful execution returns success DTO."""
        # Given: successful tool execution
        mock_result = FileExecutionResult(
            success=True,
            content="file content",
            error=None,
        )
        mock_tool_execution_port.execute_operation.return_value = mock_result

        # When: execute step
        result = await step_execution_service.execute(execution_step)

        # Then: success DTO returned
        assert isinstance(result, StepExecutionDTO)
        assert result.success is True
        assert result.result == mock_result
        assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_with_enable_write_false_passes_to_port(
        self,
        step_execution_service: StepExecutionApplicationService,
        execution_step: ExecutionStep,
        mock_tool_execution_port: MagicMock,
    ) -> None:
        """Test that enable_write parameter is passed to port."""
        # Given: successful tool execution
        mock_result = FileExecutionResult(
            success=True,
            content="file content",
            error=None,
        )
        mock_tool_execution_port.execute_operation.return_value = mock_result

        # When: execute with enable_write=False
        await step_execution_service.execute(execution_step, enable_write=False)

        # Then: enable_write=False passed to port
        mock_tool_execution_port.execute_operation.assert_called_once_with(
            tool_name="files",
            operation="read_file",
            params={"path": "test.py"},
            enable_write=False,
        )

    @pytest.mark.asyncio
    async def test_execute_with_empty_params_uses_empty_dict(
        self,
        step_execution_service: StepExecutionApplicationService,
        mock_tool_execution_port: MagicMock,
    ) -> None:
        """Test that None params are converted to empty dict."""
        # Given: step with None params
        step = ExecutionStep(
            tool="files",
            operation="list_files",
            params=None,
        )
        mock_result = FileExecutionResult(
            success=True,
            content="",
            error=None,
        )
        mock_tool_execution_port.execute_operation.return_value = mock_result

        # When: execute step
        await step_execution_service.execute(step)

        # Then: empty dict passed to port
        mock_tool_execution_port.execute_operation.assert_called_once_with(
            tool_name="files",
            operation="list_files",
            params={},
            enable_write=True,
        )


class TestStepExecutionServiceErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_execute_with_tool_error_returns_error_dto(
        self,
        step_execution_service: StepExecutionApplicationService,
        execution_step: ExecutionStep,
        mock_tool_execution_port: MagicMock,
    ) -> None:
        """Test that tool execution error returns error DTO."""
        # Given: tool execution returns error
        mock_result = FileExecutionResult(
            success=False,
            content=None,
            error="File not found",
        )
        mock_tool_execution_port.execute_operation.return_value = mock_result

        # When: execute step
        result = await step_execution_service.execute(execution_step)

        # Then: error DTO returned
        assert result.success is False
        assert result.result == mock_result
        assert result.error == "File not found"

    @pytest.mark.asyncio
    async def test_execute_with_unknown_error_normalizes_to_unknown_error(
        self,
        step_execution_service: StepExecutionApplicationService,
        execution_step: ExecutionStep,
        mock_tool_execution_port: MagicMock,
    ) -> None:
        """Test that result with success=False but no error gets normalized."""
        # Given: tool execution returns failure without error message
        mock_result = FileExecutionResult(
            success=False,
            content=None,
            error=None,  # No error message
        )
        mock_tool_execution_port.execute_operation.return_value = mock_result

        # When: execute step
        result = await step_execution_service.execute(execution_step)

        # Then: error normalized to "Unknown error"
        assert result.success is False
        assert result.result == mock_result
        assert result.error == "Unknown error"

    @pytest.mark.asyncio
    async def test_execute_with_value_error_returns_error_dto(
        self,
        step_execution_service: StepExecutionApplicationService,
        execution_step: ExecutionStep,
        mock_tool_execution_port: MagicMock,
    ) -> None:
        """Test that ValueError from port is caught and returned as error DTO."""
        # Given: port raises ValueError
        mock_tool_execution_port.execute_operation.side_effect = ValueError(
            "Invalid operation"
        )

        # When: execute step
        result = await step_execution_service.execute(execution_step)

        # Then: error DTO returned with ValueError message
        assert result.success is False
        assert result.result is None
        assert result.error == "Invalid operation"

    @pytest.mark.asyncio
    async def test_execute_with_unexpected_exception_returns_error_dto(
        self,
        step_execution_service: StepExecutionApplicationService,
        execution_step: ExecutionStep,
        mock_tool_execution_port: MagicMock,
    ) -> None:
        """Test that unexpected exception is caught and returned as error DTO."""
        # Given: port raises unexpected exception
        mock_tool_execution_port.execute_operation.side_effect = RuntimeError(
            "Unexpected error"
        )

        # When: execute step
        result = await step_execution_service.execute(execution_step)

        # Then: error DTO returned with exception message
        assert result.success is False
        assert result.result is None
        assert result.error == "Unexpected error"

