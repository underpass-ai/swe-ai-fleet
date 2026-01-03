"""Unit tests for PlanningServiceAdapter."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from backlog_review_processor.application.ports.planning_port import (
    AddAgentDeliberationRequest,
    PlanningServiceError,
    TaskCreationRequest,
)
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId


@pytest.fixture
def mock_planning_pb2():
    """Mock planning_pb2 module."""
    with patch("backlog_review_processor.infrastructure.adapters.planning_service_adapter.planning_pb2") as mock:
        # Create mock request and response classes
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.message = "Success"
        mock.AddAgentDeliberationRequest.return_value = mock_request
        mock.AddAgentDeliberationResponse.return_value = mock_response
        yield mock


@pytest.fixture
def mock_planning_pb2_grpc():
    """Mock planning_pb2_grpc module."""
    with patch("backlog_review_processor.infrastructure.adapters.planning_service_adapter.planning_pb2_grpc") as mock:
        # Create mock stub
        mock_stub = AsyncMock()
        mock.PlanningServiceStub.return_value = mock_stub
        yield mock_stub


@pytest.fixture
def mock_grpc_channel():
    """Mock gRPC channel."""
    with patch("backlog_review_processor.infrastructure.adapters.planning_service_adapter.grpc.aio.insecure_channel") as mock:
        mock_channel = AsyncMock()
        mock.return_value = mock_channel
        yield mock_channel


@pytest.fixture
def adapter(mock_planning_pb2, mock_planning_pb2_grpc, mock_grpc_channel):
    """Create PlanningServiceAdapter instance."""
    from backlog_review_processor.infrastructure.adapters.planning_service_adapter import (
        PlanningServiceAdapter,
    )

    return PlanningServiceAdapter(grpc_address="planning:50054", timeout_seconds=30.0)


@pytest.mark.asyncio
async def test_add_agent_deliberation_success_with_dict_proposal(
    adapter: PlanningServiceAdapter,
    mock_planning_pb2_grpc: AsyncMock,
    mock_planning_pb2,
) -> None:
    """Test that add_agent_deliberation successfully calls gRPC with dict proposal."""
    # Arrange
    ceremony_id = BacklogReviewCeremonyId("ceremony-123")
    story_id = StoryId("ST-456")
    proposal_dict = {"content": "Proposal content", "feedback": "Feedback text"}
    reviewed_at = datetime.now(UTC)

    request = AddAgentDeliberationRequest(
        ceremony_id=ceremony_id,
        story_id=story_id,
        role="ARCHITECT",
        agent_id="agent-architect-001",
        feedback="Feedback text",
        proposal=proposal_dict,
        reviewed_at=reviewed_at.isoformat(),
    )

    # Mock successful response
    mock_response = MagicMock()
    mock_response.success = True
    mock_response.message = "Deliberation added"
    mock_planning_pb2_grpc.AddAgentDeliberation.return_value = mock_response

    # Mock the request object to track its attributes
    mock_request = MagicMock()
    mock_planning_pb2.AddAgentDeliberationRequest.return_value = mock_request

    # Act
    await adapter.add_agent_deliberation(request)

    # Assert
    mock_planning_pb2_grpc.AddAgentDeliberation.assert_awaited_once()
    # Verify that AddAgentDeliberationRequest was called with correct parameters
    mock_planning_pb2.AddAgentDeliberationRequest.assert_called_once()
    call_kwargs = mock_planning_pb2.AddAgentDeliberationRequest.call_args[1]
    assert call_kwargs["ceremony_id"] == "ceremony-123"
    assert call_kwargs["story_id"] == "ST-456"
    assert call_kwargs["role"] == "ARCHITECT"
    assert call_kwargs["agent_id"] == "agent-architect-001"
    assert call_kwargs["feedback"] == "Feedback text"
    # Proposal should be serialized to JSON string
    assert call_kwargs["proposal"] == json.dumps(proposal_dict)
    assert call_kwargs["reviewed_at"] == reviewed_at.isoformat()


@pytest.mark.asyncio
async def test_add_agent_deliberation_success_with_string_proposal(
    adapter: PlanningServiceAdapter,
    mock_planning_pb2_grpc: AsyncMock,
    mock_planning_pb2,
) -> None:
    """Test that add_agent_deliberation successfully calls gRPC with string proposal."""
    # Arrange
    ceremony_id = BacklogReviewCeremonyId("ceremony-123")
    story_id = StoryId("ST-456")
    proposal_str = "Simple string proposal"
    reviewed_at = datetime.now(UTC)

    request = AddAgentDeliberationRequest(
        ceremony_id=ceremony_id,
        story_id=story_id,
        role="QA",
        agent_id="agent-qa-001",
        feedback="QA feedback",
        proposal=proposal_str,
        reviewed_at=reviewed_at.isoformat(),
    )

    # Mock successful response
    mock_response = MagicMock()
    mock_response.success = True
    mock_response.message = "Deliberation added"
    mock_planning_pb2_grpc.AddAgentDeliberation.return_value = mock_response

    # Mock the request object
    mock_request = MagicMock()
    mock_planning_pb2.AddAgentDeliberationRequest.return_value = mock_request

    # Act
    await adapter.add_agent_deliberation(request)

    # Assert
    mock_planning_pb2_grpc.AddAgentDeliberation.assert_awaited_once()
    # Verify that AddAgentDeliberationRequest was called with correct proposal
    mock_planning_pb2.AddAgentDeliberationRequest.assert_called_once()
    call_kwargs = mock_planning_pb2.AddAgentDeliberationRequest.call_args[1]
    assert call_kwargs["proposal"] == proposal_str


@pytest.mark.asyncio
async def test_add_agent_deliberation_raises_error_on_unsuccessful_response(
    adapter: PlanningServiceAdapter,
    mock_planning_pb2_grpc: AsyncMock,
) -> None:
    """Test that add_agent_deliberation raises PlanningServiceError on unsuccessful response."""
    # Arrange
    ceremony_id = BacklogReviewCeremonyId("ceremony-123")
    story_id = StoryId("ST-456")

    request = AddAgentDeliberationRequest(
        ceremony_id=ceremony_id,
        story_id=story_id,
        role="DEVOPS",
        agent_id="agent-devops-001",
        feedback="DevOps feedback",
        proposal={"content": "Proposal"},
        reviewed_at=datetime.now(UTC).isoformat(),
    )

    # Mock unsuccessful response
    mock_response = MagicMock()
    mock_response.success = False
    mock_response.message = "Ceremony not found"
    mock_planning_pb2_grpc.AddAgentDeliberation.return_value = mock_response

    # Act & Assert
    with pytest.raises(PlanningServiceError, match="Planning Service returned error"):
        await adapter.add_agent_deliberation(request)


@pytest.mark.asyncio
async def test_add_agent_deliberation_raises_error_on_grpc_error(
    adapter: PlanningServiceAdapter,
    mock_planning_pb2_grpc: AsyncMock,
) -> None:
    """Test that add_agent_deliberation raises PlanningServiceError on gRPC error."""
    # Arrange
    ceremony_id = BacklogReviewCeremonyId("ceremony-123")
    story_id = StoryId("ST-456")

    request = AddAgentDeliberationRequest(
        ceremony_id=ceremony_id,
        story_id=story_id,
        role="ARCHITECT",
        agent_id="agent-architect-001",
        feedback="Feedback",
        proposal={"content": "Proposal"},
        reviewed_at=datetime.now(UTC).isoformat(),
    )

    # Mock gRPC error
    grpc_error = grpc.RpcError()
    grpc_error.code = MagicMock(return_value=grpc.StatusCode.UNAVAILABLE)
    grpc_error.details = MagicMock(return_value="Service unavailable")
    mock_planning_pb2_grpc.AddAgentDeliberation.side_effect = grpc_error

    # Act & Assert
    with pytest.raises(PlanningServiceError, match="gRPC error calling Planning Service"):
        await adapter.add_agent_deliberation(request)


@pytest.mark.asyncio
async def test_add_agent_deliberation_raises_error_on_unexpected_exception(
    adapter: PlanningServiceAdapter,
    mock_planning_pb2_grpc: AsyncMock,
) -> None:
    """Test that add_agent_deliberation raises PlanningServiceError on unexpected exception."""
    # Arrange
    ceremony_id = BacklogReviewCeremonyId("ceremony-123")
    story_id = StoryId("ST-456")

    request = AddAgentDeliberationRequest(
        ceremony_id=ceremony_id,
        story_id=story_id,
        role="QA",
        agent_id="agent-qa-001",
        feedback="Feedback",
        proposal={"content": "Proposal"},
        reviewed_at=datetime.now(UTC).isoformat(),
    )

    # Mock unexpected exception
    mock_planning_pb2_grpc.AddAgentDeliberation.side_effect = ValueError("Unexpected error")

    # Act & Assert
    with pytest.raises(PlanningServiceError, match="Unexpected error calling Planning Service"):
        await adapter.add_agent_deliberation(request)


def test_init_raises_error_on_empty_grpc_address():
    """Test that __init__ raises ValueError on empty grpc_address."""
    from backlog_review_processor.infrastructure.adapters.planning_service_adapter import (
        PlanningServiceAdapter,
    )

    with pytest.raises(ValueError, match="grpc_address cannot be empty"):
        PlanningServiceAdapter(grpc_address="", timeout_seconds=30.0)


def test_init_raises_error_on_whitespace_grpc_address():
    """Test that __init__ raises ValueError on whitespace-only grpc_address."""
    from backlog_review_processor.infrastructure.adapters.planning_service_adapter import (
        PlanningServiceAdapter,
    )

    with pytest.raises(ValueError, match="grpc_address cannot be empty"):
        PlanningServiceAdapter(grpc_address="   ", timeout_seconds=30.0)


def test_init_raises_error_when_protobuf_stubs_unavailable():
    """Test that __init__ raises RuntimeError when protobuf stubs are unavailable."""
    from backlog_review_processor.infrastructure.adapters.planning_service_adapter import (
        PlanningServiceAdapter,
    )

    with patch(
        "backlog_review_processor.infrastructure.adapters.planning_service_adapter.planning_pb2",
        None,
    ):
        with pytest.raises(RuntimeError, match="protobuf stubs not available"):
            PlanningServiceAdapter(grpc_address="planning:50054", timeout_seconds=30.0)


@pytest.mark.asyncio
async def test_close_closes_channel(adapter: PlanningServiceAdapter, mock_grpc_channel):
    """Test that close() closes the gRPC channel."""
    # Act
    await adapter.close()

    # Assert
    mock_grpc_channel.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_handles_none_channel(adapter: PlanningServiceAdapter):
    """Test that close() handles None channel gracefully."""
    # Arrange
    adapter.channel = None

    # Act - Should not raise
    await adapter.close()


@pytest.mark.asyncio
async def test_create_task_success(
    adapter: PlanningServiceAdapter,
    mock_planning_pb2_grpc: AsyncMock,
    mock_planning_pb2,
) -> None:
    """Test that create_task successfully calls gRPC and returns task ID."""
    # Arrange
    story_id = StoryId("ST-456")
    request = TaskCreationRequest(
        story_id=story_id,
        title="Test Task",
        description="Test Description",
        estimated_hours=8,
        deliberation_indices=[0, 1],
        ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
        request_id="test-request-id-123",
    )

    # Mock successful response
    mock_response = MagicMock()
    mock_response.success = True
    mock_response.message = "Task created"
    mock_task = MagicMock()
    mock_task.task_id = "T-789"
    mock_response.task = mock_task
    mock_planning_pb2_grpc.CreateTask.return_value = mock_response

    # Mock the request object
    mock_proto_request = MagicMock()
    mock_planning_pb2.CreateTaskRequest.return_value = mock_proto_request

    # Act
    task_id = await adapter.create_task(request)

    # Assert
    assert task_id == "T-789"
    mock_planning_pb2_grpc.CreateTask.assert_awaited_once()
    mock_planning_pb2.CreateTaskRequest.assert_called_once()
    call_kwargs = mock_planning_pb2.CreateTaskRequest.call_args[1]
    assert call_kwargs["story_id"] == "ST-456"
    assert call_kwargs["title"] == "Test Task"
    assert call_kwargs["description"] == "Test Description"
    assert call_kwargs["type"] == "backlog_review_identified"
    assert call_kwargs["request_id"] == "test-request-id-123"


@pytest.mark.asyncio
async def test_create_task_raises_error_on_unsuccessful_response(
    adapter: PlanningServiceAdapter,
    mock_planning_pb2_grpc: AsyncMock,
    mock_planning_pb2,
) -> None:
    """Test that create_task raises PlanningServiceError on unsuccessful response."""
    # Arrange
    story_id = StoryId("ST-456")
    request = TaskCreationRequest(
        story_id=story_id,
        title="Test Task",
        description="Test Description",
        estimated_hours=8,
        deliberation_indices=[],
        ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
        request_id="test-request-id-456",
    )

    # Mock unsuccessful response
    mock_response = MagicMock()
    mock_response.success = False
    mock_response.message = "Story not found"
    mock_planning_pb2_grpc.CreateTask.return_value = mock_response

    mock_proto_request = MagicMock()
    mock_planning_pb2.CreateTaskRequest.return_value = mock_proto_request

    # Act & Assert
    with pytest.raises(PlanningServiceError, match="Planning Service returned error"):
        await adapter.create_task(request)


@pytest.mark.asyncio
async def test_create_task_raises_error_on_grpc_error(
    adapter: PlanningServiceAdapter,
    mock_planning_pb2_grpc: AsyncMock,
    mock_planning_pb2,
) -> None:
    """Test that create_task raises PlanningServiceError on gRPC error."""
    # Arrange
    story_id = StoryId("ST-456")
    request = TaskCreationRequest(
        story_id=story_id,
        title="Test Task",
        description="Test Description",
        estimated_hours=8,
        deliberation_indices=[],
        ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
        request_id="test-request-id-789",
    )

    # Mock gRPC error
    grpc_error = grpc.RpcError()
    grpc_error.code = MagicMock(return_value=grpc.StatusCode.UNAVAILABLE)
    grpc_error.details = MagicMock(return_value="Service unavailable")
    mock_planning_pb2_grpc.CreateTask.side_effect = grpc_error

    mock_proto_request = MagicMock()
    mock_planning_pb2.CreateTaskRequest.return_value = mock_proto_request

    # Act & Assert
    with pytest.raises(PlanningServiceError, match="gRPC error calling Planning Service"):
        await adapter.create_task(request)


@pytest.mark.asyncio
async def test_create_task_raises_error_on_unexpected_exception(
    adapter: PlanningServiceAdapter,
    mock_planning_pb2_grpc: AsyncMock,
    mock_planning_pb2,
) -> None:
    """Test that create_task raises PlanningServiceError on unexpected exception."""
    # Arrange
    story_id = StoryId("ST-456")
    request = TaskCreationRequest(
        story_id=story_id,
        title="Test Task",
        description="Test Description",
        estimated_hours=8,
        deliberation_indices=[],
        ceremony_id=BacklogReviewCeremonyId("ceremony-123"),
        request_id="test-request-id-999",
    )

    # Mock unexpected exception
    mock_planning_pb2_grpc.CreateTask.side_effect = ValueError("Unexpected error")

    mock_proto_request = MagicMock()
    mock_planning_pb2.CreateTaskRequest.return_value = mock_proto_request

    # Act & Assert
    with pytest.raises(PlanningServiceError, match="Unexpected error calling Planning Service"):
        await adapter.create_task(request)
