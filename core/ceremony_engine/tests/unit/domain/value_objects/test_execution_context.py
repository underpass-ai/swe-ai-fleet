"""Unit tests for ExecutionContext value object."""

import pytest

from core.ceremony_engine.domain.value_objects.context_entry import ContextEntry
from core.ceremony_engine.domain.value_objects.context_key import ContextKey
from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext


def test_execution_context_empty() -> None:
    """Test creating an empty context."""
    context = ExecutionContext.empty()

    assert context.entries == ()
    assert context.get(ContextKey.INPUTS) is None


def test_execution_context_builder() -> None:
    """Test building context with builder."""
    context = (
        ExecutionContext.builder()
        .with_entry(ContextKey.INPUTS, {"input_data": "value"})
        .with_entry(ContextKey.HUMAN_APPROVALS, {"approved": True})
        .build()
    )

    assert context.get(ContextKey.INPUTS) == {"input_data": "value"}
    assert context.get_mapping(ContextKey.HUMAN_APPROVALS) == {"approved": True}


def test_execution_context_get_and_get_mapping() -> None:
    """Test get and get_mapping behavior."""
    context = ExecutionContext(
        entries=(
            ContextEntry(key=ContextKey.INPUTS, value={"input_data": "value"}),
            ContextEntry(key=ContextKey.HUMAN_APPROVALS, value={"approved": True}),
        )
    )

    assert context.get(ContextKey.INPUTS) == {"input_data": "value"}
    assert context.get_mapping(ContextKey.HUMAN_APPROVALS) == {"approved": True}
    assert context.get_mapping(ContextKey.PUBLISH_DATA) is None


def test_execution_context_rejects_duplicate_keys() -> None:
    """Test that duplicate keys raise ValueError."""
    with pytest.raises(ValueError, match="Duplicate context key"):
        ExecutionContext(
            entries=(
                ContextEntry(key=ContextKey.INPUTS, value={}),
                ContextEntry(key=ContextKey.INPUTS, value={}),
            )
        )


def test_execution_context_rejects_invalid_entry_type() -> None:
    """Test that invalid entry type raises ValueError."""
    with pytest.raises(ValueError, match="ExecutionContext entries must contain ContextEntry"):
        ExecutionContext(entries=(("inputs", {}),))  # type: ignore[arg-type]
