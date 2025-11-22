"""Unit tests for StepExecutionResult domain entity."""

import pytest
from core.agents_and_tools.agents.domain.entities.results.step_execution_result import StepExecutionResult


class TestStepExecutionResultCreation:
    """Test StepExecutionResult entity creation."""

    def test_create_result_with_required_fields(self):
        """Test creating result with required fields."""
        result = StepExecutionResult(success=True, result={"content": "test"})

        assert result.success is True
        assert result.result == {"content": "test"}
        assert result.error is None
        assert result.operation is None
        assert result.tool_name is None

    def test_create_result_with_all_fields(self):
        """Test creating result with all fields."""
        result_data = {"content": "test", "size": 1024}

        result = StepExecutionResult(
            success=True,
            result=result_data,
            error=None,
            operation="read_file",
            tool_name="files",
        )

        assert result.success is True
        assert result.result == result_data
        assert result.error is None
        assert result.operation == "read_file"
        assert result.tool_name == "files"

    def test_create_failed_result(self):
        """Test creating failed result."""
        result = StepExecutionResult(
            success=False,
            result={},
            error="Operation failed",
            operation="read_file",
            tool_name="files",
        )

        assert result.success is False
        assert result.error == "Operation failed"


class TestStepExecutionResultImmutability:
    """Test StepExecutionResult immutability."""

    def test_result_is_immutable(self):
        """Test result is frozen (immutable)."""
        result = StepExecutionResult(success=True, result={})

        with pytest.raises(AttributeError):
            result.success = False  # type: ignore

        with pytest.raises(AttributeError):
            result.error = "new error"  # type: ignore


class TestStepExecutionResultEquality:
    """Test StepExecutionResult equality and comparison."""

    def test_results_with_same_values_are_equal(self):
        """Test results with identical values are equal."""
        result_data = {"key": "value"}
        result1 = StepExecutionResult(
            success=True,
            result=result_data,
            operation="read_file",
            tool_name="files",
        )
        result2 = StepExecutionResult(
            success=True,
            result=result_data,
            operation="read_file",
            tool_name="files",
        )

        assert result1 == result2

    def test_results_with_different_operations_are_not_equal(self):
        """Test results with different operations are not equal."""
        result1 = StepExecutionResult(success=True, result={}, operation="read_file")
        result2 = StepExecutionResult(success=True, result={}, operation="write_file")

        assert result1 != result2

