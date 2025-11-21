"""Tests for reject_decision handler."""

from unittest.mock import AsyncMock, Mock

import pytest
from planning.gen import planning_pb2

from planning.infrastructure.grpc.handlers.reject_decision_handler import (
    reject_decision_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock RejectDecisionUseCase."""
    return AsyncMock()


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.mark.asyncio
async def test_reject_decision_success(mock_use_case, mock_context):
    """Test rejecting decision successfully."""
    # Arrange
    request = planning_pb2.RejectDecisionRequest(
        story_id="STORY-001",
        decision_id="DEC-001",
        rejected_by="test_user",
        reason="Not feasible",
    )

    # Act
    response = await reject_decision_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert "Decision rejected" in response.message
    assert "DEC-001" in response.message
    mock_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_decision_validation_error(mock_use_case, mock_context):
    """Test reject with validation error."""
    # Arrange
    mock_use_case.execute.side_effect = ValueError("Invalid decision ID")
    request = planning_pb2.RejectDecisionRequest(
        story_id="STORY-001",
        decision_id="",
        rejected_by="test_user",
        reason="Invalid",
    )

    # Act
    response = await reject_decision_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert response.message  # Non-empty error message
    mock_context.set_code.assert_called_once()


@pytest.mark.asyncio
async def test_reject_decision_internal_error(mock_use_case, mock_context):
    """Test reject with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("NATS error")
    request = planning_pb2.RejectDecisionRequest(
        story_id="STORY-001",
        decision_id="DEC-001",
        rejected_by="test_user",
        reason="Error case",
    )

    # Act
    response = await reject_decision_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once()

