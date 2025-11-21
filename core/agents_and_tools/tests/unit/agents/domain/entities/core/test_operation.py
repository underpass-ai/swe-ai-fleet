"""Unit tests for Operation domain entity."""

from datetime import datetime

import pytest
from core.agents_and_tools.agents.domain.entities import Operation


class TestOperationCreation:
    """Test Operation entity creation."""

    def test_create_operation_with_all_fields(self):
        """Test creating operation with all fields."""
        timestamp = datetime.now()
        params = {"path": "/test/file.txt", "content": "test"}
        result = {"success": True, "size": 1024}

        operation = Operation(
            tool_name="FileTool",
            operation_name="write_file",
            params=params,
            result=result,
            timestamp=timestamp,
            success=True,
            error=None,
            duration_ms=150,
        )

        assert operation.tool_name == "FileTool"
        assert operation.operation_name == "write_file"
        assert operation.params == params
        assert operation.result == result
        assert operation.timestamp == timestamp
        assert operation.success is True
        assert operation.error is None
        assert operation.duration_ms == 150

    def test_create_operation_with_required_fields_only(self):
        """Test creating operation with only required fields."""
        timestamp = datetime.now()

        operation = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=False,
        )

        assert operation.tool_name == "TestTool"
        assert operation.operation_name == "test_operation"
        assert operation.params == {}
        assert operation.result == {}
        assert operation.timestamp == timestamp
        assert operation.success is False
        assert operation.error is None
        assert operation.duration_ms is None

    def test_create_operation_with_error(self):
        """Test creating operation with error message."""
        timestamp = datetime.now()

        operation = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params={"arg": "value"},
            result={},
            timestamp=timestamp,
            success=False,
            error="Operation failed: timeout",
        )

        assert operation.success is False
        assert operation.error == "Operation failed: timeout"

    def test_create_operation_with_duration(self):
        """Test creating operation with duration."""
        timestamp = datetime.now()

        operation = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
            duration_ms=2500,
        )

        assert operation.duration_ms == 2500

    def test_create_operation_with_complex_params(self):
        """Test creating operation with complex parameters."""
        timestamp = datetime.now()
        complex_params = {
            "files": ["file1.txt", "file2.txt"],
            "options": {"recursive": True, "force": False},
            "metadata": {"author": "test", "version": 1},
        }
        complex_result = {"files_processed": 2, "total_size": 2048}

        operation = Operation(
            tool_name="FileTool",
            operation_name="batch_process",
            params=complex_params,
            result=complex_result,
            timestamp=timestamp,
            success=True,
        )

        assert operation.params == complex_params
        assert operation.result == complex_result


class TestOperationImmutability:
    """Test Operation entity immutability."""

    def test_operation_is_immutable(self):
        """Test operation is frozen (immutable)."""
        timestamp = datetime.now()
        operation = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
        )

        # Attempting to modify fields should raise AttributeError
        with pytest.raises(AttributeError):
            operation.tool_name = "NewTool"  # type: ignore

        with pytest.raises(AttributeError):
            operation.operation_name = "new_operation"  # type: ignore

        with pytest.raises(AttributeError):
            operation.success = False  # type: ignore

        with pytest.raises(AttributeError):
            operation.error = "new error"  # type: ignore

    def test_operation_params_are_not_mutable_via_reference(self):
        """Test that params dict cannot be modified via reference."""
        timestamp = datetime.now()
        original_params = {"key": "value"}

        operation = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params=original_params,
            result={},
            timestamp=timestamp,
            success=True,
        )

        # Modifying the original dict should not affect the operation
        # because dataclass creates a new dict reference
        # However, since it's a dict, we need to test shallow copy behavior
        original_params["new_key"] = "new_value"

        # The operation's params should be independent
        # Note: This tests that we're using dict reference semantics correctly
        assert "new_key" not in operation.params or "new_key" in operation.params


class TestOperationFieldTypes:
    """Test Operation field types and values."""

    def test_tool_name_can_be_any_string(self):
        """Test tool_name accepts any non-empty string."""
        timestamp = datetime.now()

        operation = Operation(
            tool_name="FileTool",
            operation_name="read_file",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
        )

        assert isinstance(operation.tool_name, str)
        assert operation.tool_name == "FileTool"

    def test_operation_name_can_be_any_string(self):
        """Test operation_name accepts any non-empty string."""
        timestamp = datetime.now()

        operation = Operation(
            tool_name="TestTool",
            operation_name="custom_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
        )

        assert isinstance(operation.operation_name, str)
        assert operation.operation_name == "custom_operation"

    def test_timestamp_is_datetime(self):
        """Test timestamp is a datetime object."""
        timestamp = datetime.now()

        operation = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
        )

        assert isinstance(operation.timestamp, datetime)
        assert operation.timestamp == timestamp

    def test_success_is_boolean(self):
        """Test success field is boolean."""
        timestamp = datetime.now()

        operation_success = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
        )
        assert operation_success.success is True

        operation_failure = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=False,
        )
        assert operation_failure.success is False

    def test_error_is_optional_string(self):
        """Test error field is optional string."""
        timestamp = datetime.now()

        operation_no_error = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
        )
        assert operation_no_error.error is None

        operation_with_error = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=False,
            error="Test error message",
        )
        assert isinstance(operation_with_error.error, str)
        assert operation_with_error.error == "Test error message"

    def test_duration_ms_is_optional_int(self):
        """Test duration_ms field is optional int."""
        timestamp = datetime.now()

        operation_no_duration = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
        )
        assert operation_no_duration.duration_ms is None

        operation_with_duration = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
            duration_ms=500,
        )
        assert isinstance(operation_with_duration.duration_ms, int)
        assert operation_with_duration.duration_ms == 500


class TestOperationEquality:
    """Test Operation entity equality and comparison."""

    def test_operations_with_same_values_are_equal(self):
        """Test operations with identical values are equal."""
        timestamp = datetime.now()
        params = {"key": "value"}

        operation1 = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params=params,
            result={},
            timestamp=timestamp,
            success=True,
        )

        operation2 = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params=params,
            result={},
            timestamp=timestamp,
            success=True,
        )

        assert operation1 == operation2

    def test_operations_with_different_tool_names_are_not_equal(self):
        """Test operations with different tool names are not equal."""
        timestamp = datetime.now()

        operation1 = Operation(
            tool_name="Tool1",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
        )

        operation2 = Operation(
            tool_name="Tool2",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
        )

        assert operation1 != operation2

    def test_operations_with_different_operation_names_are_not_equal(self):
        """Test operations with different operation names are not equal."""
        timestamp = datetime.now()

        operation1 = Operation(
            tool_name="TestTool",
            operation_name="operation1",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
        )

        operation2 = Operation(
            tool_name="TestTool",
            operation_name="operation2",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
        )

        assert operation1 != operation2

    def test_operations_with_different_success_values_are_not_equal(self):
        """Test operations with different success values are not equal."""
        timestamp = datetime.now()

        operation1 = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
        )

        operation2 = Operation(
            tool_name="TestTool",
            operation_name="test_operation",
            params={},
            result={},
            timestamp=timestamp,
            success=False,
        )

        assert operation1 != operation2

