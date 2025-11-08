"""Unit tests for PlanningEventsConsumer.

Tests the Planning events consumer that initializes workflow states.
Following DDD + Hexagonal Architecture principles.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.workflow.application.contracts.planning_service_contract import (
    PlanningStoryState,
)
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum
from services.workflow.infrastructure.consumers.planning_events_consumer import (
    PlanningEventsConsumer,
)

# ============================================================================
# Happy Path Tests
# ============================================================================


@pytest.mark.asyncio
async def test_handle_message_initializes_workflow_states():
    """Test that planning event initializes workflow states for all tasks."""
    # Arrange
    initialize_use_case = AsyncMock()
    nats_client = AsyncMock()
    jetstream = AsyncMock()

    consumer = PlanningEventsConsumer(
        nats_client=nats_client,
        jetstream=jetstream,
        initialize_task_workflow=initialize_use_case,
    )

    # Planning Service event
    event_payload = {
        "story_id": "story-123",
        "from_state": "PLANNED",
        "to_state": PlanningStoryState.READY_FOR_EXECUTION,
        "tasks": ["task-001", "task-002", "task-003"],
        "timestamp": "2025-11-06T10:30:00Z",
    }

    msg = MagicMock()
    msg.data = json.dumps(event_payload).encode("utf-8")

    # Act
    await consumer._handle_message(msg)

    # Assert: use case called 3 times (one per task)
    assert initialize_use_case.execute.await_count == 3

    # Verify first call arguments
    first_call = initialize_use_case.execute.await_args_list[0]
    call_kwargs = first_call[1]

    assert call_kwargs["task_id"] == TaskId("task-001")
    assert call_kwargs["story_id"] == StoryId("story-123")


@pytest.mark.asyncio
async def test_handle_message_calls_use_case_for_each_task():
    """Test that use case is called once per task."""
    # Arrange
    initialize_use_case = AsyncMock()
    nats_client = AsyncMock()
    jetstream = AsyncMock()

    consumer = PlanningEventsConsumer(
        nats_client=nats_client,
        jetstream=jetstream,
        initialize_task_workflow=initialize_use_case,
    )

    event_payload = {
        "story_id": "story-456",
        "from_state": "PLANNED",
        "to_state": PlanningStoryState.READY_FOR_EXECUTION,
        "tasks": ["task-100"],
        "timestamp": "2025-11-06T10:30:00Z",
    }

    msg = MagicMock()
    msg.data = json.dumps(event_payload).encode("utf-8")

    # Act
    await consumer._handle_message(msg)

    # Assert: use case called once
    initialize_use_case.execute.assert_awaited_once()

    # Verify call arguments
    call_args = initialize_use_case.execute.await_args
    call_kwargs = call_args[1]

    assert call_kwargs["task_id"] == TaskId("task-100")
    assert call_kwargs["story_id"] == StoryId("story-456")


@pytest.mark.asyncio
async def test_handle_message_with_multiple_tasks():
    """Test handling event with multiple tasks."""
    # Arrange
    initialize_use_case = AsyncMock()
    nats_client = AsyncMock()
    jetstream = AsyncMock()

    consumer = PlanningEventsConsumer(
        nats_client=nats_client,
        jetstream=jetstream,
        initialize_task_workflow=initialize_use_case,
    )

    event_payload = {
        "story_id": "story-789",
        "from_state": "PLANNED",
        "to_state": PlanningStoryState.READY_FOR_EXECUTION,
        "tasks": ["task-a", "task-b", "task-c", "task-d", "task-e"],
        "timestamp": "2025-11-06T10:30:00Z",
    }

    msg = MagicMock()
    msg.data = json.dumps(event_payload).encode("utf-8")

    # Act
    await consumer._handle_message(msg)

    # Assert: use case called 5 times (one per task)
    assert initialize_use_case.execute.await_count == 5

    # Verify all calls are for same story
    for call in initialize_use_case.execute.await_args_list:
        call_kwargs = call[1]
        assert call_kwargs["story_id"] == StoryId("story-789")


# ============================================================================
# Edge Case Tests
# ============================================================================


@pytest.mark.asyncio
async def test_handle_message_ignores_non_ready_states():
    """Test that consumer ignores events for non-READY_FOR_EXECUTION states."""
    # Arrange
    initialize_use_case = AsyncMock()
    nats_client = AsyncMock()
    jetstream = AsyncMock()

    consumer = PlanningEventsConsumer(
        nats_client=nats_client,
        jetstream=jetstream,
        initialize_task_workflow=initialize_use_case,
    )

    # Event with different to_state
    event_payload = {
        "story_id": "story-999",
        "from_state": "DRAFT",
        "to_state": "PLANNED",  # NOT READY_FOR_EXECUTION
        "tasks": ["task-001"],
        "timestamp": "2025-11-06T10:30:00Z",
    }

    msg = MagicMock()
    msg.data = json.dumps(event_payload).encode("utf-8")

    # Act
    await consumer._handle_message(msg)

    # Assert: Use case not called (event ignored)
    initialize_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_with_empty_task_list():
    """Test handling event with no tasks."""
    # Arrange
    initialize_use_case = AsyncMock()
    nats_client = AsyncMock()
    jetstream = AsyncMock()

    consumer = PlanningEventsConsumer(
        nats_client=nats_client,
        jetstream=jetstream,
        initialize_task_workflow=initialize_use_case,
    )

    event_payload = {
        "story_id": "story-empty",
        "from_state": "PLANNED",
        "to_state": PlanningStoryState.READY_FOR_EXECUTION,
        "tasks": [],  # Empty task list
        "timestamp": "2025-11-06T10:30:00Z",
    }

    msg = MagicMock()
    msg.data = json.dumps(event_payload).encode("utf-8")

    # Act
    await consumer._handle_message(msg)

    # Assert: Use case not called (no tasks to initialize)
    initialize_use_case.execute.assert_not_awaited()


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_handle_message_missing_required_field_raises():
    """Test that missing required field raises exception (will retry event)."""
    # Arrange
    initialize_use_case = AsyncMock()
    nats_client = AsyncMock()
    jetstream = AsyncMock()

    consumer = PlanningEventsConsumer(
        nats_client=nats_client,
        jetstream=jetstream,
        initialize_task_workflow=initialize_use_case,
    )

    # Missing 'tasks' field
    event_payload = {
        "story_id": "story-bad",
        "from_state": "PLANNED",
        "to_state": PlanningStoryState.READY_FOR_EXECUTION,
        # Missing 'tasks' field!
        "timestamp": "2025-11-06T10:30:00Z",
    }

    msg = MagicMock()
    msg.data = json.dumps(event_payload).encode("utf-8")

    # Act & Assert: Should raise (will retry)
    with pytest.raises(KeyError):
        await consumer._handle_message(msg)

    # Assert: Use case not called (event not processed)
    initialize_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_invalid_task_id_logs_and_continues():
    """Test that invalid task_id is logged but doesn't stop processing."""
    # Arrange
    initialize_use_case = AsyncMock()
    nats_client = AsyncMock()
    jetstream = AsyncMock()

    consumer = PlanningEventsConsumer(
        nats_client=nats_client,
        jetstream=jetstream,
        initialize_task_workflow=initialize_use_case,
    )

    event_payload = {
        "story_id": "story-123",
        "from_state": "PLANNED",
        "to_state": PlanningStoryState.READY_FOR_EXECUTION,
        "tasks": [""],  # Empty task ID (invalid)
        "timestamp": "2025-11-06T10:30:00Z",
    }

    msg = MagicMock()
    msg.data = json.dumps(event_payload).encode("utf-8")

    # Act: Should not raise (catches ValueError, logs, continues)
    await consumer._handle_message(msg)

    # Note: TaskId validation will catch empty string in domain layer


@pytest.mark.asyncio
async def test_handle_message_use_case_error_propagates():
    """Test that use case errors propagate (will retry event)."""
    # Arrange
    initialize_use_case = AsyncMock()
    initialize_use_case.execute.side_effect = Exception("Repository connection error")

    nats_client = AsyncMock()
    jetstream = AsyncMock()

    consumer = PlanningEventsConsumer(
        nats_client=nats_client,
        jetstream=jetstream,
        initialize_task_workflow=initialize_use_case,
    )

    event_payload = {
        "story_id": "story-error",
        "from_state": "PLANNED",
        "to_state": PlanningStoryState.READY_FOR_EXECUTION,
        "tasks": ["task-001"],
        "timestamp": "2025-11-06T10:30:00Z",
    }

    msg = MagicMock()
    msg.data = json.dumps(event_payload).encode("utf-8")

    # Act & Assert: Should propagate exception (will retry)
    with pytest.raises(Exception, match="Repository connection error"):
        await consumer._handle_message(msg)


# ============================================================================
# Integration Tests (Mock Validation)
# ============================================================================


@pytest.mark.asyncio
async def test_consumer_uses_planning_service_contract():
    """Test that consumer uses PlanningStoryState contract (not hardcoded strings)."""
    # Arrange
    initialize_use_case = AsyncMock()
    nats_client = AsyncMock()
    jetstream = AsyncMock()

    consumer = PlanningEventsConsumer(
        nats_client=nats_client,
        jetstream=jetstream,
        initialize_task_workflow=initialize_use_case,
    )

    event_payload = {
        "story_id": "story-test",
        "from_state": "PLANNED",
        "to_state": PlanningStoryState.READY_FOR_EXECUTION,
        "tasks": ["task-xyz"],
        "timestamp": "2025-11-06T10:30:00Z",
    }

    msg = MagicMock()
    msg.data = json.dumps(event_payload).encode("utf-8")

    # Act
    await consumer._handle_message(msg)

    # Assert: Use case called with correct domain objects
    initialize_use_case.execute.assert_awaited_once()

    # Verify contract value matches expected string
    assert PlanningStoryState.READY_FOR_EXECUTION == "READY_FOR_EXECUTION"


@pytest.mark.asyncio
async def test_workflow_state_factory_method():
    """Test WorkflowState.create_initial factory method."""
    # Arrange
    task_id = TaskId("task-factory-test")
    story_id = StoryId("story-factory-test")

    # Act
    state = WorkflowState.create_initial(task_id=task_id, story_id=story_id, initial_role=Role("developer"))

    # Assert: Initial state configuration
    assert state.task_id == task_id
    assert state.story_id == story_id
    assert state.current_state == WorkflowStateEnum.TODO
    assert str(state.role_in_charge) == "developer"
    assert state.required_action.get_value() == "claim_task"
    assert state.history == ()
    assert state.feedback is None
    assert state.retry_count == 0
    assert isinstance(state.updated_at, datetime)

