"""Unit tests for TaskNeo4jMapper."""

from datetime import UTC, datetime

import pytest
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.infrastructure.mappers.task_neo4j_mapper import TaskNeo4jMapper


def test_to_graph_properties_happy_path() -> None:
    """Test Task to Neo4j properties conversion (happy path)."""
    now = datetime.now(UTC)

    task = Task(
        task_id=TaskId("T-123"),
        story_id=StoryId("STORY-456"),
        title="Test Task",
        created_at=now,
        updated_at=now,
        status=TaskStatus.IN_PROGRESS,
        type=TaskType.DEVELOPMENT,
    )

    result = TaskNeo4jMapper.to_graph_properties(task)

    assert isinstance(result, dict)
    assert result["id"] == "T-123"
    assert result["task_id"] == "T-123"
    assert result["status"] == "in_progress"
    assert result["type"] == "development"


def test_to_graph_properties_all_statuses() -> None:
    """Test to_graph_properties with different status values."""
    now = datetime.now(UTC)

    statuses = [
        TaskStatus.TODO,
        TaskStatus.IN_PROGRESS,
        TaskStatus.IN_REVIEW,
        TaskStatus.BLOCKED,
        TaskStatus.COMPLETED,
        TaskStatus.CANCELLED,
    ]

    for status in statuses:
        task = Task(
            task_id=TaskId(f"T-{status.value}"),
            story_id=StoryId("STORY-1"),
            title=f"Task {status.value}",
            created_at=now,
            updated_at=now,
            status=status,
        )

        result = TaskNeo4jMapper.to_graph_properties(task)
        assert result["status"] == status.value


def test_to_graph_properties_all_types() -> None:
    """Test to_graph_properties with different type values."""
    now = datetime.now(UTC)

    types = [
        TaskType.DEVELOPMENT,
        TaskType.FEATURE,
        TaskType.BUG_FIX,
        TaskType.TESTING,
        TaskType.CODE_REVIEW,
        TaskType.DOCUMENTATION,
    ]

    for task_type in types:
        task = Task(
            task_id=TaskId(f"T-{task_type.value}"),
            story_id=StoryId("STORY-1"),
            title=f"Task {task_type.value}",
            created_at=now,
            updated_at=now,
            type=task_type,
        )

        result = TaskNeo4jMapper.to_graph_properties(task)
        assert result["type"] == task_type.value


def test_from_node_data_happy_path() -> None:
    """Test Neo4j node data to Task conversion (happy path)."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    node_data = {
        "properties": {
            "id": "T-789",
            "task_id": "T-789",
            "story_id": "STORY-123",
            "title": "From Node Task",
            "status": "in_progress",
            "type": "development",
            "description": "Test description",
            "assigned_to": "dev-1",
            "estimated_hours": 8,
            "priority": 2,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
    }

    task = TaskNeo4jMapper.from_node_data(node_data)

    assert isinstance(task, Task)
    assert task.task_id.value == "T-789"
    assert task.story_id.value == "STORY-123"
    assert task.title == "From Node Task"
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.type == TaskType.DEVELOPMENT
    assert task.description == "Test description"
    assert task.assigned_to == "dev-1"
    assert task.estimated_hours == 8
    assert task.priority == 2
    assert task.created_at == now
    assert task.updated_at == now


def test_from_node_data_without_properties_key() -> None:
    """Test from_node_data when properties are at root level."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    node_data = {
        "task_id": "T-999",
        "story_id": "STORY-456",
        "title": "Direct Properties Task",
        "status": "completed",
        "type": "bug_fix",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    task = TaskNeo4jMapper.from_node_data(node_data)

    assert task.task_id.value == "T-999"
    assert task.story_id.value == "STORY-456"
    assert task.title == "Direct Properties Task"
    assert task.status == TaskStatus.COMPLETED
    assert task.type == TaskType.BUG_FIX


def test_from_node_data_uses_id_if_task_id_missing() -> None:
    """Test from_node_data falls back to 'id' if 'task_id' is missing."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    node_data = {
        "id": "T-FALLBACK",
        "story_id": "STORY-1",
        "title": "Fallback Task",
        "status": "todo",
        "type": "development",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    task = TaskNeo4jMapper.from_node_data(node_data)

    assert task.task_id.value == "T-FALLBACK"


def test_from_node_data_with_optional_fields() -> None:
    """Test from_node_data with optional fields."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    node_data = {
        "task_id": "T-OPTIONAL",
        "story_id": "STORY-1",
        "title": "Optional Fields Task",
        "status": "todo",
        "type": "development",
        "created_at": now_iso,
        "updated_at": now_iso,
        "plan_id": "PLAN-123",
        "description": "Optional description",
        "assigned_to": "dev-2",
        "estimated_hours": 4,
        "priority": 3,
    }

    task = TaskNeo4jMapper.from_node_data(node_data)

    assert task.plan_id is not None
    assert task.plan_id.value == "PLAN-123"
    assert task.description == "Optional description"
    assert task.assigned_to == "dev-2"
    assert task.estimated_hours == 4
    assert task.priority == 3


def test_from_node_data_without_plan_id() -> None:
    """Test from_node_data when plan_id is missing (should be None)."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    node_data = {
        "task_id": "T-NO-PLAN",
        "story_id": "STORY-1",
        "title": "No Plan Task",
        "status": "todo",
        "type": "development",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    task = TaskNeo4jMapper.from_node_data(node_data)

    assert task.plan_id is None


def test_from_node_data_with_no_plan_id_string() -> None:
    """Test from_node_data when plan_id is 'NO PLAN ID' (should be None)."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    node_data = {
        "task_id": "T-NO-PLAN-STR",
        "story_id": "STORY-1",
        "title": "No Plan String Task",
        "status": "todo",
        "type": "development",
        "created_at": now_iso,
        "updated_at": now_iso,
        "plan_id": "NO PLAN ID",
    }

    task = TaskNeo4jMapper.from_node_data(node_data)

    assert task.plan_id is None


def test_from_node_data_with_z_suffix_in_timestamps() -> None:
    """Test from_node_data handles timestamps with Z suffix."""
    now = datetime.now(UTC)
    now_iso_z = now.isoformat().replace("+00:00", "Z")

    node_data = {
        "task_id": "T-Z-SUFFIX",
        "story_id": "STORY-1",
        "title": "Z Suffix Task",
        "status": "todo",
        "type": "development",
        "created_at": now_iso_z,
        "updated_at": now_iso_z,
    }

    task = TaskNeo4jMapper.from_node_data(node_data)

    assert isinstance(task.created_at, datetime)
    assert isinstance(task.updated_at, datetime)


def test_from_node_data_all_statuses() -> None:
    """Test from_node_data with different status values."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    statuses = [
        ("todo", TaskStatus.TODO),
        ("in_progress", TaskStatus.IN_PROGRESS),
        ("in_review", TaskStatus.IN_REVIEW),
        ("blocked", TaskStatus.BLOCKED),
        ("completed", TaskStatus.COMPLETED),
        ("cancelled", TaskStatus.CANCELLED),
    ]

    for status_str, status_enum in statuses:
        node_data = {
            "task_id": f"T-{status_str}",
            "story_id": "STORY-1",
            "title": f"Task {status_str}",
            "status": status_str,
            "type": "development",
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        task = TaskNeo4jMapper.from_node_data(node_data)
        assert task.status == status_enum


def test_from_node_data_all_types() -> None:
    """Test from_node_data with different type values."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()

    types = [
        ("development", TaskType.DEVELOPMENT),
        ("feature", TaskType.FEATURE),
        ("bug_fix", TaskType.BUG_FIX),
        ("testing", TaskType.TESTING),
        ("code_review", TaskType.CODE_REVIEW),
        ("documentation", TaskType.DOCUMENTATION),
    ]

    for type_str, type_enum in types:
        node_data = {
            "task_id": f"T-{type_str}",
            "story_id": "STORY-1",
            "title": f"Task {type_str}",
            "status": "todo",
            "type": type_str,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        task = TaskNeo4jMapper.from_node_data(node_data)
        assert task.type == type_enum


def test_from_node_data_empty_data_raises_error() -> None:
    """Test from_node_data with empty data raises ValueError."""
    with pytest.raises(ValueError, match="Cannot create Task from empty node_data"):
        TaskNeo4jMapper.from_node_data({})


def test_from_node_data_missing_id_and_task_id_raises_error() -> None:
    """Test from_node_data raises error when both id and task_id are missing."""
    node_data = {
        "story_id": "STORY-1",
        "title": "Missing ID Task",
        "status": "todo",
        "type": "development",
        "created_at": "2025-01-28T10:00:00Z",
        "updated_at": "2025-01-28T10:00:00Z",
    }

    with pytest.raises(ValueError, match="Missing required field: task_id or id"):
        TaskNeo4jMapper.from_node_data(node_data)


def test_from_node_data_missing_story_id_raises_error() -> None:
    """Test from_node_data raises error when story_id is missing."""
    node_data = {
        "task_id": "T-NO-STORY",
        "title": "Missing Story Task",
        "status": "todo",
        "type": "development",
        "created_at": "2025-01-28T10:00:00Z",
        "updated_at": "2025-01-28T10:00:00Z",
    }

    with pytest.raises(ValueError, match="Missing required field: story_id"):
        TaskNeo4jMapper.from_node_data(node_data)


def test_from_node_data_missing_status_raises_error() -> None:
    """Test from_node_data raises error when status is missing."""
    node_data = {
        "task_id": "T-NO-STATUS",
        "story_id": "STORY-1",
        "title": "Missing Status Task",
        "type": "development",
        "created_at": "2025-01-28T10:00:00Z",
        "updated_at": "2025-01-28T10:00:00Z",
    }

    with pytest.raises(ValueError, match="Missing required field: status"):
        TaskNeo4jMapper.from_node_data(node_data)


def test_from_node_data_missing_type_raises_error() -> None:
    """Test from_node_data raises error when type is missing."""
    node_data = {
        "task_id": "T-NO-TYPE",
        "story_id": "STORY-1",
        "title": "Missing Type Task",
        "status": "todo",
        "created_at": "2025-01-28T10:00:00Z",
        "updated_at": "2025-01-28T10:00:00Z",
    }

    with pytest.raises(ValueError, match="Missing required field: type"):
        TaskNeo4jMapper.from_node_data(node_data)


def test_from_node_data_missing_title_raises_error() -> None:
    """Test from_node_data raises error when title is missing."""
    node_data = {
        "task_id": "T-NO-TITLE",
        "story_id": "STORY-1",
        "status": "todo",
        "type": "development",
        "created_at": "2025-01-28T10:00:00Z",
        "updated_at": "2025-01-28T10:00:00Z",
    }

    with pytest.raises(ValueError, match="Missing required field: title"):
        TaskNeo4jMapper.from_node_data(node_data)


def test_from_node_data_missing_created_at_raises_error() -> None:
    """Test from_node_data raises error when created_at is missing."""
    node_data = {
        "task_id": "T-NO-CREATED",
        "story_id": "STORY-1",
        "title": "Missing Created Task",
        "status": "todo",
        "type": "development",
        "updated_at": "2025-01-28T10:00:00Z",
    }

    with pytest.raises(ValueError, match="Missing required field: created_at"):
        TaskNeo4jMapper.from_node_data(node_data)


def test_from_node_data_missing_updated_at_raises_error() -> None:
    """Test from_node_data raises error when updated_at is missing."""
    node_data = {
        "task_id": "T-NO-UPDATED",
        "story_id": "STORY-1",
        "title": "Missing Updated Task",
        "status": "todo",
        "type": "development",
        "created_at": "2025-01-28T10:00:00Z",
    }

    with pytest.raises(ValueError, match="Missing required field: updated_at"):
        TaskNeo4jMapper.from_node_data(node_data)


def test_from_node_data_invalid_status_raises_error() -> None:
    """Test from_node_data raises error when status is invalid."""
    node_data = {
        "task_id": "T-INVALID-STATUS",
        "story_id": "STORY-1",
        "title": "Invalid Status Task",
        "status": "invalid_status",
        "type": "development",
        "created_at": "2025-01-28T10:00:00Z",
        "updated_at": "2025-01-28T10:00:00Z",
    }

    with pytest.raises(ValueError, match="Invalid task status: invalid_status"):
        TaskNeo4jMapper.from_node_data(node_data)


def test_from_node_data_invalid_type_raises_error() -> None:
    """Test from_node_data raises error when type is invalid."""
    node_data = {
        "task_id": "T-INVALID-TYPE",
        "story_id": "STORY-1",
        "title": "Invalid Type Task",
        "status": "todo",
        "type": "invalid_type",
        "created_at": "2025-01-28T10:00:00Z",
        "updated_at": "2025-01-28T10:00:00Z",
    }

    with pytest.raises(ValueError, match="Invalid task type: invalid_type"):
        TaskNeo4jMapper.from_node_data(node_data)


def test_from_node_data_invalid_created_at_format_raises_error() -> None:
    """Test from_node_data raises error when created_at format is invalid."""
    node_data = {
        "task_id": "T-INVALID-CREATED",
        "story_id": "STORY-1",
        "title": "Invalid Created Task",
        "status": "todo",
        "type": "development",
        "created_at": "invalid-date",
        "updated_at": "2025-01-28T10:00:00Z",
    }

    with pytest.raises(ValueError, match="Invalid created_at format: invalid-date"):
        TaskNeo4jMapper.from_node_data(node_data)


def test_from_node_data_invalid_updated_at_format_raises_error() -> None:
    """Test from_node_data raises error when updated_at format is invalid."""
    node_data = {
        "task_id": "T-INVALID-UPDATED",
        "story_id": "STORY-1",
        "title": "Invalid Updated Task",
        "status": "todo",
        "type": "development",
        "created_at": "2025-01-28T10:00:00Z",
        "updated_at": "invalid-date",
    }

    with pytest.raises(ValueError, match="Invalid updated_at format: invalid-date"):
        TaskNeo4jMapper.from_node_data(node_data)


def test_roundtrip_task_to_neo4j_and_back() -> None:
    """Test Task → Neo4j properties → Task roundtrip (minimal properties only)."""
    now = datetime.now(UTC)

    original = Task(
        task_id=TaskId("T-ROUNDTRIP"),
        story_id=StoryId("STORY-ROUNDTRIP"),
        title="Roundtrip Task",
        created_at=now,
        updated_at=now,
        status=TaskStatus.IN_PROGRESS,
        type=TaskType.FEATURE,
        description="Roundtrip description",
        assigned_to="dev-roundtrip",
        estimated_hours=6,
        priority=2,
    )

    # Convert to Neo4j properties (only minimal graph properties)
    neo4j_props = TaskNeo4jMapper.to_graph_properties(original)

    # Simulate Neo4j node structure with all required fields for from_node_data
    node_data = {
        "properties": {
            **neo4j_props,
            "story_id": original.story_id.value,
            "title": original.title,
            "created_at": original.created_at.isoformat(),
            "updated_at": original.updated_at.isoformat(),
            "description": original.description,
            "assigned_to": original.assigned_to,
            "estimated_hours": original.estimated_hours,
            "priority": original.priority,
        }
    }

    # Convert back to Task
    reconstructed = TaskNeo4jMapper.from_node_data(node_data)

    assert reconstructed.task_id == original.task_id
    assert reconstructed.story_id == original.story_id
    assert reconstructed.title == original.title
    assert reconstructed.status == original.status
    assert reconstructed.type == original.type
    assert reconstructed.description == original.description
    assert reconstructed.assigned_to == original.assigned_to
    assert reconstructed.estimated_hours == original.estimated_hours
    assert reconstructed.priority == original.priority
    assert reconstructed.created_at == original.created_at
    assert reconstructed.updated_at == original.updated_at

