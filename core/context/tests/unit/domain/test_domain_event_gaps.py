"""Quick coverage for domain_event.py gaps - updated for DDD refactor + hierarchy."""

from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.plan_id import PlanId
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.entity_ids.task_id import TaskId
from core.context.domain.event_type import EventType
from core.context.domain.events.task_status_changed_event import TaskStatusChangedEvent
from core.context.domain.task_status import TaskStatus


def test_task_status_changed_event_creation() -> None:
    """Test creating TaskStatusChangedEvent with complete hierarchy."""
    event = TaskStatusChangedEvent(
        event_type=EventType.TASK_STATUS_CHANGED,
        task_id=TaskId(value="task-123"),
        plan_id=PlanId(value="PLAN-123"),
        story_id=StoryId(value="US-123"),
        epic_id=EpicId(value="E-123"),
        project_id=ProjectId(value="PROJ-123"),
        status=TaskStatus.COMPLETED,
    )

    # Verify task and status
    assert event.task_id.to_string() == "task-123"
    assert event.status == TaskStatus.COMPLETED
    # Verify hierarchy (traceability)
    assert event.project_id.to_string() == "PROJ-123"
    assert event.epic_id.to_string() == "E-123"
    assert event.story_id.to_string() == "US-123"
    assert event.plan_id.to_string() == "PLAN-123"


def test_task_status_changed_event_with_blocked_status() -> None:
    """Test TaskStatusChangedEvent with BLOCKED status."""
    event = TaskStatusChangedEvent(
        event_type=EventType.TASK_STATUS_CHANGED,
        task_id=TaskId(value="task-456"),
        plan_id=PlanId(value="PLAN-456"),
        story_id=StoryId(value="US-456"),
        epic_id=EpicId(value="E-456"),
        project_id=ProjectId(value="PROJ-456"),
        status=TaskStatus.BLOCKED,
    )

    assert event.task_id.to_string() == "task-456"
    assert event.status == TaskStatus.BLOCKED


def test_task_status_changed_event_immutability() -> None:
    """Test that TaskStatusChangedEvent is immutable (frozen=True)."""
    event = TaskStatusChangedEvent(
        event_type=EventType.TASK_STATUS_CHANGED,
        task_id=TaskId(value="task-789"),
        plan_id=PlanId(value="PLAN-789"),
        story_id=StoryId(value="US-789"),
        epic_id=EpicId(value="E-789"),
        project_id=ProjectId(value="PROJ-789"),
        status=TaskStatus.DONE,
    )

    # Should not be able to modify (frozen dataclass)
    try:
        event.status = TaskStatus.BLOCKED  # type: ignore
        assert False, "Should have raised AttributeError"
    except AttributeError:
        pass  # Expected
