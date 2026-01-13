"""Valkey adapter for dual write ledger.

Following Hexagonal Architecture:
- Implements DualWriteLedgerPort
- Stores ledger entries in Valkey (Redis-compatible)
- Key format: planning:dualwrite:{operation_id}
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

import valkey

from planning.application.dto.dual_write_operation import (
    DualWriteOperation,
    DualWriteStatus,
)
from planning.application.ports.dual_write_ledger_port import DualWriteLedgerPort
from planning.infrastructure.adapters.valkey_config import ValkeyConfig
from planning.infrastructure.mappers.dual_write_operation_mapper import (
    DualWriteOperationMapper,
)

logger = logging.getLogger(__name__)

# Error messages
_OPERATION_ID_REQUIRED = "operation_id cannot be empty"
_ERROR_REQUIRED = "error cannot be empty"


class ValkeyDualWriteLedgerAdapter(DualWriteLedgerPort):
    """Valkey implementation of dual write ledger port.

    Storage Strategy:
    - Key: planning:dualwrite:{operation_id}
    - Value: JSON with operation data (status, attempts, last_error, timestamps)
    - Set: planning:dualwrite:pending → Set of operation_ids with PENDING status
    - No TTL (operations remain until explicitly marked COMPLETED)

    Following Hexagonal Architecture:
    - Infrastructure adapter implementing application port
    - No business logic, only storage operations
    """

    def __init__(self, config: ValkeyConfig | None = None):
        """Initialize Valkey dual write ledger adapter.

        Args:
            config: Valkey configuration (optional, uses env vars if not provided)
        """
        self.config = config or ValkeyConfig()

        # Create Valkey client (Redis-compatible)
        self.client = valkey.Valkey(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            decode_responses=self.config.decode_responses,
        )

        # Test connection
        self.client.ping()

        logger.info(
            f"Valkey dual write ledger adapter initialized: "
            f"{self.config.host}:{self.config.port}"
        )

    def close(self) -> None:
        """Close Valkey connection."""
        self.client.close()
        logger.info("Valkey dual write ledger adapter closed")

    def _operation_key(self, operation_id: str) -> str:
        """Get Redis key for an operation.

        Args:
            operation_id: Operation identifier

        Returns:
            Redis key string
        """
        return f"planning:dualwrite:{operation_id}"

    def _pending_set_key(self) -> str:
        """Get Redis key for pending operations set.

        Returns:
            Redis key string
        """
        return "planning:dualwrite:pending"

    async def record_pending(
        self,
        operation_id: str,
    ) -> None:
        """Record a new PENDING operation in the ledger.

        Args:
            operation_id: Unique identifier for this operation

        Raises:
            ValueError: If operation_id is empty
            Exception: If storage operation fails
        """
        if not operation_id:
            raise ValueError(_OPERATION_ID_REQUIRED)

        timestamp = datetime.now(UTC).isoformat()

        operation = DualWriteOperation(
            operation_id=operation_id,
            status=DualWriteStatus.PENDING,
            attempts=0,
            last_error=None,
            created_at=timestamp,
            updated_at=timestamp,
        )

        operation_dict = DualWriteOperationMapper.to_dict(operation)
        key = self._operation_key(operation_id)
        pending_set_key = self._pending_set_key()

        # Store operation and add to pending set (atomic transaction)
        await asyncio.to_thread(
            self._store_operation_and_add_to_pending,
            key,
            operation_dict,
            pending_set_key,
            operation_id,
        )

        logger.info(f"Recorded PENDING operation: {operation_id}")

    def _store_operation_and_add_to_pending(
        self,
        key: str,
        operation_dict: dict[str, Any],
        pending_set_key: str,
        operation_id: str,
    ) -> None:
        """Store operation and add to pending set (synchronous helper for asyncio.to_thread).

        Args:
            key: Redis key for operation
            operation_dict: Operation data as dictionary
            pending_set_key: Redis key for pending set
            operation_id: Operation identifier
        """
        pipe = self.client.pipeline()
        pipe.set(key, json.dumps(operation_dict))
        pipe.sadd(pending_set_key, operation_id)
        pipe.execute()

    async def mark_completed(
        self,
        operation_id: str,
    ) -> None:
        """Mark an operation as COMPLETED in the ledger.

        Args:
            operation_id: Unique identifier for this operation

        Raises:
            ValueError: If operation_id is empty
            Exception: If storage operation fails
        """
        if not operation_id:
            raise ValueError(_OPERATION_ID_REQUIRED)

        key = self._operation_key(operation_id)
        pending_set_key = self._pending_set_key()

        # Update operation status and remove from pending set (atomic transaction)
        await asyncio.to_thread(
            self._mark_completed_transaction,
            key,
            pending_set_key,
            operation_id,
        )

        logger.info(f"Marked operation COMPLETED: {operation_id}")

    def _mark_completed_transaction(
        self,
        key: str,
        pending_set_key: str,
        operation_id: str,
    ) -> None:
        """Mark operation as COMPLETED and remove from pending set (synchronous helper).

        Args:
            key: Redis key for operation
            pending_set_key: Redis key for pending set
            operation_id: Operation identifier
        """
        # Get current operation
        operation_json = self.client.get(key)
        if not operation_json:
            logger.warning(f"Operation not found in ledger: {operation_id}")
            return

        operation_dict = json.loads(operation_json)
        operation_dict["status"] = DualWriteStatus.COMPLETED.value
        operation_dict["updated_at"] = datetime.now(UTC).isoformat()

        # Update operation and remove from pending set (atomic)
        pipe = self.client.pipeline()
        pipe.set(key, json.dumps(operation_dict))
        pipe.srem(pending_set_key, operation_id)
        pipe.execute()

    async def record_failure(
        self,
        operation_id: str,
        error: str,
    ) -> None:
        """Record a failure attempt for a PENDING operation.

        Args:
            operation_id: Unique identifier for this operation
            error: Error message from the failed attempt

        Raises:
            ValueError: If operation_id or error is empty
            Exception: If storage operation fails
        """
        if not operation_id:
            raise ValueError(_OPERATION_ID_REQUIRED)

        if not error:
            raise ValueError(_ERROR_REQUIRED)

        key = self._operation_key(operation_id)

        await asyncio.to_thread(
            self._update_operation_failure,
            key,
            error,
        )

        logger.warning(f"Recorded failure for operation {operation_id}: {error}")

    def _update_operation_failure(
        self,
        key: str,
        error: str,
    ) -> None:
        """Update operation with failure information (synchronous helper).

        Args:
            key: Redis key for operation
            error: Error message
        """
        operation_json = self.client.get(key)
        if not operation_json:
            logger.warning(f"Operation not found in ledger: {key}")
            return

        operation_dict = json.loads(operation_json)
        operation_dict["attempts"] = operation_dict.get("attempts", 0) + 1
        operation_dict["last_error"] = error
        operation_dict["updated_at"] = datetime.now(UTC).isoformat()

        self.client.set(key, json.dumps(operation_dict))

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
        if not operation_id:
            raise ValueError(_OPERATION_ID_REQUIRED)

        key = self._operation_key(operation_id)

        operation_json = await asyncio.to_thread(self.client.get, key)

        if not operation_json:
            return None

        try:
            operation_dict = json.loads(operation_json)
            return DualWriteOperationMapper.from_dict(operation_dict)
        except ValueError as e:
            # Invalid operation data (e.g., invalid timestamp format)
            logger.warning(f"Invalid operation data for {operation_id}: {e}")
            return None

    async def list_pending_operations(
        self,
        limit: int = 100,
    ) -> list[DualWriteOperation]:
        """List all PENDING operations in the ledger.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of PENDING DualWriteOperation entities

        Raises:
            ValueError: If limit is invalid
            Exception: If storage operation fails
        """
        if limit <= 0:
            raise ValueError("limit must be positive")

        pending_set_key = self._pending_set_key()

        # Get operation IDs from pending set
        operation_ids = await asyncio.to_thread(
            self.client.smembers, pending_set_key
        )

        if not operation_ids:
            return []

        # Limit results
        operation_ids_list = list(operation_ids)[:limit]

        # Retrieve operations
        operations: list[DualWriteOperation] = []
        for op_id in operation_ids_list:
            operation = await self.get_operation(op_id)
            if operation and operation.status == DualWriteStatus.PENDING:
                operations.append(operation)

        return operations

    async def list_old_pending_operations(
        self,
        age_seconds: float,
        limit: int = 100,
    ) -> list[DualWriteOperation]:
        """List PENDING operations older than specified age.

        Args:
            age_seconds: Minimum age in seconds (operations older than this)
            limit: Maximum number of operations to return

        Returns:
            List of PENDING DualWriteOperation entities older than age_seconds

        Raises:
            ValueError: If age_seconds is negative or limit is invalid
            Exception: If storage operation fails
        """
        if age_seconds < 0:
            raise ValueError("age_seconds cannot be negative")

        if limit <= 0:
            raise ValueError("limit must be positive")

        # Get all pending operations first
        all_pending = await self.list_pending_operations(limit=1000)

        if not all_pending:
            return []

        # Calculate cutoff time
        cutoff_time = datetime.now(UTC).timestamp() - age_seconds

        # Filter by age (check created_at)
        old_operations: list[DualWriteOperation] = []
        for operation in all_pending:
            try:
                # Parse created_at timestamp
                created_timestamp = datetime.fromisoformat(
                    operation.created_at.replace("Z", "+00:00")
                ).timestamp()

                # Check if operation is older than cutoff
                if created_timestamp < cutoff_time:
                    old_operations.append(operation)

                    # Limit results
                    if len(old_operations) >= limit:
                        break
            except (ValueError, AttributeError) as e:
                logger.warning(
                    f"Invalid timestamp format for operation {operation.operation_id}: {e}"
                )
                continue

        return old_operations
