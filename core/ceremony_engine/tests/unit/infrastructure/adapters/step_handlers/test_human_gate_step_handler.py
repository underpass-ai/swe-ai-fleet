"""Unit tests for HumanGateStepHandler."""

import pytest

from core.ceremony_engine.domain.value_objects import (
    ContextEntry,
    ContextKey,
    ExecutionContext,
    Step,
    StepId,
    StepHandlerType,
    StepStatus,
)
from core.ceremony_engine.infrastructure.adapters.step_handlers.human_gate_step_handler import (
    HumanGateStepHandler,
)


@pytest.mark.asyncio
async def test_execute_human_gate_waiting() -> None:
    """Test human gate step when waiting for approval."""
    handler = HumanGateStepHandler()
    step = Step(
        id=StepId("approve"),
        state="STARTED",
        handler=StepHandlerType.HUMAN_GATE_STEP,
        config={"role": "product_owner", "message": "Approve this?"},
    )

    result = await handler.execute(step, ExecutionContext.empty())

    assert result.status == StepStatus.WAITING_FOR_HUMAN
    assert result.output["waiting"] is True


@pytest.mark.asyncio
async def test_execute_human_gate_approved() -> None:
    """Test human gate step when approved."""
    handler = HumanGateStepHandler()
    step = Step(
        id=StepId("approve"),
        state="STARTED",
        handler=StepHandlerType.HUMAN_GATE_STEP,
        config={"role": "product_owner", "message": "Approve this?"},
    )

    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.HUMAN_APPROVALS,
                value={"approve:product_owner": True},
            ),
        )
    )
    result = await handler.execute(step, context)

    assert result.status == StepStatus.COMPLETED
    assert result.output["approved"] is True


@pytest.mark.asyncio
async def test_execute_human_gate_rejected() -> None:
    """Test human gate step when rejected."""
    handler = HumanGateStepHandler()
    step = Step(
        id=StepId("approve"),
        state="STARTED",
        handler=StepHandlerType.HUMAN_GATE_STEP,
        config={"role": "product_owner", "message": "Approve this?"},
    )

    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.HUMAN_APPROVALS,
                value={"approve:product_owner": False},
            ),
        )
    )
    result = await handler.execute(step, context)

    assert result.status == StepStatus.FAILED
    assert result.error_message is not None
    assert "rejected" in result.error_message.lower()


@pytest.mark.asyncio
async def test_execute_human_gate_missing_config() -> None:
    """Test human gate step with missing config."""
    handler = HumanGateStepHandler()
    # Step validation requires non-empty config, so we need to provide at least one key
    step = Step(
        id=StepId("approve"),
        state="STARTED",
        handler=StepHandlerType.HUMAN_GATE_STEP,
        config={"other_key": "value"},  # Missing role and message
    )

    with pytest.raises(ValueError, match="missing required keys"):
        await handler.execute(step, ExecutionContext.empty())
