"""Unit tests for ValkeyStorageAdapter task methods."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.infrastructure.adapters.valkey_adapter import ValkeyStorageAdapter
from planning.infrastructure.adapters.valkey_config import ValkeyConfig


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


class TestValkeyAdapterSaveTask:
    """Test save_task method."""

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    @patch("planning.infrastructure.adapters.valkey_adapter.TaskValkeyMapper")
    async def test_save_task_persists_all_fields(self, mock_mapper, mock_redis, sample_task):
        """Should persist task hash and set memberships."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.hget.return_value = None  # No old plan_id

        task_data = {
            "task_id": "T-TEST-001",
            "story_id": "story-123",
            "title": "Test Task",
            "type": "development",
            "status": "todo",
            "plan_id": "P-TEST-001",
            "description": "Test description",
            "assigned_to": "developer",
            "estimated_hours": "8",
            "priority": "1",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        mock_mapper.to_dict.return_value = task_data

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        await adapter.save_task(sample_task)

        # Verify mapper was called
        mock_mapper.to_dict.assert_called_once_with(sample_task)

        # Verify Redis operations
        mock_redis_instance.hset.assert_called_once()
        mock_redis_instance.sadd.assert_called()

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_save_task_adds_to_all_tasks_set(self, mock_redis, sample_task):
        """Should add task ID to all tasks set."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.hget.return_value = None

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        await adapter.save_task(sample_task)

        # Verify task added to all tasks set
        calls = [call[0][0] for call in mock_redis_instance.sadd.call_args_list]
        assert "planning:tasks:all" in calls

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_save_task_adds_to_story_set(self, mock_redis, sample_task):
        """Should add task ID to story-specific set."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.hget.return_value = None

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        await adapter.save_task(sample_task)

        # Verify task added to story set
        calls = [call[0][0] for call in mock_redis_instance.sadd.call_args_list]
        assert "planning:tasks:story:story-123" in calls

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_save_task_adds_to_plan_set_when_provided(self, mock_redis, sample_task):
        """Should add task ID to plan set when plan_id is provided."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = None  # No old plan_id

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        await adapter.save_task(sample_task)

        # Verify task added to plan set
        calls = [call[0][0] for call in mock_redis_instance.sadd.call_args_list]
        assert "planning:tasks:plan:P-TEST-001" in calls

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_save_task_does_not_add_to_plan_set_when_none(self, mock_redis, sample_task_no_plan):
        """Should not add task ID to plan set when plan_id is None."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.hget.return_value = None

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        await adapter.save_task(sample_task_no_plan)

        # Verify task NOT added to plan set
        calls = [call[0][0] for call in mock_redis_instance.sadd.call_args_list]
        plan_calls = [call for call in calls if "plan:" in call]
        assert len(plan_calls) == 0

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_save_task_updates_plan_sets_on_change(self, mock_redis, sample_task):
        """Should update plan sets when plan_id changes."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.hget.return_value = "P-OLD-001"  # Old plan_id

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        await adapter.save_task(sample_task)

        # Verify old plan removed and new plan added
        assert mock_redis_instance.srem.called  # Remove from old plan
        calls = [call[0][0] for call in mock_redis_instance.sadd.call_args_list]
        assert "planning:tasks:plan:P-TEST-001" in calls

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_save_task_removes_from_old_plan_when_changed_to_none(self, mock_redis):
        """Should remove from old plan set when plan_id changes to None."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.hget.return_value = "P-OLD-001"  # Old plan_id exists

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        # Task with plan_id=None (removing plan association)
        now = datetime.now(UTC)
        task_no_plan = Task(
            task_id=TaskId("T-TEST-003"),
            story_id=StoryId("story-123"),
            title="Task without plan",
            created_at=now,
            updated_at=now,
            plan_id=None,  # Changed from P-OLD-001 to None
        )

        await adapter.save_task(task_no_plan)

        # Verify old plan removed
        assert mock_redis_instance.srem.called
        # Verify NOT added to any plan set
        calls = [call[0][0] for call in mock_redis_instance.sadd.call_args_list]
        plan_calls = [call for call in calls if "plan:" in call]
        assert len(plan_calls) == 0

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_save_task_raises_on_missing_story_id(self, mock_redis):
        """Should raise ValueError when story_id is missing."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        # Mock task to have None story_id (simulating invalid state)
        # This tests the validation in save_task
        # Note: We can't create a real Task with None story_id (StoryId validation prevents it)
        # So we use MagicMock to simulate the invalid state
        task_with_none_story = MagicMock(spec=Task)
        task_with_none_story.task_id = TaskId("T-INVALID")
        task_with_none_story.story_id = None  # None story_id
        task_with_none_story.plan_id = None

        with pytest.raises(ValueError, match="Task story_id is required"):
            await adapter.save_task(task_with_none_story)


class TestValkeyAdapterGetTask:
    """Test get_task method."""

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    @patch("planning.infrastructure.adapters.valkey_adapter.TaskValkeyMapper")
    async def test_get_task_retrieves_task(self, mock_mapper, mock_redis, sample_task):
        """Should retrieve task from Valkey."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        task_data = {
            "task_id": "T-TEST-001",
            "story_id": "story-123",
            "title": "Test Task",
            "type": "development",
            "status": "todo",
            "plan_id": "P-TEST-001",
            "description": "Test description",
            "assigned_to": "developer",
            "estimated_hours": "8",
            "priority": "1",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        mock_redis_instance.hgetall.return_value = task_data
        mock_mapper.from_dict.return_value = sample_task

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        result = await adapter.get_task(TaskId("T-TEST-001"))

        assert result == sample_task
        mock_redis_instance.hgetall.assert_called_once()
        mock_mapper.from_dict.assert_called_once_with(task_data)

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_get_task_returns_none_when_not_found(self, mock_redis):
        """Should return None when task not found."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.hgetall.return_value = {}  # Empty dict

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        result = await adapter.get_task(TaskId("T-NOT-FOUND"))

        assert result is None


class TestValkeyAdapterListTasks:
    """Test list_tasks method."""

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_list_tasks_returns_all_tasks(self, mock_redis, sample_task):
        """Should return all tasks when no filter provided."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.smembers.return_value = {"T-TEST-001", "T-TEST-002"}
        mock_redis_instance.hgetall.return_value = {}  # Will return None from _get_task_sync

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        # Mock _get_task_sync to return sample_task
        with patch.object(adapter, "_get_task_sync", return_value=sample_task):
            result = await adapter.list_tasks()

            assert len(result) == 2
            assert all(isinstance(task, Task) for task in result)

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_list_tasks_filters_by_story(self, mock_redis, sample_task):
        """Should filter tasks by story_id."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.smembers.return_value = {"T-TEST-001"}

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        with patch.object(adapter, "_get_task_sync", return_value=sample_task):
            result = await adapter.list_tasks(story_id=StoryId("story-123"))

            assert len(result) == 1
            mock_redis_instance.smembers.assert_called_with("planning:tasks:story:story-123")

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_list_tasks_applies_pagination(self, mock_redis, sample_task):
        """Should apply limit and offset for pagination."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.smembers.return_value = {
            "T-TEST-001",
            "T-TEST-002",
            "T-TEST-003",
            "T-TEST-004",
            "T-TEST-005",
        }

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        with patch.object(adapter, "_get_task_sync", return_value=sample_task):
            result = await adapter.list_tasks(limit=2, offset=1)

            # Should return 2 tasks (limit=2) starting from offset=1
            assert len(result) == 2

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_list_tasks_handles_empty_set(self, mock_redis):
        """Should return empty list when no tasks found."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.smembers.return_value = set()  # Empty set

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        result = await adapter.list_tasks()

        assert result == []

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_list_tasks_filters_out_none_tasks(self, mock_redis):
        """Should filter out None tasks (when _get_task_sync returns None)."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.smembers.return_value = {"T-VALID", "T-INVALID"}

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        # Mock _get_task_sync to return None for invalid task
        def mock_get_task_sync(task_id):
            if task_id.value == "T-VALID":
                now = datetime.now(UTC)
                return Task(
                    task_id=TaskId("T-VALID"),
                    story_id=StoryId("story-123"),
                    title="Valid Task",
                    created_at=now,
                    updated_at=now,
                )
            return None  # Invalid task

        with patch.object(adapter, "_get_task_sync", side_effect=mock_get_task_sync):
            result = await adapter.list_tasks()

            # Should only return valid task
            assert len(result) == 1
            assert result[0].task_id.value == "T-VALID"

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    @patch("planning.infrastructure.adapters.valkey_adapter.TaskValkeyMapper")
    async def test_get_task_handles_deserialization_error(self, mock_mapper, mock_redis):
        """Should return None when deserialization fails."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.hgetall.return_value = {"task_id": "T-INVALID"}

        # Mock mapper to raise ValueError
        mock_mapper.from_dict.side_effect = ValueError("Invalid data")

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        result = await adapter.get_task(TaskId("T-INVALID"))

        assert result is None

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    @patch("planning.infrastructure.adapters.valkey_adapter.TaskValkeyMapper")
    async def test_get_task_handles_key_error(self, mock_mapper, mock_redis):
        """Should return None when KeyError occurs during deserialization."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.hgetall.return_value = {"task_id": "T-INVALID"}

        # Mock mapper to raise KeyError
        mock_mapper.from_dict.side_effect = KeyError("missing_field")

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        result = await adapter.get_task(TaskId("T-INVALID"))

        assert result is None

    @pytest.mark.asyncio
    @patch("planning.infrastructure.adapters.valkey_adapter.valkey.Valkey")
    async def test_list_tasks_with_offset_exceeds_total(self, mock_redis, sample_task):
        """Should return empty list when offset exceeds total tasks."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.smembers.return_value = {"T-TEST-001", "T-TEST-002"}

        adapter = ValkeyStorageAdapter(ValkeyConfig())

        with patch.object(adapter, "_get_task_sync", return_value=sample_task):
            result = await adapter.list_tasks(limit=10, offset=100)

            # Should return empty list (offset exceeds total)
            assert result == []

