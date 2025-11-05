"""Unit tests for TaskId value object."""

import pytest

from services.workflow.domain.value_objects.task_id import TaskId


def test_task_id_creation_success():
    """Test TaskId creation with valid value."""
    task_id = TaskId("task-001")

    assert task_id.value == "task-001"
    assert str(task_id) == "task-001"


def test_task_id_empty_raises_error():
    """Test TaskId with empty string raises ValueError."""
    with pytest.raises(ValueError, match="TaskId cannot be empty"):
        TaskId("")


def test_task_id_equality():
    """Test TaskId equality comparison."""
    task_id_1 = TaskId("task-001")
    task_id_2 = TaskId("task-001")
    task_id_3 = TaskId("task-002")

    assert task_id_1 == task_id_2
    assert task_id_1 != task_id_3


def test_task_id_immutable():
    """Test TaskId is immutable (frozen)."""
    task_id = TaskId("task-001")

    with pytest.raises(AttributeError):
        task_id.value = "task-002"  # type: ignore

