"""Unit tests for Operations collection."""

from datetime import datetime

from core.agents_and_tools.agents.domain.entities import Operation, Operations


class TestOperationsCreation:
    """Test Operations collection creation."""

    def test_create_empty_operations(self):
        """Test creating empty operations collection."""
        operations = Operations()

        assert operations.items == []
        assert operations.count() == 0

    def test_create_operations_with_items(self):
        """Test creating operations collection with initial items."""
        timestamp = datetime.now()
        operation1 = Operation(
            tool_name="Tool1",
            operation_name="op1",
            params={},
            result={},
            timestamp=timestamp,
            success=True,
        )
        operation2 = Operation(
            tool_name="Tool2",
            operation_name="op2",
            params={},
            result={},
            timestamp=timestamp,
            success=False,
        )

        operations = Operations(items=[operation1, operation2])

        assert operations.count() == 2
        assert len(operations.items) == 2


class TestOperationsAdd:
    """Test Operations.add() method."""

    def test_add_successful_operation(self):
        """Test adding a successful operation."""
        operations = Operations()

        operations.add(
            tool_name="FileTool",
            operation="write_file",
            success=True,
            params={"path": "/test.txt"},
            result={"size": 1024},
        )

        assert operations.count() == 1
        assert len(operations.items) == 1
        op = operations.items[0]
        assert op.tool_name == "FileTool"
        assert op.operation_name == "write_file"
        assert op.params == {"path": "/test.txt"}
        assert op.result == {"size": 1024}
        assert op.success is True
        assert op.error is None

    def test_add_failed_operation(self):
        """Test adding a failed operation."""
        operations = Operations()

        operations.add(
            tool_name="FileTool",
            operation="read_file",
            success=False,
            params={"path": "/missing.txt"},
            error="File not found",
        )

        assert operations.count() == 1
        op = operations.items[0]
        assert op.success is False
        assert op.error == "File not found"

    def test_add_operation_with_duration(self):
        """Test adding operation with duration."""
        operations = Operations()

        operations.add(
            tool_name="TestTool",
            operation="test_op",
            success=True,
            duration_ms=3500,
        )

        op = operations.items[0]
        assert op.duration_ms == 3500

    def test_add_multiple_operations(self):
        """Test adding multiple operations."""
        operations = Operations()

        operations.add(tool_name="Tool1", operation="op1", success=True)
        operations.add(tool_name="Tool2", operation="op2", success=True)
        operations.add(tool_name="Tool3", operation="op3", success=False)

        assert operations.count() == 3
        assert len(operations.items) == 3

    def test_add_operation_with_default_params(self):
        """Test adding operation with None params defaults to empty dict."""
        operations = Operations()

        operations.add(
            tool_name="TestTool",
            operation="test_op",
            success=True,
            params=None,
            result=None,
        )

        op = operations.items[0]
        assert op.params == {}
        assert op.result == {}

    def test_add_operation_creates_timestamp(self):
        """Test that add() creates a timestamp for the operation."""
        operations = Operations()
        before = datetime.now()

        operations.add(tool_name="TestTool", operation="test_op", success=True)

        after = datetime.now()
        op = operations.items[0]
        assert before <= op.timestamp <= after


class TestOperationsGetAll:
    """Test Operations.get_all() method."""

    def test_get_all_returns_all_operations(self):
        """Test get_all returns all operations."""
        operations = Operations()
        operations.add(tool_name="Tool1", operation="op1", success=True)
        operations.add(tool_name="Tool2", operation="op2", success=True)
        operations.add(tool_name="Tool3", operation="op3", success=False)

        all_ops = operations.get_all()

        assert len(all_ops) == 3
        assert all_ops == operations.items

    def test_get_all_returns_empty_list_when_no_operations(self):
        """Test get_all returns empty list when no operations."""
        operations = Operations()

        all_ops = operations.get_all()

        assert all_ops == []
        assert len(all_ops) == 0


class TestOperationsGetByTool:
    """Test Operations.get_by_tool() method."""

    def test_get_by_tool_returns_matching_operations(self):
        """Test get_by_tool returns operations for specific tool."""
        operations = Operations()
        operations.add(tool_name="FileTool", operation="read", success=True)
        operations.add(tool_name="FileTool", operation="write", success=True)
        operations.add(tool_name="GitTool", operation="commit", success=True)
        operations.add(tool_name="FileTool", operation="delete", success=False)

        file_ops = operations.get_by_tool("FileTool")

        assert len(file_ops) == 3
        assert all(op.tool_name == "FileTool" for op in file_ops)
        assert file_ops[0].operation_name == "read"
        assert file_ops[1].operation_name == "write"
        assert file_ops[2].operation_name == "delete"

    def test_get_by_tool_returns_empty_list_when_no_matches(self):
        """Test get_by_tool returns empty list when no matches."""
        operations = Operations()
        operations.add(tool_name="FileTool", operation="read", success=True)

        git_ops = operations.get_by_tool("GitTool")

        assert git_ops == []
        assert len(git_ops) == 0

    def test_get_by_tool_is_case_sensitive(self):
        """Test get_by_tool is case sensitive."""
        operations = Operations()
        operations.add(tool_name="FileTool", operation="read", success=True)

        file_ops_lower = operations.get_by_tool("filetool")

        assert file_ops_lower == []


class TestOperationsGetByOperation:
    """Test Operations.get_by_operation() method."""

    def test_get_by_operation_returns_matching_operations(self):
        """Test get_by_operation returns operations with specific name."""
        operations = Operations()
        operations.add(tool_name="FileTool", operation="read", success=True)
        operations.add(tool_name="FileTool", operation="read", success=False)
        operations.add(tool_name="GitTool", operation="read", success=True)
        operations.add(tool_name="FileTool", operation="write", success=True)

        read_ops = operations.get_by_operation("read")

        assert len(read_ops) == 3
        assert all(op.operation_name == "read" for op in read_ops)
        assert read_ops[0].tool_name == "FileTool"
        assert read_ops[1].tool_name == "FileTool"
        assert read_ops[2].tool_name == "GitTool"

    def test_get_by_operation_returns_empty_list_when_no_matches(self):
        """Test get_by_operation returns empty list when no matches."""
        operations = Operations()
        operations.add(tool_name="FileTool", operation="read", success=True)

        write_ops = operations.get_by_operation("write")

        assert write_ops == []
        assert len(write_ops) == 0

    def test_get_by_operation_is_case_sensitive(self):
        """Test get_by_operation is case sensitive."""
        operations = Operations()
        operations.add(tool_name="FileTool", operation="read", success=True)

        read_ops_upper = operations.get_by_operation("READ")

        assert read_ops_upper == []


class TestOperationsGetSuccessful:
    """Test Operations.get_successful() method."""

    def test_get_successful_returns_only_successful_operations(self):
        """Test get_successful returns only successful operations."""
        operations = Operations()
        operations.add(tool_name="Tool1", operation="op1", success=True)
        operations.add(tool_name="Tool2", operation="op2", success=False)
        operations.add(tool_name="Tool3", operation="op3", success=True)
        operations.add(tool_name="Tool4", operation="op4", success=False)
        operations.add(tool_name="Tool5", operation="op5", success=True)

        successful = operations.get_successful()

        assert len(successful) == 3
        assert all(op.success is True for op in successful)
        assert successful[0].tool_name == "Tool1"
        assert successful[1].tool_name == "Tool3"
        assert successful[2].tool_name == "Tool5"

    def test_get_successful_returns_empty_list_when_no_successful(self):
        """Test get_successful returns empty list when no successful operations."""
        operations = Operations()
        operations.add(tool_name="Tool1", operation="op1", success=False)
        operations.add(tool_name="Tool2", operation="op2", success=False)

        successful = operations.get_successful()

        assert successful == []
        assert len(successful) == 0

    def test_get_successful_returns_all_when_all_successful(self):
        """Test get_successful returns all when all operations are successful."""
        operations = Operations()
        operations.add(tool_name="Tool1", operation="op1", success=True)
        operations.add(tool_name="Tool2", operation="op2", success=True)
        operations.add(tool_name="Tool3", operation="op3", success=True)

        successful = operations.get_successful()

        assert len(successful) == 3
        assert len(successful) == operations.count()


class TestOperationsGetFailed:
    """Test Operations.get_failed() method."""

    def test_get_failed_returns_only_failed_operations(self):
        """Test get_failed returns only failed operations."""
        operations = Operations()
        operations.add(tool_name="Tool1", operation="op1", success=True)
        operations.add(tool_name="Tool2", operation="op2", success=False)
        operations.add(tool_name="Tool3", operation="op3", success=True)
        operations.add(tool_name="Tool4", operation="op4", success=False)
        operations.add(tool_name="Tool5", operation="op5", success=True)

        failed = operations.get_failed()

        assert len(failed) == 2
        assert all(op.success is False for op in failed)
        assert failed[0].tool_name == "Tool2"
        assert failed[1].tool_name == "Tool4"

    def test_get_failed_returns_empty_list_when_no_failed(self):
        """Test get_failed returns empty list when no failed operations."""
        operations = Operations()
        operations.add(tool_name="Tool1", operation="op1", success=True)
        operations.add(tool_name="Tool2", operation="op2", success=True)

        failed = operations.get_failed()

        assert failed == []
        assert len(failed) == 0

    def test_get_failed_returns_all_when_all_failed(self):
        """Test get_failed returns all when all operations are failed."""
        operations = Operations()
        operations.add(tool_name="Tool1", operation="op1", success=False)
        operations.add(tool_name="Tool2", operation="op2", success=False)
        operations.add(tool_name="Tool3", operation="op3", success=False)

        failed = operations.get_failed()

        assert len(failed) == 3
        assert len(failed) == operations.count()


class TestOperationsCount:
    """Test Operations.count() method."""

    def test_count_returns_zero_for_empty_collection(self):
        """Test count returns zero for empty collection."""
        operations = Operations()

        assert operations.count() == 0

    def test_count_returns_correct_number(self):
        """Test count returns correct number of operations."""
        operations = Operations()

        assert operations.count() == 0

        operations.add(tool_name="Tool1", operation="op1", success=True)
        assert operations.count() == 1

        operations.add(tool_name="Tool2", operation="op2", success=True)
        assert operations.count() == 2

        operations.add(tool_name="Tool3", operation="op3", success=False)
        assert operations.count() == 3

    def test_count_matches_items_length(self):
        """Test count matches len(items)."""
        operations = Operations()
        operations.add(tool_name="Tool1", operation="op1", success=True)
        operations.add(tool_name="Tool2", operation="op2", success=True)
        operations.add(tool_name="Tool3", operation="op3", success=False)

        assert operations.count() == len(operations.items)
        assert operations.count() == 3


class TestOperationsComplexScenarios:
    """Test Operations collection with complex scenarios."""

    def test_filter_operations_by_multiple_criteria(self):
        """Test filtering operations by multiple criteria."""
        operations = Operations()
        operations.add(tool_name="FileTool", operation="read", success=True)
        operations.add(tool_name="FileTool", operation="write", success=True)
        operations.add(tool_name="FileTool", operation="read", success=False)
        operations.add(tool_name="GitTool", operation="read", success=True)

        # Get successful FileTool operations
        file_successful = [
            op
            for op in operations.get_by_tool("FileTool")
            if op.success
        ]
        assert len(file_successful) == 2

        # Get failed read operations
        failed_read = [
            op
            for op in operations.get_by_operation("read")
            if not op.success
        ]
        assert len(failed_read) == 1
        assert failed_read[0].tool_name == "FileTool"

    def test_operations_preserve_order(self):
        """Test that operations preserve insertion order."""
        operations = Operations()
        operations.add(tool_name="Tool1", operation="op1", success=True)
        operations.add(tool_name="Tool2", operation="op2", success=True)
        operations.add(tool_name="Tool3", operation="op3", success=True)

        all_ops = operations.get_all()

        assert all_ops[0].tool_name == "Tool1"
        assert all_ops[1].tool_name == "Tool2"
        assert all_ops[2].tool_name == "Tool3"

    def test_operations_with_different_timestamps(self):
        """Test operations can have different timestamps."""
        operations = Operations()
        import time

        operations.add(tool_name="Tool1", operation="op1", success=True)
        time.sleep(0.01)  # Small delay to ensure different timestamps
        operations.add(tool_name="Tool2", operation="op2", success=True)

        ops = operations.get_all()
        assert ops[0].timestamp < ops[1].timestamp

