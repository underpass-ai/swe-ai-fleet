import json
from unittest.mock import AsyncMock, Mock

import pytest

from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.infrastructure.consumers.agent_work_completed_consumer import (
    AgentWorkCompletedConsumer,
)


def _enveloped_bytes(payload: dict[str, object]) -> bytes:
    envelope = EventEnvelope(
        event_type="agent.work.completed",
        payload=payload,
        idempotency_key="idemp-test-agent.work.completed",
        correlation_id="corr-test-agent.work.completed",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="workflow-tests",
    )
    return json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")


@pytest.mark.asyncio
async def test_handle_message_happy_path_executes_use_case() -> None:
    execute_uc = AsyncMock()
    new_state = Mock()
    new_state.get_current_state_value.return_value = "done"
    execute_uc.execute.return_value = new_state

    consumer = AgentWorkCompletedConsumer(
        nats_client=Mock(),
        jetstream=AsyncMock(),
        execute_workflow_action=execute_uc,
    )

    msg = AsyncMock()
    msg.data = _enveloped_bytes(
        {
            "task_id": "task-001",
            "action": "commit_code",
            "actor_role": "developer",
            "timestamp": "2025-12-30T10:00:00+00:00",
            "feedback": "ok",
        }
    )

    await consumer._handle_message(msg)

    execute_uc.execute.assert_awaited_once()
    args = execute_uc.execute.call_args.kwargs
    assert isinstance(args["task_id"], TaskId)
    assert str(args["task_id"]) == "task-001"
    assert args["feedback"] == "ok"


@pytest.mark.asyncio
async def test_handle_message_drops_invalid_envelope() -> None:
    execute_uc = AsyncMock()
    consumer = AgentWorkCompletedConsumer(
        nats_client=Mock(),
        jetstream=AsyncMock(),
        execute_workflow_action=execute_uc,
    )

    msg = AsyncMock()
    # Valid JSON but missing EventEnvelope required fields
    msg.data = json.dumps({"task_id": "task-001"}).encode("utf-8")

    await consumer._handle_message(msg)

    execute_uc.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_raises_on_missing_required_payload_field() -> None:
    execute_uc = AsyncMock()
    consumer = AgentWorkCompletedConsumer(
        nats_client=Mock(),
        jetstream=AsyncMock(),
        execute_workflow_action=execute_uc,
    )

    msg = AsyncMock()
    msg.data = _enveloped_bytes(
        {
            # Missing "action"
            "task_id": "task-001",
            "actor_role": "developer",
            "timestamp": "2025-12-30T10:00:00+00:00",
        }
    )

    with pytest.raises(KeyError):
        await consumer._handle_message(msg)

    execute_uc.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_propagates_unexpected_errors() -> None:
    execute_uc = AsyncMock()
    execute_uc.execute.side_effect = RuntimeError("boom")
    consumer = AgentWorkCompletedConsumer(
        nats_client=Mock(),
        jetstream=AsyncMock(),
        execute_workflow_action=execute_uc,
    )

    msg = AsyncMock()
    msg.data = _enveloped_bytes(
        {
            "task_id": "task-001",
            "action": "commit_code",
            "actor_role": "developer",
            "timestamp": "2025-12-30T10:00:00+00:00",
        }
    )

    with pytest.raises(RuntimeError, match="boom"):
        await consumer._handle_message(msg)
