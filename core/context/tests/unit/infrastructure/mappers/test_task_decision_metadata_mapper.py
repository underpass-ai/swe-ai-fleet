"""Unit tests for TaskDecisionMetadataMapper.

Tests the mapper in isolation following hexagonal architecture testing principles.
"""

import pytest
from core.context.domain.task_decision_metadata import TaskDecisionMetadata
from core.context.infrastructure.mappers.task_decision_metadata_mapper import (
    TaskDecisionMetadataMapper,
)


def test_from_neo4j_record_with_complete_data() -> None:
    """Test mapping from complete Neo4j record."""
    # Arrange
    record = {
        "decided_by": "ARCHITECT",
        "decision_reason": "Need to refactor authentication module",
        "council_feedback": "Council analysis shows critical security concerns",
        "decided_at": "2025-12-03T10:00:00Z",
        "source": "BACKLOG_REVIEW",
    }

    # Act
    result = TaskDecisionMetadataMapper.from_neo4j_record(record)

    # Assert
    assert isinstance(result, TaskDecisionMetadata)
    assert result.decided_by == "ARCHITECT"
    assert result.decision_reason == "Need to refactor authentication module"
    assert result.council_feedback == "Council analysis shows critical security concerns"
    assert result.decided_at == "2025-12-03T10:00:00Z"
    assert result.source == "BACKLOG_REVIEW"


def test_from_neo4j_record_with_partial_data_uses_defaults() -> None:
    """Test that missing fields are filled with defensive defaults."""
    # Arrange - only decided_by provided
    record = {
        "decided_by": "QA",
    }

    # Act
    result = TaskDecisionMetadataMapper.from_neo4j_record(record)

    # Assert
    assert result.decided_by == "QA"
    assert result.decision_reason == "No reason provided"
    assert result.council_feedback == "No feedback available"
    assert result.decided_at == "UNKNOWN"
    assert result.source == "UNKNOWN"


def test_from_neo4j_record_with_empty_record_uses_defaults() -> None:
    """Test that empty record uses all defaults."""
    # Arrange
    record = {}

    # Act
    result = TaskDecisionMetadataMapper.from_neo4j_record(record)

    # Assert
    assert result.decided_by == "UNKNOWN"
    assert result.decision_reason == "No reason provided"
    assert result.council_feedback == "No feedback available"
    assert result.decided_at == "UNKNOWN"
    assert result.source == "UNKNOWN"


def test_from_neo4j_record_with_all_councils() -> None:
    """Test mapping works for all valid council types."""
    councils = ["ARCHITECT", "QA", "DEVOPS"]

    for council in councils:
        # Arrange
        record = {
            "decided_by": council,
            "decision_reason": f"{council} decision",
            "council_feedback": f"{council} feedback",
            "decided_at": "2025-12-03T10:00:00Z",
            "source": "PLANNING_MEETING",
        }

        # Act
        result = TaskDecisionMetadataMapper.from_neo4j_record(record)

        # Assert
        assert result.decided_by == council


def test_from_neo4j_record_with_all_valid_sources() -> None:
    """Test mapping works for all valid source types."""
    valid_sources = ["BACKLOG_REVIEW", "PLANNING_MEETING", "UNKNOWN"]

    for source in valid_sources:
        # Arrange
        record = {
            "decided_by": "ARCHITECT",
            "decision_reason": "Test reason",
            "council_feedback": "Test feedback",
            "decided_at": "2025-12-03T10:00:00Z",
            "source": source,
        }

        # Act
        result = TaskDecisionMetadataMapper.from_neo4j_record(record)

        # Assert
        assert result.source == source


def test_from_neo4j_record_raises_on_invalid_source() -> None:
    """Test that invalid source raises ValueError from domain validation."""
    # Arrange
    record = {
        "decided_by": "ARCHITECT",
        "decision_reason": "Test reason",
        "council_feedback": "Test feedback",
        "decided_at": "2025-12-03T10:00:00Z",
        "source": "INVALID_SOURCE",
    }

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid source"):
        TaskDecisionMetadataMapper.from_neo4j_record(record)


def test_mapper_is_stateless() -> None:
    """Test that mapper does not maintain state between calls."""
    # Arrange
    record1 = {
        "decided_by": "ARCHITECT",
        "decision_reason": "Reason 1",
        "council_feedback": "Feedback 1",
        "decided_at": "2025-12-03T10:00:00Z",
        "source": "BACKLOG_REVIEW",
    }
    record2 = {
        "decided_by": "QA",
        "decision_reason": "Reason 2",
        "council_feedback": "Feedback 2",
        "decided_at": "2025-12-03T11:00:00Z",
        "source": "PLANNING_MEETING",
    }

    # Act
    result1 = TaskDecisionMetadataMapper.from_neo4j_record(record1)
    result2 = TaskDecisionMetadataMapper.from_neo4j_record(record2)

    # Assert - results are independent
    assert result1.decided_by == "ARCHITECT"
    assert result2.decided_by == "QA"
    assert result1.decision_reason != result2.decision_reason
    assert result1 != result2

