"""Unit tests for PlanningStoryTransitionedDTO.

Tests DTO validation and immutability.
Following DDD + Hexagonal Architecture principles.
"""

import pytest

from services.workflow.application.dto.planning_event_dto import (
    PlanningStoryTransitionedDTO,
)

# ============================================================================
# Happy Path Tests
# ============================================================================


def test_create_planning_story_transitioned_dto():
    """Test creating valid DTO."""
    dto = PlanningStoryTransitionedDTO(
        story_id="story-123",
        from_state="PLANNED",
        to_state="READY_FOR_EXECUTION",
        tasks=["task-001", "task-002"],
        timestamp="2025-11-06T10:30:00Z",
    )

    assert dto.story_id == "story-123"
    assert dto.from_state == "PLANNED"
    assert dto.to_state == "READY_FOR_EXECUTION"
    assert dto.tasks == ["task-001", "task-002"]
    assert dto.timestamp == "2025-11-06T10:30:00Z"


def test_dto_is_immutable():
    """Test that DTO is immutable (frozen=True)."""
    dto = PlanningStoryTransitionedDTO(
        story_id="story-123",
        from_state="PLANNED",
        to_state="READY_FOR_EXECUTION",
        tasks=["task-001"],
        timestamp="2025-11-06T10:30:00Z",
    )

    # Should raise (frozen dataclass)
    with pytest.raises(AttributeError):
        dto.story_id = "story-456"  # type: ignore


def test_dto_with_empty_tasks_list():
    """Test DTO with empty tasks list (valid)."""
    dto = PlanningStoryTransitionedDTO(
        story_id="story-empty",
        from_state="PLANNED",
        to_state="READY_FOR_EXECUTION",
        tasks=[],  # Empty list OK
        timestamp="2025-11-06T10:30:00Z",
    )

    assert dto.tasks == []
    assert isinstance(dto.tasks, list)


# ============================================================================
# Validation Tests (Fail-Fast)
# ============================================================================


def test_dto_rejects_empty_story_id():
    """Test that empty story_id is rejected."""
    with pytest.raises(ValueError, match="story_id cannot be empty"):
        PlanningStoryTransitionedDTO(
            story_id="",  # Empty!
            from_state="PLANNED",
            to_state="READY_FOR_EXECUTION",
            tasks=["task-001"],
            timestamp="2025-11-06T10:30:00Z",
        )


def test_dto_rejects_empty_to_state():
    """Test that empty to_state is rejected."""
    with pytest.raises(ValueError, match="to_state cannot be empty"):
        PlanningStoryTransitionedDTO(
            story_id="story-123",
            from_state="PLANNED",
            to_state="",  # Empty!
            tasks=["task-001"],
            timestamp="2025-11-06T10:30:00Z",
        )


def test_dto_rejects_non_list_tasks():
    """Test that tasks must be a list."""
    with pytest.raises(ValueError, match="tasks must be a list"):
        PlanningStoryTransitionedDTO(
            story_id="story-123",
            from_state="PLANNED",
            to_state="READY_FOR_EXECUTION",
            tasks="task-001",  # String, not list!
            timestamp="2025-11-06T10:30:00Z",
        )


def test_dto_rejects_empty_timestamp():
    """Test that empty timestamp is rejected."""
    with pytest.raises(ValueError, match="timestamp cannot be empty"):
        PlanningStoryTransitionedDTO(
            story_id="story-123",
            from_state="PLANNED",
            to_state="READY_FOR_EXECUTION",
            tasks=["task-001"],
            timestamp="",  # Empty!
        )

