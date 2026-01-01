"""Tests for IdempotencyState enum."""

import pytest

from core.shared.idempotency.idempotency_state import IdempotencyState


class TestIdempotencyState:
    """Test cases for IdempotencyState enum."""

    def test_pending_state(self):
        """Test PENDING state properties."""
        state = IdempotencyState.PENDING

        assert state.value == "PENDING"
        assert not state.is_terminal()
        assert not state.is_in_progress()

    def test_in_progress_state(self):
        """Test IN_PROGRESS state properties."""
        state = IdempotencyState.IN_PROGRESS

        assert state.value == "IN_PROGRESS"
        assert not state.is_terminal()
        assert state.is_in_progress()

    def test_completed_state(self):
        """Test COMPLETED state properties."""
        state = IdempotencyState.COMPLETED

        assert state.value == "COMPLETED"
        assert state.is_terminal()
        assert not state.is_in_progress()

    def test_state_values(self):
        """Test all state values are strings."""
        assert isinstance(IdempotencyState.PENDING.value, str)
        assert isinstance(IdempotencyState.IN_PROGRESS.value, str)
        assert isinstance(IdempotencyState.COMPLETED.value, str)
