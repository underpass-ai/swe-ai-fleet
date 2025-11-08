"""Unit tests for ExecutionMode value object."""

import pytest
from core.agents_and_tools.common.domain.entities.execution_mode import (
    ExecutionMode,
    ExecutionModeEnum,
)


class TestExecutionModeCreation:
    """Test ExecutionMode value object creation."""

    def test_create_full_mode(self):
        """Test creating full execution mode."""
        mode = ExecutionMode(value=ExecutionModeEnum.FULL)

        assert mode.value == ExecutionModeEnum.FULL
        assert mode.is_full() is True
        assert mode.is_read_only() is False
        assert mode.allows_write() is True

    def test_create_read_only_mode(self):
        """Test creating read-only execution mode."""
        mode = ExecutionMode(value=ExecutionModeEnum.READ_ONLY)

        assert mode.value == ExecutionModeEnum.READ_ONLY
        assert mode.is_full() is False
        assert mode.is_read_only() is True
        assert mode.allows_write() is False

    def test_execution_mode_is_immutable(self):
        """Test mode is frozen (immutable)."""
        mode = ExecutionMode(value=ExecutionModeEnum.FULL)

        with pytest.raises(AttributeError):
            mode.value = ExecutionModeEnum.READ_ONLY  # type: ignore


class TestExecutionModeStringRepresentation:
    """Test ExecutionMode string methods."""

    def test_str_returns_mode_value(self):
        """Test __str__ returns mode value."""
        mode = ExecutionMode(value=ExecutionModeEnum.FULL)
        assert str(mode) == "full"

        mode_ro = ExecutionMode(value=ExecutionModeEnum.READ_ONLY)
        assert str(mode_ro) == "read_only"

