"""Idempotency port for persistent message deduplication.

Following Hexagonal Architecture:
- This is a PORT (interface) in the application layer
- Infrastructure adapters implement this port
- Use cases and consumers depend on this port, not concrete adapters
"""

from typing import Protocol

from core.shared.idempotency.idempotency_state import IdempotencyState


class IdempotencyPort(Protocol):
    """Port for idempotency gate operations.

    Provides persistent deduplication for message processing:
    - Check if a message has already been processed (COMPLETED)
    - Mark message as IN_PROGRESS when processing starts
    - Mark message as COMPLETED when processing succeeds
    - Detect stale IN_PROGRESS states (for recovery)

    Following Hexagonal Architecture:
    - This is a PORT (interface)
    - Infrastructure provides ADAPTERS (ValkeyIdempotencyAdapter, etc.)
    - Application depends on PORT, not concrete implementation
    """

    async def check_status(
        self,
        idempotency_key: str,
    ) -> IdempotencyState | None:
        """Check the current status of an idempotency key.

        Args:
            idempotency_key: Unique key for the operation

        Returns:
            IdempotencyState if key exists, None if not found

        Raises:
            Exception: If storage operation fails
        """
        ...

    async def mark_in_progress(
        self,
        idempotency_key: str,
        ttl_seconds: int,
    ) -> bool:
        """Mark an idempotency key as IN_PROGRESS.

        This is an atomic operation that:
        - Sets state to IN_PROGRESS if key doesn't exist or is PENDING
        - Returns False if key is already IN_PROGRESS or COMPLETED
        - Sets TTL to prevent stale locks

        Args:
            idempotency_key: Unique key for the operation
            ttl_seconds: Time-to-live in seconds (for stale detection)

        Returns:
            True if successfully marked IN_PROGRESS, False if already processed

        Raises:
            Exception: If storage operation fails
        """
        ...

    async def mark_completed(
        self,
        idempotency_key: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """Mark an idempotency key as COMPLETED.

        This should only be called after successful processing.
        The key will be kept to prevent redelivery from re-executing.

        Args:
            idempotency_key: Unique key for the operation
            ttl_seconds: Optional TTL for completed state (default: keep forever)

        Raises:
            Exception: If storage operation fails
        """
        ...

    async def is_stale(
        self,
        idempotency_key: str,
        max_age_seconds: int,
    ) -> bool:
        """Check if an IN_PROGRESS state is stale (exceeded max age).

        Used for recovery: if a handler crashed, the IN_PROGRESS state
        may be stale and should be cleared to allow retry.

        Args:
            idempotency_key: Unique key for the operation
            max_age_seconds: Maximum age in seconds before considered stale

        Returns:
            True if IN_PROGRESS and stale, False otherwise

        Raises:
            Exception: If storage operation fails
        """
        ...
