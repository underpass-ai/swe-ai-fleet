"""Unit tests for StepHandlerRegistry."""

import pytest
from unittest.mock import AsyncMock

from core.ceremony_engine.application.ports.deliberation_port import DeliberationPort
from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.ceremony_engine.application.ports.task_extraction_port import TaskExtractionPort
from core.ceremony_engine.application.use_cases.submit_deliberation_usecase import (
    SubmitDeliberationUseCase,
)
from core.ceremony_engine.application.use_cases.submit_task_extraction_usecase import (
    SubmitTaskExtractionUseCase,
)
from core.ceremony_engine.domain.value_objects import (
    ContextEntry,
    ContextKey,
    ExecutionContext,
    Step,
    StepId,
    StepHandlerType,
    StepResult,
    StepStatus,
)
from core.ceremony_engine.infrastructure.adapters.step_handlers.step_handler_registry import (
    StepHandlerRegistry,
)
from core.shared.idempotency.idempotency_port import IdempotencyPort


@pytest.mark.asyncio
async def test_execute_step_deliberation() -> None:
    """Test executing deliberation step."""
    deliberation_port = AsyncMock(spec=DeliberationPort)
    deliberation_port.submit_backlog_review_deliberation.return_value = "delib-123"
    registry = StepHandlerRegistry(
        SubmitDeliberationUseCase(deliberation_port),
        SubmitTaskExtractionUseCase(AsyncMock(spec=TaskExtractionPort)),
        AsyncMock(spec=MessagingPort),
        AsyncMock(spec=IdempotencyPort),
    )
    step = Step(
        id=StepId("deliberate"),
        state="STARTED",
        handler=StepHandlerType.DELIBERATION_STEP,
        config={"prompt": "Test prompt", "role": "DEV", "num_agents": 2},
    )

    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"story_id": "story-1", "ceremony_id": "cer-1"},
            ),
        )
    )
    result = await registry.execute_step(step, context)

    assert result.status == StepStatus.COMPLETED
    assert "deliberation_id" in result.output


@pytest.mark.asyncio
async def test_execute_step_task_extraction() -> None:
    """Test executing task extraction step."""
    task_extraction_port = AsyncMock(spec=TaskExtractionPort)
    task_extraction_port.submit_task_extraction.return_value = "delib-456"
    registry = StepHandlerRegistry(
        SubmitDeliberationUseCase(AsyncMock(spec=DeliberationPort)),
        SubmitTaskExtractionUseCase(task_extraction_port),
        AsyncMock(spec=MessagingPort),
        AsyncMock(spec=IdempotencyPort),
    )
    step = Step(
        id=StepId("extract_tasks"),
        state="STARTED",
        handler=StepHandlerType.TASK_EXTRACTION_STEP,
        config={"source": "artifact-1"},
    )

    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={
                    "story_id": "story-1",
                    "ceremony_id": "cer-1",
                    "agent_deliberations": [
                        {"agent_id": "a1", "role": "DEV", "proposal": {"content": "x"}},
                    ],
                },
            ),
        )
    )
    result = await registry.execute_step(step, context)

    assert result.status == StepStatus.COMPLETED
    assert "deliberation_id" in result.output
    assert result.output["status"] == "submitted"


@pytest.mark.asyncio
async def test_execute_step_aggregation() -> None:
    """Test executing aggregation step."""
    registry = StepHandlerRegistry(
        SubmitDeliberationUseCase(AsyncMock(spec=DeliberationPort)),
        SubmitTaskExtractionUseCase(AsyncMock(spec=TaskExtractionPort)),
        AsyncMock(spec=MessagingPort),
        AsyncMock(spec=IdempotencyPort),
    )
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": ["step1", "step2"], "aggregation_type": "merge"},
    )
    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"step1": {"a": 1}, "step2": {"b": 2}},
            ),
        )
    )

    result = await registry.execute_step(step, context)

    assert result.status == StepStatus.COMPLETED


@pytest.mark.asyncio
async def test_execute_step_publish() -> None:
    """Test executing publish step."""
    messaging_port = AsyncMock(spec=MessagingPort)
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = None
    idempotency_port.mark_in_progress.return_value = True
    registry = StepHandlerRegistry(
        SubmitDeliberationUseCase(AsyncMock(spec=DeliberationPort)),
        SubmitTaskExtractionUseCase(AsyncMock(spec=TaskExtractionPort)),
        messaging_port,
        idempotency_port,
    )
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

    result = await registry.execute_step(step, context)

    assert result.status == StepStatus.COMPLETED
    messaging_port.publish_event.assert_awaited_once()
    assert result.output["published"] is True


@pytest.mark.asyncio
async def test_execute_step_human_gate_waiting() -> None:
    """Test executing human gate step when waiting for approval."""
    registry = StepHandlerRegistry(
        SubmitDeliberationUseCase(AsyncMock(spec=DeliberationPort)),
        SubmitTaskExtractionUseCase(AsyncMock(spec=TaskExtractionPort)),
        AsyncMock(spec=MessagingPort),
        AsyncMock(spec=IdempotencyPort),
    )
    step = Step(
        id=StepId("approve"),
        state="STARTED",
        handler=StepHandlerType.HUMAN_GATE_STEP,
        config={"role": "product_owner", "message": "Approve?"},
    )

    result = await registry.execute_step(step, ExecutionContext.empty())

    assert result.status == StepStatus.WAITING_FOR_HUMAN


@pytest.mark.asyncio
async def test_execute_step_human_gate_approved() -> None:
    """Test executing human gate step when approved."""
    registry = StepHandlerRegistry(
        SubmitDeliberationUseCase(AsyncMock(spec=DeliberationPort)),
        SubmitTaskExtractionUseCase(AsyncMock(spec=TaskExtractionPort)),
        AsyncMock(spec=MessagingPort),
        AsyncMock(spec=IdempotencyPort),
    )
    step = Step(
        id=StepId("approve"),
        state="STARTED",
        handler=StepHandlerType.HUMAN_GATE_STEP,
        config={"role": "product_owner", "message": "Approve?"},
    )

    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.HUMAN_APPROVALS,
                value={"approve:product_owner": True},
            ),
        )
    )
    result = await registry.execute_step(step, context)

    assert result.status == StepStatus.COMPLETED
    assert result.output["approved"] is True


@pytest.mark.asyncio
async def test_execute_step_human_gate_rejected() -> None:
    """Test executing human gate step when rejected."""
    registry = StepHandlerRegistry(
        SubmitDeliberationUseCase(AsyncMock(spec=DeliberationPort)),
        SubmitTaskExtractionUseCase(AsyncMock(spec=TaskExtractionPort)),
        AsyncMock(spec=MessagingPort),
        AsyncMock(spec=IdempotencyPort),
    )
    step = Step(
        id=StepId("approve"),
        state="STARTED",
        handler=StepHandlerType.HUMAN_GATE_STEP,
        config={"role": "product_owner", "message": "Approve?"},
    )

    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.HUMAN_APPROVALS,
                value={"approve:product_owner": False},
            ),
        )
    )
    result = await registry.execute_step(step, context)

    assert result.status == StepStatus.FAILED
    assert result.error_message is not None


@pytest.mark.asyncio
async def test_execute_step_publish() -> None:
    """Test executing publish step."""
    messaging_port = AsyncMock(spec=MessagingPort)
    idempotency_port = AsyncMock(spec=IdempotencyPort)
    idempotency_port.check_status.return_value = None
    idempotency_port.mark_in_progress.return_value = True
    registry = StepHandlerRegistry(
        SubmitDeliberationUseCase(AsyncMock(spec=DeliberationPort)),
        SubmitTaskExtractionUseCase(AsyncMock(spec=TaskExtractionPort)),
        messaging_port,
        idempotency_port,
    )
    step = Step(
        id=StepId("publish"),
        state="STARTED",
        handler=StepHandlerType.PUBLISH_STEP,
        config={"subject": "test.subject", "event_type": "test.event"},
    )
    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"ceremony_id": "cer-1", "correlation_id": "corr-1"},
            ),
        )
    )

    result = await registry.execute_step(step, context)

    assert result.status == StepStatus.COMPLETED
    assert result.output["published"] is True
    messaging_port.publish_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_step_unknown_handler() -> None:
    """Test executing step with unknown handler type."""
    registry = StepHandlerRegistry(
        SubmitDeliberationUseCase(AsyncMock(spec=DeliberationPort)),
        SubmitTaskExtractionUseCase(AsyncMock(spec=TaskExtractionPort)),
        AsyncMock(spec=MessagingPort),
        AsyncMock(spec=IdempotencyPort),
    )
    # Create step with invalid handler type (using a value that doesn't exist)
    # We'll use a mock step that bypasses validation
    from unittest.mock import Mock

    step = Mock(spec=Step)
    step.id = StepId("unknown")
    step.state = "STARTED"
    step.handler = Mock()  # Mock handler that doesn't match any registered
    step.handler.value = "invalid_handler_type"
    step.config = {"test": "value"}

    # This should fail when trying to execute
    with pytest.raises(ValueError, match="is not supported"):
        await registry.execute_step(step, ExecutionContext.empty())
