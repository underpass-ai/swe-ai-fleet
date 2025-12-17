"""Unit tests for Neo4jTaskDecisionMetadataQueryAdapter.

Tests the adapter in isolation with mocked Neo4jQueryStore and mapper.
"""

from unittest.mock import Mock

import pytest
from core.context.adapters.neo4j_task_decision_metadata_query_adapter import (
    Neo4jTaskDecisionMetadataQueryAdapter,
)
from core.context.domain.neo4j_queries import Neo4jQuery
from core.context.domain.task_decision_metadata import TaskDecisionMetadata


@pytest.mark.asyncio
async def test_returns_metadata_when_found() -> None:
    """Test successful retrieval of decision metadata from Neo4j using mapper."""
    # Arrange
    task_id = "task-123"
    neo4j_record = {
        "decided_by": "ARCHITECT",
        "decision_reason": "Need to refactor authentication",
        "council_feedback": "Critical security concern",
        "decided_at": "2025-12-03T10:00:00Z",
        "source": "BACKLOG_REVIEW",
    }
    mock_query_store = Mock()
    mock_query_store.query.return_value = [neo4j_record]

    adapter = Neo4jTaskDecisionMetadataQueryAdapter(neo4j_query_store=mock_query_store)

    # Act
    result = await adapter.get_task_decision_metadata(task_id)

    # Assert
    assert result is not None
    assert isinstance(result, TaskDecisionMetadata)
    assert result.decided_by == "ARCHITECT"
    assert result.decision_reason == "Need to refactor authentication"
    assert result.council_feedback == "Critical security concern"
    assert result.decided_at == "2025-12-03T10:00:00Z"
    assert result.source == "BACKLOG_REVIEW"

    # Verify Neo4j query was called correctly with enum
    mock_query_store.query.assert_called_once()
    call_args = mock_query_store.query.call_args
    assert call_args[0][0] == Neo4jQuery.GET_TASK_DECISION_METADATA.value
    assert call_args[0][1] == {"task_id": task_id}


@pytest.mark.asyncio
async def test_returns_none_when_no_results() -> None:
    """Test that None is returned when no decision metadata exists."""
    # Arrange
    task_id = "task-456"
    mock_query_store = Mock()
    mock_query_store.query.return_value = []

    adapter = Neo4jTaskDecisionMetadataQueryAdapter(neo4j_query_store=mock_query_store)

    # Act
    result = await adapter.get_task_decision_metadata(task_id)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_results_is_none() -> None:
    """Test that None is returned when query returns None."""
    # Arrange
    task_id = "task-789"
    mock_query_store = Mock()
    mock_query_store.query.return_value = None

    adapter = Neo4jTaskDecisionMetadataQueryAdapter(neo4j_query_store=mock_query_store)

    # Act
    result = await adapter.get_task_decision_metadata(task_id)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_handles_missing_fields_with_defaults() -> None:
    """Test that missing fields are handled with defensive defaults."""
    # Arrange
    task_id = "task-incomplete"
    mock_query_store = Mock()
    mock_query_store.query.return_value = [
        {
            # Only partial data
            "decided_by": "QA",
        }
    ]

    adapter = Neo4jTaskDecisionMetadataQueryAdapter(neo4j_query_store=mock_query_store)

    # Act
    result = await adapter.get_task_decision_metadata(task_id)

    # Assert
    assert result is not None
    assert result.decided_by == "QA"
    assert result.decision_reason == "No reason provided"
    assert result.council_feedback == "No feedback available"
    assert result.decided_at == "UNKNOWN"
    assert result.source == "UNKNOWN"


@pytest.mark.asyncio
async def test_propagates_neo4j_exceptions() -> None:
    """Test that Neo4j exceptions are propagated to caller."""
    # Arrange
    task_id = "task-error"
    mock_query_store = Mock()
    mock_query_store.query.side_effect = Exception("Neo4j connection timeout")

    adapter = Neo4jTaskDecisionMetadataQueryAdapter(neo4j_query_store=mock_query_store)

    # Act & Assert
    with pytest.raises(Exception, match="Neo4j connection timeout"):
        await adapter.get_task_decision_metadata(task_id)


@pytest.mark.asyncio
async def test_uses_limit_1_in_query() -> None:
    """Test that query includes LIMIT 1 for performance."""
    # Arrange
    task_id = "task-limit"
    mock_query_store = Mock()
    mock_query_store.query.return_value = [
        {
            "decided_by": "DEVOPS",
            "decision_reason": "Reason",
            "council_feedback": "Feedback",
            "decided_at": "2025-12-03T10:00:00Z",
            "source": "PLANNING_MEETING",
        }
    ]

    adapter = Neo4jTaskDecisionMetadataQueryAdapter(neo4j_query_store=mock_query_store)

    # Act
    await adapter.get_task_decision_metadata(task_id)

    # Assert - verify LIMIT 1 is in query
    call_args = mock_query_store.query.call_args
    query = call_args[0][0]
    assert "LIMIT 1" in query


@pytest.mark.asyncio
async def test_uses_query_enum() -> None:
    """Test that adapter uses Neo4jQuery enum for query."""
    # Arrange
    task_id = "task-enum"
    mock_query_store = Mock()
    mock_query_store.query.return_value = [
        {
            "decided_by": "ARCHITECT",
            "decision_reason": "Security refactor needed",
            "council_feedback": "All councils agree",
            "decided_at": "2025-12-03T10:00:00Z",
            "source": "BACKLOG_REVIEW",
        }
    ]

    adapter = Neo4jTaskDecisionMetadataQueryAdapter(neo4j_query_store=mock_query_store)

    # Act
    await adapter.get_task_decision_metadata(task_id)

    # Assert - verify query uses enum
    call_args = mock_query_store.query.call_args
    query_used = call_args[0][0]
    assert query_used == Neo4jQuery.GET_TASK_DECISION_METADATA.value
    # Verify enum query contains expected Cypher structure
    assert "MATCH (p:Plan)-[ht:HAS_TASK]->(t:Task" in Neo4jQuery.GET_TASK_DECISION_METADATA.value
    assert "ht.decided_by" in Neo4jQuery.GET_TASK_DECISION_METADATA.value

