"""Unit tests for AggregationStepHandler."""

import pytest

from core.ceremony_engine.domain.value_objects import (
    ContextEntry,
    ContextKey,
    ExecutionContext,
    Step,
    StepHandlerType,
    StepId,
    StepStatus,
)
from core.ceremony_engine.infrastructure.adapters.step_handlers.aggregation_step_handler import (
    AggregationStepHandler,
)


@pytest.mark.asyncio
async def test_aggregation_merge_single_value() -> None:
    handler = AggregationStepHandler()
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": ["input_data"], "aggregation_type": "merge"},
    )
    context = ExecutionContext(
        entries=(
            ContextEntry(key=ContextKey.INPUTS, value={"input_data": "value"}),
        )
    )

    result = await handler.execute(step, context)

    assert result.status == StepStatus.COMPLETED
    assert result.output["aggregated_result"] == "value"


@pytest.mark.asyncio
async def test_aggregation_merge_dicts() -> None:
    handler = AggregationStepHandler()
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": ["a", "b"], "aggregation_type": "merge"},
    )
    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.INPUTS,
                value={"a": {"x": 1}, "b": {"y": 2, "x": 3}},
            ),
        )
    )

    result = await handler.execute(step, context)

    assert result.output["aggregated_result"] == {"x": 3, "y": 2}


@pytest.mark.asyncio
async def test_aggregation_list() -> None:
    handler = AggregationStepHandler()
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": ["a", "b"], "aggregation_type": "list"},
    )
    context = ExecutionContext(
        entries=(ContextEntry(key=ContextKey.INPUTS, value={"a": 1, "b": 2}),)
    )

    result = await handler.execute(step, context)

    assert result.output["aggregated_result"] == [1, 2]


@pytest.mark.asyncio
async def test_aggregation_concat() -> None:
    handler = AggregationStepHandler()
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": ["a", "b"], "aggregation_type": "concat"},
    )
    context = ExecutionContext(
        entries=(ContextEntry(key=ContextKey.INPUTS, value={"a": "x", "b": "y"}),)
    )

    result = await handler.execute(step, context)

    assert result.output["aggregated_result"] == "xy"


@pytest.mark.asyncio
async def test_aggregation_rejects_missing_source() -> None:
    handler = AggregationStepHandler()
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": ["missing"], "aggregation_type": "merge"},
    )
    context = ExecutionContext(
        entries=(ContextEntry(key=ContextKey.INPUTS, value={"a": 1}),)
    )

    with pytest.raises(ValueError, match="source 'missing' not found"):
        await handler.execute(step, context)


@pytest.mark.asyncio
async def test_aggregation_reads_step_outputs() -> None:
    handler = AggregationStepHandler()
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": ["step_a"], "aggregation_type": "list"},
    )
    context = ExecutionContext(
        entries=(
            ContextEntry(
                key=ContextKey.STEP_OUTPUTS,
                value={"step_a": {"value": 1}},
            ),
        )
    )

    result = await handler.execute(step, context)

    assert result.output["aggregated_result"] == [{"value": 1}]
