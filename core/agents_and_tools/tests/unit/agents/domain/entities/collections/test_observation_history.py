"""Unit tests for Observation domain entity."""

import pytest
from core.agents_and_tools.agents.domain.entities.collections.observation_history import Observation
from core.agents_and_tools.agents.domain.entities.core.execution_step import ExecutionStep


class TestObservationCreation:
    """Test Observation entity creation."""

    def test_create_observation_with_required_fields(self):
        """Test creating observation with required fields."""
        step = ExecutionStep(tool="files", operation="read_file")
        result = {"content": "test content"}

        observation = Observation(
            iteration=1,
            action=step,
            result=result,
            success=True,
        )

        assert observation.iteration == 1
        assert observation.action == step
        assert observation.result == result
        assert observation.success is True
        assert observation.error is None

    def test_create_observation_with_error(self):
        """Test creating observation with error."""
        step = ExecutionStep(tool="files", operation="read_file")

        observation = Observation(
            iteration=1,
            action=step,
            result={},
            success=False,
            error="File not found",
        )

        assert observation.success is False
        assert observation.error == "File not found"


class TestObservationImmutability:
    """Test Observation immutability."""

    def test_observation_is_immutable(self):
        """Test observation is frozen (immutable)."""
        step = ExecutionStep(tool="files", operation="read_file")
        observation = Observation(
            iteration=1,
            action=step,
            result={},
            success=True,
        )

        with pytest.raises(AttributeError):
            observation.success = False  # type: ignore

        with pytest.raises(AttributeError):
            observation.error = "new error"  # type: ignore

