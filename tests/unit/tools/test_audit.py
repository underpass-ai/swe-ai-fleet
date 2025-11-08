"""Unit tests for audit logger."""

import json
import time
from unittest.mock import Mock

from core.agents_and_tools.tools.audit import AuditEntry, AuditLogger

# =============================================================================
# AuditEntry Tests
# =============================================================================

class TestAuditEntry:
    """Test AuditEntry dataclass."""

    def test_creates_entry_with_all_fields(self):
        """Should create entry with all fields."""
        entry = AuditEntry(
            timestamp=time.time(),
            tool="docker",
            operation="build",
            params={"tag": "myapp:v1"},
            success=True,
            metadata={"image": "myapp:v1"},
            workspace="/workspace",
            error=None,
        )

        assert entry.tool == "docker"
        assert entry.operation == "build"
        assert entry.success is True

    def test_creates_entry_with_optional_fields_none(self):
        """Should allow workspace and error to be None."""
        entry = AuditEntry(
            timestamp=time.time(),
            tool="git",
            operation="status",
            params={},
            success=True,
            metadata={},
        )

        assert entry.workspace is None
        assert entry.error is None


# =============================================================================
# AuditLogger Initialization Tests
# =============================================================================

class TestAuditLoggerInitialization:
    """Test AuditLogger initialization."""

    def test_creates_logger_with_file_only(self, tmp_path):
        """Should create logger with file path."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        assert logger.log_file == log_file
        assert logger.redis_client is None
        assert logger.neo4j_driver is None

    def test_creates_logger_with_all_backends(self, tmp_path):
        """Should create logger with all backends."""
        log_file = tmp_path / "audit.log"
        redis_mock = Mock()
        neo4j_mock = Mock()

        logger = AuditLogger(
            log_file=log_file,
            redis_client=redis_mock,
            neo4j_driver=neo4j_mock,
        )

        assert logger.log_file == log_file
        assert logger.redis_client == redis_mock
        assert logger.neo4j_driver == neo4j_mock

    def test_creates_log_directory_if_not_exists(self, tmp_path):
        """Should create parent directories for log file."""
        log_file = tmp_path / "logs" / "nested" / "audit.log"
        logger = AuditLogger(log_file=log_file)

        assert log_file.parent.exists()
        assert log_file.parent.is_dir()

    def test_creates_logger_without_backends(self):
        """Should create logger without any backend."""
        logger = AuditLogger()

        assert logger.log_file is None
        assert logger.redis_client is None
        assert logger.neo4j_driver is None


# =============================================================================
# File Logging Tests
# =============================================================================

class TestAuditLoggerFileLogging:
    """Test file-based audit logging."""

    def test_logs_entry_to_file(self, tmp_path):
        """Should log entry to NDJSON file."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        entry = AuditEntry(
            timestamp=1234567890.0,
            tool="docker",
            operation="build",
            params={"tag": "test"},
            success=True,
            metadata={"image": "test:latest"},
            workspace="/workspace",
        )

        logger.log(entry)

        # Verify file was written
        assert log_file.exists()
        content = log_file.read_text()
        logged = json.loads(content.strip())

        assert logged["tool"] == "docker"
        assert logged["operation"] == "build"
        assert logged["success"] is True

    def test_logs_dict_to_file(self, tmp_path):
        """Should convert dict to AuditEntry and log."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        entry_dict = {
            "tool": "git",
            "operation": "commit",
            "params": {"message": "test"},
            "success": True,
            "metadata": {},
        }

        logger.log(entry_dict)

        # Verify entry was logged
        assert log_file.exists()
        content = log_file.read_text()
        logged = json.loads(content.strip())

        assert logged["tool"] == "git"
        assert logged["operation"] == "commit"
        assert "timestamp" in logged  # Auto-added

    def test_appends_multiple_entries(self, tmp_path):
        """Should append multiple entries to same file."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        for i in range(3):
            entry = AuditEntry(
                timestamp=time.time(),
                tool="tool",
                operation=f"op{i}",
                params={},
                success=True,
                metadata={},
            )
            logger.log(entry)

        # Verify 3 entries
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_handles_file_write_error_gracefully(self, tmp_path, capsys):
        """Should handle file write errors without raising."""
        log_file = tmp_path / "readonly" / "audit.log"
        logger = AuditLogger(log_file=log_file)

        # Make parent directory read-only
        log_file.parent.chmod(0o444)

        entry = AuditEntry(
            timestamp=time.time(),
            tool="test",
            operation="test",
            params={},
            success=True,
            metadata={},
        )

        # Should not raise
        logger.log(entry)

        # Check warning was printed
        captured = capsys.readouterr()
        assert "Warning: Failed to write audit log to file" in captured.out

        # Cleanup
        log_file.parent.chmod(0o755)

    def test_skips_file_logging_when_no_file_configured(self):
        """Should skip file logging when log_file is None."""
        logger = AuditLogger(log_file=None)

        entry = AuditEntry(
            timestamp=time.time(),
            tool="test",
            operation="test",
            params={},
            success=True,
            metadata={},
        )

        # Should not raise
        logger.log(entry)


# =============================================================================
# Redis Logging Tests
# =============================================================================

class TestAuditLoggerRedisLogging:
    """Test Redis stream audit logging."""

    def test_logs_entry_to_redis(self, tmp_path):
        """Should log entry to Redis stream."""
        redis_mock = Mock()
        logger = AuditLogger(redis_client=redis_mock)

        entry = AuditEntry(
            timestamp=1234567890.0,
            tool="docker",
            operation="run",
            params={"image": "nginx"},
            success=True,
            metadata={"container_id": "abc123"},
            workspace="/workspace",
        )

        logger.log(entry)

        # Verify Redis xadd was called
        redis_mock.xadd.assert_called_once()
        call_args = redis_mock.xadd.call_args

        assert call_args[0][0] == "tool_audit"  # Stream name
        data = call_args[0][1]
        assert data["tool"] == "docker"
        assert data["operation"] == "run"
        assert data["success"] == "True"

    def test_handles_redis_error_gracefully(self, capsys):
        """Should handle Redis errors without raising."""
        redis_mock = Mock()
        redis_mock.xadd.side_effect = Exception("Redis connection failed")

        logger = AuditLogger(redis_client=redis_mock)

        entry = AuditEntry(
            timestamp=time.time(),
            tool="test",
            operation="test",
            params={},
            success=True,
            metadata={},
        )

        # Should not raise
        logger.log(entry)

        # Check warning was printed
        captured = capsys.readouterr()
        assert "Warning: Failed to write audit log to Redis" in captured.out

    def test_skips_redis_logging_when_no_client_configured(self):
        """Should skip Redis logging when redis_client is None."""
        logger = AuditLogger(redis_client=None)

        entry = AuditEntry(
            timestamp=time.time(),
            tool="test",
            operation="test",
            params={},
            success=True,
            metadata={},
        )

        # Should not raise
        logger.log(entry)


# =============================================================================
# Neo4j Logging Tests
# =============================================================================

class TestAuditLoggerNeo4jLogging:
    """Test Neo4j graph audit logging."""

    def test_logs_entry_to_neo4j(self):
        """Should log entry to Neo4j as ToolExecution node."""
        neo4j_mock = Mock()
        session_mock = Mock()
        context_manager_mock = Mock()
        context_manager_mock.__enter__ = Mock(return_value=session_mock)
        context_manager_mock.__exit__ = Mock(return_value=False)
        neo4j_mock.session.return_value = context_manager_mock

        logger = AuditLogger(neo4j_driver=neo4j_mock)

        entry = AuditEntry(
            timestamp=1234567890.0,
            tool="git",
            operation="commit",
            params={"message": "test"},
            success=True,
            metadata={"hash": "abc123"},
            workspace="/workspace",
            error=None,
        )

        logger.log(entry)

        # Verify Neo4j session was created
        neo4j_mock.session.assert_called_once()

        # Verify query was executed
        session_mock.run.assert_called_once()
        call_args = session_mock.run.call_args

        query = call_args[0][0]
        assert "CREATE (e:ToolExecution" in query
        assert call_args[1]["tool"] == "git"
        assert call_args[1]["operation"] == "commit"

    def test_handles_neo4j_error_gracefully(self, capsys):
        """Should handle Neo4j errors without raising."""
        neo4j_mock = Mock()
        neo4j_mock.session.side_effect = Exception("Neo4j connection failed")

        logger = AuditLogger(neo4j_driver=neo4j_mock)

        entry = AuditEntry(
            timestamp=time.time(),
            tool="test",
            operation="test",
            params={},
            success=True,
            metadata={},
        )

        # Should not raise
        logger.log(entry)

        # Check warning was printed
        captured = capsys.readouterr()
        assert "Warning: Failed to write audit log to Neo4j" in captured.out

    def test_skips_neo4j_logging_when_no_driver_configured(self):
        """Should skip Neo4j logging when neo4j_driver is None."""
        logger = AuditLogger(neo4j_driver=None)

        entry = AuditEntry(
            timestamp=time.time(),
            tool="test",
            operation="test",
            params={},
            success=True,
            metadata={},
        )

        # Should not raise
        logger.log(entry)


# =============================================================================
# Query Logs Tests
# =============================================================================

class TestAuditLoggerQueryLogs:
    """Test query_logs functionality."""

    def test_queries_all_logs_without_filters(self, tmp_path):
        """Should return all logs when no filters applied."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        # Log 3 entries
        for i in range(3):
            logger.log({
                "tool": f"tool{i}",
                "operation": "test",
                "params": {},
                "success": True,
                "metadata": {},
            })

        # Query without filters
        results = logger.query_logs()

        assert len(results) == 3

    def test_filters_by_tool(self, tmp_path):
        """Should filter logs by tool name."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        logger.log({"tool": "docker", "operation": "build", "params": {}, "success": True, "metadata": {}})
        logger.log({"tool": "git", "operation": "commit", "params": {}, "success": True, "metadata": {}})
        logger.log({"tool": "docker", "operation": "run", "params": {}, "success": True, "metadata": {}})

        results = logger.query_logs(tool="docker")

        assert len(results) == 2
        assert all(r["tool"] == "docker" for r in results)

    def test_filters_by_operation(self, tmp_path):
        """Should filter logs by operation."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        logger.log({"tool": "docker", "operation": "build", "params": {}, "success": True, "metadata": {}})
        logger.log({"tool": "docker", "operation": "run", "params": {}, "success": True, "metadata": {}})
        logger.log({"tool": "git", "operation": "build", "params": {}, "success": True, "metadata": {}})

        results = logger.query_logs(operation="build")

        assert len(results) == 2
        assert all(r["operation"] == "build" for r in results)

    def test_filters_by_success(self, tmp_path):
        """Should filter logs by success status."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        logger.log({"tool": "docker", "operation": "build", "params": {}, "success": True, "metadata": {}})
        logger.log({"tool": "docker", "operation": "run", "params": {}, "success": False, "metadata": {}})
        logger.log({"tool": "git", "operation": "commit", "params": {}, "success": True, "metadata": {}})

        results = logger.query_logs(success=False)

        assert len(results) == 1
        assert results[0]["success"] is False

    def test_filters_with_multiple_criteria(self, tmp_path):
        """Should filter logs with multiple criteria."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        logger.log({"tool": "docker", "operation": "build", "params": {}, "success": True, "metadata": {}})
        logger.log({"tool": "docker", "operation": "build", "params": {}, "success": False, "metadata": {}})
        logger.log({"tool": "docker", "operation": "run", "params": {}, "success": True, "metadata": {}})

        results = logger.query_logs(tool="docker", operation="build", success=True)

        assert len(results) == 1
        assert results[0]["tool"] == "docker"
        assert results[0]["operation"] == "build"
        assert results[0]["success"] is True

    def test_respects_limit(self, tmp_path):
        """Should respect limit parameter."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        # Log 10 entries
        for i in range(10):
            logger.log({"tool": "test", "operation": f"op{i}", "params": {}, "success": True, "metadata": {}})

        results = logger.query_logs(limit=5)

        assert len(results) == 5

    def test_returns_empty_when_file_not_exists(self, tmp_path):
        """Should return empty list when log file doesn't exist."""
        log_file = tmp_path / "nonexistent.log"
        logger = AuditLogger(log_file=log_file)

        results = logger.query_logs()

        assert results == []

    def test_returns_empty_when_no_file_configured(self):
        """Should return empty list when no file configured."""
        logger = AuditLogger(log_file=None)

        results = logger.query_logs()

        assert results == []

    def test_handles_malformed_json_gracefully(self, tmp_path):
        """Should skip malformed JSON lines."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        # Write some valid and some invalid JSON
        log_file.write_text(
            '{"tool": "valid1", "operation": "test", "params": {}, "success": true, "metadata": {}}\n'
            'INVALID JSON LINE\n'
            '{"tool": "valid2", "operation": "test", "params": {}, "success": true, "metadata": {}}\n'
        )

        results = logger.query_logs()

        # Should return only valid entries
        assert len(results) == 2
        assert results[0]["tool"] == "valid1"
        assert results[1]["tool"] == "valid2"

    def test_handles_query_error_gracefully(self, tmp_path, capsys):
        """Should handle query errors without raising."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        # Create file then make it unreadable
        log_file.write_text('{"tool": "test"}\n')
        log_file.chmod(0o000)

        # Should not raise
        results = logger.query_logs()

        assert results == []

        # Check warning was printed
        captured = capsys.readouterr()
        assert "Warning: Failed to query audit logs" in captured.out

        # Cleanup
        log_file.chmod(0o644)


# =============================================================================
# Helper Method Tests
# =============================================================================

class TestAuditLoggerHelperMethods:
    """Test extracted helper methods."""

    def test_parse_log_entry_parses_valid_json(self, tmp_path):
        """Should parse valid JSON line."""
        logger = AuditLogger()

        line = '{"tool": "docker", "operation": "build", "params": {}, "success": true, "metadata": {}}'
        entry = logger._parse_log_entry(line)

        assert entry is not None
        assert entry["tool"] == "docker"

    def test_parse_log_entry_returns_none_for_invalid_json(self, tmp_path):
        """Should return None for invalid JSON."""
        logger = AuditLogger()

        entry = logger._parse_log_entry("INVALID JSON")

        assert entry is None

    def test_matches_filters_returns_true_when_all_match(self):
        """Should return True when entry matches all filters."""
        logger = AuditLogger()

        entry = {
            "tool": "docker",
            "operation": "build",
            "success": True,
        }

        result = logger._matches_filters(entry, tool="docker", operation="build", success=True)

        assert result is True

    def test_matches_filters_returns_false_when_tool_mismatch(self):
        """Should return False when tool doesn't match."""
        logger = AuditLogger()

        entry = {"tool": "git", "operation": "build", "success": True}

        result = logger._matches_filters(entry, tool="docker", operation=None, success=None)

        assert result is False

    def test_matches_filters_returns_false_when_operation_mismatch(self):
        """Should return False when operation doesn't match."""
        logger = AuditLogger()

        entry = {"tool": "docker", "operation": "run", "success": True}

        result = logger._matches_filters(entry, tool=None, operation="build", success=None)

        assert result is False

    def test_matches_filters_returns_false_when_success_mismatch(self):
        """Should return False when success doesn't match."""
        logger = AuditLogger()

        entry = {"tool": "docker", "operation": "build", "success": False}

        result = logger._matches_filters(entry, tool=None, operation=None, success=True)

        assert result is False

    def test_matches_filters_returns_true_when_no_filters(self):
        """Should return True when no filters provided."""
        logger = AuditLogger()

        entry = {"tool": "docker", "operation": "build", "success": True}

        result = logger._matches_filters(entry, tool=None, operation=None, success=None)

        assert result is True


# =============================================================================
# Multi-Backend Logging Tests
# =============================================================================

class TestAuditLoggerMultiBackend:
    """Test logging to multiple backends simultaneously."""

    def test_logs_to_all_configured_backends(self, tmp_path):
        """Should log to all configured backends."""
        log_file = tmp_path / "audit.log"
        redis_mock = Mock()
        neo4j_mock = Mock()
        session_mock = Mock()
        context_manager_mock = Mock()
        context_manager_mock.__enter__ = Mock(return_value=session_mock)
        context_manager_mock.__exit__ = Mock(return_value=False)
        neo4j_mock.session.return_value = context_manager_mock

        logger = AuditLogger(
            log_file=log_file,
            redis_client=redis_mock,
            neo4j_driver=neo4j_mock,
        )

        entry = AuditEntry(
            timestamp=time.time(),
            tool="docker",
            operation="build",
            params={},
            success=True,
            metadata={},
        )

        logger.log(entry)

        # Verify all backends were called
        assert log_file.exists()  # File
        redis_mock.xadd.assert_called_once()  # Redis
        session_mock.run.assert_called_once()  # Neo4j

    def test_continues_if_one_backend_fails(self, tmp_path, capsys):
        """Should continue logging to other backends if one fails."""
        log_file = tmp_path / "audit.log"
        redis_mock = Mock()
        redis_mock.xadd.side_effect = Exception("Redis failed")
        neo4j_mock = Mock()
        session_mock = Mock()
        context_manager_mock = Mock()
        context_manager_mock.__enter__ = Mock(return_value=session_mock)
        context_manager_mock.__exit__ = Mock(return_value=False)
        neo4j_mock.session.return_value = context_manager_mock

        logger = AuditLogger(
            log_file=log_file,
            redis_client=redis_mock,
            neo4j_driver=neo4j_mock,
        )

        entry = AuditEntry(
            timestamp=time.time(),
            tool="docker",
            operation="build",
            params={},
            success=True,
            metadata={},
        )

        logger.log(entry)

        # File and Neo4j should still work
        assert log_file.exists()
        session_mock.run.assert_called_once()

        # Redis error should be logged
        captured = capsys.readouterr()
        assert "Warning: Failed to write audit log to Redis" in captured.out


# =============================================================================
# Dict Entry Conversion Tests
# =============================================================================

class TestAuditLoggerDictConversion:
    """Test conversion of dict to AuditEntry."""

    def test_adds_timestamp_when_missing(self, tmp_path):
        """Should add timestamp to dict entry."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        before = time.time()
        logger.log({
            "tool": "test",
            "operation": "test",
            "params": {},
            "success": True,
            "metadata": {},
        })
        after = time.time()

        # Verify timestamp was added
        content = log_file.read_text()
        logged = json.loads(content.strip())

        assert "timestamp" in logged
        assert before <= logged["timestamp"] <= after

    def test_preserves_existing_timestamp(self, tmp_path):
        """Should preserve timestamp if already in dict."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        custom_timestamp = 1234567890.0
        logger.log({
            "timestamp": custom_timestamp,
            "tool": "test",
            "operation": "test",
            "params": {},
            "success": True,
            "metadata": {},
        })

        content = log_file.read_text()
        logged = json.loads(content.strip())

        assert logged["timestamp"] == custom_timestamp

    def test_adds_default_values_for_missing_fields(self, tmp_path):
        """Should add default values for missing optional fields."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        # Minimal dict
        logger.log({})

        content = log_file.read_text()
        logged = json.loads(content.strip())

        # Verify defaults were added
        assert logged["tool"] == "unknown"
        assert logged["operation"] == "unknown"
        assert logged["params"] == {}
        assert logged["success"] is False
        assert logged["metadata"] == {}

