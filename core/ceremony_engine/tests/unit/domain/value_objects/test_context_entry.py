"""Unit tests for ContextEntry value object."""

import pytest

from core.ceremony_engine.domain.value_objects.context_entry import ContextEntry
from core.ceremony_engine.domain.value_objects.context_key import ContextKey


def test_context_entry_happy_path() -> None:
    """Test creating a valid ContextEntry."""
    entry = ContextEntry(key=ContextKey.INPUTS, value={"input_data": "value"})

    assert entry.key == ContextKey.INPUTS
    assert entry.value == {"input_data": "value"}


def test_context_entry_rejects_invalid_key_type() -> None:
    """Test that invalid key type raises ValueError."""
    with pytest.raises(ValueError, match="ContextEntry key must be ContextKey"):
        ContextEntry(key="inputs", value={})  # type: ignore[arg-type]
