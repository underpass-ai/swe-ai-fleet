import json
from unittest.mock import AsyncMock, Mock

import pytest

from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.infrastructure.adapters.nats_messaging_adapter import NatsMessagingAdapter


@pytest.mark.asyncio
async def test_publish_state_changed_publishes_enveloped_message() -> None:
    js = AsyncMock()
    adapter = NatsMessagingAdapter(nats_client=Mock(), jetstream=js)

    state = WorkflowState.create_initial(
        task_id=TaskId("task-001"),
        story_id=StoryId("story-001"),
        initial_role=Role.developer(),
    )

    await adapter.publish_state_changed(workflow_state=state, event_type="test.event")

    js.publish.assert_awaited_once()
    kwargs = js.publish.call_args.kwargs
    assert "subject" in kwargs
    assert "payload" in kwargs
    payload = json.loads(kwargs["payload"].decode("utf-8"))

    # Envelope fields exist
    assert payload["event_type"] == "workflow.state.changed"
    assert payload["producer"] == "workflow-service"
    assert payload["idempotency_key"]
    assert payload["correlation_id"]
    assert isinstance(payload["payload"], dict)
    assert payload["payload"]["task_id"] == "task-001"


@pytest.mark.asyncio
async def test_publish_task_assigned_publishes_enveloped_message() -> None:
    js = AsyncMock()
    adapter = NatsMessagingAdapter(nats_client=Mock(), jetstream=js)

    await adapter.publish_task_assigned(
        task_id="task-001",
        story_id="story-001",
        role="developer",
        action_required="claim_task",
    )

    js.publish.assert_awaited_once()
    payload = json.loads(js.publish.call_args.kwargs["payload"].decode("utf-8"))
    assert payload["event_type"] == "workflow.task.assigned"
    assert payload["payload"]["task_id"] == "task-001"
    assert payload["payload"]["role"] == "developer"


@pytest.mark.asyncio
async def test_publish_validation_required_publishes_enveloped_message() -> None:
    js = AsyncMock()
    adapter = NatsMessagingAdapter(nats_client=Mock(), jetstream=js)

    await adapter.publish_validation_required(
        task_id="task-001",
        story_id="story-001",
        validator_role="qa",
        artifact_type="tests",
    )

    js.publish.assert_awaited_once()
    payload = json.loads(js.publish.call_args.kwargs["payload"].decode("utf-8"))
    assert payload["event_type"] == "workflow.validation.required"
    assert payload["payload"]["validator_role"] == "qa"
    assert payload["payload"]["artifact_type"] == "tests"


@pytest.mark.asyncio
async def test_publish_task_completed_publishes_enveloped_message() -> None:
    js = AsyncMock()
    adapter = NatsMessagingAdapter(nats_client=Mock(), jetstream=js)

    await adapter.publish_task_completed(
        task_id="task-001",
        story_id="story-001",
        final_state="done",
    )

    js.publish.assert_awaited_once()
    payload = json.loads(js.publish.call_args.kwargs["payload"].decode("utf-8"))
    assert payload["event_type"] == "workflow.task.completed"
    assert payload["payload"]["final_state"] == "done"
