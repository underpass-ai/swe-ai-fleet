"""Valkey (Redis-compatible) adapter for IdempotencyPort.

Provides persistent idempotency tracking using Valkey:
- Atomic operations for state transitions
- TTL support for stale detection
- Efficient key-based lookups

Following Hexagonal Architecture:
- This is an ADAPTER (infrastructure implementation)
- Implements IdempotencyPort (application port)
- Uses Valkey for persistence (external dependency)
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

import valkey  # Valkey is Redis-compatible (synchronous client)

from core.shared.idempotency.idempotency_port import IdempotencyPort
from core.shared.idempotency.idempotency_state import IdempotencyState

logger = logging.getLogger(__name__)


class ValkeyIdempotencyAdapter(IdempotencyPort):
    """Valkey adapter for persistent idempotency tracking.

    Storage Strategy:
    - Key format: idempotency:{idempotency_key}
    - Value: JSON with state and timestamp
    - TTL: Set on IN_PROGRESS to prevent stale locks
    - COMPLETED: Optional TTL (default: keep forever)

    Data Model:
    - idempotency:{key} → {"state": "IN_PROGRESS", "timestamp": "2025-01-01T00:00:00Z"}

    Operations:
    - check_status: GET key → parse JSON → return state
    - mark_in_progress: SETNX with TTL (atomic)
    - mark_completed: SET key (overwrite)
    - is_stale: GET key → check timestamp vs max_age
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        decode_responses: bool = True,
    ):
        """Initialize Valkey idempotency adapter.

        Args:
            host: Valkey host
            port: Valkey port
            db: Valkey database number
            decode_responses: Whether to decode responses as strings
        """
        self._host = host
        self._port = port
        self._db = db
        self._decode_responses = decode_responses

        # Create Valkey client (synchronous)
        self._client = valkey.Valkey(
            host=host,
            port=port,
            db=db,
            decode_responses=decode_responses,
        )

        # Test connection
        try:
            self._client.ping()
            logger.info(
                f"Valkey idempotency adapter initialized: {host}:{port}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Valkey: {e}")
            raise RuntimeError(f"Valkey connection failed: {e}") from e

    def close(self) -> None:
        """Close Valkey connection."""
        self._client.close()
        logger.info("Valkey idempotency adapter connection closed")

    def _key(self, idempotency_key: str) -> str:
        """Generate Valkey key for idempotency tracking.

        Args:
            idempotency_key: Idempotency key

        Returns:
            Valkey key string
        """
        return f"idempotency:{idempotency_key}"

    def _serialize_state(
        self,
        state: IdempotencyState,
        timestamp: str | None = None,
    ) -> str:
        """Serialize idempotency state to JSON.

        Args:
            state: Idempotency state
            timestamp: ISO 8601 timestamp (default: current UTC)

        Returns:
            JSON string
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        data = {
            "state": state.value,
            "timestamp": timestamp,
        }
        return json.dumps(data)

    def _deserialize_state(self, json_str: str) -> tuple[IdempotencyState, str]:
        """Deserialize idempotency state from JSON.

        Args:
            json_str: JSON string

        Returns:
            Tuple of (IdempotencyState, timestamp)

        Raises:
            ValueError: If JSON is invalid or missing required fields
        """
        data = json.loads(json_str)
        state_str = data.get("state")
        timestamp = data.get("timestamp", "")

        if not state_str:
            raise ValueError("Missing 'state' field in idempotency data")

        try:
            state = IdempotencyState(state_str)
        except ValueError:
            raise ValueError(f"Invalid state: {state_str}") from None

        return state, timestamp

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
        if not idempotency_key:
            raise ValueError("idempotency_key cannot be empty")

        key = self._key(idempotency_key)

        try:
            json_str = await asyncio.to_thread(self._client.get, key)
            if json_str is None:
                return None

            state, _ = self._deserialize_state(json_str)
            return state

        except Exception as e:
            logger.error(
                f"Failed to check idempotency status for {idempotency_key}: {e}",
                exc_info=True,
            )
            raise

    async def mark_in_progress(
        self,
        idempotency_key: str,
        ttl_seconds: int,
    ) -> bool:
        """Mark an idempotency key as IN_PROGRESS (atomic operation).

        Uses SETNX (SET if Not eXists) to atomically:
        - Set state to IN_PROGRESS if key doesn't exist
        - Return False if key already exists (already processed or in progress)

        Args:
            idempotency_key: Unique key for the operation
            ttl_seconds: Time-to-live in seconds (for stale detection)

        Returns:
            True if successfully marked IN_PROGRESS, False if already exists

        Raises:
            ValueError: If idempotency_key is empty or ttl_seconds is invalid
            Exception: If storage operation fails
        """
        if not idempotency_key:
            raise ValueError("idempotency_key cannot be empty")

        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        key = self._key(idempotency_key)
        value = self._serialize_state(IdempotencyState.IN_PROGRESS)

        try:
            # SETNX: Set if not exists (atomic)
            # Returns True if key was set, False if key already exists
            result = await asyncio.to_thread(
                self._client.set,
                key,
                value,
                ex=ttl_seconds,
                nx=True,  # Only set if not exists
            )

            if result:
                logger.debug(
                    f"Marked idempotency key as IN_PROGRESS: {idempotency_key[:16]}..."
                )
                return True

            # Key already exists - check current state
            current_state = await self.check_status(idempotency_key)
            if current_state == IdempotencyState.COMPLETED:
                logger.debug(
                    f"Idempotency key already COMPLETED: {idempotency_key[:16]}..."
                )
            elif current_state == IdempotencyState.IN_PROGRESS:
                logger.debug(
                    f"Idempotency key already IN_PROGRESS: {idempotency_key[:16]}..."
                )

            return False

        except Exception as e:
            logger.error(
                f"Failed to mark idempotency key as IN_PROGRESS: {idempotency_key[:16]}...: {e}",
                exc_info=True,
            )
            raise

    async def mark_completed(
        self,
        idempotency_key: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """Mark an idempotency key as COMPLETED.

        Overwrites any existing state. This should only be called
        after successful processing.

        Args:
            idempotency_key: Unique key for the operation
            ttl_seconds: Optional TTL for completed state (default: keep forever)

        Raises:
            ValueError: If idempotency_key is empty
            Exception: If storage operation fails
        """
        if not idempotency_key:
            raise ValueError("idempotency_key cannot be empty")

        key = self._key(idempotency_key)
        value = self._serialize_state(IdempotencyState.COMPLETED)

        try:
            if ttl_seconds is not None:
                await asyncio.to_thread(
                    self._client.set,
                    key,
                    value,
                    ex=ttl_seconds,
                )
            else:
                # Keep forever (no TTL)
                await asyncio.to_thread(self._client.set, key, value)

            logger.debug(
                f"Marked idempotency key as COMPLETED: {idempotency_key[:16]}..."
            )

        except Exception as e:
            logger.error(
                f"Failed to mark idempotency key as COMPLETED: {idempotency_key[:16]}...: {e}",
                exc_info=True,
            )
            raise

    async def is_stale(
        self,
        idempotency_key: str,
        max_age_seconds: int,
    ) -> bool:
        """Check if an IN_PROGRESS state is stale (exceeded max age).

        Args:
            idempotency_key: Unique key for the operation
            max_age_seconds: Maximum age in seconds before considered stale

        Returns:
            True if IN_PROGRESS and stale, False otherwise

        Raises:
            ValueError: If idempotency_key is empty or max_age_seconds is invalid
            Exception: If storage operation fails
        """
        if not idempotency_key:
            raise ValueError("idempotency_key cannot be empty")

        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")

        key = self._key(idempotency_key)

        try:
            json_str = await asyncio.to_thread(self._client.get, key)
            if json_str is None:
                return False  # Key doesn't exist, not stale

            state, timestamp_str = self._deserialize_state(json_str)

            # Only check staleness for IN_PROGRESS states
            if state != IdempotencyState.IN_PROGRESS:
                return False

            # Parse timestamp and check age
            try:
                timestamp = datetime.fromisoformat(
                    timestamp_str.replace("Z", "+00:00")
                )
                now = datetime.now(timezone.utc)
                age_seconds = (now - timestamp).total_seconds()

                is_stale = age_seconds > max_age_seconds

                if is_stale:
                    logger.warning(
                        f"Idempotency key is stale (age: {age_seconds:.1f}s > max: {max_age_seconds}s): {idempotency_key[:16]}..."
                    )

                return is_stale

            except (ValueError, AttributeError) as e:
                logger.error(
                    f"Invalid timestamp format in idempotency data: {timestamp_str}: {e}"
                )
                # If timestamp is invalid, consider it stale (safer to retry)
                return True

        except Exception as e:
            logger.error(
                f"Failed to check staleness for idempotency key: {idempotency_key[:16]}...: {e}",
                exc_info=True,
            )
            raise
