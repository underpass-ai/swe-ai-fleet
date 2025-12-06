"""Unit tests for ContextSerializationHelper."""

from unittest.mock import Mock

import pytest
from services.context.infrastructure.helpers.context_serialization_helper import (
    ContextSerializationHelper,
)


def test_serialize_prompt_blocks_with_all_sections() -> None:
    """Test serializing prompt blocks with all sections present."""
    # Arrange
    prompt_blocks = Mock()
    prompt_blocks.system = "System instructions here"
    prompt_blocks.context = "Context information here"
    prompt_blocks.tools = "Tool descriptions here"

    # Act
    result = ContextSerializationHelper.serialize_prompt_blocks(prompt_blocks)

    # Assert
    assert "# System\n\nSystem instructions here" in result
    assert "# Context\n\nContext information here" in result
    assert "# Tools\n\nTool descriptions here" in result
    assert result.count("\n\n---\n\n") == 2  # Two separators for three sections


def test_serialize_prompt_blocks_with_only_system() -> None:
    """Test serializing prompt blocks with only system section."""
    # Arrange
    prompt_blocks = Mock()
    prompt_blocks.system = "System only"
    prompt_blocks.context = None
    prompt_blocks.tools = None

    # Act
    result = ContextSerializationHelper.serialize_prompt_blocks(prompt_blocks)

    # Assert
    assert "# System\n\nSystem only" in result
    assert "# Context" not in result
    assert "# Tools" not in result
    assert "---" not in result  # No separators with only one section


def test_serialize_prompt_blocks_with_only_context() -> None:
    """Test serializing prompt blocks with only context section."""
    # Arrange
    prompt_blocks = Mock()
    prompt_blocks.system = None
    prompt_blocks.context = "Context only"
    prompt_blocks.tools = None

    # Act
    result = ContextSerializationHelper.serialize_prompt_blocks(prompt_blocks)

    # Assert
    assert "# Context\n\nContext only" in result
    assert "# System" not in result
    assert "# Tools" not in result


def test_serialize_prompt_blocks_with_system_and_context() -> None:
    """Test serializing prompt blocks with system and context sections."""
    # Arrange
    prompt_blocks = Mock()
    prompt_blocks.system = "System data"
    prompt_blocks.context = "Context data"
    prompt_blocks.tools = None

    # Act
    result = ContextSerializationHelper.serialize_prompt_blocks(prompt_blocks)

    # Assert
    assert "# System\n\nSystem data" in result
    assert "# Context\n\nContext data" in result
    assert "# Tools" not in result
    assert result.count("\n\n---\n\n") == 1  # One separator for two sections


def test_serialize_prompt_blocks_with_empty_sections() -> None:
    """Test serializing prompt blocks with empty string sections (should be excluded)."""
    # Arrange
    prompt_blocks = Mock()
    prompt_blocks.system = ""
    prompt_blocks.context = "Has content"
    prompt_blocks.tools = ""

    # Act
    result = ContextSerializationHelper.serialize_prompt_blocks(prompt_blocks)

    # Assert
    # Empty strings are falsy, so they should not appear
    assert "# System" not in result
    assert "# Context\n\nHas content" in result
    assert "# Tools" not in result


def test_serialize_prompt_blocks_section_order() -> None:
    """Test that sections are serialized in correct order: System, Context, Tools."""
    # Arrange
    prompt_blocks = Mock()
    prompt_blocks.system = "FIRST"
    prompt_blocks.context = "SECOND"
    prompt_blocks.tools = "THIRD"

    # Act
    result = ContextSerializationHelper.serialize_prompt_blocks(prompt_blocks)

    # Assert: Check order by finding indices
    system_idx = result.find("FIRST")
    context_idx = result.find("SECOND")
    tools_idx = result.find("THIRD")

    assert system_idx < context_idx < tools_idx


def test_format_scope_reason_when_all_allowed() -> None:
    """Test formatting scope reason when all scopes are allowed."""
    # Arrange
    scope_check = Mock()
    scope_check.allowed = True
    scope_check.missing = []
    scope_check.extra = []

    # Act
    result = ContextSerializationHelper.format_scope_reason(scope_check)

    # Assert
    assert result == "All scopes are allowed"


def test_format_scope_reason_with_missing_scopes() -> None:
    """Test formatting scope reason with missing scopes."""
    # Arrange
    scope_check = Mock()
    scope_check.allowed = False
    scope_check.missing = ["admin", "write"]
    scope_check.extra = []

    # Act
    result = ContextSerializationHelper.format_scope_reason(scope_check)

    # Assert
    assert "Missing required scopes: admin, write" in result


def test_format_scope_reason_with_extra_scopes() -> None:
    """Test formatting scope reason with extra scopes."""
    # Arrange
    scope_check = Mock()
    scope_check.allowed = False
    scope_check.missing = []
    scope_check.extra = ["unauthorized", "invalid"]

    # Act
    result = ContextSerializationHelper.format_scope_reason(scope_check)

    # Assert
    assert "Extra scopes not allowed: unauthorized, invalid" in result


def test_format_scope_reason_with_both_missing_and_extra() -> None:
    """Test formatting scope reason with both missing and extra scopes."""
    # Arrange
    scope_check = Mock()
    scope_check.allowed = False
    scope_check.missing = ["required1", "required2"]
    scope_check.extra = ["extra1"]

    # Act
    result = ContextSerializationHelper.format_scope_reason(scope_check)

    # Assert
    assert "Missing required scopes: required1, required2" in result
    assert "Extra scopes not allowed: extra1" in result
    assert "; " in result  # Check separator


def test_format_scope_reason_with_single_missing() -> None:
    """Test formatting scope reason with single missing scope."""
    # Arrange
    scope_check = Mock()
    scope_check.allowed = False
    scope_check.missing = ["admin"]
    scope_check.extra = []

    # Act
    result = ContextSerializationHelper.format_scope_reason(scope_check)

    # Assert
    assert result == "Missing required scopes: admin"


def test_format_scope_reason_with_single_extra() -> None:
    """Test formatting scope reason with single extra scope."""
    # Arrange
    scope_check = Mock()
    scope_check.allowed = False
    scope_check.missing = []
    scope_check.extra = ["invalid"]

    # Act
    result = ContextSerializationHelper.format_scope_reason(scope_check)

    # Assert
    assert result == "Extra scopes not allowed: invalid"
