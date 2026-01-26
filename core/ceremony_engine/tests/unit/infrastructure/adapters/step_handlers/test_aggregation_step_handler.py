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


@pytest.mark.asyncio
async def test_aggregation_merge_rejects_non_dict_sources() -> None:
    """Test that merge aggregation rejects sources that are not dicts."""
    handler = AggregationStepHandler()
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": ["a", "b"], "aggregation_type": "merge"},
    )
    context = ExecutionContext(
        entries=(
            ContextEntry(key=ContextKey.INPUTS, value={"a": {"x": 1}, "b": "not_a_dict"}),
        )
    )

    with pytest.raises(ValueError, match="merge aggregation requires all sources to be dicts"):
        await handler.execute(step, context)


@pytest.mark.asyncio
async def test_aggregation_concat_rejects_non_string_sources() -> None:
    """Test that concat aggregation rejects sources that are not strings."""
    handler = AggregationStepHandler()
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": ["a", "b"], "aggregation_type": "concat"},
    )
    context = ExecutionContext(
        entries=(ContextEntry(key=ContextKey.INPUTS, value={"a": "x", "b": 123}),)
    )

    with pytest.raises(ValueError, match="concat aggregation requires all sources to be strings"):
        await handler.execute(step, context)


@pytest.mark.asyncio
async def test_aggregation_rejects_empty_sources_list() -> None:
    """Test that aggregation rejects empty sources list."""
    handler = AggregationStepHandler()
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": [], "aggregation_type": "list"},
    )
    context = ExecutionContext(entries=())

    with pytest.raises(ValueError, match="sources must be a non-empty list"):
        await handler.execute(step, context)


@pytest.mark.asyncio
async def test_aggregation_rejects_non_list_sources() -> None:
    """Test that aggregation rejects non-list sources."""
    handler = AggregationStepHandler()
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": "not_a_list", "aggregation_type": "list"},
    )
    context = ExecutionContext(entries=())

    with pytest.raises(ValueError, match="sources must be a non-empty list"):
        await handler.execute(step, context)


@pytest.mark.asyncio
async def test_aggregation_rejects_empty_string_source() -> None:
    """Test that aggregation rejects empty string sources."""
    handler = AggregationStepHandler()
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": [""], "aggregation_type": "list"},
    )
    context = ExecutionContext(entries=())

    with pytest.raises(ValueError, match="sources must be non-empty strings"):
        await handler.execute(step, context)


@pytest.mark.asyncio
async def test_aggregation_rejects_non_string_source_items() -> None:
    """Test that aggregation rejects non-string source items."""
    handler = AggregationStepHandler()
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": [123], "aggregation_type": "list"},
    )
    context = ExecutionContext(entries=())

    with pytest.raises(ValueError, match="sources must be non-empty strings"):
        await handler.execute(step, context)


@pytest.mark.asyncio
async def test_aggregation_rejects_unsupported_aggregation_type() -> None:
    """Test that aggregation rejects unsupported aggregation types."""
    handler = AggregationStepHandler()
    step = Step(
        id=StepId("aggregate"),
        state="STARTED",
        handler=StepHandlerType.AGGREGATION_STEP,
        config={"sources": ["a"], "aggregation_type": "unsupported_type"},
    )
    context = ExecutionContext(
        entries=(ContextEntry(key=ContextKey.INPUTS, value={"a": 1}),)
    )

    with pytest.raises(ValueError, match="Unsupported aggregation_type"):
        await handler.execute(step, context)
