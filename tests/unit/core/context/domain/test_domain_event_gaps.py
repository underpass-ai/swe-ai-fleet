"""Quick coverage for domain_event.py gaps - updated for DDD refactor."""

from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.event_type import EventType
from core.context.domain.events.task_status_changed_event import TaskStatusChangedEvent
from core.context.domain.task_status import TaskStatus


def test_task_status_changed_event_creation() -> None:
    """Test creating TaskStatusChangedEvent (renamed from subtask)."""
    event = TaskStatusChangedEvent(
        event_type=EventType.TASK_STATUS_CHANGED,
        task_id=TaskId(value="task-123"),
        status=TaskStatus.COMPLETED,
    )
    
    # TaskId VO has to_string() method
    assert event.task_id.to_string() == "task-123"
    assert event.status == TaskStatus.COMPLETED


def test_task_status_changed_event_with_none_status() -> None:
    """Test TaskStatusChangedEvent allows None status."""
    event = TaskStatusChangedEvent(
        event_type=EventType.TASK_STATUS_CHANGED,
        task_id=TaskId(value="task-456"),
        status=None,  # Optional status
    )
    
    assert event.task_id.to_string() == "task-456"
    assert event.status is None


def test_task_status_changed_event_immutability() -> None:
    """Test that TaskStatusChangedEvent is immutable (frozen=True)."""
    event = TaskStatusChangedEvent(
        event_type=EventType.TASK_STATUS_CHANGED,
        task_id=TaskId(value="task-789"),
        status=TaskStatus.DONE,
    )
    
    # Should not be able to modify (frozen dataclass)
    try:
        event.status = TaskStatus.BLOCKED  # type: ignore
        assert False, "Should have raised AttributeError"
    except AttributeError:
        pass  # Expected
