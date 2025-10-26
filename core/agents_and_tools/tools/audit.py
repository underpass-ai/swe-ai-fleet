"""
Audit trail system for tool operations.

Tracks all tool executions with timestamps, parameters, and results.
"""

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class AuditEntry:
    """Single audit entry for a tool operation."""

    timestamp: float
    tool: str
    operation: str
    params: dict[str, Any]
    success: bool
    metadata: dict[str, Any]
    workspace: str | None = None
    error: str | None = None


class AuditLogger:
    """
    Audit logger for tool operations.

    Logs all tool executions to:
    - File (NDJSON format)
    - Redis Stream (if available)
    - Neo4j (if available)
    """

    def __init__(
        self,
        log_file: str | Path | None = None,
        redis_client: Any | None = None,
        neo4j_driver: Any | None = None,
    ):
        """
        Initialize audit logger.

        Args:
            log_file: Path to audit log file (NDJSON format)
            redis_client: Optional Redis client for streaming
            neo4j_driver: Optional Neo4j driver for graph storage
        """
        self.log_file = Path(log_file) if log_file else None
        self.redis_client = redis_client
        self.neo4j_driver = neo4j_driver

        # Create log file if specified
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, entry: AuditEntry | dict[str, Any]) -> None:
        """
        Log an audit entry to all configured destinations.

        Args:
            entry: AuditEntry or dict with audit data
        """
        # Convert to AuditEntry if dict
        if isinstance(entry, dict):
            # Add timestamp if not present
            if "timestamp" not in entry:
                entry["timestamp"] = time.time()

            # Ensure required fields
            entry.setdefault("tool", "unknown")
            entry.setdefault("operation", "unknown")
            entry.setdefault("params", {})
            entry.setdefault("success", False)
            entry.setdefault("metadata", {})

            audit_entry = AuditEntry(**entry)
        else:
            audit_entry = entry

        # Log to file (NDJSON)
        if self.log_file:
            self._log_to_file(audit_entry)

        # Log to Redis Stream
        if self.redis_client:
            self._log_to_redis(audit_entry)

        # Log to Neo4j
        if self.neo4j_driver:
            self._log_to_neo4j(audit_entry)

    def _log_to_file(self, entry: AuditEntry) -> None:
        """Log entry to NDJSON file."""
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(asdict(entry)) + "\n")
        except Exception as e:
            # Don't fail on audit logging errors
            print(f"Warning: Failed to write audit log to file: {e}")

    def _log_to_redis(self, entry: AuditEntry) -> None:
        """Log entry to Redis Stream."""
        try:
            stream_name = "tool_audit"
            self.redis_client.xadd(
                stream_name,
                {
                    "timestamp": entry.timestamp,
                    "tool": entry.tool,
                    "operation": entry.operation,
                    "params": json.dumps(entry.params),
                    "success": str(entry.success),
                    "metadata": json.dumps(entry.metadata),
                    "workspace": entry.workspace or "",
                    "error": entry.error or "",
                },
                maxlen=10000,  # Keep last 10K entries
            )
        except Exception as e:
            # Don't fail on audit logging errors
            print(f"Warning: Failed to write audit log to Redis: {e}")

    def _log_to_neo4j(self, entry: AuditEntry) -> None:
        """Log entry to Neo4j as ToolExecution node."""
        try:
            query = """
            CREATE (e:ToolExecution {
                timestamp: $timestamp,
                tool: $tool,
                operation: $operation,
                params: $params,
                success: $success,
                metadata: $metadata,
                workspace: $workspace,
                error: $error
            })
            RETURN e
            """

            with self.neo4j_driver.session() as session:
                session.run(
                    query,
                    timestamp=entry.timestamp,
                    tool=entry.tool,
                    operation=entry.operation,
                    params=json.dumps(entry.params),
                    success=entry.success,
                    metadata=json.dumps(entry.metadata),
                    workspace=entry.workspace or "",
                    error=entry.error or "",
                )
        except Exception as e:
            # Don't fail on audit logging errors
            print(f"Warning: Failed to write audit log to Neo4j: {e}")

    def query_logs(
        self,
        tool: str | None = None,
        operation: str | None = None,
        success: bool | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Query audit logs from file.

        Args:
            tool: Filter by tool name
            operation: Filter by operation
            success: Filter by success status
            limit: Maximum entries to return

        Returns:
            List of audit entries matching filters
        """
        if not self.log_file or not self.log_file.exists():
            return []

        entries = []

        try:
            with open(self.log_file) as f:
                for line in f:
                    if len(entries) >= limit:
                        break

                    try:
                        entry = json.loads(line.strip())

                        # Apply filters
                        if tool and entry.get("tool") != tool:
                            continue
                        if operation and entry.get("operation") != operation:
                            continue
                        if success is not None and entry.get("success") != success:
                            continue

                        entries.append(entry)

                    except json.JSONDecodeError:
                        continue

            return entries

        except Exception as e:
            print(f"Warning: Failed to query audit logs: {e}")
            return []


# Global audit logger instance (can be configured at startup)
_global_audit_logger: AuditLogger | None = None


def configure_audit_logger(
    log_file: str | Path | None = None,
    redis_client: Any | None = None,
    neo4j_driver: Any | None = None,
) -> AuditLogger:
    """
    Configure global audit logger.

    Args:
        log_file: Path to audit log file
        redis_client: Optional Redis client
        neo4j_driver: Optional Neo4j driver

    Returns:
        Configured AuditLogger instance
    """
    global _global_audit_logger
    _global_audit_logger = AuditLogger(log_file, redis_client, neo4j_driver)
    return _global_audit_logger


def get_audit_logger() -> AuditLogger:
    """
    Get global audit logger instance.

    Returns:
        Global AuditLogger (creates in-memory logger if not configured)
    """
    global _global_audit_logger
    if _global_audit_logger is None:
        # Create default logger without persistence
        _global_audit_logger = AuditLogger()
    return _global_audit_logger


def audit_tool_operation(entry: dict[str, Any]) -> None:
    """
    Log tool operation to audit trail.

    Args:
        entry: Audit entry data

    Example:
        audit_tool_operation({
            "tool": "git",
            "operation": "commit",
            "params": {"message": "feat: add feature"},
            "success": True,
            "metadata": {"commit_sha": "abc123"},
            "workspace": "/workspace"
        })
    """
    logger = get_audit_logger()
    logger.log(entry)

