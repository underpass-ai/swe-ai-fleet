"""Unit tests for GetTaskDecisionMetadataUseCase.

Tests the use case in isolation with mocked port.
Following hexagonal architecture testing principles.
"""

from unittest.mock import AsyncMock

import pytest
from core.context.application.usecases.get_task_decision_metadata import (
    GetTaskDecisionMetadataUseCase,
)
from core.context.domain.task_decision_metadata import TaskDecisionMetadata


@pytest.mark.asyncio
async def test_execute_returns_metadata_when_found() -> None:
    """Test successful retrieval of task decision metadata."""
    # Arrange
    task_id = "task-123"
    expected_metadata = TaskDecisionMetadata(
        decided_by="ARCHITECT",
        decision_reason="Need to refactor authentication module for better security",
        council_feedback="Council agreed this is critical for security compliance",
        decided_at="2025-12-03T10:00:00Z",
        source="BACKLOG_REVIEW",
    )

    mock_port = AsyncMock()
    mock_port.get_task_decision_metadata.return_value = expected_metadata

    use_case = GetTaskDecisionMetadataUseCase(query_port=mock_port)

    # Act
    result = await use_case.execute(task_id)

    # Assert
    assert result == expected_metadata
    mock_port.get_task_decision_metadata.assert_awaited_once_with(task_id)


@pytest.mark.asyncio
async def test_execute_returns_none_when_not_found() -> None:
    """Test that None is returned when task has no decision metadata."""
    # Arrange
    task_id = "task-456"

    mock_port = AsyncMock()
    mock_port.get_task_decision_metadata.return_value = None

    use_case = GetTaskDecisionMetadataUseCase(query_port=mock_port)

    # Act
    result = await use_case.execute(task_id)

    # Assert
    assert result is None
    mock_port.get_task_decision_metadata.assert_awaited_once_with(task_id)


@pytest.mark.asyncio
async def test_execute_raises_on_empty_task_id() -> None:
    """Test that empty task_id raises ValueError (fail-fast)."""
    # Arrange
    mock_port = AsyncMock()
    use_case = GetTaskDecisionMetadataUseCase(query_port=mock_port)

    # Act & Assert - empty string
    with pytest.raises(ValueError, match="task_id is required and cannot be empty"):
        await use_case.execute("")

    # Act & Assert - whitespace only
    with pytest.raises(ValueError, match="task_id is required and cannot be empty"):
        await use_case.execute("   ")

    # Verify port was never called
    mock_port.get_task_decision_metadata.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_propagates_adapter_exceptions() -> None:
    """Test that exceptions from adapter are propagated to caller."""
    # Arrange
    task_id = "task-789"

    mock_port = AsyncMock()
    mock_port.get_task_decision_metadata.side_effect = Exception("Neo4j connection failed")

    use_case = GetTaskDecisionMetadataUseCase(query_port=mock_port)

    # Act & Assert
    with pytest.raises(Exception, match="Neo4j connection failed"):
        await use_case.execute(task_id)


@pytest.mark.asyncio
async def test_execute_with_different_councils() -> None:
    """Test retrieval works for different council types."""
    # Arrange
    councils = ["ARCHITECT", "QA", "DEVOPS"]
    task_id = "task-multi"

    mock_port = AsyncMock()
    use_case = GetTaskDecisionMetadataUseCase(query_port=mock_port)

    for council in councils:
        metadata = TaskDecisionMetadata(
            decided_by=council,
            decision_reason=f"{council} council decision",
            council_feedback=f"{council} council feedback",
            decided_at="2025-12-03T10:00:00Z",
            source="PLANNING_MEETING",
        )
        mock_port.get_task_decision_metadata.return_value = metadata

        # Act
        result = await use_case.execute(task_id)

        # Assert
        assert result is not None
        assert result.decided_by == council

