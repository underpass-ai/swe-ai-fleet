"""Tests for delete_story handler."""

from unittest.mock import AsyncMock, Mock

import pytest
import grpc
from planning.gen import planning_pb2
from planning.infrastructure.grpc.handlers.delete_story_handler import (
    delete_story_handler,
)


@pytest.fixture
def mock_use_case():
    """Create mock DeleteStoryUseCase."""
    return AsyncMock()


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    return Mock()


@pytest.mark.asyncio
async def test_delete_story_success(mock_use_case, mock_context):
    """Test deleting story successfully."""
    # Arrange
    request = planning_pb2.DeleteStoryRequest(story_id="s-001")

    # Act
    response = await delete_story_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is True
    assert "Story deleted: s-001" in response.message
    mock_use_case.execute.assert_awaited_once()
    mock_context.set_code.assert_not_called()


@pytest.mark.asyncio
async def test_delete_story_empty_id(mock_use_case, mock_context):
    """Test deleting story with empty ID."""
    # Arrange
    request = planning_pb2.DeleteStoryRequest(story_id="")

    # Act
    response = await delete_story_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "story_id is required" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
    mock_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_story_validation_error(mock_use_case, mock_context):
    """Test deleting story with validation error."""
    # Arrange
    mock_use_case.execute.side_effect = ValueError("story_id cannot be empty")
    request = planning_pb2.DeleteStoryRequest(story_id="s-001")

    # Act
    response = await delete_story_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "story_id cannot be empty" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)


@pytest.mark.asyncio
async def test_delete_story_internal_error(mock_use_case, mock_context):
    """Test delete story with internal error."""
    # Arrange
    mock_use_case.execute.side_effect = Exception("Database error")
    request = planning_pb2.DeleteStoryRequest(story_id="s-001")

    # Act
    response = await delete_story_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "Internal error" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)


@pytest.mark.asyncio
async def test_delete_story_missing_story_id_field(mock_use_case, mock_context):
    """Test delete story with missing story_id field in request."""
    # Arrange
    request = planning_pb2.DeleteStoryRequest()
    # story_id is empty string by default

    # Act
    response = await delete_story_handler(request, mock_context, mock_use_case)

    # Assert
    assert response.success is False
    assert "story_id is required" in response.message
    mock_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
    mock_use_case.execute.assert_not_awaited()
