"""Unit tests for TaskDecisionMetadata domain value object.

Tests immutability, validation, and formatting.
"""

import pytest
from core.context.domain.task_decision_metadata import TaskDecisionMetadata


def test_create_valid_metadata() -> None:
    """Test creating valid TaskDecisionMetadata."""
    # Arrange & Act
    metadata = TaskDecisionMetadata(
        decided_by="ARCHITECT",
        decision_reason="Need to refactor authentication module",
        council_feedback="Council analysis shows critical security concerns",
        decided_at="2025-12-03T10:00:00Z",
        source="BACKLOG_REVIEW",
    )

    # Assert
    assert metadata.decided_by == "ARCHITECT"
    assert metadata.decision_reason == "Need to refactor authentication module"
    assert metadata.council_feedback == "Council analysis shows critical security concerns"
    assert metadata.decided_at == "2025-12-03T10:00:00Z"
    assert metadata.source == "BACKLOG_REVIEW"


def test_metadata_is_immutable() -> None:
    """Test that TaskDecisionMetadata is frozen (immutable)."""
    # Arrange
    metadata = TaskDecisionMetadata(
        decided_by="QA",
        decision_reason="Test reason",
        council_feedback="Test feedback",
        decided_at="2025-12-03T10:00:00Z",
        source="PLANNING_MEETING",
    )

    # Act & Assert
    with pytest.raises(Exception):  # FrozenInstanceError in Python 3.10+
        metadata.decided_by = "DEVOPS"  # type: ignore


def test_rejects_empty_decided_by() -> None:
    """Test that empty decided_by raises ValueError (fail-fast)."""
    # Act & Assert - empty string
    with pytest.raises(ValueError, match="decided_by cannot be empty"):
        TaskDecisionMetadata(
            decided_by="",
            decision_reason="Test reason",
            council_feedback="Test feedback",
            decided_at="2025-12-03T10:00:00Z",
            source="BACKLOG_REVIEW",
        )

    # Act & Assert - whitespace only
    with pytest.raises(ValueError, match="decided_by cannot be empty"):
        TaskDecisionMetadata(
            decided_by="   ",
            decision_reason="Test reason",
            council_feedback="Test feedback",
            decided_at="2025-12-03T10:00:00Z",
            source="BACKLOG_REVIEW",
        )


def test_rejects_empty_decision_reason() -> None:
    """Test that empty decision_reason raises ValueError (fail-fast)."""
    # Act & Assert
    with pytest.raises(ValueError, match="decision_reason cannot be empty"):
        TaskDecisionMetadata(
            decided_by="ARCHITECT",
            decision_reason="",
            council_feedback="Test feedback",
            decided_at="2025-12-03T10:00:00Z",
            source="BACKLOG_REVIEW",
        )


def test_rejects_empty_council_feedback() -> None:
    """Test that empty council_feedback raises ValueError (fail-fast)."""
    # Act & Assert
    with pytest.raises(ValueError, match="council_feedback cannot be empty"):
        TaskDecisionMetadata(
            decided_by="ARCHITECT",
            decision_reason="Test reason",
            council_feedback="",
            decided_at="2025-12-03T10:00:00Z",
            source="BACKLOG_REVIEW",
        )


def test_rejects_empty_decided_at() -> None:
    """Test that empty decided_at raises ValueError (fail-fast)."""
    # Act & Assert
    with pytest.raises(ValueError, match="decided_at cannot be empty"):
        TaskDecisionMetadata(
            decided_by="ARCHITECT",
            decision_reason="Test reason",
            council_feedback="Test feedback",
            decided_at="",
            source="BACKLOG_REVIEW",
        )


def test_rejects_invalid_source() -> None:
    """Test that invalid source raises ValueError (fail-fast)."""
    # Act & Assert
    with pytest.raises(ValueError, match="Invalid source"):
        TaskDecisionMetadata(
            decided_by="ARCHITECT",
            decision_reason="Test reason",
            council_feedback="Test feedback",
            decided_at="2025-12-03T10:00:00Z",
            source="INVALID_SOURCE",
        )


def test_accepts_valid_sources() -> None:
    """Test that all valid sources are accepted."""
    valid_sources = ["BACKLOG_REVIEW", "PLANNING_MEETING", "UNKNOWN"]

    for source in valid_sources:
        metadata = TaskDecisionMetadata(
            decided_by="ARCHITECT",
            decision_reason="Test reason",
            council_feedback="Test feedback",
            decided_at="2025-12-03T10:00:00Z",
            source=source,
        )
        assert metadata.source == source


def test_format_for_llm_contains_all_fields() -> None:
    """Test that format_for_llm includes all metadata fields."""
    # Arrange
    metadata = TaskDecisionMetadata(
        decided_by="ARCHITECT",
        decision_reason="Refactor auth module for better security",
        council_feedback="Critical for compliance requirements",
        decided_at="2025-12-03T10:00:00Z",
        source="BACKLOG_REVIEW",
    )

    # Act
    formatted = metadata.format_for_llm()

    # Assert
    assert "ARCHITECT" in formatted
    assert "Refactor auth module for better security" in formatted
    assert "Critical for compliance requirements" in formatted
    assert "2025-12-03T10:00:00Z" in formatted
    assert "BACKLOG_REVIEW" in formatted.upper()


def test_format_for_llm_has_structure() -> None:
    """Test that format_for_llm produces well-structured output."""
    # Arrange
    metadata = TaskDecisionMetadata(
        decided_by="QA",
        decision_reason="Need integration tests",
        council_feedback="Test coverage gaps identified",
        decided_at="2025-12-03T10:00:00Z",
        source="PLANNING_MEETING",
    )

    # Act
    formatted = metadata.format_for_llm()

    # Assert
    assert "TASK DECISION CONTEXT" in formatted
    assert "DECIDED BY:" in formatted
    assert "DECISION REASON:" in formatted
    assert "FULL COUNCIL ANALYSIS:" in formatted
    assert "SOURCE:" in formatted
    assert "DECIDED AT:" in formatted


def test_two_instances_with_same_values_are_equal() -> None:
    """Test value object equality semantics."""
    # Arrange
    metadata1 = TaskDecisionMetadata(
        decided_by="DEVOPS",
        decision_reason="Test reason",
        council_feedback="Test feedback",
        decided_at="2025-12-03T10:00:00Z",
        source="BACKLOG_REVIEW",
    )
    metadata2 = TaskDecisionMetadata(
        decided_by="DEVOPS",
        decision_reason="Test reason",
        council_feedback="Test feedback",
        decided_at="2025-12-03T10:00:00Z",
        source="BACKLOG_REVIEW",
    )

    # Assert
    assert metadata1 == metadata2
    assert hash(metadata1) == hash(metadata2)

