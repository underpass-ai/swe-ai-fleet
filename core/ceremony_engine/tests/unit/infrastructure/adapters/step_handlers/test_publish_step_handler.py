"""Unit tests for PublishStepHandler."""

from unittest.mock import AsyncMock

import pytest

from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.value_objects import (
    ContextEntry,
    ContextKey,
    ExecutionContext,
    Inputs,
    Output,
    Role,
    State,
    Step,
    StepHandlerType,
    StepId,
    StepStatus,
    Timeouts,
    Transition,
    TransitionTrigger,
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


def _create_definition_with_output_schema(
    output_name: str, schema: dict[str, str] | None
) -> CeremonyDefinition:
    """Create a test ceremony definition with an output schema."""
    states = (
        State(id="STARTED", description="Started", initial=True, terminal=False),
        State(id="COMPLETED", description="Completed", initial=False, terminal=True),
    )
    transitions = (
        Transition(
            from_state="STARTED",
            to_state="COMPLETED",
            trigger=TransitionTrigger("complete"),
            guards=(),
            description="Complete",
        ),
    )
    steps = (
        Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"subject": "test.subject", "event_type": "test.event"},
        ),
    )
    outputs = {}
    if schema is not None:
        outputs[output_name] = Output(type="object", schema=schema)
    else:
        outputs[output_name] = Output(type="object", schema=None)

    return CeremonyDefinition(
        version="1.0",
        name="test_ceremony",
        description="Test ceremony",
        inputs=Inputs(required=(), optional=()),
        outputs=outputs,
        states=states,
        transitions=transitions,
        steps=steps,
        guards={},
        roles=(Role(id="SYSTEM", description="System", allowed_actions=()),),
        timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
        retry_policies={},
    )


@pytest.mark.asyncio
async def test_publish_step_validates_payload_against_schema() -> None:
    """Test that publish step validates payload against output schema when defined."""
    messaging_port = AsyncMock(spec=MessagingPort)
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = None
    idempotency_port.mark_in_progress.return_value = True
    handler = PublishStepHandler(messaging_port, idempotency_port)

    schema = {
        "status": "string",
    }
    definition = _create_definition_with_output_schema("publication", schema)

    step = Step(
        id=StepId("publish_results"),
        state="STARTED",
        handler=StepHandlerType.PUBLISH_STEP,
        config={
            "subject": "test.subject",
            "event_type": "test.event",
            "output": "publication",
            "payload_template": {"status": "ok"},
        },
    )
    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"ceremony_id": "cer-1", "correlation_id": "corr-1"},
            ),
            ContextEntry(key=ContextKey.DEFINITION, value=definition),
        )
    )

    result = await handler.execute(step, context)

    assert result.status == StepStatus.COMPLETED
    messaging_port.publish_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_step_rejects_payload_missing_required_field() -> None:
    """Test that publish step rejects payload missing required schema fields."""
    messaging_port = AsyncMock(spec=MessagingPort)
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    handler = PublishStepHandler(messaging_port, idempotency_port)

    schema = {
        "status": "string",  # Required but missing in payload
    }
    definition = _create_definition_with_output_schema("publication", schema)

    step = Step(
        id=StepId("publish_results"),
        state="STARTED",
        handler=StepHandlerType.PUBLISH_STEP,
        config={
            "subject": "test.subject",
            "event_type": "test.event",
            "output": "publication",
            "payload_template": {},  # Missing "status"
        },
    )
    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"ceremony_id": "cer-1", "correlation_id": "corr-1"},
            ),
            ContextEntry(key=ContextKey.DEFINITION, value=definition),
        )
    )

    with pytest.raises(ValueError, match="missing required field: 'status'"):
        await handler.execute(step, context)

    messaging_port.publish_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_step_rejects_payload_with_wrong_type() -> None:
    """Test that publish step rejects payload with wrong field types."""
    messaging_port = AsyncMock(spec=MessagingPort)
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    handler = PublishStepHandler(messaging_port, idempotency_port)

    schema = {
        "count": "number",
    }
    definition = _create_definition_with_output_schema("publication", schema)

    step = Step(
        id=StepId("publish_results"),
        state="STARTED",
        handler=StepHandlerType.PUBLISH_STEP,
        config={
            "subject": "test.subject",
            "event_type": "test.event",
            "output": "publication",
            "payload_template": {"count": "not-a-number"},  # Wrong type
        },
    )
    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"ceremony_id": "cer-1", "correlation_id": "corr-1"},
            ),
            ContextEntry(key=ContextKey.DEFINITION, value=definition),
        )
    )

    with pytest.raises(ValueError, match="must be a number"):
        await handler.execute(step, context)

    messaging_port.publish_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_step_skips_validation_when_no_schema() -> None:
    """Test that publish step skips validation when output has no schema."""
    messaging_port = AsyncMock(spec=MessagingPort)
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = None
    idempotency_port.mark_in_progress.return_value = True
    handler = PublishStepHandler(messaging_port, idempotency_port)

    # Output with no schema
    definition = _create_definition_with_output_schema("publication", None)

    step = Step(
        id=StepId("publish_results"),
        state="STARTED",
        handler=StepHandlerType.PUBLISH_STEP,
        config={
            "subject": "test.subject",
            "event_type": "test.event",
            "output": "publication",
        },
    )
    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"ceremony_id": "cer-1", "correlation_id": "corr-1"},
            ),
            ContextEntry(key=ContextKey.DEFINITION, value=definition),
        )
    )

    result = await handler.execute(step, context)

    assert result.status == StepStatus.COMPLETED
    messaging_port.publish_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_step_skips_validation_when_no_definition_in_context() -> None:
    """Test that publish step skips validation when definition not in context (backward compatibility)."""
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
            "subject": "test.subject",
            "event_type": "test.event",
        },
    )
    # Context without DEFINITION (backward compatibility)
    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"ceremony_id": "cer-1", "correlation_id": "corr-1"},
            ),
        )
    )

    result = await handler.execute(step, context)

    assert result.status == StepStatus.COMPLETED
    messaging_port.publish_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_step_infers_output_name_from_step_id() -> None:
    """Test that publish step infers output name from step.id when not specified in config."""
    messaging_port = AsyncMock(spec=MessagingPort)
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = None
    idempotency_port.mark_in_progress.return_value = True
    handler = PublishStepHandler(messaging_port, idempotency_port)

    schema = {"status": "string"}
    # Output name "results" inferred from step.id "publish_results" -> "results"
    definition = _create_definition_with_output_schema("results", schema)

    step = Step(
        id=StepId("publish_results"),  # Will infer "results" from this (remove "publish_" prefix)
        state="STARTED",
        handler=StepHandlerType.PUBLISH_STEP,
        config={
            "subject": "test.subject",
            "event_type": "test.event",
            # No "output" in config - will infer from step.id
            "payload_template": {"status": "ok"},
        },
    )
    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"ceremony_id": "cer-1", "correlation_id": "corr-1"},
            ),
            ContextEntry(key=ContextKey.DEFINITION, value=definition),
        )
    )

    result = await handler.execute(step, context)

    assert result.status == StepStatus.COMPLETED
    messaging_port.publish_event.assert_awaited_once()
