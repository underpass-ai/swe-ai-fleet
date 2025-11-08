"""Unit tests for PlanningEventMapper.

Tests event deserialization from NATS messages.
Following DDD + Hexagonal Architecture principles.
"""

import json

import pytest

from services.workflow.application.dto.planning_event_dto import (
    PlanningStoryTransitionedDTO,
)
from services.workflow.infrastructure.mappers.planning_event_mapper import (
    PlanningEventMapper,
)

# ============================================================================
# Happy Path Tests
# ============================================================================


def test_from_nats_message_valid_event():
    """Test deserializing valid NATS message."""
    payload = {
        "story_id": "story-123",
        "from_state": "PLANNED",
        "to_state": "READY_FOR_EXECUTION",
        "tasks": ["task-001", "task-002", "task-003"],
        "timestamp": "2025-11-06T10:30:00Z",
    }

    message_data = json.dumps(payload).encode("utf-8")

    # Act
    dto = PlanningEventMapper.from_nats_message(message_data)

    # Assert
    assert isinstance(dto, PlanningStoryTransitionedDTO)
    assert dto.story_id == "story-123"
    assert dto.from_state == "PLANNED"
    assert dto.to_state == "READY_FOR_EXECUTION"
    assert dto.tasks == ["task-001", "task-002", "task-003"]
    assert dto.timestamp == "2025-11-06T10:30:00Z"


def test_from_nats_message_with_empty_tasks():
    """Test deserializing event with empty tasks list."""
    payload = {
        "story_id": "story-empty",
        "from_state": "PLANNED",
        "to_state": "READY_FOR_EXECUTION",
        "tasks": [],  # Empty list
        "timestamp": "2025-11-06T10:30:00Z",
    }

    message_data = json.dumps(payload).encode("utf-8")

    # Act
    dto = PlanningEventMapper.from_nats_message(message_data)

    # Assert
    assert dto.tasks == []
    assert isinstance(dto.tasks, list)


def test_from_nats_message_with_many_tasks():
    """Test deserializing event with many tasks."""
    tasks_list = [f"task-{i:03d}" for i in range(1, 51)]  # 50 tasks

    payload = {
        "story_id": "story-large",
        "from_state": "PLANNED",
        "to_state": "READY_FOR_EXECUTION",
        "tasks": tasks_list,
        "timestamp": "2025-11-06T10:30:00Z",
    }

    message_data = json.dumps(payload).encode("utf-8")

    # Act
    dto = PlanningEventMapper.from_nats_message(message_data)

    # Assert
    assert len(dto.tasks) == 50
    assert dto.tasks[0] == "task-001"
    assert dto.tasks[49] == "task-050"


# ============================================================================
# Error Handling Tests (Fail-Fast)
# ============================================================================


def test_from_nats_message_missing_field_raises():
    """Test that missing required field raises KeyError."""
    payload = {
        "story_id": "story-123",
        "from_state": "PLANNED",
        # Missing 'to_state'!
        "tasks": ["task-001"],
        "timestamp": "2025-11-06T10:30:00Z",
    }

    message_data = json.dumps(payload).encode("utf-8")

    # Act & Assert
    with pytest.raises(KeyError):
        PlanningEventMapper.from_nats_message(message_data)


def test_from_nats_message_invalid_json_raises():
    """Test that malformed JSON raises JSONDecodeError."""
    message_data = b"{invalid json}"

    # Act & Assert
    with pytest.raises(json.JSONDecodeError):
        PlanningEventMapper.from_nats_message(message_data)


def test_from_nats_message_empty_story_id_raises():
    """Test that DTO validation catches empty story_id."""
    payload = {
        "story_id": "",  # Empty!
        "from_state": "PLANNED",
        "to_state": "READY_FOR_EXECUTION",
        "tasks": ["task-001"],
        "timestamp": "2025-11-06T10:30:00Z",
    }

    message_data = json.dumps(payload).encode("utf-8")

    # Act & Assert: DTO validation should catch this
    with pytest.raises(ValueError, match="story_id cannot be empty"):
        PlanningEventMapper.from_nats_message(message_data)


def test_from_nats_message_tasks_not_list_raises():
    """Test that tasks must be a list (mapper validates)."""
    payload = {
        "story_id": "story-123",
        "from_state": "PLANNED",
        "to_state": "READY_FOR_EXECUTION",
        "tasks": "task-001",  # String, not list!
        "timestamp": "2025-11-06T10:30:00Z",
    }

    message_data = json.dumps(payload).encode("utf-8")

    # Act & Assert: Mapper should catch this before DTO
    with pytest.raises(ValueError, match="Expected tasks to be list"):
        PlanningEventMapper.from_nats_message(message_data)


def test_from_nats_message_empty_to_state_raises():
    """Test that DTO validation catches empty to_state."""
    payload = {
        "story_id": "story-123",
        "from_state": "PLANNED",
        "to_state": "",  # Empty!
        "tasks": ["task-001"],
        "timestamp": "2025-11-06T10:30:00Z",
    }

    message_data = json.dumps(payload).encode("utf-8")

    # Act & Assert: DTO validation should catch this
    with pytest.raises(ValueError, match="to_state cannot be empty"):
        PlanningEventMapper.from_nats_message(message_data)


def test_from_nats_message_empty_timestamp_raises():
    """Test that DTO validation catches empty timestamp."""
    payload = {
        "story_id": "story-123",
        "from_state": "PLANNED",
        "to_state": "READY_FOR_EXECUTION",
        "tasks": ["task-001"],
        "timestamp": "",  # Empty!
    }

    message_data = json.dumps(payload).encode("utf-8")

    # Act & Assert: DTO validation should catch this
    with pytest.raises(ValueError, match="timestamp cannot be empty"):
        PlanningEventMapper.from_nats_message(message_data)

