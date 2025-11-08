"""DataAccessAuditPort - Port for audit logging (RBAC L3)."""

from typing import Protocol

from core.context.domain.value_objects.data_access_log_entry import DataAccessLogEntry


class DataAccessAuditPort(Protocol):
    """Port for logging data access for RBAC L3 compliance.

    Implementations might:
    - Write to structured log files
    - Send to centralized logging (e.g., ELK, Datadog)
    - Store in audit database
    - Send to SIEM system

    IMPORTANT: Audit logging MUST be fail-safe.
    If logging fails, the operation should continue (but log the failure).
    """

    async def log_access(self, entry: DataAccessLogEntry) -> None:
        """Log a data access event.

        This method MUST be fail-safe:
        - If logging fails, catch exception and log error
        - Do NOT propagate exceptions to caller
        - Audit failures should not break business operations

        Args:
            entry: Audit log entry with access details
        """
        ...

    async def log_access_denied(
        self,
        user_id: str,
        role: str,
        story_id: str,
        reason: str,
    ) -> None:
        """Log an access denial (convenience method).

        Args:
            user_id: User identifier
            role: Role string
            story_id: Story identifier
            reason: Why access was denied
        """
        ...

    async def get_access_history(
        self,
        user_id: str | None = None,
        story_id: str | None = None,
        limit: int = 100,
    ) -> list[DataAccessLogEntry]:
        """Get access history (for audit review).

        Args:
            user_id: Filter by user (optional)
            story_id: Filter by story (optional)
            limit: Maximum entries to return

        Returns:
            List of audit log entries
        """
        ...

