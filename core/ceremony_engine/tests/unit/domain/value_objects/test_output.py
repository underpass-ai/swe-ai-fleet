"""Unit tests for Output value object."""

import pytest

from core.ceremony_engine.domain.value_objects.output import Output


def test_output_happy_path() -> None:
    """Test creating a valid output."""
    output = Output(type="object")

    assert output.type == "object"
    assert output.schema is None


def test_output_with_schema() -> None:
    """Test creating an output with schema."""
    schema = {"sprint_id": "string", "story_ids": "array[string]"}
    output = Output(type="object", schema=schema)

    assert output.type == "object"
    assert output.schema == schema


def test_output_all_valid_types() -> None:
    """Test creating outputs with all valid types."""
    for output_type in ["object", "array", "string", "number", "boolean"]:
        output = Output(type=output_type)
        assert output.type == output_type


def test_output_rejects_empty_type() -> None:
    """Test that empty type raises ValueError."""
    with pytest.raises(ValueError, match="Output type cannot be empty"):
        Output(type="")


def test_output_rejects_whitespace_type() -> None:
    """Test that whitespace-only type raises ValueError."""
    with pytest.raises(ValueError, match="Output type cannot be empty"):
        Output(type="   ")


def test_output_rejects_invalid_type() -> None:
    """Test that invalid type raises ValueError."""
    with pytest.raises(ValueError, match="Output type must be one of"):
        Output(type="invalid_type")


def test_output_rejects_integer_type() -> None:
    """Test that integer (should be 'number') raises ValueError."""
    # Type is a string, so "integer" is not in valid types
    with pytest.raises(ValueError, match="Output type must be one of"):
        Output(type="integer")


def test_output_allows_none_schema() -> None:
    """Test that schema can be None."""
    output = Output(type="string", schema=None)
    assert output.schema is None


def test_output_is_immutable() -> None:
    """Test that output is immutable (frozen dataclass)."""
    output = Output(type="object", schema={"key": "value"})

    with pytest.raises(Exception):  # frozen dataclass raises exception on mutation
        output.type = "string"  # type: ignore[misc]
