"""Unit tests for TaskValkeyMapper."""

from datetime import UTC, datetime

import pytest
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.infrastructure.mappers.task_valkey_mapper import TaskValkeyMapper


@pytest.fixture
def sample_task():
    """Create sample task for tests."""
    now = datetime.now(UTC)
    return Task(
        task_id=TaskId("T-TEST-001"),
        story_id=StoryId("story-123"),  # REQUIRED - domain invariant
        title="Test Task",
        created_at=now,
        updated_at=now,
        plan_id=PlanId("P-TEST-001"),  # Optional
        description="Test description",
        assigned_to="developer",
        estimated_hours=8,
        type=TaskType.DEVELOPMENT,
        status=TaskStatus.TODO,
        priority=1,
    )


@pytest.fixture
def sample_task_no_plan():
    """Create sample task without plan_id."""
    now = datetime.now(UTC)
    return Task(
        task_id=TaskId("T-TEST-002"),
        story_id=StoryId("story-123"),  # REQUIRED - domain invariant
        title="Test Task No Plan",
        created_at=now,
        updated_at=now,
        plan_id=None,  # Optional - not provided
        description="",
        assigned_to="",
        estimated_hours=0,
        type=TaskType.DEVELOPMENT,
        status=TaskStatus.TODO,
        priority=1,
    )


class TestTaskValkeyMapperToDict:
    """Test TaskValkeyMapper.to_dict method."""

    def test_to_dict_includes_all_required_fields(self, sample_task):
        """Test that to_dict includes all required fields."""
        result = TaskValkeyMapper.to_dict(sample_task)

        assert result["task_id"] == "T-TEST-001"
        assert result["story_id"] == "story-123"
        assert result["title"] == "Test Task"
        assert result["type"] == "development"
        assert result["status"] == "todo"
        assert result["assigned_to"] == "developer"
        assert result["estimated_hours"] == "8"
        assert result["priority"] == "1"
        assert "created_at" in result
        assert "updated_at" in result

    def test_to_dict_includes_optional_plan_id_when_provided(self, sample_task):
        """Test that to_dict includes plan_id when provided."""
        result = TaskValkeyMapper.to_dict(sample_task)

        assert result["plan_id"] == "P-TEST-001"

    def test_to_dict_omits_plan_id_when_none(self, sample_task_no_plan):
        """Test that to_dict omits plan_id when None."""
        result = TaskValkeyMapper.to_dict(sample_task_no_plan)

        assert "plan_id" not in result

    def test_to_dict_includes_description_when_provided(self, sample_task):
        """Test that to_dict includes description when provided."""
        result = TaskValkeyMapper.to_dict(sample_task)

        assert result["description"] == "Test description"

    def test_to_dict_omits_description_when_empty(self, sample_task_no_plan):
        """Test that to_dict omits description when empty."""
        result = TaskValkeyMapper.to_dict(sample_task_no_plan)

        assert "description" not in result

    def test_to_dict_converts_enums_to_strings(self, sample_task):
        """Test that to_dict converts TaskType and TaskStatus to strings."""
        result = TaskValkeyMapper.to_dict(sample_task)

        assert isinstance(result["type"], str)
        assert isinstance(result["status"], str)
        assert result["type"] == "development"
        assert result["status"] == "todo"

    def test_to_dict_converts_timestamps_to_isoformat(self, sample_task):
        """Test that to_dict converts datetime to ISO format."""
        result = TaskValkeyMapper.to_dict(sample_task)

        assert isinstance(result["created_at"], str)
        assert isinstance(result["updated_at"], str)
        # Verify ISO format
        datetime.fromisoformat(result["created_at"])
        datetime.fromisoformat(result["updated_at"])


class TestTaskValkeyMapperFromDict:
    """Test TaskValkeyMapper.from_dict method."""

    def test_from_dict_creates_task_with_all_fields(self, sample_task):
        """Test that from_dict creates Task with all fields."""
        data = TaskValkeyMapper.to_dict(sample_task)
        result = TaskValkeyMapper.from_dict(data)

        assert result.task_id.value == "T-TEST-001"
        assert result.story_id.value == "story-123"
        assert result.title == "Test Task"
        assert result.plan_id.value == "P-TEST-001"
        assert result.description == "Test description"
        assert result.assigned_to == "developer"
        assert result.estimated_hours == 8
        assert result.type == TaskType.DEVELOPMENT
        assert result.status == TaskStatus.TODO
        assert result.priority == 1

    def test_from_dict_handles_missing_plan_id(self):
        """Test that from_dict handles missing plan_id (None)."""
        now = datetime.now(UTC)
        data = {
            "task_id": "T-TEST-002",
            "story_id": "story-123",
            "title": "Test Task",
            "type": "development",
            "status": "todo",
            "assigned_to": "",
            "estimated_hours": "0",
            "priority": "1",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        result = TaskValkeyMapper.from_dict(data)

        assert result.plan_id is None

    def test_from_dict_handles_missing_description(self):
        """Test that from_dict handles missing description (empty string)."""
        now = datetime.now(UTC)
        data = {
            "task_id": "T-TEST-003",
            "story_id": "story-123",
            "title": "Test Task",
            "type": "development",
            "status": "todo",
            "assigned_to": "",
            "estimated_hours": "0",
            "priority": "1",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        result = TaskValkeyMapper.from_dict(data)

        assert result.description == ""

    def test_from_dict_handles_bytes_keys(self):
        """Test that from_dict handles bytes keys (decode_responses=False)."""
        now = datetime.now(UTC)
        data = {
            b"task_id": b"T-TEST-004",
            b"story_id": b"story-123",
            b"title": b"Test Task",
            b"type": b"development",
            b"status": b"todo",
            b"assigned_to": b"",
            b"estimated_hours": b"0",
            b"priority": b"1",
            b"created_at": now.isoformat().encode("utf-8"),
            b"updated_at": now.isoformat().encode("utf-8"),
        }

        result = TaskValkeyMapper.from_dict(data)

        assert result.task_id.value == "T-TEST-004"
        assert result.story_id.value == "story-123"
        assert result.title == "Test Task"

    def test_from_dict_raises_on_empty_dict(self):
        """Test that from_dict raises ValueError on empty dict."""
        with pytest.raises(ValueError, match="Cannot create Task from empty dict"):
            TaskValkeyMapper.from_dict({})

    def test_from_dict_raises_on_missing_required_field(self):
        """Test that from_dict raises ValueError on missing required field."""
        now = datetime.now(UTC)
        data = {
            "task_id": "T-TEST-005",
            # Missing story_id (required)
            "title": "Test Task",
            "type": "development",
            "status": "todo",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        with pytest.raises(ValueError, match="Missing required field: story_id"):
            TaskValkeyMapper.from_dict(data)

    def test_from_dict_roundtrip(self, sample_task):
        """Test that to_dict and from_dict are inverse operations."""
        data = TaskValkeyMapper.to_dict(sample_task)
        result = TaskValkeyMapper.from_dict(data)

        assert result.task_id == sample_task.task_id
        assert result.story_id == sample_task.story_id
        assert result.title == sample_task.title
        assert result.plan_id == sample_task.plan_id
        assert result.description == sample_task.description
        assert result.assigned_to == sample_task.assigned_to
        assert result.estimated_hours == sample_task.estimated_hours
        assert result.type == sample_task.type
        assert result.status == sample_task.status
        assert result.priority == sample_task.priority
        assert result.created_at == sample_task.created_at
        assert result.updated_at == sample_task.updated_at

