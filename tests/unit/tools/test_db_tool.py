"""Unit tests for db_tool.py coverage - PostgreSQL, Redis, Neo4j operations."""

import sys
import pytest
from unittest.mock import Mock, MagicMock, patch

from core.agents_and_tools.tools.db_tool import DatabaseTool, DbResult


# =============================================================================
# PostgreSQL Query Tests
# =============================================================================

class TestDatabaseToolPostgreSQLQuery:
    """Test postgresql_query method."""

    def test_executes_select_query_successfully(self):
        """Should execute SELECT query and return results."""
        # Mock psycopg2 module
        mock_psycopg2 = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchmany.return_value = [(1, "test"), (2, "data")]
        mock_cursor.rowcount = 2
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2.connect.return_value = mock_conn

        with patch.dict('sys.modules', {'psycopg2': mock_psycopg2}):
            tool = DatabaseTool.create()
            result = tool.postgresql_query(
                connection_string="postgresql://user:pass@localhost:5432/db",
                query="SELECT id, name FROM users",
            )

        # Verify result
        assert result.success is True
        assert result.db_type == "postgresql"
        assert result.operation == "query"
        assert result.rows_affected == 2
        assert len(result.data) == 2
        assert result.data[0] == {"id": 1, "name": "test"}

        # Verify connection was closed
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_executes_insert_query_successfully(self):
        """Should execute INSERT query and commit."""
        mock_psycopg2 = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = None  # No results for INSERT
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2.connect.return_value = mock_conn

        with patch.dict('sys.modules', {'psycopg2': mock_psycopg2}):
            tool = DatabaseTool.create()
            result = tool.postgresql_query(
                connection_string="postgresql://user:pass@localhost:5432/db",
                query="INSERT INTO users (name) VALUES ('test')",
            )

        # Verify result
        assert result.success is True
        assert result.rows_affected == 1
        assert result.data is None  # No data for INSERT

        # Verify commit was called
        mock_conn.commit.assert_called_once()

    def test_executes_parameterized_query(self):
        """Should execute parameterized query with params."""
        mock_psycopg2 = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("count",)]
        mock_cursor.fetchmany.return_value = [(42,)]
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2.connect.return_value = mock_conn

        with patch.dict('sys.modules', {'psycopg2': mock_psycopg2}):
            tool = DatabaseTool.create()
            result = tool.postgresql_query(
                connection_string="postgresql://user:pass@localhost:5432/db",
                query="SELECT COUNT(*) FROM users WHERE active = %s",
                params=(True,),
            )

        # Verify params were passed
        mock_cursor.execute.assert_any_call(
            "SELECT COUNT(*) FROM users WHERE active = %s",
            (True,)
        )
        assert result.success is True

    def test_handles_connection_error(self):
        """Should handle PostgreSQL connection errors."""
        mock_psycopg2 = Mock()
        mock_psycopg2.connect.side_effect = Exception("Connection refused")

        with patch.dict('sys.modules', {'psycopg2': mock_psycopg2}):
            tool = DatabaseTool.create()
            result = tool.postgresql_query(
                connection_string="postgresql://user:pass@localhost:5432/db",
                query="SELECT 1",
            )

        assert result.success is False
        assert "PostgreSQL error" in result.error
        assert "Connection refused" in result.error

    def test_handles_psycopg2_not_installed(self):
        """Should handle missing psycopg2 library."""
        # Save original module state
        original_psycopg2 = sys.modules.get('psycopg2')
        
        try:
            # Remove psycopg2 from sys.modules
            if 'psycopg2' in sys.modules:
                del sys.modules['psycopg2']
            
            # Mock __import__ to raise ImportError for psycopg2
            import builtins
            original_import = builtins.__import__
            
            def mock_import(name, *args, **kwargs):
                if name == 'psycopg2':
                    raise ImportError("No module named 'psycopg2'")
                return original_import(name, *args, **kwargs)
            
            builtins.__import__ = mock_import
            
            tool = DatabaseTool.create()
            result = tool.postgresql_query(
                connection_string="postgresql://user:pass@localhost:5432/db",
                query="SELECT 1",
            )

            assert result.success is False
            assert "psycopg2 not installed" in result.error
        
        finally:
            # Restore original state
            builtins.__import__ = original_import
            if original_psycopg2 is not None:
                sys.modules['psycopg2'] = original_psycopg2


# =============================================================================
# Redis Command Tests  
# =============================================================================

class TestDatabaseToolRedisCommand:
    """Test redis_command method."""

    def test_executes_redis_get_command(self):
        """Should execute Redis GET command."""
        mock_redis_module = Mock()
        mock_client = Mock()
        mock_client.execute_command.return_value = b"value123"
        mock_redis_module.from_url.return_value = mock_client

        with patch.dict('sys.modules', {'redis': mock_redis_module}):
            tool = DatabaseTool.create()
            result = tool.redis_command(
                connection_string="redis://localhost:6379/0",
                command=["GET", "mykey"],
            )

        # Verify result
        assert result.success is True
        assert result.db_type == "redis"
        assert result.operation == "GET mykey"
        assert result.data == "value123"  # Decoded from bytes

        # Verify client was closed
        mock_client.close.assert_called_once()

    def test_handles_redis_list_result(self):
        """Should handle Redis commands returning lists."""
        mock_redis_module = Mock()
        mock_client = Mock()
        mock_client.execute_command.return_value = [b"item1", b"item2", b"item3"]
        mock_redis_module.from_url.return_value = mock_client

        with patch.dict('sys.modules', {'redis': mock_redis_module}):
            tool = DatabaseTool.create()
            result = tool.redis_command(
                connection_string="redis://localhost:6379/0",
                command=["LRANGE", "mylist", "0", "-1"],
            )

        assert result.success is True
        assert result.data == ["item1", "item2", "item3"]  # All decoded

    def test_handles_redis_connection_error(self):
        """Should handle Redis connection errors."""
        mock_redis_module = Mock()
        mock_redis_module.from_url.side_effect = Exception("Connection refused")

        with patch.dict('sys.modules', {'redis': mock_redis_module}):
            tool = DatabaseTool.create()
            result = tool.redis_command(
                connection_string="redis://localhost:6379/0",
                command=["GET", "key"],
            )

        assert result.success is False
        assert "Redis error" in result.error
        assert "Connection refused" in result.error

    def test_handles_redis_not_installed(self):
        """Should handle missing redis library."""
        # Save original module state
        original_redis = sys.modules.get('redis')
        
        try:
            # Remove redis from sys.modules
            if 'redis' in sys.modules:
                del sys.modules['redis']
            
            # Mock __import__ to raise ImportError for redis
            import builtins
            original_import = builtins.__import__
            
            def mock_import(name, *args, **kwargs):
                if name == 'redis':
                    raise ImportError("No module named 'redis'")
                return original_import(name, *args, **kwargs)
            
            builtins.__import__ = mock_import
            
            tool = DatabaseTool.create()
            result = tool.redis_command(
                connection_string="redis://localhost:6379/0",
                command=["GET", "key"],
            )

            assert result.success is False
            assert "redis library not installed" in result.error
        
        finally:
            # Restore original state
            builtins.__import__ = original_import
            if original_redis is not None:
                sys.modules['redis'] = original_redis


# =============================================================================
# Neo4j Query Tests
# =============================================================================

class TestDatabaseToolNeo4jQuery:
    """Test neo4j_query method."""

    def test_executes_neo4j_query_successfully(self):
        """Should execute Neo4j query and return results."""
        # Mock neo4j module
        mock_neo4j = Mock()
        mock_graph_db = Mock()
        mock_driver = Mock()
        mock_session = Mock()
        mock_result = Mock()
        
        # Mock record objects
        mock_record1 = {"name": "Alice", "age": 30}
        mock_record2 = {"name": "Bob", "age": 25}
        mock_result.__iter__ = Mock(return_value=iter([mock_record1, mock_record2]))
        
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_driver.session.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver
        mock_neo4j.GraphDatabase = mock_graph_db

        with patch.dict('sys.modules', {'neo4j': mock_neo4j}):
            tool = DatabaseTool.create()
            result = tool.neo4j_query(
                uri="neo4j://localhost:7687",
                username="neo4j",
                password="password",
                query="MATCH (n:Person) RETURN n.name AS name, n.age AS age",
            )

        # Verify result
        assert result.success is True
        assert result.db_type == "neo4j"
        assert result.operation == "cypher"
        assert len(result.data) == 2
        assert result.data[0] == {"name": "Alice", "age": 30}

        # Verify driver was closed
        mock_driver.close.assert_called_once()

    def test_handles_neo4j_connection_error(self):
        """Should handle Neo4j connection errors."""
        mock_neo4j = Mock()
        mock_graph_db = Mock()
        mock_graph_db.driver.side_effect = Exception("Connection failed")
        mock_neo4j.GraphDatabase = mock_graph_db

        with patch.dict('sys.modules', {'neo4j': mock_neo4j}):
            tool = DatabaseTool.create()
            result = tool.neo4j_query(
                uri="neo4j://localhost:7687",
                username="neo4j",
                password="wrongpass",
                query="MATCH (n) RETURN n",
            )

        assert result.success is False
        assert "Neo4j error" in result.error
        assert "Connection failed" in result.error

    def test_handles_neo4j_not_installed(self):
        """Should handle missing neo4j library."""
        # Save original module state
        original_neo4j = sys.modules.get('neo4j')
        
        try:
            # Remove neo4j from sys.modules
            if 'neo4j' in sys.modules:
                del sys.modules['neo4j']
            
            # Mock __import__ to raise ImportError for neo4j
            import builtins
            original_import = builtins.__import__
            
            def mock_import(name, *args, **kwargs):
                if name == 'neo4j':
                    raise ImportError("No module named 'neo4j'")
                return original_import(name, *args, **kwargs)
            
            builtins.__import__ = mock_import
            
            tool = DatabaseTool.create()
            result = tool.neo4j_query(
                uri="neo4j://localhost:7687",
                username="neo4j",
                password="password",
                query="MATCH (n) RETURN n",
            )

            assert result.success is False
            assert "neo4j library not installed" in result.error
        
        finally:
            # Restore original state
            builtins.__import__ = original_import
            if original_neo4j is not None:
                sys.modules['neo4j'] = original_neo4j


# =============================================================================
# Audit Callback Tests
# =============================================================================

class TestDatabaseToolAuditCallback:
    """Test audit callback functionality."""

    def test_calls_audit_callback_on_query(self):
        """Should call audit callback with operation details."""
        mock_psycopg2 = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = None
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2.connect.return_value = mock_conn

        audit_callback = Mock()
        
        with patch.dict('sys.modules', {'psycopg2': mock_psycopg2}):
            tool = DatabaseTool.create(audit_callback=audit_callback)
            
            tool.postgresql_query(
                connection_string="postgresql://user:pass@localhost:5432/db",
                query="SELECT 1",
            )

        # Verify callback was called
        audit_callback.assert_called_once()
        call_args = audit_callback.call_args[0][0]
        
        assert call_args["tool"] == "database"
        assert call_args["operation"] == "query"
        assert call_args["success"] is True
        assert call_args["metadata"]["db_type"] == "postgresql"


# =============================================================================
# Execute Method Tests
# =============================================================================

class TestDatabaseToolExecute:
    """Test execute() method."""

    def test_executes_postgresql_query_by_name(self):
        """Should execute postgresql_query via execute() method."""
        mock_psycopg2 = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = None
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2.connect.return_value = mock_conn

        with patch.dict('sys.modules', {'psycopg2': mock_psycopg2}):
            tool = DatabaseTool.create()
            result = tool.execute(
                operation="postgresql_query",
                connection_string="postgresql://user:pass@localhost:5432/db",
                query="SELECT 1",
            )

        assert result.success is True
        assert result.db_type == "postgresql"

    def test_execute_raises_on_invalid_operation(self):
        """Should raise ValueError for unsupported operation."""
        tool = DatabaseTool.create()
        
        with pytest.raises(ValueError, match="Unknown database operation"):
            tool.execute(operation="invalid_op")


# =============================================================================
# Summarize and Collect Artifacts Tests
# =============================================================================

class TestDatabaseToolSummarizeAndCollect:
    """Test summarize_result and collect_artifacts methods."""

    def test_summarize_result_with_content(self):
        """Should summarize result with content."""
        tool = DatabaseTool.create()
        
        # Create a mock result with content attribute
        mock_result = Mock()
        mock_result.content = "row1\nrow2\nrow3"
        
        summary = tool.summarize_result("query", mock_result, {})
        
        assert "3 rows" in summary

    def test_summarize_result_without_content(self):
        """Should handle result without content."""
        tool = DatabaseTool.create()
        
        # Create a mock result without content
        mock_result = Mock()
        mock_result.content = None
        
        summary = tool.summarize_result("query", mock_result, {})
        
        assert "Database query completed" in summary

    def test_collect_artifacts_with_content(self):
        """Should collect artifacts with content."""
        tool = DatabaseTool.create()
        
        # Create a mock result with content
        mock_result = Mock()
        mock_result.content = "row1\nrow2"
        
        artifacts = tool.collect_artifacts("query", mock_result, {})
        
        assert isinstance(artifacts, dict)
        assert artifacts["rows_returned"] == 2

    def test_collect_artifacts_without_content(self):
        """Should handle result without content."""
        tool = DatabaseTool.create()
        
        # Create a mock result without content
        mock_result = Mock()
        mock_result.content = None
        
        artifacts = tool.collect_artifacts("query", mock_result, {})
        
        assert isinstance(artifacts, dict)
        assert artifacts == {}
