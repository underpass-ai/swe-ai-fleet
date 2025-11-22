"""Unit tests for ExecutionStep domain entity."""

import pytest
from core.agents_and_tools.agents.domain.entities.core.execution_step import ExecutionStep


class TestExecutionStepCreation:
    """Test ExecutionStep entity creation."""

    def test_create_step_with_required_fields(self):
        """Test creating step with required fields."""
        step = ExecutionStep(tool="files", operation="read_file")

        assert step.tool == "files"
        assert step.operation == "read_file"
        assert step.params is None

    def test_create_step_with_params(self):
        """Test creating step with parameters."""
        params = {"path": "/test/file.txt", "encoding": "utf-8"}
        step = ExecutionStep(tool="files", operation="read_file", params=params)

        assert step.tool == "files"
        assert step.operation == "read_file"
        assert step.params == params

    def test_create_step_with_empty_params_dict(self):
        """Test creating step with empty params dict."""
        step = ExecutionStep(tool="files", operation="list_files", params={})

        assert step.params == {}


class TestExecutionStepValidation:
    """Test ExecutionStep validation."""

    def test_step_raises_error_on_empty_tool(self):
        """Test step raises error on empty tool."""
        with pytest.raises(ValueError, match="tool cannot be empty or whitespace"):
            ExecutionStep(tool="", operation="read_file")

    def test_step_raises_error_on_whitespace_tool(self):
        """Test step raises error on whitespace-only tool."""
        with pytest.raises(ValueError, match="tool cannot be empty or whitespace"):
            ExecutionStep(tool="   ", operation="read_file")

    def test_step_raises_error_on_empty_operation(self):
        """Test step raises error on empty operation."""
        with pytest.raises(ValueError, match="operation cannot be empty or whitespace"):
            ExecutionStep(tool="files", operation="")

    def test_step_raises_error_on_whitespace_operation(self):
        """Test step raises error on whitespace-only operation."""
        with pytest.raises(ValueError, match="operation cannot be empty or whitespace"):
            ExecutionStep(tool="files", operation="   ")

    def test_step_accepts_valid_tool_and_operation(self):
        """Test step accepts valid tool and operation."""
        step = ExecutionStep(tool="git", operation="commit")
        assert step.tool == "git"
        assert step.operation == "commit"


class TestExecutionStepImmutability:
    """Test ExecutionStep immutability."""

    def test_step_is_immutable(self):
        """Test step is frozen (immutable)."""
        step = ExecutionStep(tool="files", operation="read_file")

        with pytest.raises(AttributeError):
            step.tool = "git"  # type: ignore

        with pytest.raises(AttributeError):
            step.operation = "commit"  # type: ignore


class TestExecutionStepEquality:
    """Test ExecutionStep equality and comparison."""

    def test_steps_with_same_values_are_equal(self):
        """Test steps with identical values are equal."""
        params = {"path": "/test.txt"}
        step1 = ExecutionStep(tool="files", operation="read_file", params=params)
        step2 = ExecutionStep(tool="files", operation="read_file", params=params)

        assert step1 == step2

    def test_steps_with_different_tools_are_not_equal(self):
        """Test steps with different tools are not equal."""
        step1 = ExecutionStep(tool="files", operation="read_file")
        step2 = ExecutionStep(tool="git", operation="read_file")

        assert step1 != step2

    def test_steps_with_different_operations_are_not_equal(self):
        """Test steps with different operations are not equal."""
        step1 = ExecutionStep(tool="files", operation="read_file")
        step2 = ExecutionStep(tool="files", operation="write_file")

        assert step1 != step2

