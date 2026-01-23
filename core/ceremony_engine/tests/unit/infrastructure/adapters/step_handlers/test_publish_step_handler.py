"""Unit tests for PublishStepHandler."""

from unittest.mock import AsyncMock

import pytest

from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.ceremony_engine.domain.value_objects import (
    ContextEntry,
    ContextKey,
    ExecutionContext,
    Step,
    StepHandlerType,
    StepId,
    StepStatus,
)
from core.ceremony_engine.infrastructure.adapters.step_handlers.publish_step_handler import (
    PublishStepHandler,
)
from core.shared.idempotency.idempotency_port import IdempotencyPort
from core.shared.idempotency.idempotency_state import IdempotencyState


@pytest.mark.asyncio
async def test_publish_step_publishes_event() -> None:
    messaging_port = AsyncMock(spec=MessagingPort)
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = None
    idempotency_port.mark_in_progress.return_value = True
    handler = PublishStepHandler(messaging_port, idempotency_port)
    step = Step(
        id=StepId("publish_results"),
        state="STARTED",
        handler=StepHandlerType.PUBLISH_STEP,
        config={
            "subject": "planning.ceremony.completed",
            "event_type": "planning.ceremony.completed",
            "payload_template": {"status": "ok"},
        },
    )
    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"ceremony_id": "cer-1", "correlation_id": "corr-1"},
            ),
            ContextEntry(key=ContextKey.PUBLISH_DATA, value={"story_id": "story-1"}),
        )
    )

    result = await handler.execute(step, context)

    assert result.status == StepStatus.COMPLETED
    assert result.output["published"] is True
    messaging_port.publish_event.assert_awaited_once()
    call_kwargs = messaging_port.publish_event.call_args.kwargs
    assert call_kwargs["subject"] == "planning.ceremony.completed"
    assert call_kwargs["envelope"].event_type == "planning.ceremony.completed"
    assert call_kwargs["envelope"].correlation_id == "corr-1"
    assert call_kwargs["envelope"].payload["story_id"] == "story-1"


@pytest.mark.asyncio
async def test_publish_step_requires_ceremony_id() -> None:
    messaging_port = AsyncMock(spec=MessagingPort)
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    handler = PublishStepHandler(messaging_port, idempotency_port)
    step = Step(
        id=StepId("publish_results"),
        state="STARTED",
        handler=StepHandlerType.PUBLISH_STEP,
        config={"subject": "planning.ceremony.completed", "event_type": "planning.ceremony.completed"},
    )
    context = ExecutionContext(
        entries=(ContextEntry(key=ContextKey.INPUTS, value={}),)
    )

    with pytest.raises(ValueError, match="ceremony_id"):
        await handler.execute(step, context)


def test_publish_step_requires_messaging_port() -> None:
    with pytest.raises(ValueError, match="messaging_port is required"):
        PublishStepHandler(None, AsyncMock(spec=IdempotencyPort))  # type: ignore[arg-type]


def test_publish_step_requires_idempotency_port() -> None:
    with pytest.raises(ValueError, match="idempotency_port is required"):
        PublishStepHandler(AsyncMock(spec=MessagingPort), None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_publish_step_skips_when_idempotent() -> None:
    messaging_port = AsyncMock(spec=MessagingPort)
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = IdempotencyState.COMPLETED
    handler = PublishStepHandler(messaging_port, idempotency_port)
    step = Step(
        id=StepId("publish_results"),
        state="STARTED",
        handler=StepHandlerType.PUBLISH_STEP,
        config={"subject": "ceremony.test", "event_type": "ceremony.test"},
    )
    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"ceremony_id": "cer-1", "correlation_id": "corr-1"},
            ),
        )
    )

    result = await handler.execute(step, context)

    assert result.output["published"] is False
    messaging_port.publish_event.assert_not_awaited()
