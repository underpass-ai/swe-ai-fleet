"""Tests for approve_decision handler."""

import pytest
from unittest.mock import AsyncMock, Mock

from planning.domain.value_objects.decision_id import DecisionId
from planning.domain.value_objects.story_id import StoryId
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.approve_decision_handler import approve_decision


@pytest.fixture
def mock_use_case():
    """Create mock ApproveDecisionUseCase."""
    return AsyncMock()


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.mark.asyncio
async def test_approve_decision_success(mock_use_case, mock_context):
    """Test approving decision successfully."""
    # Arrange
    request = planning_pb2.ApproveDecisionRequest(
        story_id="STORY-001",
        decision_id="DEC-001",
        approved_by="test_user",
    )

    # Act
    response = await approve_decision(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert "Decision approved" in response.message
    assert "DEC-001" in response.message
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_approve_decision_validation_error(mock_use_case, mock_context):
    """Test approve with validation error."""
    # Arrange
    mock_use_case.execute.side_effect = ValueError("Invalid decision ID")
    request = planning_pb2.ApproveDecisionRequest(
        story_id="STORY-001",
        decision_id="",
        approved_by="test_user",
    )

    # Act
    response = await approve_decision(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert response.message  # Non-empty error message
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_approve_decision_internal_error(mock_use_case, mock_context):
    """Test approve with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("NATS error")
    request = planning_pb2.ApproveDecisionRequest(
        story_id="STORY-001",
        decision_id="DEC-001",
        approved_by="test_user",
    )

    # Act
    response = await approve_decision(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once()

