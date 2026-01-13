"""Dual write ledger port for tracking dual persistence operations.

Following Hexagonal Architecture:
- This is a PORT (interface) in the application layer
- Infrastructure adapters implement this port
- Application depends on PORT, not concrete implementation
"""

from typing import Protocol

from planning.application.dto.dual_write_operation import DualWriteOperation


class DualWriteLedgerPort(Protocol):
    """Port for dual write ledger operations.

    Tracks operations that write to both Valkey (source of truth) and Neo4j (projection).
    If Neo4j write fails, the operation remains PENDING until reconciliation completes.

    Key format: planning:dualwrite:{operation_id}

    Following Hexagonal Architecture:
    - This is a PORT (interface)
    - Infrastructure provides ADAPTERS (ValkeyDualWriteLedgerAdapter, etc.)
    - Application depends on PORT, not concrete implementation
    """

    async def record_pending(
        self,
        operation_id: str,
    ) -> None:
        """Record a new PENDING operation in the ledger.

        Called after successfully writing to Valkey (source of truth) but
        before attempting Neo4j write. If Neo4j write fails, this entry
        will be used by the reconciler to retry.

        Args:
            operation_id: Unique identifier for this operation

        Raises:
            ValueError: If operation_id is empty
            Exception: If storage operation fails
        """
        ...

    async def mark_completed(
        self,
        operation_id: str,
    ) -> None:
        """Mark an operation as COMPLETED in the ledger.

        Called after successfully writing to both Valkey and Neo4j.
        This operation is now complete and no longer needs reconciliation.

        Args:
            operation_id: Unique identifier for this operation

        Raises:
            ValueError: If operation_id is empty
            Exception: If storage operation fails
        """
        ...

    async def record_failure(
        self,
        operation_id: str,
        error: str,
    ) -> None:
        """Record a failure attempt for a PENDING operation.

        Called when Neo4j write fails. Increments attempts counter and
        stores error message for observability.

        Args:
            operation_id: Unique identifier for this operation
            error: Error message from the failed attempt

        Raises:
            ValueError: If operation_id or error is empty
            Exception: If storage operation fails
        """
        ...

    async def get_operation(
        self,
        operation_id: str,
    ) -> DualWriteOperation | None:
        """Retrieve an operation from the ledger.

        Args:
            operation_id: Unique identifier for this operation

        Returns:
            DualWriteOperation if found, None otherwise

        Raises:
            ValueError: If operation_id is empty
            Exception: If storage operation fails
        """
        ...

    async def list_pending_operations(
        self,
        limit: int = 100,
    ) -> list[DualWriteOperation]:
        """List all PENDING operations in the ledger.

        Used by reconciler to find operations that need retry.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of PENDING DualWriteOperation entities

        Raises:
            ValueError: If limit is invalid
            Exception: If storage operation fails
        """
        ...

    async def list_old_pending_operations(
        self,
        age_seconds: float,
        limit: int = 100,
    ) -> list[DualWriteOperation]:
        """List PENDING operations older than specified age.

        Used by audit job to find operations that need reconciliation.

        Args:
            age_seconds: Minimum age in seconds (operations older than this)
            limit: Maximum number of operations to return

        Returns:
            List of PENDING DualWriteOperation entities older than age_seconds

        Raises:
            ValueError: If age_seconds is negative or limit is invalid
            Exception: If storage operation fails
        """
        ...
