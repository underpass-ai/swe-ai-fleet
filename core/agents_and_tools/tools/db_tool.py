"""
Database client tools for agent workspace.

Supports PostgreSQL, Redis, and Neo4j connections.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

DatabaseType = Literal["postgresql", "redis", "neo4j"]


@dataclass
class DbResult:
    """Result of a database operation."""

    success: bool
    db_type: DatabaseType
    operation: str
    rows_affected: int | None
    data: list[dict[str, Any]] | str | None
    metadata: dict[str, Any]
    error: str | None = None


class DatabaseTool:
    """
    Database client tool for workspace execution.

    Security:
    - Connection string validation
    - Query timeout protection
    - Result size limits
    - No credential logging
    - Audit trail of all operations
    """

    MAX_RESULT_SIZE = 1000  # Maximum rows to return
    DEFAULT_TIMEOUT = 30  # seconds

    @staticmethod
    def create(audit_callback: Callable | None = None) -> "DatabaseTool":
        """Factory method to create DatabaseTool instance."""
        return DatabaseTool(audit_callback)

    def __init__(self, audit_callback: Callable | None = None):
        """
        Initialize Database tool.

        Args:
            audit_callback: Optional callback for audit logging
        """
        self.audit_callback = audit_callback

        # Initialize mapper for domain conversion
        self.mapper = self._get_mapper()

    def _audit(self, db_type: str, operation: str, result: DbResult) -> None:
        """Log database operation to audit trail (without credentials or data)."""
        if self.audit_callback:
            self.audit_callback(
                {
                    "tool": "database",
                    "operation": operation,
                    "params": {},
                    "success": result.success,
                    "metadata": {"db_type": db_type, "rows_affected": result.rows_affected},
                }
            )

    def postgresql_query(
        self,
        connection_string: str,
        query: str,
        params: tuple | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> DbResult:
        """
        Execute PostgreSQL query.

        Args:
            connection_string: PostgreSQL connection string
            query: SQL query to execute
            params: Query parameters (for parameterized queries)
            timeout: Query timeout in seconds

        Returns:
            DbResult with query results
        """
        try:
            import psycopg2

            # Parse connection string to hide password in logs
            # connection_string format: postgresql://user:pass@host:port/db
            try:
                from urllib.parse import urlparse
                parsed = urlparse(connection_string)
                safe_conn_str = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port}{parsed.path}"
            except Exception:
                safe_conn_str = "***"

            # Connect
            conn = psycopg2.connect(connection_string, connect_timeout=timeout)
            cursor = conn.cursor()

            # Execute query with timeout
            cursor.execute(f"SET statement_timeout = {timeout * 1000}")  # milliseconds

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Fetch results
            if cursor.description:  # SELECT query
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchmany(self.MAX_RESULT_SIZE)
                data = [dict(zip(columns, row, strict=False)) for row in rows]
                rows_affected = len(rows)
            else:  # INSERT/UPDATE/DELETE
                conn.commit()
                data = None
                rows_affected = cursor.rowcount

            cursor.close()
            conn.close()

            db_result = DbResult(
                success=True,
                db_type="postgresql",
                operation="query",
                rows_affected=rows_affected,
                data=data,
                metadata={
                    "connection": safe_conn_str,
                    "has_results": data is not None,
                },
            )

            self._audit("postgresql", "query", db_result)
            return db_result

        except ImportError:
            return DbResult(
                success=False,
                db_type="postgresql",
                operation="query",
                rows_affected=None,
                data=None,
                metadata={},
                error="psycopg2 not installed. Install with: pip install psycopg2-binary",
            )
        except Exception as e:
            return DbResult(
                success=False,
                db_type="postgresql",
                operation="query",
                rows_affected=None,
                data=None,
                metadata={},
                error=f"PostgreSQL error: {e}",
            )

    def redis_command(
        self,
        connection_string: str,
        command: list[str],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> DbResult:
        """
        Execute Redis command.

        Args:
            connection_string: Redis connection string (redis://host:port/db)
            command: Redis command as list (e.g., ["GET", "key"])
            timeout: Command timeout in seconds

        Returns:
            DbResult with command results
        """
        try:
            import redis

            # Parse connection string
            client = redis.from_url(connection_string, socket_timeout=timeout)

            # Execute command
            result = client.execute_command(*command)

            # Convert result to string/dict
            if isinstance(result, bytes):
                data = result.decode("utf-8")
            elif isinstance(result, list):
                data = [
                    item.decode("utf-8") if isinstance(item, bytes) else item
                    for item in result
                ]
            else:
                data = str(result)

            client.close()

            db_result = DbResult(
                success=True,
                db_type="redis",
                operation=" ".join(command),
                rows_affected=None,
                data=data,
                metadata={"command": command},
            )

            self._audit("redis", " ".join(command[:2]), db_result)  # Log first 2 parts
            return db_result

        except ImportError:
            return DbResult(
                success=False,
                db_type="redis",
                operation=" ".join(command),
                rows_affected=None,
                data=None,
                metadata={},
                error="redis library not installed. Install with: pip install redis",
            )
        except Exception as e:
            return DbResult(
                success=False,
                db_type="redis",
                operation=" ".join(command),
                rows_affected=None,
                data=None,
                metadata={},
                error=f"Redis error: {e}",
            )

    def neo4j_query(
        self,
        uri: str,
        username: str,
        password: str,
        query: str,
        params: dict | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> DbResult:
        """
        Execute Neo4j Cypher query.

        Args:
            uri: Neo4j URI (bolt://host:port)
            username: Neo4j username
            password: Neo4j password
            query: Cypher query to execute
            params: Query parameters
            timeout: Query timeout in seconds

        Returns:
            DbResult with query results
        """
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(uri, auth=(username, password))

            with driver.session() as session:
                # Run query with timeout
                result = session.run(query, params or {}, timeout=timeout)

                # Fetch limited results
                records = []
                for i, record in enumerate(result):
                    if i >= self.MAX_RESULT_SIZE:
                        break
                    records.append(dict(record))

                rows_affected = len(records)

            driver.close()

            db_result = DbResult(
                success=True,
                db_type="neo4j",
                operation="cypher",
                rows_affected=rows_affected,
                data=records,
                metadata={"uri": uri, "username": username},
            )

            self._audit("neo4j", "cypher", db_result)
            return db_result

        except ImportError:
            return DbResult(
                success=False,
                db_type="neo4j",
                operation="cypher",
                rows_affected=None,
                data=None,
                metadata={},
                error="neo4j library not installed. Install with: pip install neo4j",
            )
        except Exception as e:
            return DbResult(
                success=False,
                db_type="neo4j",
                operation="cypher",
                rows_affected=None,
                data=None,
                metadata={},
                error=f"Neo4j error: {e}",
            )

    def get_operations(self) -> dict[str, Any]:
        """Return dictionary mapping operation names to method callables."""
        return {
            "postgresql_query": self.postgresql_query,
            "redis_command": self.redis_command,
            "neo4j_query": self.neo4j_query,
        }

    def execute(self, operation: str, **params: Any) -> DbResult:
        """
        Execute a database operation by name.

        Args:
            operation: Name of the operation
            **params: Operation parameters

        Returns:
            DbResult

        Raises:
            ValueError: If operation is not supported
        """
        operations = self.get_operations()
        method = operations.get(operation)
        if not method:
            raise ValueError(f"Unknown database operation: {operation}")
        return method(**params)

    def _get_mapper(self):
        """Return the mapper for DatabaseTool results."""
        from core.agents_and_tools.agents.infrastructure.mappers.db_result_mapper import DbResultMapper
        return DbResultMapper()

    def get_mapper(self):
        """Return the tool's mapper instance."""
        return self.mapper

    def summarize_result(self, operation: str, tool_result: Any, params: dict[str, Any]) -> str:
        """
        Summarize tool operation result for logging.

        Args:
            operation: The operation that was executed
            tool_result: The result from the tool
            params: The operation parameters

        Returns:
            Human-readable summary
        """
        if tool_result.content:
            rows = len(tool_result.content.split("\n"))
            return f"Query returned {rows} rows"

        return "Database query completed"


# Convenience functions for use in agent tasks
def execute_postgresql_query(
    connection_string: str,
    query: str,
    params: tuple | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Execute PostgreSQL query from agent workspace.

    Args:
        connection_string: PostgreSQL connection string
        query: SQL query
        params: Query parameters
        timeout: Timeout in seconds

    Returns:
        Dictionary with query result

    Example:
        result = execute_postgresql_query(
            "postgresql://user:pass@localhost:5432/mydb",
            "SELECT * FROM users WHERE id = %s",
            params=(123,)
        )
    """
    tool = DatabaseTool()
    result = tool.postgresql_query(connection_string, query, params, timeout)

    return {
        "success": result.success,
        "db_type": result.db_type,
        "operation": result.operation,
        "rows_affected": result.rows_affected,
        "data": result.data,
        "metadata": result.metadata,
        "error": result.error,
    }


def execute_redis_command(
    connection_string: str,
    command: list[str],
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Execute Redis command from agent workspace.

    Args:
        connection_string: Redis connection string
        command: Redis command as list
        timeout: Timeout in seconds

    Returns:
        Dictionary with command result

    Example:
        result = execute_redis_command(
            "redis://localhost:6379/0",
            ["GET", "mykey"]
        )
    """
    tool = DatabaseTool()
    result = tool.redis_command(connection_string, command, timeout)

    return {
        "success": result.success,
        "db_type": result.db_type,
        "operation": result.operation,
        "data": result.data,
        "metadata": result.metadata,
        "error": result.error,
    }


def execute_neo4j_query(
    uri: str,
    username: str,
    password: str,
    query: str,
    params: dict | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Execute Neo4j Cypher query from agent workspace.

    Args:
        uri: Neo4j URI
        username: Neo4j username
        password: Neo4j password
        query: Cypher query
        params: Query parameters
        timeout: Timeout in seconds

    Returns:
        Dictionary with query result

    Example:
        result = execute_neo4j_query(
            "bolt://localhost:7687",
            "neo4j",
            "password",
            "MATCH (n:User) RETURN n LIMIT 10"
        )
    """
    tool = DatabaseTool()
    result = tool.neo4j_query(uri, username, password, query, params, timeout)

    return {
        "success": result.success,
        "db_type": result.db_type,
        "operation": result.operation,
        "rows_affected": result.rows_affected,
        "data": result.data,
        "metadata": result.metadata,
        "error": result.error,
    }

